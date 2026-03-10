from django.db import models

import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


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

    judul = models.CharField(max_length=255)
    ringkasan = models.TextField(blank=True, null=True)
    konten = models.TextField()

    gambar = models.ImageField(
        upload_to='artikel/',
        blank=True,
        null=True
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
