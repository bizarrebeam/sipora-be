from rest_framework import serializers
from .models import LaporanKerusakan, FotoBuktiPendukung, RiwayatStatusLaporan
from akun.models import Pengguna
from datetime import datetime, date as _date


class FotoBuktiSerializer(serializers.ModelSerializer):
    class Meta:
        model = FotoBuktiPendukung
        fields = ['id', 'foto', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']


class PelaporSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pengguna
        fields = ['id', 'username', 'nama_lengkap', 'role']


class RiwayatStatusSerializer(serializers.ModelSerializer):
    diubah_oleh_nama = serializers.SerializerMethodField()

    class Meta:
        model = RiwayatStatusLaporan
        fields = ['id', 'status', 'catatan', 'diubah_oleh_nama', 'waktu']
        read_only_fields = ['id', 'status', 'catatan', 'diubah_oleh_nama', 'waktu']

    def get_diubah_oleh_nama(self, obj):
        if obj.diubah_oleh:
            return obj.diubah_oleh.nama_lengkap or obj.diubah_oleh.username
        return 'Sistem'


class LaporanKerusakanSerializer(serializers.ModelSerializer):
    foto_bukti = FotoBuktiSerializer(many=True, read_only=True)
    pelapor_info = serializers.SerializerMethodField()
    pengirim_username = serializers.SerializerMethodField()
    nama_lengkap = serializers.SerializerMethodField()
    kelas_pengirim = serializers.SerializerMethodField()
    foto_pendukung = serializers.SerializerMethodField()
    riwayat_status = RiwayatStatusSerializer(many=True, read_only=True)

    class Meta:
        model = LaporanKerusakan
        fields = [
            'id', 'no_laporan', 'judul', 'deskripsi', 'lokasi',
            'tanggal_kejadian', 'status', 'catatan_admin',
            'anonimitas', 'pelapor_info', 'pengirim_username', 'nama_lengkap',
            'kelas_pengirim', 'tanggal_laporan', 'updated_at',
            'foto_bukti', 'foto_pendukung', 'riwayat_status'
        ]
        read_only_fields = [
            'id', 'no_laporan', 'tanggal_laporan', 'updated_at'
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

    def get_foto_pendukung(self, obj):
        request = self.context.get('request')
        foto_list = []
        for foto in obj.foto_bukti.all():
            if foto.foto and hasattr(foto.foto, 'url'):
                url = request.build_absolute_uri(foto.foto.url) if request else foto.foto.url
                foto_list.append(url)
        return foto_list if foto_list else None


class CreateLaporanKerusakanSerializer(serializers.ModelSerializer):
    foto_bukti = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
        max_length=5
    )
    tanggal_kejadian = serializers.CharField()
    
    class Meta:
        model = LaporanKerusakan
        fields = [
            'judul', 'deskripsi', 'lokasi', 'tanggal_kejadian',
            'anonimitas', 'foto_bukti'
        ]
    
    def validate_foto_bukti(self, value):
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
        errors = {}

        if not attrs.get('judul') or not str(attrs.get('judul')).strip():
            errors['judul'] = 'Judul wajib diisi'

        if not attrs.get('deskripsi') or not str(attrs.get('deskripsi')).strip():
            errors['deskripsi'] = 'Deskripsi wajib diisi'

        if not attrs.get('lokasi') or not str(attrs.get('lokasi')).strip():
            errors['lokasi'] = 'Lokasi wajib diisi'

        t = attrs.get('tanggal_kejadian')
        if not t:
            errors['tanggal_kejadian'] = 'Tanggal wajib diisi'
        else:
            parsed = None
            if isinstance(t, _date):
                parsed = t
            else:
                for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
                    try:
                        parsed = datetime.strptime(str(t), fmt).date()
                        break
                    except Exception:
                        parsed = None

            if not parsed:
                errors['tanggal_kejadian'] = 'Format tanggal tidak valid'
            else:
                if parsed > datetime.now().date():
                    errors['tanggal_kejadian'] = 'Tanggal kejadian tidak boleh lebih dari hari ini'
                else:
                    attrs['tanggal_kejadian'] = parsed

        if errors:
            raise serializers.ValidationError(errors)

        return attrs
    
    def create(self, validated_data):
        foto_bukti_list = validated_data.pop('foto_bukti', [])
        pelapor = self.context['request'].user
        
        laporan = LaporanKerusakan.objects.create(
            pelapor=pelapor,
            **validated_data
        )
        
        for foto in foto_bukti_list:
            FotoBuktiPendukung.objects.create(
                laporan=laporan,
                foto=foto
            )

        # Create initial riwayat status
        RiwayatStatusLaporan.objects.create(
            laporan=laporan,
            status='menunggu',
            catatan='Laporan berhasil dibuat',
            diubah_oleh=pelapor
        )

        return laporan
