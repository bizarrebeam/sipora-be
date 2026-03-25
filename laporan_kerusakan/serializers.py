from rest_framework import serializers
from .models import LaporanKerusakan, FotoBuktiPendukung, RiwayatStatusLaporan
from akun.models import Pengguna
from datetime import datetime, date as _date
import re


MAX_FILES = 5
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024
MAX_TOTAL_SIZE_BYTES = MAX_FILES * MAX_FILE_SIZE_BYTES
MIN_REPORT_DATE = _date(2000, 1, 1)
FORBIDDEN_SPECIAL_CHARS_REGEX = re.compile(r'[@!~`#$%^*+]')


def normalize_text(value):
    if value is None:
        return ''
    text = str(value)
    text = re.sub(r'[\u200B-\u200D\uFEFF]', '', text)
    return text.strip()


def validate_text_field(field_name, value, min_length=None, max_length=None):
    normalized = normalize_text(value)

    if not normalized:
        return f'{field_name} wajib diisi'
    if FORBIDDEN_SPECIAL_CHARS_REGEX.search(normalized):
        return f'{field_name} mengandung karakter yang tidak diperbolehkan'
    if min_length and len(normalized) < min_length:
        return f'{field_name} minimal {min_length} karakter'
    if max_length and len(normalized) > max_length:
        return f'{field_name} maksimal {max_length} karakter'

    return None


def validate_uploaded_files(file_list):
    if len(file_list) > MAX_FILES:
        raise serializers.ValidationError(f'Maksimal {MAX_FILES} foto')

    allowed_types = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp']
    total_size = 0
    signatures = set()

    for foto in file_list:
        signature = f'{foto.name}|{foto.size}'
        if signature in signatures:
            raise serializers.ValidationError(f'File duplikat terdeteksi: {foto.name}')
        signatures.add(signature)

        if foto.size == 0:
            raise serializers.ValidationError(f'File {foto.name} kosong')

        if foto.size > MAX_FILE_SIZE_BYTES:
            raise serializers.ValidationError(
                f'Ukuran file {foto.name} maksimal 5 MB'
            )

        content_type = foto.content_type
        if content_type not in allowed_types:
            raise serializers.ValidationError(
                f'Format file {foto.name} tidak didukung. '
                'Hanya PNG, JPG, JPEG, dan WEBP yang diperbolehkan.'
            )

        total_size += foto.size

    if total_size > MAX_TOTAL_SIZE_BYTES:
        raise serializers.ValidationError('Total ukuran semua foto maksimal 25 MB')

    return file_list


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
    foto_pendukung = serializers.SerializerMethodField()
    riwayat_status = RiwayatStatusSerializer(many=True, read_only=True)
    akun_terverifikasi = serializers.SerializerMethodField()

    class Meta:
        model = LaporanKerusakan
        fields = [
            'id', 'no_laporan', 'judul', 'deskripsi', 'lokasi',
            'tanggal_kejadian', 'status', 'catatan_admin',
            'anonimitas', 'pelapor_info', 'pengirim_username', 'nama_lengkap',
            'akun_terverifikasi', 'tanggal_laporan', 'updated_at', 'foto_bukti',
            'foto_pendukung', 'riwayat_status'
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
            'kelas': obj.pelapor.kelas or '-',
            'role': obj.pelapor.role,
            'akun_terverifikasi': obj.pelapor.is_verified if obj.pelapor else False
        }
    
    def get_pengirim_username(self, obj):
        if obj.anonimitas:
            return None
        return obj.pelapor.username if obj.pelapor else None

    def get_akun_terverifikasi(self, obj):
        if obj.anonimitas or not obj.pelapor:
            return None
        return obj.pelapor.is_verified
    
    def get_nama_lengkap(self, obj):
        if obj.anonimitas:
            kelas = obj.pelapor.kelas or '-'
            return f'Anonim dari Kelas {kelas}'
        return obj.pelapor.nama_lengkap if obj.pelapor else None
    
    def get_foto_pendukung(self, obj):
        request = self.context.get('request')
        foto_list = []
        for foto in obj.foto_bukti.all():
            if foto.foto and hasattr(foto.foto, 'url'):
                url = request.build_absolute_uri(foto.foto.url) if request else foto.foto.url
                foto_list.append(url)
        return foto_list if foto_list else None


class LaporanKerusakanListSerializer(serializers.ModelSerializer):
    """Lean serializer for list view - no foto_bukti, no riwayat_status to avoid N+1"""
    pelapor_info = serializers.SerializerMethodField()
    nama_lengkap = serializers.SerializerMethodField()
    akun_terverifikasi = serializers.SerializerMethodField()

    class Meta:
        model = LaporanKerusakan
        fields = [
            'id', 'no_laporan', 'judul', 'lokasi',
            'tanggal_kejadian', 'status', 'anonimitas',
            'pelapor_info', 'nama_lengkap', 'akun_terverifikasi',
            'tanggal_laporan', 'updated_at',
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
            'kelas': obj.pelapor.kelas or '-',
            'role': obj.pelapor.role,
            'akun_terverifikasi': obj.pelapor.is_verified if obj.pelapor else False
        }

    def get_nama_lengkap(self, obj):
        if obj.anonimitas:
            kelas = obj.pelapor.kelas or '-'
            return f'Anonim dari Kelas {kelas}'
        return obj.pelapor.nama_lengkap if obj.pelapor else None

    def get_akun_terverifikasi(self, obj):
        if obj.anonimitas or not obj.pelapor:
            return None
        return obj.pelapor.is_verified


