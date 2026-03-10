import uuid
from django.db import models

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