"""
Models module for the tanggapan application.

Provides generic response/comment models for damage reports and other report types.
Current implementation focuses on laporan_kerusakan; can be extended to laporan_bullying.
"""

import uuid
from django.db import models
from django.conf import settings
from laporan_kerusakan.models import LaporanKerusakan


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
