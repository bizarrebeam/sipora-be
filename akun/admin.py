from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Pengguna

class PenggunaAdmin(UserAdmin):
    model = Pengguna
    fieldsets = UserAdmin.fieldsets + (
        ('Informasi Tambahan', {'fields': ('role', 'nisn', 'nama_lengkap')}),
    )
    list_display = ['username', 'email', 'nama_lengkap', 'role', 'is_staff']

admin.site.register(Pengguna, PenggunaAdmin)