"""
Database Models for Activity Logging.

This module defines the centralized audit trail table `LogAktivitas`, engineered
to irreversibly record critical state changes and user interactions.
"""

import uuid
from django.db import models
from django.conf import settings

class LogAktivitas(models.Model):
    """
    Immutable representation of a user-driven or systemic action.
    This model explicitly ignores update and delete signals to preserve audit integrity.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pengguna = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    aksi = models.CharField(max_length=255, db_index=True)
    deskripsi = models.TextField()
    waktu = models.DateTimeField(auto_now_add=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    modul = models.CharField(max_length=100, db_index=True)

    def save(self, *args, **kwargs):
        if not self._state.adding:
            return
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    class Meta:
        ordering = ['-waktu']

    def __str__(self):
        return f"{self.aksi} - {self.waktu}"