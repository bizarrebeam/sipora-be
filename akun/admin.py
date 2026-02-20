from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Pengguna

class PenggunaAdmin(UserAdmin):
    model = Pengguna
    fieldsets = UserAdmin.fieldsets + (
        ('Informasi Tambahan', {'fields': ('role', 'nisn', 'nuptk', 'nama_lengkap', 'kelas', 'mata_pelajaran')}),
    )
    list_display = ['username', 'nama_lengkap', 'role', 'nisn', 'nuptk', 'kelas', 'is_staff']
    list_filter = ['role', 'kelas']
    search_fields = ['username', 'nama_lengkap', 'nisn', 'nuptk']

admin.site.register(Pengguna, PenggunaAdmin)