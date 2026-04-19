"""
Serializers module for the konsultasi application.


Handles validation and serialization for:
- JadwalKonsultasi (PBI-38)
- BookingKonsultasi (PBI-39, PBI-43)
"""

from rest_framework import serializers
from django.utils import timezone
from datetime import date, datetime
from .models import JadwalKonsultasi, BookingKonsultasi


class JadwalKonsultasiSerializer(serializers.ModelSerializer):
    """
    Serializer untuk membuat dan mengubah jadwal ketersediaan Guru BK (PBI-38).
    
    Fitur validasi:
    - Format waktu harus valid
    - Urutan waktu: waktu_mulai < waktu_selesai
    - Tanggal tidak boleh sebelum hari ini
    - Tidak boleh ada tabrakan dengan jadwal lain pada tanggal yang sama
    - Untuk hari ini, waktu_mulai tidak boleh di masa lalu
    
    Fields:
        is_booked (SerializerMethodField): Boolean apakah slot sudah dipesan
        nama_guru_bk (SerializerMethodField): Nama lengkap Guru BK (dari relasi)
    """
    # Field tambahan: cek status ketersediaan slot
    is_booked = serializers.SerializerMethodField()
    
    # Field tambahan: tampilkan nama Guru BK alih-alih ID
    nama_guru_bk = serializers.SerializerMethodField()

    class Meta:
        model = JadwalKonsultasi
        fields = [
            'id',
            'guru_bk',
            'nama_guru_bk',
            'tanggal',
            'waktu_mulai',
            'waktu_selesai',
            'status',
            'catatan',
            'is_booked',
            'dibuat_pada',
            'updated_at',
        ]
        read_only_fields = ['id', 'guru_bk', 'status', 'dibuat_pada', 'updated_at']

    def get_is_booked(self, obj):
        """
        Dapatkan status ketersediaan slot.
        
        Returns:
            bool: True jika sudah dipesan (is_booked), False jika masih tersedia
        """
        return obj.is_booked()

    def get_nama_guru_bk(self, obj):
        """
        Dapatkan nama lengkap Guru BK.
        
        Returns:
            str: Nama lengkap dari relasi user, jika tidak ada kembalikan str(user)
        """
        return getattr(obj.guru_bk, 'nama_lengkap', str(obj.guru_bk))

    def validate_tanggal(self, value):
        """
        Validasi bahwa tanggal tidak boleh sebelum hari ini dan maksimal 1 bulan (30 hari) ke depan.
        
        Args:
            value (date): Tanggal yang akan divalidasi
            
        Returns:
            date: Tanggal yang sudah divalidasi
            
        Raises:
            serializers.ValidationError: Jika tanggal tidak valid
        """
        from datetime import timedelta
        
        if value < date.today():
            raise serializers.ValidationError(
                "Tanggal tidak boleh sebelum hari ini."
            )
            
        if value > date.today() + timedelta(days=30):
            raise serializers.ValidationError(
                "Jadwal hanya bisa dibuat maksimal 1 bulan (30 hari) ke depan."
            )
            
        return value

    def validate(self, data):
        """
        Validasi lintas field untuk integritas data jadwal:
        1. waktu_mulai harus lebih kecil dari waktu_selesai
        2. Tidak boleh tabrakan dengan jadwal lain milik Guru BK di tanggal yang sama
        3. Untuk tanggal hari ini, waktu_mulai tidak boleh di masa lalu (sudah lewat)
        4. Untuk partial update, gunakan nilai dari instance jika field tidak diberikan
        
        Args:
            data (dict): Data yang akan divalidasi
            
        Returns:
            dict: Data yang sudah divalidasi
            
        Raises:
            serializers.ValidationError: Jika ada violasi validasi
        """
        waktu_mulai = data.get('waktu_mulai')
        waktu_selesai = data.get('waktu_selesai')
        tanggal = data.get('tanggal')

        # Ambil dari instance jika partial update
        if self.instance:
            waktu_mulai = waktu_mulai or self.instance.waktu_mulai
            waktu_selesai = waktu_selesai or self.instance.waktu_selesai
            tanggal = tanggal or self.instance.tanggal

        if waktu_mulai and waktu_selesai:
            if waktu_mulai >= waktu_selesai:
                raise serializers.ValidationError(
                    "Waktu mulai harus lebih kecil dari waktu selesai."
                )
            
            from datetime import time
            if waktu_mulai < time(6, 0) or waktu_selesai > time(16, 0):
                raise serializers.ValidationError(
                    "Jadwal hanya bisa dibuat pada jam kerja (06:00 - 16:00)"
                )
                
            diff_minutes = (waktu_selesai.hour * 60 + waktu_selesai.minute) - (waktu_mulai.hour * 60 + waktu_mulai.minute)
            if diff_minutes > 60:
                raise serializers.ValidationError(
                    "Maksimal durasi jadwal adalah 1 jam."
                )

        # Cegah pembuatan/perubahan slot di masa lalu untuk tanggal hari ini.
        if tanggal == date.today() and waktu_mulai:
            current_time = timezone.localtime().time().replace(second=0, microsecond=0)
            if waktu_mulai <= current_time:
                raise serializers.ValidationError(
                    "Waktu mulai untuk hari ini harus lebih besar dari waktu saat ini."
                )

        # Validasi tabrakan jadwal dengan slot lain milik Guru BK pada tanggal yang sama
        if waktu_mulai and waktu_selesai and tanggal:
            request = self.context.get('request')
            # Ambil Guru BK dari instance (jika update) atau dari user (jika create)
            guru_bk = self.instance.guru_bk if self.instance else (
                request.user if request else None
            )

            if guru_bk:
                # Query jadwal lain untuk Guru BK yang sama pada tanggal yang sama
                # Exclude jadwal yang sedang di-update (jika ada)
                qs = JadwalKonsultasi.objects.filter(
                    guru_bk=guru_bk,
                    tanggal=tanggal,
                ).exclude(
                    pk=self.instance.pk if self.instance else None
                )

                for jadwal in qs:
                    # Deteksi tabrakan waktu menggunakan logika interval:
                    # Tabrakan terjadi jika: mulai_baru < selesai_lama DAN selesai_baru > mulai_lama
                    if waktu_mulai < jadwal.waktu_selesai and waktu_selesai > jadwal.waktu_mulai:
                        raise serializers.ValidationError(
                            "Slot waktu bertabrakan dengan jadwal lain pada tanggal yang sama."
                        )

        return data


