"""
Models module for the laporan_kerusakan application.

Defines database schemas for facility-damage reports,
supporting photos, and status history records.
"""

import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


def laporan_foto_upload_path(instance, filename):
    """
    Generate a unique upload path for report evidence photos.

    Photos are grouped by report UUID and stored using randomized file names
    to avoid collisions.
    """
    ext = filename.split('.')[-1]
    new_filename = f"{uuid.uuid4()}.{ext}"
    return f"laporan_kerusakan/{instance.laporan.id}/{new_filename}"


class LaporanKerusakan(models.Model):
    """Model representing a facility damage report submitted by a user."""
    STATUS_CHOICES = [
        ('menunggu', 'Menunggu Konfirmasi'),
        ('diproses', 'Diproses'),
        ('menunggu_konfirmasi_selesai', 'Menunggu Konfirmasi Selesai'),
        ('selesai', 'Selesai'),
        ('ditolak', 'Ditolak'),
        ('dibatalkan', 'Dibatalkan'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    no_laporan = models.CharField(max_length=20, unique=True, editable=False, db_index=True)
    judul = models.CharField(max_length=255, db_index=True)
    deskripsi = models.TextField()
    lokasi = models.CharField(max_length=255, db_index=True)
    tanggal_kejadian = models.DateField(db_index=True)
    status = models.CharField(max_length=40, choices=STATUS_CHOICES, default='menunggu', db_index=True)
    catatan_admin = models.TextField(blank=True, null=True)    
    pelapor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='laporan_kerusakan'
    )
    anonimitas = models.BooleanField(default=False)    
    tanggal_laporan = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)    
    diproses_oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='laporan_diproses'
    )
    diproses_pada = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-tanggal_laporan']
        verbose_name = 'Laporan Kerusakan'
        verbose_name_plural = 'Laporan Kerusakan'
    
    def __str__(self):
        return f"{self.no_laporan} - {self.judul}"
    
    def save(self, *args, **kwargs):
        """
        Auto-generate a yearly sequential report number.

        Format: LK-<YEAR>-<SEQUENCE>.
        """
        if not self.no_laporan:
            year = timezone.now().year
            last_laporan = LaporanKerusakan.objects.filter(
                no_laporan__startswith=f"LK-{year}-"
            ).order_by('-no_laporan').first()
            
            if last_laporan:
                last_number = int(last_laporan.no_laporan.split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.no_laporan = f"LK-{year}-{str(new_number).zfill(4)}"
        
        super().save(*args, **kwargs)


class RiwayatStatusLaporan(models.Model):
    """Audit trail model for tracking report status transitions."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    laporan = models.ForeignKey(
        LaporanKerusakan,
        on_delete=models.CASCADE,
        related_name='riwayat_status'
    )
    status = models.CharField(max_length=40, choices=LaporanKerusakan.STATUS_CHOICES)
    catatan = models.TextField(blank=True, null=True)
    diubah_oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    waktu = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['waktu']
        verbose_name = 'Riwayat Status Laporan'
        verbose_name_plural = 'Riwayat Status Laporan'

    def __str__(self):
        return f"{self.laporan.no_laporan} → {self.status}"


class FotoBuktiPendukung(models.Model):    
    """Model for storing photo evidence attached to damage reports."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    laporan = models.ForeignKey(
        LaporanKerusakan,
        on_delete=models.CASCADE,
        related_name='foto_bukti'
    )
    foto = models.ImageField(upload_to=laporan_foto_upload_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['uploaded_at']
        verbose_name = 'Foto Bukti Pendukung'
        verbose_name_plural = 'Foto Bukti Pendukung'
    
    def __str__(self):
        return f"Foto untuk {self.laporan.no_laporan}"

