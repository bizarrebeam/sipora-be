"""
Models module for the konsultasi application.

Covers:
- JadwalKonsultasi: Slot waktu yang dibuat oleh Guru BK (PBI-38)
- BookingKonsultasi: Pemesanan slot oleh Siswa (PBI-39, PBI-43)
"""

import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


class JadwalKonsultasi(models.Model):
    """
    Model untuk menyimpan slot waktu ketersediaan Guru BK untuk konsultasi one-on-one.
    
    Setiap Guru BK dapat membuat, mengubah, dan menghapus jadwal milik mereka sendiri.
    Siswa dapat melihat jadwal yang tersedia dan membuat booking untuk slot yang diinginkan.
    
    Attributes:
        id (UUIDField): Primary key unik untuk setiap jadwal
        guru_bk (ForeignKey): Referensi ke user Guru BK yang membuat jadwal
        tanggal (DateField): Tanggal ketersediaan (indexed untuk performa query)
        waktu_mulai (TimeField): Waktu mulai konsultasi
        waktu_selesai (TimeField): Waktu selesai konsultasi
        status (CharField): Status ketersediaan jadwal (indexed untuk performa filter)
        catatan (TextField): Catatan tambahan/notes untuk jadwal ini
        dibuat_pada (DateTimeField): Timestamp saat jadwal dibuat (auto_now_add)
        updated_at (DateTimeField): Timestamp terakhir kali diubah (auto_now)
    """

    # Pilihan status untuk jadwal konsultasi
    STATUS_CHOICES = [
        # Slot belum dipesan oleh siswa
        ('tersedia', 'Tersedia'),
        # Slot sudah dipesan siswa, menunggu konfirmasi dari Guru BK
        ('menunggu_konfirmasi', 'Menunggu Konfirmasi'),
        # Booking sudah dikonfirmasi oleh Guru BK
        ('dikonfirmasi', 'Dikonfirmasi'),
        # Booking ditolak oleh Guru BK
        ('ditolak', 'Ditolak'),
        # Booking dibatalkan oleh Siswa
        ('dibatalkan_siswa', 'Dibatalkan oleh Siswa'),
        # Booking dibatalkan oleh Guru BK
        ('dibatalkan_guru_bk', 'Dibatalkan oleh Guru BK'),
    ]

    # Primary key unik menggunakan UUID
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Referensi ke Guru BK yang membuat jadwal
    guru_bk = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='jadwal_konsultasi'
    )

    # Tanggal ketersediaan (di-index untuk performa query filter)
    tanggal = models.DateField(db_index=True)
    
    # Waktu mulai konsultasi
    waktu_mulai = models.TimeField()
    
    # Waktu selesai konsultasi
    waktu_selesai = models.TimeField()

    # Status ketersediaan slot (di-index untuk performa filter)
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='tersedia',
        db_index=True
    )

    # Catatan tambahan/notes untuk jadwal ini
    catatan = models.TextField(blank=True, null=True)

    # Timestamp saat jadwal dibuat (tidak dapat diubah)
    dibuat_pada = models.DateTimeField(auto_now_add=True)
    
    # Timestamp terakhir kali jadwal diubah (otomatis update)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['tanggal', 'waktu_mulai']
        verbose_name = 'Jadwal Konsultasi'
        verbose_name_plural = 'Jadwal Konsultasi'

    def __str__(self):
        """
        Representasi string dari jadwal konsultasi.
        Format: [Nama Guru BK] | [Tanggal] [Waktu Mulai]-[Waktu Selesai] [Status]
        """
        return f"{self.guru_bk} | {self.tanggal} {self.waktu_mulai}-{self.waktu_selesai} [{self.status}]"

    def is_booked(self):
        """
        Cek apakah slot jadwal ini sudah dipesan.
        
        Returns:
            bool: True jika slot sudah dipesan (status != 'tersedia'), False jika masih tersedia
        """
        return self.status != 'tersedia'


class BookingKonsultasi(models.Model):
    """
    Model untuk menyimpan data pemesanan (booking) konsultasi dari Siswa ke Guru BK.
    
    Setiap booking merepresentasikan pemesanan siswa untuk satu slot jadwal konsultasi.
    Siswa dapat membuat booking, dan kemudian Guru BK dapat mengkonfirmasi atau menolak.
    
    Attributes:
        id (UUIDField): Primary key unik untuk setiap booking
        siswa (ForeignKey): Referensi ke user Siswa yang membuat booking
        jadwal (OneToOneField): Referensi ke JadwalKonsultasi yang dipesan (satu slot = satu booking)
        deskripsi (TextField): Deskripsi alasan mengapa siswa ingin berkonsultasi
        status (CharField): Status pemesanan (menunggu konfirmasi, dikonfirmasi, ditolak, dll)
        alasan_penolakan (TextField): Alasan jika booking ditolak oleh Guru BK
        alasan_pembatalan (TextField): Alasan jika booking dibatalkan
        dibuat_pada (DateTimeField): Timestamp saat booking dibuat (auto_now_add)
        updated_at (DateTimeField): Timestamp terakhir kali diubah (auto_now)
    """

    # Pilihan status untuk booking konsultasi
    STATUS_CHOICES = [
        # Booking baru, menunggu konfirmasi dari Guru BK
        ('menunggu_konfirmasi', 'Menunggu Konfirmasi'),
        # Guru BK sudah mengkonfirmasi booking
        ('dikonfirmasi', 'Dikonfirmasi'),
        # Guru BK menolak booking ini
        ('ditolak', 'Ditolak'),
        # Booking dibatalkan oleh Siswa
        ('dibatalkan_siswa', 'Dibatalkan oleh Siswa'),
        # Booking dibatalkan oleh Guru BK
        ('dibatalkan_guru_bk', 'Dibatalkan oleh Guru BK'),
        # Konsultasi sudah selesai dilakukan
        ('selesai', 'Selesai'),
    ]

    # Primary key unik menggunakan UUID
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Referensi ke Siswa yang membuat booking
    siswa = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='booking_konsultasi'
    )

    # Referensi ke JadwalKonsultasi yang dipesan (OneToOne: satu slot = satu booking)
    jadwal = models.OneToOneField(
        JadwalKonsultasi,
        on_delete=models.CASCADE,
        related_name='booking',
        error_messages={
            'unique': 'Maaf, jadwal ini sudah tidak tersedia'
        }
    )

    # Deskripsi alasan mengapa siswa ingin berkonsultasi
    deskripsi = models.TextField()

    # Status pemesanan konsultasi
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='menunggu_konfirmasi',
        db_index=True
    )

    # Alasan penolakan jika Guru BK menolak booking ini
    alasan_penolakan = models.TextField(blank=True, null=True)
    
    # Alasan pembatalan jika booking dibatalkan
    alasan_pembatalan = models.TextField(blank=True, null=True)

    # Timestamp saat booking dibuat (tidak dapat diubah)
    dibuat_pada = models.DateTimeField(auto_now_add=True)
    
    # Timestamp terakhir kali booking diubah (otomatis update)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-dibuat_pada']
        verbose_name = 'Booking Konsultasi'
        verbose_name_plural = 'Booking Konsultasi'

    def __str__(self):
        """
        Representasi string dari booking konsultasi.
        Format: Booking [Nama Siswa] -> [Jadwal] [Status]
        """
        return f"Booking {self.siswa} -> {self.jadwal} [{self.status}]"