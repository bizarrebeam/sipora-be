from django.contrib import admin
from .models import Artikel, FotoArtikel


class FotoArtikelInline(admin.TabularInline):
    model = FotoArtikel
    extra = 0
    readonly_fields = ['uploaded_at']


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
    
    # Inline untuk foto
    inlines = [FotoArtikelInline]
    
    # Urutan default (terbaru di atas)
    ordering = ('-created_at',)


@admin.register(FotoArtikel)
class FotoArtikelAdmin(admin.ModelAdmin):
    list_display = ['artikel', 'foto', 'uploaded_at']
    list_filter = ['uploaded_at']
    search_fields = ['artikel__judul']
    readonly_fields = ['id', 'uploaded_at']