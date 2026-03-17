from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Pengguna

class PenggunaAdmin(UserAdmin):
    model = Pengguna
    fieldsets = UserAdmin.fieldsets + (
        ('Informasi Tambahan', {'fields': ('role', 'nis', 'nuptk', 'nama_lengkap', 'kelas', 'mata_pelajaran', 'is_verified')}),
    )
    list_display = ['username', 'nama_lengkap', 'role', 'nis', 'nuptk', 'kelas', 'is_verified', 'is_staff']
    list_filter = ['role', 'is_verified', 'is_staff']
    search_fields = ['username', 'nama_lengkap', 'nis', 'nuptk', 'email']

admin.site.register(Pengguna, PenggunaAdmin)