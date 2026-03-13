from django.db import models
from django.core.validators import MinLengthValidator, MaxLengthValidator

import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


# Character validation constants for Artikel fields
JUDUL_MIN_CHARS = 5  # Minimum characters for title
JUDUL_MAX_CHARS = 70  # Maximum characters for title
KONTEN_MIN_CHARS = 400  # Minimum characters for content
KONTEN_MAX_CHARS = 10000  # Maximum characters for content
RINGKASAN_MIN_CHARS = 5  # Minimum characters for summary
RINGKASAN_MAX_CHARS = 150  # Maximum characters for summary
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB, maximum image upload size



def artikel_foto_upload_path(instance, filename):
    """
    Generate upload path for article images.
    Images are stored under media/artikel/<artikel_id>/<uuid>.<ext>
    """
    ext = filename.split('.')[-1]
    new_filename = f"{uuid.uuid4()}.{ext}"
    return f"artikel/{instance.artikel.id}/{new_filename}"


class Artikel(models.Model):
    """
    Main model representing an article.
    Stores title, summary, content, status, and timestamps.
    """

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
        """
        String representation of the article (returns the title).
        """
        return self.judul



class FotoArtikel(models.Model):
    """
    Model for storing images related to an article.
    Each image is linked to a single Artikel instance.
    """
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
        """
        String representation of the image (shows the article title).
        """
        return f"Foto untuk {self.artikel.judul}"


class FotoBuktiPendukung(models.Model):
    """
    Model for storing supporting evidence images for an article.
    Used for additional documentation or proof.
    """
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
        """
        String representation of the supporting image (shows the article number).
        """
        return f"Foto untuk {self.artikel.no_artikel}"
