"""
Serializers for the `aspirasi` application.

Includes lightweight list/detail serializers, helpers for input normalization
and validation, and the create serializer which handles image uploads and
related `FotoBuktiPendukung` creation.
"""

import re
from rest_framework import serializers
from .models import Aspirasi, FotoBuktiPendukung, RiwayatStatusDitandai
from akun.models import Pengguna
from datetime import datetime, date as _date


def normalize_text(value):
    """Normalize text input by removing zero-width chars and trimming spaces."""
    if value is None:
        return ''
    text = str(value)
    text = re.sub(r'[\u200B-\u200D\uFEFF]', '', text)
    return text.strip()


def validate_text_field(field_name, value, min_length=None, max_length=None):
    """Run common text validations used by title/description/location fields."""
    normalized = normalize_text(value)

    if not normalized:
        return f'{field_name} wajib diisi'
    if min_length and len(normalized) < min_length:
        return f'{field_name} minimal {min_length} karakter'
    if max_length and len(normalized) > max_length:
        return f'{field_name} maksimal {max_length} karakter'

    return None

class FotoBuktiSerializer(serializers.ModelSerializer):
    """Serializer for photo evidence attached to an `Aspirasi`.

    Read-only: `id` and `uploaded_at` are returned to clients.
    """
    class Meta:
        model = FotoBuktiPendukung
        fields = ['id', 'foto', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']


class PelaporSerializer(serializers.ModelSerializer):
    """Minimal serializer for the `Pengguna` who submitted an aspirasi."""
    class Meta:
        model = Pengguna
        fields = ['id', 'username', 'nama_lengkap', 'role']


class RiwayatStatusSerializer(serializers.ModelSerializer):
    """Serializer for `RiwayatStatusDitandai` entries (history of marks)."""
    diubah_oleh_nama = serializers.SerializerMethodField()

    class Meta:
        model = RiwayatStatusDitandai
        fields = ['id', 'status_ditandai', 'diubah_oleh_nama', 'waktu']
        read_only_fields = ['id', 'status_ditandai', 'diubah_oleh_nama', 'waktu']

    def get_diubah_oleh_nama(self, obj):
        if obj.diubah_oleh:
            return getattr(obj.diubah_oleh, 'nama_lengkap', None) or getattr(obj.diubah_oleh, 'username', 'Unknown')
        return 'Sistem'

"""
Detail Serializer
"""
class AspirasiSerializer(serializers.ModelSerializer):
    """Full-detail serializer for an `Aspirasi`.

    Provides related fields: `foto_bukti`, readable `pelapor_info`,
    public fields for anonymous display, and `riwayat_status` history.
    """
    foto_bukti = FotoBuktiSerializer(many=True, read_only=True)
    pelapor_info = serializers.SerializerMethodField()
    pengirim_username = serializers.SerializerMethodField()
    nama_lengkap = serializers.SerializerMethodField()
    kelas_pengirim = serializers.SerializerMethodField()
    akun_terverifikasi = serializers.SerializerMethodField()
    foto_pendukung = serializers.SerializerMethodField()
    riwayat_status = RiwayatStatusSerializer(many=True, read_only=True, source='riwayat_status_ditandai')

    class Meta:
        model = Aspirasi
        fields = [
            'id', 'no_laporan', 'judul', 'kategori', 'deskripsi','status_ditandai', 
            'anonimitas', 'pelapor_info', 'pengirim_username', 'nama_lengkap',
            'kelas_pengirim', 'akun_terverifikasi', 'tanggal_aspirasi', 'updated_at',
            'foto_bukti', 'foto_pendukung', 'riwayat_status'
        ]
        read_only_fields = [
            'id', 'no_laporan', 'tanggal_aspirasi', 'updated_at'
        ]
    
    def get_pelapor_info(self, obj):
        if obj.anonimitas:
            kelas = obj.pelapor.kelas or '-'
            return {
                'nama_lengkap': f'Anonim dari Kelas {kelas}',
                'kelas': kelas,
                'role': obj.pelapor.role
            }
        return {
            'id': str(obj.pelapor.id),
            'username': obj.pelapor.username,
            'nama_lengkap': obj.pelapor.nama_lengkap,
            'role': obj.pelapor.role
        }
    
    def get_pengirim_username(self, obj):
        if obj.anonimitas:
            return None
        return obj.pelapor.username if obj.pelapor else None
    
    def get_nama_lengkap(self, obj):
        if obj.anonimitas:
            kelas = obj.pelapor.kelas or '-'
            return f'Anonim dari Kelas {kelas}'
        return obj.pelapor.nama_lengkap if obj.pelapor else None
    
    def get_kelas_pengirim(self, obj):
        return obj.pelapor.kelas or '-' if obj.pelapor else '-'

    def get_akun_terverifikasi(self, obj):
        return getattr(obj.pelapor, 'is_verified', False)

    def get_foto_pendukung(self, obj):
        request = self.context.get('request')
        foto_list = []
        for foto in obj.foto_bukti.all():
            if foto.foto and hasattr(foto.foto, 'url'):
                url = foto.foto.url
                if not url.startswith('http') and request:
                    url = request.build_absolute_uri(url)
                foto_list.append(url)
        return foto_list if foto_list else None


"""
List Serializer
"""
class AspirasiListSerializer(serializers.ModelSerializer):
    """Lean serializer for list view - no foto_bukti, no riwayat_status to avoid N+1"""
    pelapor_info = serializers.SerializerMethodField()
    nama_lengkap = serializers.SerializerMethodField()
    akun_terverifikasi = serializers.SerializerMethodField()

    class Meta:
        model = Aspirasi
        fields = [
            'id', 'no_laporan', 'judul', 'kategori', 'status_ditandai',
            'anonimitas', 'pelapor_info', 'nama_lengkap',
            'akun_terverifikasi', 'tanggal_aspirasi', 'updated_at',
        ]
        read_only_fields = [
            'id', 'no_laporan', 'tanggal_aspirasi', 'updated_at'
        ]

    def get_pelapor_info(self, obj):
        if obj.anonimitas:
            kelas = obj.pelapor.kelas or '-'
            return {
                'nama_lengkap': f'Anonim dari Kelas {kelas}',
                'kelas': kelas,
                'role': obj.pelapor.role
            }
        return {
            'id': str(obj.pelapor.id),
            'username': obj.pelapor.username,
            'nama_lengkap': obj.pelapor.nama_lengkap,
            'role': obj.pelapor.role
        }

    def get_nama_lengkap(self, obj):
        if obj.anonimitas:
            kelas = obj.pelapor.kelas or '-'
            return f'Anonim dari Kelas {kelas}'
        return obj.pelapor.nama_lengkap if obj.pelapor else None

    def get_akun_terverifikasi(self, obj):
        return getattr(obj.pelapor, 'is_verified', False)


"""
Persist Aspirasi
"""
class CreateAspirasiSerializer(serializers.ModelSerializer):
    """Serializer used when creating an `Aspirasi`.

    Accepts `foto_bukti` as a list of images (max 5). Validates file size
    and type, runs text normalization and field validations, and on create
    persists `FotoBuktiPendukung` instances linked to the new aspirasi.
    """
    foto_bukti = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
        max_length=5
    )    
    class Meta:
        model = Aspirasi
        fields = [
            'judul', 'kategori', 'deskripsi',
            'anonimitas', 'foto_bukti'
        ]
    
    def validate_foto_bukti(self, value):
        # Validate Photos
        if len(value) > 5:
            raise serializers.ValidationError("Maksimal 5 foto")
        
        for foto in value:
            if foto.size > 5 * 1024 * 1024:  # 5MB
                raise serializers.ValidationError(
                    f"Ukuran file {foto.name} maksimal 5 MB"
                )
            
            allowed_types = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp']
            content_type = foto.content_type
            if content_type not in allowed_types:
                raise serializers.ValidationError(
                    f"Format file {foto.name} tidak didukung. "
                    "Hanya PNG, JPG, JPEG, dan WEBP yang diperbolehkan."
                )
        
        return value
    
    def validate(self, attrs):
        """Validate required fields, date constraints, and normalize text values."""
        errors = {}

        judul_error = validate_text_field('Judul', attrs.get('judul'), min_length=5, max_length=120)
        deskripsi_error = validate_text_field('Deskripsi', attrs.get('deskripsi'), min_length=50, max_length=2000)

        if judul_error:
            errors['judul'] = judul_error
        if deskripsi_error:
            errors['deskripsi'] = deskripsi_error

        if 'judul' in attrs:
            attrs['judul'] = normalize_text(attrs.get('judul'))
        if 'deskripsi' in attrs:
            attrs['deskripsi'] = normalize_text(attrs.get('deskripsi'))
        if 'lokasi' in attrs:
            attrs['lokasi'] = normalize_text(attrs.get('lokasi'))

        if errors:
            raise serializers.ValidationError(errors)

        return attrs

    
    def create(self, validated_data):
        foto_bukti_list = validated_data.pop('foto_bukti', [])
        pelapor = self.context['request'].user
        
        laporan = Aspirasi.objects.create(
            pelapor=pelapor,
            **validated_data
        )
        
        for foto in foto_bukti_list:
            FotoBuktiPendukung.objects.create(
                laporan=laporan,
                foto=foto
            )

        return laporan