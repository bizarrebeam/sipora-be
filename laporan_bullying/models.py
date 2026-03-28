"""
Models module for the laporan_bullying application.

This module contains the database schema definitions for bullying reports,
including the main report data, uploaded evidence photos, and the status history.
"""

from django.db import models
import uuid
from django.conf import settings
from django.utils import timezone


def laporan_bullying_foto_upload_path(instance, filename):
    """
    Generate a dynamic and unique upload path for bullying evidence photos.
    
    The photo will be uploaded to a directory named after the report's UUID
    to keep files organized per report. The filename itself is randomized using UUID4.
    
    Args:
        instance (FotoBuktiBullying): The photo instance being saved.
        filename (str): The original filename of the uploaded image.
        
    Returns:
        str: The generated file path indicating where the image will be stored.
    """
    ext = filename.split('.')[-1]
    new_filename = f"{uuid.uuid4()}.{ext}"
    return f"laporan_bullying/{instance.laporan.id}/{new_filename}"

class LaporanBullying(models.Model):
    """
    Model representing a Bullying Report submitted by a student or teacher.
    
    Stores comprehensive data about the bullying incident, including exactly what
    happened, when and where it took place, and the report's processing status.
    """
    
    STATUS_CHOICES = [
        ('menunggu', 'Menunggu Konfirmasi'),
        ('diproses', 'Diproses'),
        ('selesai', 'Selesai'),
        ('dibatalkan', 'Dibatalkan'),
    ]

    JENIS_BULLYING_CHOICES = [
        ('verbal', 'Bullying Verbal'),
        ('fisik', 'Bullying Fisik'),
        ('sosial', 'Bullying Sosial'),
        ('cyber', 'Cyberbullying'),
        ('seksual', 'Kekerasan Seksual'),
        ('lainnya', 'Lainnya'),
    ]

    # Primary key and unique human-readable identifier
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    no_laporan = models.CharField(max_length=20, unique=True, editable=False, db_index=True)

    # Core report components
    judul = models.CharField(max_length=255, db_index=True)
    deskripsi = models.TextField()
    lokasi = models.CharField(max_length=255, db_index=True)
    tanggal_kejadian = models.DateField(db_index=True)
    jenis_bullying = models.CharField(max_length=20, choices=JENIS_BULLYING_CHOICES, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='menunggu', db_index=True)
    catatan_admin = models.TextField(blank=True, null=True)

    # Relationship to the user who created the report
    pelapor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='laporan_bullying'
    )

    # Flag for whether the reporter wants to remain anonymous
    anonimitas = models.BooleanField(default=False)

    # Auto-generated timestamps
    tanggal_laporan = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Relationship indicating the staff member (Kemahasiswaan or Guru BK) handling the case
    diproses_oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='laporan_bullying_diproses'
    )
    diproses_pada = models.DateTimeField(null=True, blank=True)

    # Stores the reason if the report gets canceled
    alasan_pembatalan = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-tanggal_laporan']
        verbose_name = 'Laporan Bullying'
        verbose_name_plural = 'Laporan Bullying'

    def __str__(self):
        return f"{self.no_laporan} - {self.judul}"

    def save(self, *args, **kwargs):
        """
        Custom save method to auto-generate a unique report number (no_laporan).
        
        The format follows 'LB-<YEAR>-<SEQUENCE>', starting sequentially from '0001' 
        for each given year. The sequence resets every new year.
        """
        if not self.no_laporan:
            year = timezone.now().year
            last_laporan = LaporanBullying.objects.filter(
                no_laporan__startswith=f"LB-{year}-"
            ).order_by('-no_laporan').first()

            if last_laporan:
                last_number = int(last_laporan.no_laporan.split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1

            self.no_laporan = f"LB-{year}-{str(new_number).zfill(4)}"

        super().save(*args, **kwargs)

    def get_nama_pelapor(self):
        """
        Return the reporter's name, substituting it with 'Pengguna Anonim'
        (Anonymous User) if the reporter elected for anonymity.
        
        Returns:
            str: The full name or the anonymous placeholder string.
        """
        if self.anonimitas:
            return "Pengguna Anonim"
        return self.pelapor.nama_lengkap

    def is_pelapor_terverifikasi(self):
        """
        Check whether the reporter's account has been verified.
        
        Returns:
            bool: True if verified, False otherwise.
        """
        return getattr(self.pelapor, 'is_verified', False)

class FotoBuktiBullying(models.Model):
    """
    Model representing photographic evidence attached to a bullying report.
    
    A single report can have multiple photos associated with it via a Foreign Key relationship.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # The specific bullying report this photo belongs to
    laporan = models.ForeignKey(
        LaporanBullying,
        on_delete=models.CASCADE,
        related_name='foto_bukti'
    )

    # Image field configured with a dynamic upload path resolver
    foto = models.ImageField(upload_to=laporan_bullying_foto_upload_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']
        verbose_name = 'Foto Bukti Bullying'
        verbose_name_plural = 'Foto Bukti Bullying'

    def __str__(self):
        return f"Foto untuk {self.laporan.no_laporan}"

class RiwayatStatusBullying(models.Model):
    """
    Model to track the timeline and status changes of a bullying report.
    
    Acts as an audit log detailing when a report's status was changed, 
    what the new status was, who made the change, and any notes left by them.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    laporan = models.ForeignKey(
        LaporanBullying,
        on_delete=models.CASCADE,
        related_name='riwayat_status'
    )

    status = models.CharField(
        max_length=20,
        choices=LaporanBullying.STATUS_CHOICES
    )

    # Optional notes added when changing the status
    catatan = models.TextField(blank=True, null=True)

    # The user (staff or reporter submitting cancellation) who altered the status
    diubah_oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Riwayat Status Bullying'
        verbose_name_plural = 'Riwayat Status Bullying'

    def __str__(self):
        return f"{self.laporan.no_laporan} - {self.status}"