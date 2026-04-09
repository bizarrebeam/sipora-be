"""Models for response/comment management across report types."""

import uuid
from django.db import models
from django.conf import settings
from laporan_kerusakan.models import LaporanKerusakan
from laporan_bullying.models import LaporanBullying


class TanggapanLaporanKerusakan(models.Model):
    """
    Model representing a response/comment to a facility damage report.
    
    Stores message content, sender info, and timestamp for each response
    in the report conversation thread.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Foreign key to the report being responded to
    laporan = models.ForeignKey(
        LaporanKerusakan,
        on_delete=models.CASCADE,
        related_name='tanggapan'
    )
    
    # Sender information
    pengirim = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tanggapan_kerusakan'
    )
    
    # Display name (may be "Pengguna Anonim" if report is anonymous)
    nama_pengirim = models.CharField(max_length=255)
    
    # The response message content
    pesan = models.TextField()
    
    # Auto-generated timestamp
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['created_at']
        verbose_name = 'Tanggapan Laporan Kerusakan'
        verbose_name_plural = 'Tanggapan Laporan Kerusakan'
        indexes = [
            models.Index(fields=['laporan', 'created_at']),
        ]
    
    def __str__(self):
        return f"Tanggapan pada {self.laporan.no_laporan} oleh {self.nama_pengirim}"

    
class TanggapanLaporanBullying(models.Model):
    """Model representing a response/comment to a bullying report."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    laporan = models.ForeignKey(
        LaporanBullying,
        on_delete=models.CASCADE,
        related_name='tanggapan'
    )
    
    pengirim = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tanggapan_bullying'
    )
    
    nama_pengirim = models.CharField(max_length=255)
    pesan = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['created_at']
        verbose_name = 'Tanggapan Laporan Bullying'
        verbose_name_plural = 'Tanggapan Laporan Bullying'
        indexes = [
            models.Index(fields=['laporan', 'created_at']),
        ]
    
    def __str__(self):
        return f"Tanggapan pada {self.laporan.no_laporan} oleh {self.nama_pengirim}"
