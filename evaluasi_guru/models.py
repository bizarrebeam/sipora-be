from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()

def get_tahun_ajaran(tanggal):
    """
    Menentukan tahun ajaran (misal '2023/2024') berdasarkan tanggal.
    Tahun ajaran baru dimulai setiap bulan Juli.
    """
    if tanggal.month >= 7:
        return f"{tanggal.year}/{tanggal.year + 1}"
    return f"{tanggal.year - 1}/{tanggal.year}"


def get_semester(tanggal):
    """
    Menentukan semester berdasarkan bulan.
    Ganjil: Juli - Desember
    Genap: Januari - Juni
    """
    return "Ganjil" if tanggal.month >= 7 else "Genap"

class KategoriPenilaian(models.Model):
    nama = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nama

class Indikator(models.Model):
    kategori = models.ForeignKey(
        KategoriPenilaian,
        on_delete=models.CASCADE,
        related_name="indikator"
    )
    deskripsi = models.TextField()
    
    urutan = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["urutan"]   

    def __str__(self):
        return self.deskripsi

class Evaluasi(models.Model):
    siswa = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="evaluasi_diberikan",
        limit_choices_to={"role": "siswa"},
    )
    guru = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="evaluasi_diterima",
        limit_choices_to={"role": "guru"}, 
    )
    
    komentar = models.TextField(blank=True, null=True)
    
    tahun_ajaran = models.CharField(max_length=9, blank=True)  
    semester = models.CharField(max_length=6, blank=True)     
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("siswa", "guru", "tahun_ajaran", "semester")
        verbose_name = "Evaluasi"
        verbose_name_plural = "Evaluasi"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.tahun_ajaran or not self.semester:
            now = self.created_at or timezone.now()
            if not self.tahun_ajaran:
                self.tahun_ajaran = get_tahun_ajaran(now)
            if not self.semester:
                self.semester = get_semester(now)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.siswa} → {self.guru} | {self.semester} {self.tahun_ajaran}"

class NilaiEvaluasi(models.Model):
    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]

    evaluasi = models.ForeignKey(
        Evaluasi,
        on_delete=models.CASCADE,
        related_name="nilai"
    )
    indikator = models.ForeignKey(
        Indikator,
        on_delete=models.CASCADE
    )
    nilai = models.PositiveSmallIntegerField(choices=RATING_CHOICES, validators=[MinValueValidator(1), MaxValueValidator(5)])

    def __str__(self):
        return f"{self.indikator} - {self.nilai}"
