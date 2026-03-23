from rest_framework import serializers
from datetime import datetime, date
from .models import LaporanBullying, FotoBuktiBullying, RiwayatStatusBullying
import re

# Function for sanitize user input
def sanitize_text(value):
    # Delete script tag and dangerous character
    value = re.sub(r'<.*?>', '', value)
    value = re.sub(r'[<>\"\'%;()&+]', '', value)

    return value.strip()

# Serializer untuk foto bukti bullying
class FotoBuktiBullyingSerializer(serializers.ModelSerializer):
    foto = serializers.SerializerMethodField()

    class Meta:
        model = FotoBuktiBullying
        fields = ['id', 'foto', 'uploaded_at']

    def get_foto(self, obj):
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.foto.url)
        return obj.foto.url

class RiwayatStatusBullyingSerializer(serializers.ModelSerializer):
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
    class Meta:
        model = LaporanBullying
        fields = [
            'id',
            'judul',
            'deskripsi',
            'lokasi',
            'tanggal_kejadian',
            'jenis_bullying',
            'anonimitas'
        ]
        read_only_fields = ['id']

    def validate_judul(self, value):
        value = sanitize_text(value)

        if not value:
            raise serializers.ValidationError("Judul wajib diisi")

        if len(value) > 255:
            raise serializers.ValidationError("Judul terlalu panjang")

        return value

    def validate_deskripsi(self, value):
        value = sanitize_text(value)

        if not value:
            raise serializers.ValidationError("Deskripsi wajib diisi")
            
        if len(value) < 50:
            raise serializers.ValidationError("Deskripsi wajib diisi minimal 50 karakter")

        return value

    def validate_lokasi(self, value):
        value = sanitize_text(value)

        if not value:
            raise serializers.ValidationError("Lokasi wajib diisi")

        return value

    def validate_tanggal_kejadian(self, value):
        if value > date.today():
            raise serializers.ValidationError("Tanggal kejadian tidak boleh lebih dari hari ini")
        return value

class LaporanBullyingListSerializer(serializers.ModelSerializer):
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
            'lokasi',
            'status',
            'nama_pengirim',
            'kelas',
            'akun_terverifikasi',
            'tanggal_laporan'
        ]

    def get_nama_pengirim(self, obj):
        return obj.get_nama_pelapor()

    def get_kelas(self, obj):
        return getattr(obj.pelapor, 'kelas', None)

class LaporanBullyingDetailSerializer(serializers.ModelSerializer):
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
            'jenis_bullying',
            'status',
            'foto_bukti',
            'tanggal_laporan',
            'updated_at',
            'akun_terverifikasi',
            'riwayat_status'
        ]

    def get_nama_pengirim(self, obj):
        return obj.get_nama_pelapor()

    def get_kelas(self, obj):
        if obj.anonimitas:
            return "Dirahasiakan"
        return getattr(obj.pelapor, 'kelas', None)

class CancelLaporanSerializer(serializers.Serializer):
    alasan_pembatalan = serializers.CharField()

    def validate_alasan_pembatalan(self, value):
        if not value or len(value) < 50:
            raise serializers.ValidationError("Alasan pembatalan wajib diisi minimal 50 karakter")
        return value