class JadwalKonsultasiListSerializer(serializers.ModelSerializer):
    """
    Serializer ringkas untuk menampilkan daftar jadwal konsultasi.
    
    Digunakan untuk GET list jadwal dengan informasi dasar:
    - Nama Guru BK
    - Tanggal, waktu mulai-selesai
    - Status dan apakah sudah dipesan
    - Info siswa yang booking (jika ada)
    
    Fields tambahan:
        is_booked (SerializerMethodField): Boolean apakah slot sudah dipesan
        nama_guru_bk (SerializerMethodField): Nama lengkap Guru BK
        nama_siswa_booking (SerializerMethodField): Nama siswa yang booking (jika ada)
        kelas_siswa_booking (SerializerMethodField): Kelas siswa yang booking (jika ada)
    """
    # Field tambahan: apakah slot sudah dipesan
    is_booked = serializers.SerializerMethodField()
    
    # Field tambahan: nama Guru BK
    nama_guru_bk = serializers.SerializerMethodField()
    
    # Field tambahan: nama siswa yang booking (jika ada)
    nama_siswa_booking = serializers.SerializerMethodField()
    
    # Field tambahan: kelas siswa yang booking (jika ada)
    kelas_siswa_booking = serializers.SerializerMethodField()

    class Meta:
        model = JadwalKonsultasi
        fields = [
            'id',
            'nama_guru_bk',
            'tanggal',
            'waktu_mulai',
            'waktu_selesai',
            'status',
            'is_booked',
            'nama_siswa_booking',
            'kelas_siswa_booking',
        ]

    def get_is_booked(self, obj):
        """Cek apakah slot sudah dipesan oleh siswa."""
        return obj.is_booked()

    def get_nama_guru_bk(self, obj):
        """Ambil nama lengkap Guru BK dari relasi."""
        return getattr(obj.guru_bk, 'nama_lengkap', str(obj.guru_bk))

    def get_nama_siswa_booking(self, obj):
        """
        Ambil nama siswa yang booking untuk slot ini.
        
        Returns:
            str: Nama siswa jika ada booking, None jika belum ada booking
        """
        booking = getattr(obj, 'booking', None)
        if not booking or not booking.siswa_id:
            return None
        return getattr(booking.siswa, 'nama_lengkap', str(booking.siswa))

    def get_kelas_siswa_booking(self, obj):
        """
        Ambil kelas siswa yang booking untuk slot ini.
        
        Returns:
            str: Kelas siswa jika ada booking, None jika belum ada booking
        """
        booking = getattr(obj, 'booking', None)
        if not booking or not booking.siswa_id:
            return None
        return getattr(booking.siswa, 'kelas', None)


