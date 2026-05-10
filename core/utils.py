"""
Shared text utilities for validation and sanitization across modules.
"""

import re



MIN_REJECTION_REASON_LENGTH = 50
MIN_STATUS_NOTE_LENGTH = 50


def sanitize_text(value):
    """
    Sanitize user input to prevent XSS and other injection attacks by
    removing HTML tags and potentially dangerous characters from a string.

    Args:
        value (str): The raw text string inputted by the user.

    Returns:
        str: The sanitized text string.
    """
    value = re.sub(r'<.*?>', '', value)
    value = re.sub(r'[<>\\\"\';%()\&+]', '', value)

    return value.strip()


STATUS_LABELS = {
    'menunggu': 'Menunggu Konfirmasi',
    'diproses': 'Diproses',
    'menunggu_konfirmasi_selesai': 'Menunggu Konfirmasi Selesai',
    'selesai': 'Selesai',
    'ditolak': 'Ditolak',
    'dibatalkan': 'Dibatalkan',
}


def build_status_change_catatan(status_current, status_new, reason='', note=''):
    """Return a consistent history note for status transitions."""
    reason = (reason or '').strip()
    note = (note or '').strip()

    if status_new == 'ditolak' and reason:
        return f"Status diperbarui ke {STATUS_LABELS['ditolak']}. Alasan: {reason}"

    if status_new == 'menunggu_konfirmasi_selesai':
        return (
            f"Status diperbarui ke {STATUS_LABELS['menunggu_konfirmasi_selesai']}. "
            f"Catatan tindak lanjut: {note}"
        )

    if status_current == 'menunggu_konfirmasi_selesai' and status_new == 'selesai':
        if note:
            return f"Pelapor mengonfirmasi laporan selesai. Catatan: {note}"
        return 'Pelapor mengonfirmasi laporan selesai'

    if status_current == 'menunggu_konfirmasi_selesai' and status_new == 'diproses':
        return 'Pelapor menyatakan laporan belum selesai dan dikembalikan ke Diproses'

    if note:
        return f"Status diperbarui ke {STATUS_LABELS.get(status_new, status_new)}. Catatan: {note}"

    return None