class CreateLaporanKerusakanSerializer(serializers.ModelSerializer):
    foto_bukti = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
        max_length=MAX_FILES
    )
    tanggal_kejadian = serializers.CharField()
    
    class Meta:
        model = LaporanKerusakan
        fields = [
            'judul', 'deskripsi', 'lokasi', 'tanggal_kejadian',
            'anonimitas', 'foto_bukti'
        ]
    
    def validate_foto_bukti(self, value):
        return validate_uploaded_files(value)

    def validate(self, attrs):
        errors = {}

        judul_error = validate_text_field('Judul', attrs.get('judul'), min_length=5, max_length=120)
        deskripsi_error = validate_text_field('Deskripsi', attrs.get('deskripsi'), min_length=20, max_length=2000)
        lokasi_error = validate_text_field('Lokasi', attrs.get('lokasi'), min_length=3, max_length=255)

        if judul_error:
            errors['judul'] = judul_error
        if deskripsi_error:
            errors['deskripsi'] = deskripsi_error
        if lokasi_error:
            errors['lokasi'] = lokasi_error

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
                if parsed < MIN_REPORT_DATE:
                    errors['tanggal_kejadian'] = 'Tanggal kejadian tidak valid'
                elif parsed > datetime.now().date():
                    errors['tanggal_kejadian'] = 'Tanggal kejadian tidak boleh lebih dari hari ini'
                else:
                    attrs['tanggal_kejadian'] = parsed

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
        
        laporan = LaporanKerusakan.objects.create(
            pelapor=pelapor,
            **validated_data
        )
        
        for foto in foto_bukti_list:
            FotoBuktiPendukung.objects.create(
                laporan=laporan,
                foto=foto
            )

        RiwayatStatusLaporan.objects.create(
            laporan=laporan,
            status='menunggu',
            catatan='Laporan berhasil dibuat',
            diubah_oleh=pelapor
        )

        return laporan


class EditLaporanKerusakanSerializer(serializers.ModelSerializer):
    foto_bukti = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
        max_length=MAX_FILES
    )
    tanggal_kejadian = serializers.CharField()

    class Meta:
        model = LaporanKerusakan
        fields = [
            'judul', 'deskripsi', 'lokasi', 'tanggal_kejadian',
            'anonimitas', 'foto_bukti'
        ]

    def validate_foto_bukti(self, value):
        return validate_uploaded_files(value)

    def validate(self, attrs):
        errors = {}

        judul_error = validate_text_field('Judul', attrs.get('judul'), min_length=5, max_length=120)
        deskripsi_error = validate_text_field('Deskripsi', attrs.get('deskripsi'), min_length=20, max_length=2000)
        lokasi_error = validate_text_field('Lokasi', attrs.get('lokasi'), min_length=3, max_length=255)

        if judul_error:
            errors['judul'] = judul_error
        if deskripsi_error:
            errors['deskripsi'] = deskripsi_error
        if lokasi_error:
            errors['lokasi'] = lokasi_error

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
                if parsed < MIN_REPORT_DATE:
                    errors['tanggal_kejadian'] = 'Tanggal kejadian tidak valid'
                elif parsed > datetime.now().date():
                    errors['tanggal_kejadian'] = 'Tanggal kejadian tidak boleh lebih dari hari ini'
                else:
                    attrs['tanggal_kejadian'] = parsed

        if 'judul' in attrs:
            attrs['judul'] = normalize_text(attrs.get('judul'))
        if 'deskripsi' in attrs:
            attrs['deskripsi'] = normalize_text(attrs.get('deskripsi'))
        if 'lokasi' in attrs:
            attrs['lokasi'] = normalize_text(attrs.get('lokasi'))

        if errors:
            raise serializers.ValidationError(errors)

        return attrs

    def update(self, instance, validated_data):
        foto_bukti_list = validated_data.pop('foto_bukti', [])

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        for foto in foto_bukti_list:
            FotoBuktiPendukung.objects.create(
                laporan=instance,
                foto=foto
            )

        return instance


class CancelLaporanKerusakanSerializer(serializers.Serializer):
    alasan = serializers.CharField()

    def validate_alasan(self, value):
        if not value or not str(value).strip():
            raise serializers.ValidationError('Alasan pembatalan wajib diisi')
        if len(value.strip()) < 50:
            raise serializers.ValidationError('Alasan pembatalan wajib minimal 50 karakter')
        return value.strip()
