from django.db import models

import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone

def laporan_foto_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    new_filename = f"{uuid.uuid4()}.{ext}"
    return f"aspirasi/{instance.laporan.id}/{new_filename}"

class Aspirasi(models.Model):
    KATEGORI_CHOICES = [
        ('sarana', 'Sarana & Prasarana'),
        ('kurikulum', 'Kurikulum & Pembelajaran'),
        ('layanan', 'Layanan Infrastruktur & Akademik'),
        ('ekstrakulikuler', 'Ekstrakulikuler & Bakat'),
        ('kesehatan', 'Kesehatan & Keamanan'),
        ('lainnya', 'Lainnya'),
    ]

    DITANDAI_CHOICES = [
        ('ditandai', 'Ditandai'),
        ('tidak_ditandai', 'Tidak Ditandai'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    no_laporan = models.CharField(max_length=20, unique=True, editable=False, db_index=True)
    judul = models.CharField(max_length=255, db_index=True)
    kategori = models.CharField(max_length=32, choices=KATEGORI_CHOICES, db_index=True)
    deskripsi = models.TextField()
    status_ditandai = models.CharField(max_length=20, choices=DITANDAI_CHOICES, default='tidak_ditandai', db_index=True)
    pelapor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='aspirasi'
    )
    anonimitas = models.BooleanField(default=False)
    tanggal_aspirasi = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    ditandai_oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='aspirasi_ditandai'
    )
    diproses_pada = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-tanggal_aspirasi']
        verbose_name = 'Aspirasi'
        verbose_name_plural = 'Aspirasi'

    def __str__(self):
        return f"{self.no_laporan} - {self.judul}"

    def save(self, *args, **kwargs):
        if not self.no_laporan:
            year = timezone.now().year
            last_laporan = Aspirasi.objects.filter(
                no_laporan__startswith=f"ASP-{year}-"
            ).order_by('-no_laporan').first()

            if last_laporan:
                last_number = int(last_laporan.no_laporan.split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1

            self.no_laporan = f"ASP-{year}-{str(new_number).zfill(4)}"

        super().save(*args, **kwargs)

class RiwayatStatusDitandai(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    laporan = models.ForeignKey(
        Aspirasi,
        on_delete=models.CASCADE,
        related_name='riwayat_status_ditandai'
    )
    status_ditandai = models.CharField(max_length=20, choices=Aspirasi.DITANDAI_CHOICES)
    diubah_oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    waktu = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['waktu']
        verbose_name = 'Riwayat Status Ditandai'
        verbose_name_plural = 'Riwayat Status Ditandai'

    def __str__(self):
        return f"{self.laporan.no_laporan} → {self.status_ditandai}"


class FotoBuktiPendukung(models.Model):    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    laporan = models.ForeignKey(
        Aspirasi,
        on_delete=models.CASCADE,
        related_name='foto_bukti'
    )
    foto = models.ImageField(upload_to=laporan_foto_upload_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['uploaded_at']
        verbose_name = 'Foto Bukti Pendukung'
        verbose_name_plural = 'Foto Bukti Pendukung'
    
    def __str__(self):
        return f"Foto untuk {self.laporan.no_laporan}"

