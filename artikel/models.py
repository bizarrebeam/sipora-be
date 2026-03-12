from django.db import models
from django.core.validators import MinLengthValidator, MaxLengthValidator

import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone

# Character validation constants
JUDUL_MIN_CHARS = 5
JUDUL_MAX_CHARS = 70
KONTEN_MIN_CHARS = 400
KONTEN_MAX_CHARS = 10000
RINGKASAN_MIN_CHARS = 5
RINGKASAN_MAX_CHARS = 150
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def artikel_foto_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    new_filename = f"{uuid.uuid4()}.{ext}"
    return f"artikel/{instance.artikel.id}/{new_filename}"

class Artikel(models.Model):

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    judul = models.CharField(
        max_length=JUDUL_MAX_CHARS,
        validators=[MinLengthValidator(JUDUL_MIN_CHARS)]
    )
    ringkasan = models.TextField(
        blank=True,
        null=True,
        validators=[MaxLengthValidator(RINGKASAN_MAX_CHARS)]
    )
    konten = models.TextField(
        validators=[MinLengthValidator(KONTEN_MIN_CHARS), MaxLengthValidator(KONTEN_MAX_CHARS)]
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'artikel'
        ordering = ['-created_at']

    def __str__(self):
        return self.judul


class FotoArtikel(models.Model):
    """Model untuk menyimpan foto artikel sebagai entitas terpisah"""
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    artikel = models.ForeignKey(
        Artikel,
        on_delete=models.CASCADE,
        related_name='foto_artikel'
    )
    foto = models.ImageField(upload_to=artikel_foto_upload_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']
        verbose_name = 'Foto Artikel'
        verbose_name_plural = 'Foto Artikel'

    def __str__(self):
        return f"Foto untuk {self.artikel.judul}"
        return self.judul

class FotoBuktiPendukung(models.Model):    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    artikel = models.ForeignKey(
        Artikel,
        on_delete=models.CASCADE,
        related_name='foto_bukti'
    )
    foto = models.ImageField(upload_to=artikel_foto_upload_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['uploaded_at']
        verbose_name = 'Foto Bukti Pendukung'
        verbose_name_plural = 'Foto Bukti Pendukung'
    
    def __str__(self):
        return f"Foto untuk {self.artikel.no_artikel}"
