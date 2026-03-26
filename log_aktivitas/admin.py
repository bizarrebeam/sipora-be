"""
Django Admin Configuration for Activity Logs.

This module defines the read-only interface for administrators to monitor
system-wide user activity logs directly from the Django Admin dashboard.
"""

from django.contrib import admin
from .models import LogAktivitas

class LogAktivitasAdmin(admin.ModelAdmin):
    """
    Read-only admin interface for the LogAktivitas model.
    Prevents manual insertion, modification, or deletion of audit trails to ensure integrity.
    """
    list_display = ('aksi', 'pengguna', 'modul', 'waktu', 'ip_address')
    list_filter = ('modul', 'waktu')
    search_fields = ('aksi', 'deskripsi', 'pengguna__username')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

admin.site.register(LogAktivitas, LogAktivitasAdmin)