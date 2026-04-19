"""
Serializers module for the laporan_kerusakan application.

Contains validation and data transformation logic for report creation,
editing, listing, detail retrieval, cancellation, attached photos, and
status history.
"""

import re
from datetime import datetime, date as _date

from rest_framework import serializers

from akun.models import Pengguna
from .models import LaporanKerusakan, FotoBuktiPendukung, RiwayatStatusLaporan


MAX_FILES = 5
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024
MAX_TOTAL_SIZE_BYTES = MAX_FILES * MAX_FILE_SIZE_BYTES
MIN_REPORT_DATE = _date(2000, 1, 1)
MIN_CANCEL_REASON_LENGTH = 50
MIN_REJECTION_REASON_LENGTH = 50
MIN_STATUS_NOTE_LENGTH = 50
FORBIDDEN_SPECIAL_CHARS_REGEX = re.compile(r'[@!~`#$%^*+]')


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
    if FORBIDDEN_SPECIAL_CHARS_REGEX.search(normalized):
        return f'{field_name} mengandung karakter yang tidak diperbolehkan'
    if min_length and len(normalized) < min_length:
        return f'{field_name} minimal {min_length} karakter'
    if max_length and len(normalized) > max_length:
        return f'{field_name} maksimal {max_length} karakter'

    return None


def validate_uploaded_files(file_list):
    """Validate evidence file count, size, duplication, and MIME type constraints."""
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
    """Serializer for evidence photo records attached to a report."""
    class Meta:
        model = FotoBuktiPendukung
        fields = ['id', 'foto', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']


class PelaporSerializer(serializers.ModelSerializer):
    """Serializer for basic reporter identity fields."""
    class Meta:
        model = Pengguna
        fields = ['id', 'username', 'nama_lengkap', 'role']


class RiwayatStatusSerializer(serializers.ModelSerializer):
    """Serializer for status history timeline entries."""
    diubah_oleh_nama = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()

    class Meta:
        model = RiwayatStatusLaporan
        fields = ['id', 'status', 'catatan', 'diubah_oleh_nama', 'waktu', 'user']
        read_only_fields = ['id', 'status', 'catatan', 'diubah_oleh_nama', 'waktu', 'user']

    def get_diubah_oleh_nama(self, obj):
        """Return display name of the user who changed status, or 'Sistem'."""
        if obj.diubah_oleh:
            if obj.laporan and obj.laporan.anonimitas and obj.diubah_oleh_id == obj.laporan.pelapor_id:
                return 'Pengguna Anonim'
            return obj.diubah_oleh.nama_lengkap or obj.diubah_oleh.username
        return 'Sistem'

    def get_user(self, obj):
        """Return user object with nama_lengkap and role for display purposes."""
        if obj.diubah_oleh:
            if obj.laporan and obj.laporan.anonimitas and obj.diubah_oleh_id == obj.laporan.pelapor_id:
                return {'nama_lengkap': 'Pengguna Anonim', 'role': None}
            return {
                'nama_lengkap': obj.diubah_oleh.nama_lengkap or obj.diubah_oleh.username,
                'role': obj.diubah_oleh.role
            }
        return {'nama_lengkap': 'Sistem', 'role': None}


class PelaporInfoMixin:
    """Shared helper methods for reporter-related display fields."""
    def get_pelapor_info(self, obj):
        """Build public reporter info, masking identity when report is anonymous."""
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
            'role': obj.pelapor.role
        }

    def get_nama_lengkap(self, obj):
        """Return reporter full name with anonymity formatting when needed."""
        if obj.anonimitas:
            kelas = obj.pelapor.kelas or '-'
            return f'Anonim dari Kelas {kelas}'
        return obj.pelapor.nama_lengkap if obj.pelapor else None

    def get_akun_terverifikasi(self, obj):
        """Return verification status unless anonymity hides identity."""
        if obj.anonimitas or not obj.pelapor:
            return None
        return obj.pelapor.is_verified


class LaporanKerusakanSerializer(PelaporInfoMixin, serializers.ModelSerializer):
    """Comprehensive serializer for report detail responses."""
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
    
    def get_pengirim_username(self, obj):
        """Return sender username unless anonymity is enabled."""
        if obj.anonimitas:
            return None
        return obj.pelapor.username if obj.pelapor else None
    
    def get_foto_pendukung(self, obj):
        """Return absolute URLs for all attached evidence photos."""
        request = self.context.get('request')
        foto_list = []
        for foto in obj.foto_bukti.all():
            if foto.foto and hasattr(foto.foto, 'url'):
                url = foto.foto.url
                if not url.startswith('http') and request:
                    url = request.build_absolute_uri(url)
                foto_list.append(url)
        return foto_list if foto_list else None


class LaporanKerusakanListSerializer(PelaporInfoMixin, serializers.ModelSerializer):
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


class BaseCreateEditLaporanKerusakanSerializer(serializers.ModelSerializer):
    """Base serializer for create/edit payload validation and normalization."""
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
        """Validate uploaded photos using shared file validation rules."""
        return validate_uploaded_files(value)

    def validate(self, attrs):
        """Validate required fields, date constraints, and normalize text values."""
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


class CreateLaporanKerusakanSerializer(BaseCreateEditLaporanKerusakanSerializer):
    """Serializer for report creation, including photo and status-history creation."""
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


class EditLaporanKerusakanSerializer(BaseCreateEditLaporanKerusakanSerializer):
    """Serializer for report editing, with optional additional photo uploads."""
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
    """Serializer for validating cancellation reason payload."""
    alasan = serializers.CharField()

    def validate_alasan(self, value):
        """Ensure cancellation reason is present and meets minimum length."""
        if not value or not str(value).strip():
            raise serializers.ValidationError('Alasan pembatalan wajib diisi')
        if len(value.strip()) < MIN_CANCEL_REASON_LENGTH:
            raise serializers.ValidationError(
                f'Alasan pembatalan wajib minimal {MIN_CANCEL_REASON_LENGTH} karakter'
            )
        return value.strip()

class UpdateStatusLaporanKerusakanSerializer(serializers.Serializer):
    """Serializer for validating status update request payload."""
    status = serializers.ChoiceField(
        choices=['menunggu', 'diproses', 'menunggu_konfirmasi_selesai', 'selesai', 'ditolak'],
        required=True
    )
    reason = serializers.CharField(required=False, allow_blank=True)
    note = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        """Validate status transitions and required fields."""
        status_new = data.get('status')
        reason = data.get('reason', '').strip() if data.get('reason') else ''
        note = data.get('note', '').strip() if data.get('note') else ''

        # Validation for ditolak status - reason is required
        if status_new == 'ditolak':
            if not reason:
                raise serializers.ValidationError(
                    'Alasan penolakan wajib diisi ketika status ditolak'
                )
            if len(reason) < MIN_REJECTION_REASON_LENGTH:
                raise serializers.ValidationError(
                    f'Alasan penolakan minimal {MIN_REJECTION_REASON_LENGTH} karakter'
                )

        if status_new == 'menunggu_konfirmasi_selesai' and not note:
            raise serializers.ValidationError(
                'Catatan tindak lanjut wajib diisi sebelum meminta konfirmasi pelapor'
            )

        if status_new == 'menunggu_konfirmasi_selesai' and len(note) < MIN_STATUS_NOTE_LENGTH:
            raise serializers.ValidationError(
                f'Catatan tindak lanjut minimal {MIN_STATUS_NOTE_LENGTH} karakter'
            )

        return data