# =============================================================================
# Booking Serializers
# =============================================================================

class BookingKonsultasiCreateSerializer(serializers.ModelSerializer):
    """
    Serializer untuk membuat booking konsultasi baru oleh Siswa (PBI-39).
    
    Fitur validasi:
    - Deskripsi harus diisi dan tidak boleh kosong
    - Slot jadwal harus berstatus 'tersedia'
    - Waktu slot tidak boleh sudah lewat
    - Cegah tabrakan: siswa tidak boleh punya 2 booking yang berkonflik waktu pada hari yang sama
    
    Note: Gunakan select_for_update() + atomic transaction di views untuk prevent race condition
    ketika 2 siswa mencoba booking slot yang sama bersamaan.
    """

    class Meta:
        model = BookingKonsultasi
        fields = [
            'id',
            'jadwal',
            'deskripsi',
        ]
        read_only_fields = ['id']
        extra_kwargs = {
            'jadwal': {
                'error_messages': {
                    'unique': 'Maaf, jadwal ini sudah tidak tersedia karena telah dipesan oleh siswa lain.',
                }
            }
        }

    def validate_deskripsi(self, value):
        """
        Validasi deskripsi alasan konsultasi.
        
        Args:
            value (str): Deskripsi alasan konsultasi
            
        Returns:
            str: Deskripsi yang sudah di-strip whitespace
            
        Raises:
            serializers.ValidationError: Jika deskripsi kosong/hanya whitespace
        """
        if not value or not value.strip():
            raise serializers.ValidationError("Deskripsi konsultasi wajib diisi.")
            
        val_stripped = value.strip()
        if len(val_stripped) < 20 or len(val_stripped) > 150:
            raise serializers.ValidationError("Alasan konsultasi harus 20 - 150 karakter.")
            
        return val_stripped

    def validate_jadwal(self, value):
        """
        Validasi slot jadwal yang akan dipesan.
        
        Checks:
        1. Slot harus berstatus 'tersedia' (belum dipesan)
        2. Waktu slot tidak boleh sudah lewat (past datetime)
        
        Args:
            value (JadwalKonsultasi): Object jadwal yang akan dipesan
            
        Returns:
            JadwalKonsultasi: Jadwal yang sudah divalidasi
            
        Raises:
            serializers.ValidationError: Jika slot tidak tersedia atau sudah lewat
        """
        if value.status != 'tersedia':
            raise serializers.ValidationError(
                "Slot jadwal yang dipilih tidak tersedia."
            )

        # Gabungkan tanggal + waktu_mulai, bandingkan dengan sekarang
        slot_datetime = datetime.combine(value.tanggal, value.waktu_mulai)
        slot_datetime = timezone.make_aware(slot_datetime)
        if slot_datetime <= timezone.now():
            raise serializers.ValidationError(
                "Waktu slot yang dipilih sudah melewati waktu saat ini."
            )

        return value

    def validate(self, data):
        """
        Validasi lintas field untuk prevent tabrakan booking.
        
        Checks:
        1. Cek apakah siswa sudah punya booking aktif yang berkonflik waktu
           dengan jadwal yang ingin dipesan
        2. Konflik terjadi jika pada tanggal yang sama ada booking dengan
           interval waktu yang overlapping
        
        Args:
            data (dict): Data booking yang akan dibuat
            
        Returns:
            dict: Data yang sudah divalidasi
            
        Raises:
            serializers.ValidationError: Jika ada tabrakan booking yang belum selesai
        """
        request = self.context.get('request')
        siswa = request.user if request else None
        jadwal = data.get('jadwal')

        if siswa and jadwal:
            # Ambil semua booking aktif siswa
            # Cari semua booking siswa yang masih aktif (belum selesai/dibatalkan)
            booking_aktif = BookingKonsultasi.objects.filter(
                siswa=siswa,
                # Hanya cek booking yang status-nya menunggu konfirmasi atau sudah dikonfirmasi
                status__in=['menunggu_konfirmasi', 'dikonfirmasi']
            ).select_related('jadwal')

            for booking in booking_aktif:
                j = booking.jadwal
                # Jika ada booking pada tanggal yang sama
                if j.tanggal == jadwal.tanggal:
                    # Deteksi tabrakan waktu dengan logika interval overlap
                    # Tabrakan jika: waktu_mulai_baru < waktu_selesai_lama AND waktu_selesai_baru > waktu_mulai_lama
                    if (jadwal.waktu_mulai < j.waktu_selesai and
                            jadwal.waktu_selesai > j.waktu_mulai):
                        raise serializers.ValidationError(
                            "Kamu sudah memiliki booking lain yang waktunya bertabrakan."
                        )

        return data


