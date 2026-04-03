"""
Serializers module for the laporan_bullying application.

This module provides definitions for Django REST Framework (DRF) serializers
used to validate, serialize, and deserialize data related to bullying reports,
photos, and status histories.
"""

from rest_framework import serializers
from datetime import datetime, date
from .models import LaporanBullying, FotoBuktiBullying, RiwayatStatusBullying
import re

def sanitize_text(value):
    """
    Sanitize user input to prevent XSS and other injection attacks by 
    removing HTML tags and potentially dangerous characters from a string.
    
    Args:
        value (str): The raw text string inputted by the user.
        
    Returns:
        str: The sanitized text string.
    """
    # Delete script tags and HTML elements
    value = re.sub(r'<.*?>', '', value)
    # Delete dangerous characters
    value = re.sub(r'[<>\"\'%;()&+]', '', value)

    return value.strip()

class FotoBuktiBullyingSerializer(serializers.ModelSerializer):
    """
    Serializer for handling bullying report evidence photos (Foto Bukti).
    Converts model instances to JSON formats and automatically builds
    absolute URLs for image access.
    """
    foto = serializers.SerializerMethodField()

    class Meta:
        model = FotoBuktiBullying
        fields = ['id', 'foto', 'uploaded_at']

    def get_foto(self, obj):
        """
        Retrieves the absolute URL of the uploaded photo.
        
        Args:
            obj (FotoBuktiBullying): The photo instance being serialized.
            
        Returns:
            str: The absolute or relative URL string to the image file.
        """
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.foto.url)
        return obj.foto.url

class RiwayatStatusBullyingSerializer(serializers.ModelSerializer):
    """
    Serializer for the history of bullying report statuses (Riwayat Status).
    Tracks status changes, notes (catatan), and the user who modified the status.
    Respects anonymity settings when displaying the user's name.
    """
    user = serializers.SerializerMethodField()
    
    class Meta:
        model = RiwayatStatusBullying
        fields = [
            'status',
            'catatan',
            'diubah_oleh',
            'created_at',
            'user'
        ]

    def get_user(self, obj):
        """
        Retrieves formatted data for the user who modified the status.
        If the report is set to anonymous and the modifier is the reporter themselves,
        the name is masked as 'Pengguna Anonim' (Anonymous User).
        
        Args:
            obj (RiwayatStatusBullying): The status history instance.
            
        Returns:
            dict or None: A dictionary containing the user's ID and Name, 
                          or None if no user is specified.
        """
        if obj.diubah_oleh:
            if obj.laporan.anonimitas and obj.diubah_oleh == obj.laporan.pelapor:
                return {
                    'id': obj.diubah_oleh.id,
                    'nama': 'Pengguna Anonim'
                }
            return {
                'id': obj.diubah_oleh.id,
                'nama': getattr(obj.diubah_oleh, 'nama_lengkap', 'Admin')
            }
        return None

class LaporanBullyingCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer to handle creating and updating bullying reports.
    Performs field-level validations and sanitization on text-based
    fields to enforce business logic and security.
    """
    class Meta:
        model = LaporanBullying
        fields = [
            'id',
            'judul',
            'deskripsi',
            'lokasi',
            'tanggal_kejadian',
            'waktu_kejadian',
            'jenis_bullying',
            'anonimitas'
        ]
        read_only_fields = ['id']

    def validate_judul(self, value):
        """
        Sanitize and validate the title (judul) field.
        
        Raises:
            ValidationError: If the title is empty after sanitization or exceeds 255 characters.
        """
        value = sanitize_text(value)

        if not value:
            raise serializers.ValidationError("Judul wajib diisi")

        if len(value) > 255:
            raise serializers.ValidationError("Judul terlalu panjang")

        return value

    def validate_deskripsi(self, value):
        """
        Sanitize and validate the description (deskripsi) field.
        
        Raises:
            ValidationError: If the description is empty or contains less than 50 characters.
        """
        value = sanitize_text(value)

        if not value:
            raise serializers.ValidationError("Deskripsi wajib diisi")
            
        if len(value) < 50:
            raise serializers.ValidationError("Deskripsi wajib diisi minimal 50 karakter")

        return value

    def validate_lokasi(self, value):
        """
        Sanitize and validate the location (lokasi) field.
        
        Raises:
            ValidationError: If the location is empty after sanitization.
        """
        value = sanitize_text(value)

        if not value:
            raise serializers.ValidationError("Lokasi wajib diisi")

        return value

    def validate_tanggal_kejadian(self, value):
        """
        Validate the incident date (tanggal_kejadian) field.
        
        Raises:
            ValidationError: If the event date is set in the future.
        """
        if value > date.today():
            raise serializers.ValidationError("Tanggal kejadian tidak boleh lebih dari hari ini")
        return value

class LaporanBullyingListSerializer(serializers.ModelSerializer):
    """
    Serializer used for retrieving compact lists of bullying reports.
    
    Limits the fetched data to essential fields needed for list displays
    such as tables or cards, resolving relationships and computed fields efficiently.
    """
    nama_pengirim = serializers.SerializerMethodField()
    akun_terverifikasi = serializers.BooleanField(source='pelapor.is_verified', read_only=True)
    kelas = serializers.SerializerMethodField()

    class Meta:
        model = LaporanBullying
        fields = [
            'id',
            'no_laporan',
            'judul',
            'tanggal_kejadian',
            'waktu_kejadian',
            'lokasi',
            'status',
            'nama_pengirim',
            'kelas',
            'akun_terverifikasi',
            'tanggal_laporan',
            'jenis_bullying'
        ]

    def get_nama_pengirim(self, obj):
        """
        Retrieves the sender's formatted name depending on anonymity settings.
        
        Returns:
            str: Reporter's name or 'Anonim' if anonymity is requested.
        """
        return obj.get_nama_pelapor()

    def get_kelas(self, obj):
        """
        Retrieves the reporter's class (kelas).
        
        Returns:
            str or None: The class of the user making the report.
        """
        return getattr(obj.pelapor, 'kelas', None)

class LaporanBullyingDetailSerializer(serializers.ModelSerializer):
    """
    Comprehensive serializer for detailed views of bullying reports.
    
    Nests related serializers (evidence photos and status history) and fetches
    complete user and report details, taking anonymity flags into account.
    """
    pelapor = serializers.IntegerField(source='pelapor.id', read_only=True)
    foto_bukti = FotoBuktiBullyingSerializer(many=True, read_only=True)
    nama_pengirim = serializers.SerializerMethodField()
    akun_terverifikasi = serializers.BooleanField(source='pelapor.is_verified', read_only=True)
    kelas = serializers.SerializerMethodField()
    riwayat_status = RiwayatStatusBullyingSerializer(many=True, read_only=True)

    class Meta:
        model = LaporanBullying
        fields = [
            'id',
            'pelapor',
            'no_laporan',
            'nama_pengirim',
            'kelas',
            'judul',
            'deskripsi',
            'lokasi',
            'tanggal_kejadian',
            'waktu_kejadian',
            'jenis_bullying',
            'status',
            'foto_bukti',
            'tanggal_laporan',
            'updated_at',
            'akun_terverifikasi',
            'riwayat_status'
        ]

    def get_nama_pengirim(self, obj):
        """
        Retrieves the formatted sender name honoring anonymity rules.
        """
        return obj.get_nama_pelapor()

    def get_kelas(self, obj):
        """
        Retrieves the reporter's class, masking it if the report is anonymous.
        
        Returns:
            str: 'Dirahasiakan' if anonymous, otherwise returns the class code.
        """
        if obj.anonimitas:
            return "Dirahasiakan"
        return getattr(obj.pelapor, 'kelas', None)

class CancelLaporanSerializer(serializers.Serializer):
    """
    Serializer specifically for report cancellation validation.
    
    Only acts to ensure the cancellation reason (alasan_pembatalan)
    meets the mandatory requirements.
    """
    alasan_pembatalan = serializers.CharField()

    def validate_alasan_pembatalan(self, value):
        """
        Validates the text provided as a cancellation reason.
        
        Raises:
            ValidationError: If the reason length is fewer than 50 characters.
        """
        if not value or len(value) < 50:
            raise serializers.ValidationError("Alasan pembatalan wajib diisi minimal 50 karakter")
        return value

