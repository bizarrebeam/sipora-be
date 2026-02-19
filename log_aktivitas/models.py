from django.db import models
from django.conf import settings

class LogAktivitas(models.Model):
    pengguna = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    aksi = models.CharField(max_length=255)
    deskripsi = models.TextField()
    waktu = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    modul = models.CharField(max_length=100)

    def save(self, *args, **kwargs):
        if self.pk:
            return
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    class Meta:
        ordering = ['-waktu']

    def __str__(self):
        return f"{self.aksi} - {self.waktu}"