"""
Models for the Account (Akun) Application.

This module defines the custom user model used across the SIPORA platform,
featuring role-based access control (RBAC), verification tracking, and
Optimistic Concurrency Control (OCC) via the `updated_at` field.
"""

import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from datetime import date

class Pengguna(AbstractUser):
    """
    Custom User model representing all authentication entities (Siswa, Kemahasiswaan, Guru, Guru BK) in the system.
    Extends Django's AbstractUser to include domain-specific fields, verification tracking, and OCC metadata.
    """
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

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.username} - {self.role}"


def get_tahun_ajaran():
    """
    Calculates the current academic year based on the current date.
    The academic year begins in July.
    
    Returns:
        str: Formatted academic year string (e.g., '2025/2026').
    """
    today = date.today()
    if today.month >= 7:
        return f"{today.year}/{today.year + 1}"
    return f"{today.year - 1}/{today.year}"


def get_semester():
    """
    Determines the current academic semester based on the month.
    Ganjil (Odd) runs from July to December. Genap (Even) runs from January to June.
    
    Returns:
        str: 'Ganjil' or 'Genap'.
    """
    today = date.today()
    return "Ganjil" if today.month >= 7 else "Genap"

class MataPelajaranGuruSemester(models.Model):
    """
    Model for mapping a teacher (Guru) to multiple subjects (Mata Pelajaran)
    and the classes (Kelas) they teach, historically tracked per semester.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    guru = models.ForeignKey(Pengguna, on_delete=models.CASCADE, related_name='riwayat_mengajar', db_index=True)
    nama_mata_pelajaran = models.CharField(max_length=255)
    kelas_diajar = models.JSONField(default=list)
    tahun_ajaran = models.CharField(max_length=9, db_index=True)
    semester = models.CharField(max_length=6, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-tahun_ajaran', '-semester', 'nama_mata_pelajaran']

    def __str__(self):
        return f"{self.guru.username} - {self.nama_mata_pelajaran} ({self.semester} {self.tahun_ajaran})"
