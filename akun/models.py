import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from datetime import date


class Pengguna(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ROLE_CHOICES = [
        ('kemahasiswaan', 'Kemahasiswaan'),
        ('guru_bk', 'Guru BK'),
        ('siswa', 'Siswa'),
        ('guru', 'Guru'),
    ]
    KELAS_CHOICES = [
        ('7A', '7A'), ('7B', '7B'),
        ('8A', '8A'), ('8B', '8B'),
        ('9A', '9A'), ('9B', '9B'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    nisn = models.CharField(max_length=10, null=True, blank=True, unique=True)
    nuptk = models.CharField(max_length=16, null=True, blank=True, unique=True)
    nama_lengkap = models.CharField(max_length=255)
    kelas = models.CharField(max_length=5, choices=KELAS_CHOICES, null=True, blank=True)
    mata_pelajaran = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.username} - {self.role}"


def get_tahun_ajaran():
    today = date.today()
    if today.month >= 7:
        return f"{today.year}/{today.year + 1}"
    return f"{today.year - 1}/{today.year}"


def get_semester():
    today = date.today()
    return "Ganjil" if today.month >= 7 else "Genap"