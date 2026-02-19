from django.core.management.base import BaseCommand
from akun.models import Pengguna

class Command(BaseCommand):
    help = 'Membuat akun default untuk kemahasiswaan dan guru BK'

    def handle(self, *args, **kwargs):
        if not Pengguna.objects.filter(username='kemahasiswaan').exists():
            Pengguna.objects.create_superuser(
                username='kemahasiswaan',
                password='password123',
                role='kemahasiswaan',
                nama_lengkap='Admin Kemahasiswaan'
            )
            self.stdout.write(self.style.SUCCESS('Akun kemahasiswaan berhasil dibuat.'))

        if not Pengguna.objects.filter(username='gurubk').exists():
            Pengguna.objects.create_user(
                username='gurubk',
                password='password123',
                role='guru_bk',
                nama_lengkap='Guru Bimbingan Konseling'
            )
            self.stdout.write(self.style.SUCCESS('Akun guru_bk berhasil dibuat.'))