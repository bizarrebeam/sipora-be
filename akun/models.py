from django.contrib.auth.models import AbstractUser
from django.db import models

class Pengguna(AbstractUser):
    ROLE_CHOICES = [
        ('kemahasiswaan', 'Kemahasiswaan'),
        ('guru_bk', 'Guru BK'),
        ('pelapor', 'Pelapor'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    nisn = models.CharField(max_length=10, null=True, blank=True, unique=True)
    nama_lengkap = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.username} - {self.role}"