from django.contrib import admin
from .models import Artikel, FotoArtikel



class FotoArtikelInline(admin.TabularInline):
    """
    Inline admin for FotoArtikel, allowing images to be managed directly from the Artikel admin page.
    """
    model = FotoArtikel
    extra = 0
    readonly_fields = ['uploaded_at']



@admin.register(Artikel)
class ArtikelAdmin(admin.ModelAdmin):
    """
    Admin configuration for Artikel model.
    Displays key fields, enables filtering, searching, and inline image management.
    """
    list_display = ('judul', 'status', 'created_at', 'updated_at')
    list_filter = ('status', 'created_at')
    search_fields = ('judul', 'ringkasan')
    readonly_fields = ('id', 'created_at', 'updated_at')
    inlines = [FotoArtikelInline]
    ordering = ('-created_at',)



@admin.register(FotoArtikel)
class FotoArtikelAdmin(admin.ModelAdmin):
    """
    Admin configuration for FotoArtikel model.
    Allows image management and filtering by upload date.
    """
    list_display = ['artikel', 'foto', 'uploaded_at']
    list_filter = ['uploaded_at']
    search_fields = ['artikel__judul']
    readonly_fields = ['id', 'uploaded_at']