"""

import logging

logger = logging.getLogger(__name__)

Core Utility Functions for Activity Logging.

This module exposes the primary, decoupled procedural functions for writing to the audit ledger
without strictly requiring active HTTP request contexts.
"""

def catat_log(user, aksi, deskripsi, modul, ip_address=None):
    """
    Globally reusable generic logging procedure for the system audit trail.
    This function should be executed synchronously across views and services whenever
    a monitored entity is mutated.

    Args:
        user: The authenticated User model triggering the event, if applicable.
        aksi (str): Short action classification (e.g., 'BUAT_AKUN', 'LOGIN').
        deskripsi (str): Read-friendly summary of the mutation or event.
        modul (str): The logical application domain.
        ip_address (str): The requesting client's extracted IP, if trackable.
    """
    from .models import LogAktivitas
    
    try:
        LogAktivitas.objects.create(
            pengguna=user,
            aksi=aksi,
            deskripsi=deskripsi,
            modul=modul,
            ip_address=ip_address
        )
    except Exception as e:
        # Prevents systemic failure if the logging persistence layer encounters an error
        logger.error(f"Log Audit failed to save for {aksi}: {str(e)}")
