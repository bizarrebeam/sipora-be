from django.contrib import admin

from django.contrib import admin
from .models import LaporanKerusakan, FotoBuktiPendukung


class FotoBuktiInline(admin.TabularInline):
    model = FotoBuktiPendukung
    extra = 0
    readonly_fields = ['uploaded_at']


@admin.register(LaporanKerusakan)
class LaporanKerusakanAdmin(admin.ModelAdmin):
    list_display = [
        'no_laporan', 'judul', 'lokasi', 'status',
        'pelapor', 'anonimitas', 'tanggal_laporan'
    ]
    list_filter = ['status', 'anonimitas', 'tanggal_laporan']
    search_fields = ['no_laporan', 'judul', 'lokasi', 'deskripsi']
    readonly_fields = [
        'id', 'no_laporan', 'tanggal_laporan', 'updated_at'
    ]
    inlines = [FotoBuktiInline]
    
    fieldsets = (
        ('Informasi Laporan', {
            'fields': ('id', 'no_laporan', 'judul', 'deskripsi', 'lokasi', 'tanggal_kejadian')
        }),
        ('Pelapor', {
            'fields': ('pelapor', 'anonimitas')
        }),
        ('Status', {
            'fields': ('status', 'catatan_admin', 'diproses_oleh', 'diproses_pada')
        }),
        ('Timestamps', {
            'fields': ('tanggal_laporan', 'updated_at')
        }),
    )


@admin.register(FotoBuktiPendukung)
class FotoBuktiPendukungAdmin(admin.ModelAdmin):
    list_display = ['laporan', 'foto', 'uploaded_at']
    list_filter = ['uploaded_at']
    search_fields = ['laporan__no_laporan']
    readonly_fields = ['id', 'uploaded_at']

