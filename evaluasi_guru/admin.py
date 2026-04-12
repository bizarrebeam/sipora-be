from django.contrib import admin
from .models import KategoriPenilaian, Indikator, Evaluasi, NilaiEvaluasi

class IndikatorInline(admin.TabularInline):
    model = Indikator
    extra = 1

@admin.register(KategoriPenilaian)
class KategoriPenilaianAdmin(admin.ModelAdmin):
    list_display = ('id', 'nama')
    search_fields = ('nama',)
    inlines = [IndikatorInline]

@admin.register(Indikator)
class IndikatorAdmin(admin.ModelAdmin):
    list_display = ('id', 'kategori', 'urutan', 'deskripsi')
    list_filter = ('kategori',)
    search_fields = ('deskripsi',)
    list_editable = ('urutan',)
    ordering = ('kategori', 'urutan')

class NilaiEvaluasiInline(admin.TabularInline):
    model = NilaiEvaluasi
    extra = 0
    readonly_fields = ('indikator', 'nilai') 
    can_delete = False

@admin.register(Evaluasi)
class EvaluasiAdmin(admin.ModelAdmin):
    list_display = ('id', 'siswa', 'guru', 'semester', 'tahun_ajaran', 'created_at')
    list_filter = ('semester', 'tahun_ajaran', 'created_at')
    search_fields = (
        'siswa__username', 
        'siswa__nama_lengkap', 
        'guru__username', 
        'guru__nama_lengkap', 
        'komentar'
    )
    readonly_fields = ('created_at',)
    inlines = [NilaiEvaluasiInline]

@admin.register(NilaiEvaluasi)
class NilaiEvaluasiAdmin(admin.ModelAdmin):
    list_display = ('id', 'evaluasi', 'indikator', 'nilai')
    list_filter = ('nilai', 'indikator__kategori')
    search_fields = (
        'evaluasi__siswa__username', 
        'evaluasi__guru__username', 
        'indikator__deskripsi'
    )
