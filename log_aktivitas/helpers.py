"""
Helper Utilities for Activity Logging.

This module provides legacy or alternative request-based logging mechanisms.
"""

from .models import LogAktivitas

def catat_log(request, aksi, deskripsi, modul):
    """
    Records a system activity to the audit ledger by extracting the user and IP directly from the HTTP request.
    
    Args:
        request: The Django HttpRequest object.
        aksi (str): A short identifier for the action performed.
        deskripsi (str): A detailed human-readable description of the event.
        modul (str): The domain or systemic boundary where the action occurred.
    """
    ip_address = None
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')
            
    LogAktivitas.objects.create(
        pengguna=request.user if request and request.user.is_authenticated else None,
        aksi=aksi,
        deskripsi=deskripsi,
        ip_address=ip_address,
        modul=modul
    )