from django.contrib import admin
from .models import LogAktivitas

class LogAktivitasAdmin(admin.ModelAdmin):
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