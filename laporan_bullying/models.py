# Import library yang dibutuhkan
from django.db import models
import uuid
from django.conf import settings
from django.utils import timezone


# Fungsi untuk upload foto bukti bullying
def laporan_bullying_foto_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    new_filename = f"{uuid.uuid4()}.{ext}"
    return f"laporan_bullying/{instance.laporan.id}/{new_filename}"

# Model Laporan Bullying yang akan digunakan untuk menyimpan data laporan bullying
class LaporanBullying(models.Model):
    # Status laporan bullying dalam sistem
    STATUS_CHOICES = [
        ('menunggu', 'Menunggu Konfirmasi'),
        ('diproses', 'Diproses'),
        ('selesai', 'Selesai'),
        ('dibatalkan', 'Dibatalkan'),
    ]

    # Jenis bullying
    JENIS_BULLYING_CHOICES = [
        ('verbal', 'Bullying Verbal'),
        ('fisik', 'Bullying Fisik'),
        ('sosial', 'Bullying Sosial'),
        ('cyber', 'Cyberbullying'),
        ('seksual', 'Kekerasan Seksual'),
        ('lainnya', 'Lainnya'),
    ]

    # Id untuk identifier dan nomor laporan sebagai kode unik
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    no_laporan = models.CharField(max_length=20, unique=True, editable=False, db_index=True)

    # Komponen laporan
    judul = models.CharField(max_length=255, db_index=True)
    deskripsi = models.TextField()
    lokasi = models.CharField(max_length=255, db_index=True)
    tanggal_kejadian = models.DateField(db_index=True)
    jenis_bullying = models.CharField(max_length=20, choices=JENIS_BULLYING_CHOICES, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='menunggu', db_index=True)
    catatan_admin = models.TextField(blank=True, null=True)

    pelapor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='laporan_bullying'
    )

    anonimitas = models.BooleanField(default=False)

    tanggal_laporan = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Kemahasiswaan atau Guru BK yang memproses laporan
    diproses_oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='laporan_bullying_diproses'
    )
    diproses_pada = models.DateTimeField(null=True, blank=True)

    # Alasan pembatalan laporan
    alasan_pembatalan = models.TextField(blank=True, null=True)

    # Meta data untuk laporan bullying
    class Meta:
        ordering = ['-tanggal_laporan']
        verbose_name = 'Laporan Bullying'
        verbose_name_plural = 'Laporan Bullying'

    def __str__(self):
        return f"{self.no_laporan} - {self.judul}"

    # Generate nomor laporan otomatis
    def save(self, *args, **kwargs):
        if not self.no_laporan:
            year = timezone.now().year
            last_laporan = LaporanBullying.objects.filter(
                no_laporan__startswith=f"LB-{year}-"
            ).order_by('-no_laporan').first()

            if last_laporan:
                last_number = int(last_laporan.no_laporan.split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1

            self.no_laporan = f"LB-{year}-{str(new_number).zfill(4)}"

        super().save(*args, **kwargs)

    # Nama pelapor (anonim / asli)
    def get_nama_pelapor(self):
        if self.anonimitas:
            return "Pengguna Anonim"
        return self.pelapor.nama_lengkap

    # Status verifikasi akun pelapor
    def is_pelapor_terverifikasi(self):
        return getattr(self.pelapor, 'is_verified', False)

# Model Foto Bukti Bullying
class FotoBuktiBullying(models.Model):
    # Id untuk identifier foto
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Laporan bullying yang terkait dengan foto
    laporan = models.ForeignKey(
        LaporanBullying,
        on_delete=models.CASCADE,
        related_name='foto_bukti'
    )

    # Foto bukti bullying
    foto = models.ImageField(upload_to=laporan_bullying_foto_upload_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    # Meta data untuk foto bukti bullying
    class Meta:
        ordering = ['uploaded_at']
        verbose_name = 'Foto Bukti Bullying'
        verbose_name_plural = 'Foto Bukti Bullying'

    def __str__(self):
        return f"Foto untuk {self.laporan.no_laporan}"

class RiwayatStatusBullying(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    laporan = models.ForeignKey(
        LaporanBullying,
        on_delete=models.CASCADE,
        related_name='riwayat_status'
    )

    status = models.CharField(
        max_length=20,
        choices=LaporanBullying.STATUS_CHOICES
    )

    catatan = models.TextField(blank=True, null=True)

    diubah_oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Riwayat Status Bullying'
        verbose_name_plural = 'Riwayat Status Bullying'

    def __str__(self):
        return f"{self.laporan.no_laporan} - {self.status}"