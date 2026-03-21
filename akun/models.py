import uuid
from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import date

class ActiveUserManager(UserManager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


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

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, db_index=True)
    nis = models.CharField(max_length=4, null=True, blank=True, unique=True, db_index=True)
    nuptk = models.CharField(max_length=16, null=True, blank=True, unique=True, db_index=True)
    nama_lengkap = models.CharField(max_length=255, db_index=True)
    email = models.EmailField('email address', max_length=254, null=True, blank=True, unique=True, db_index=True)
    kelas = models.CharField(max_length=5, choices=KELAS_CHOICES, null=True, blank=True)
    mata_pelajaran = models.CharField(max_length=255, null=True, blank=True)
    is_verified = models.BooleanField(default=False, db_index=True)

    # WBS Soft Delete Logic for Acccount Deactivations
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL, 
        related_name='+'
    )

    objects = ActiveUserManager()
    all_objects = UserManager()

    def soft_delete(self, user=None):
        self.is_active = False # Additional deactivation flag
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save()

    def delete(self, *args, **kwargs):
        self.soft_delete()

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