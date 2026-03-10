from django.contrib import admin
from .models import Artikel

@admin.register(Artikel)
class ArtikelAdmin(admin.ModelAdmin):
    # Kolom yang muncul di daftar tabel
    list_display = ('judul', 'status', 'created_at', 'updated_at')
    
    # Fitur filter di sebelah kanan
    list_filter = ('status', 'created_at')
    
    # Fitur pencarian berdasarkan judul dan ringkasan
    search_fields = ('judul', 'ringkasan')
    
    # Agar ID (UUID) terlihat tapi tidak bisa diedit di form detail
    readonly_fields = ('id', 'created_at', 'updated_at')
    
    # Urutan default (terbaru di atas)
    ordering = ('-created_at',)