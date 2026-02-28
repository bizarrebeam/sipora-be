from rest_framework import serializers
from datetime import datetime, date
from .models import LaporanBullying, FotoBuktiBullying

# Serializer untuk foto bukti bullying
class FotoBuktiBullyingSerializer(serializers.ModelSerializer):
    class Meta:
        model = FotoBuktiBullying
        fields = ['id', 'foto', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']

class LaporanBullyingCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LaporanBullying
        fields = [
            'judul',
            'deskripsi',
            'lokasi',
            'tanggal_kejadian',
            'jenis_bullying',
            'anonimitas'
        ]

    def validate_judul(self, value):
        if not value:
            raise serializers.ValidationError("Judul wajib diisi")
        return value

    def validate_deskripsi(self, value):
        if not value:
            raise serializers.ValidationError("Deskripsi wajib diisi")
        return value

    def validate_lokasi(self, value):
        if not value:
            raise serializers.ValidationError("Lokasi wajib diisi")
        return value

    def validate_tanggal_kejadian(self, value):
        if value > date.today():
            raise serializers.ValidationError("Tanggal kejadian tidak boleh lebih dari hari ini")
        return value

class LaporanBullyingListSerializer(serializers.ModelSerializer):
    nama_pengirim = serializers.SerializerMethodField()
    akun_terverifikasi = serializers.SerializerMethodField()

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
            'akun_terverifikasi',
            'tanggal_laporan'
        ]

    def get_nama_pengirim(self, obj):
        return obj.get_nama_pelapor()

    def get_akun_terverifikasi(self, obj):
        return getattr(obj.pelapor, 'is_verified', False)

class LaporanBullyingDetailSerializer(serializers.ModelSerializer):
    foto_bukti = FotoBuktiBullyingSerializer(many=True, read_only=True)
    nama_pengirim = serializers.SerializerMethodField()
    akun_terverifikasi = serializers.SerializerMethodField()
    kelas_pengirim = serializers.SerializerMethodField()

    class Meta:
        model = LaporanBullying
        fields = [
            'id',
            'no_laporan',
            'nama_pengirim',
            'kelas_pengirim',
            'judul',
            'deskripsi',
            'lokasi',
            'tanggal_kejadian',
            'jenis_bullying',
            'status',
            'foto_bukti',
            'tanggal_laporan',
            'updated_at',
            'akun_terverifikasi'
        ]

    def get_nama_pengirim(self, obj):
        return obj.get_nama_pelapor()

    def get_kelas_pengirim(self, obj):
        return getattr(obj.pelapor, 'kelas', None)

    def get_akun_terverifikasi(self, obj):
        return getattr(obj.pelapor, 'is_verified', False)

class CancelLaporanSerializer(serializers.Serializer):
    alasan_pembatalan = serializers.CharField()

    def validate_alasan_pembatalan(self, value):
        if not value or len(value) < 50:
            raise serializers.ValidationError("Alasan pembatalan wajib diisi minimal 50 karakter")
        return value