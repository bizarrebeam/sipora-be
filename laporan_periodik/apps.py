"""
Application configuration for the laporan_periodik module.
"""

from django.apps import AppConfig


class LaporanPeriodikConfig(AppConfig):
    """Configuration class for the Laporan Periodik application."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'laporan_periodik'
    verbose_name = 'Laporan Periodik'
