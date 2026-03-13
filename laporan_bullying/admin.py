from django.contrib import admin
from .models import LaporanBullying, FotoBuktiBullying

class FotoBuktiBullyingInline(admin.TabularInline):
    model = FotoBuktiBullying
    extra = 1

@admin.register(LaporanBullying)
class LaporanBullyingAdmin(admin.ModelAdmin):
    list_display = ('id', 'no_laporan', 'judul', 'pelapor', 'jenis_bullying', 'status', 'tanggal_laporan')
    list_filter = ('status', 'jenis_bullying', 'tanggal_laporan')
    search_fields = ('no_laporan', 'judul', 'pelapor__username', 'pelapor__nama_lengkap')
    readonly_fields = ('id', 'no_laporan', 'tanggal_laporan', 'updated_at')
    inlines = [FotoBuktiBullyingInline]

@admin.register(FotoBuktiBullying)
class FotoBuktiBullyingAdmin(admin.ModelAdmin):
    list_display = ('id', 'laporan', 'uploaded_at')
    readonly_fields = ('id', 'uploaded_at')
