from django.contrib import admin
from .models import TanggapanLaporanKerusakan


@admin.register(TanggapanLaporanKerusakan)
class TanggapanLaporanKerusakanAdmin(admin.ModelAdmin):
    list_display = ('id', 'laporan', 'nama_pengirim', 'created_at')
    list_filter = ('created_at', 'laporan')
    search_fields = ('nama_pengirim', 'pesan')
    readonly_fields = ('id', 'created_at')