class BookingKonsultasiListSerializer(serializers.ModelSerializer):
    """
    Serializer untuk menampilkan daftar booking konsultasi (PBI-43).
    
    Menampilkan informasi ringkas tentang booking:
    - Nama siswa yang booking
    - Detail jadwal (tanggal, waktu)
    - Deskripsi alasan
    - Status dan timestamps
    
    Catatan: Di views, dilakukan filtering berdasarkan role:
    - Siswa hanya melihat booking milik mereka sendiri
    - Guru BK melihat semua booking
    
    Fields tambahan:
        nama_siswa (SerializerMethodField): Nama lengkap siswa
        tanggal_konsultasi (SerializerMethodField): Tanggal dari relasi jadwal
        waktu_mulai (SerializerMethodField): Waktu mulai dari relasi jadwal
        waktu_selesai (SerializerMethodField): Waktu selesai dari relasi jadwal
    """
    # Field tambahan: nama siswa dari relasi
    nama_siswa = serializers.SerializerMethodField()
    
    # Field tambahan: tanggal konsultasi dari relasi jadwal
    tanggal_konsultasi = serializers.SerializerMethodField()
    
    # Field tambahan: waktu mulai dari relasi jadwal
    waktu_mulai = serializers.SerializerMethodField()
    
    # Field tambahan: waktu selesai dari relasi jadwal
    waktu_selesai = serializers.SerializerMethodField()

    class Meta:
        model = BookingKonsultasi
        fields = [
            'id',
            'nama_siswa',
            'jadwal',
            'tanggal_konsultasi',
            'waktu_mulai',
            'waktu_selesai',
            'deskripsi',
            'status',
            'dibuat_pada',
            'updated_at',
        ]

    def get_nama_siswa(self, obj):
        """Ambil nama lengkap siswa dari relasi."""
        return getattr(obj.siswa, 'nama_lengkap', str(obj.siswa))

    def get_tanggal_konsultasi(self, obj):
        """Ambil tanggal konsultasi dari relasi jadwal."""
        return obj.jadwal.tanggal

    def get_waktu_mulai(self, obj):
        """Ambil waktu mulai konsultasi dari relasi jadwal."""
        return obj.jadwal.waktu_mulai

    def get_waktu_selesai(self, obj):
        """Ambil waktu selesai konsultasi dari relasi jadwal."""
        return obj.jadwal.waktu_selesai


class BookingKonsultasiDetailSerializer(serializers.ModelSerializer):
    """
    Serializer detail lengkap untuk menampilkan satu booking konsultasi.
    
    Menampilkan informasi detail termasuk:
    - Data siswa dan jadwal lengkap
    - Deskripsi alasan konsultasi
    - Status dan alasan jika ditolak atau dibatalkan
    - Timestamps pembuatan dan perubahan terakhir
    
    Fields tambahan:
        nama_siswa (SerializerMethodField): Nama lengkap siswa
        jadwal_detail (SerializerMethodField): Serializer penuh untuk jadwal (nested)
    """
    # Field tambahan: nama siswa dari relasi
    nama_siswa = serializers.SerializerMethodField()
    
    # Field nested: serializer lengkap untuk jadwal (untuk informasi detail)
    jadwal_detail = JadwalKonsultasiSerializer(source='jadwal', read_only=True)

    class Meta:
        model = BookingKonsultasi
        fields = [
            'id',
            'nama_siswa',
            'jadwal',
            'jadwal_detail',
            'deskripsi',
            'status',
            'alasan_penolakan',
            'alasan_pembatalan',
            'dibuat_pada',
            'updated_at',
        ]

    def get_nama_siswa(self, obj):
        """Ambil nama lengkap siswa dari relasi."""
        return getattr(obj.siswa, 'nama_lengkap', str(obj.siswa))