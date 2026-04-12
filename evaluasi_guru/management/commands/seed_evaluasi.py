from django.core.management.base import BaseCommand
from evaluasi_guru.models import KategoriPenilaian, Indikator

class Command(BaseCommand):
    help = 'Seeds initial master data for evaluasi guru indicators'

    def handle(self, *args, **kwargs):
        data = {
            "Kompetensi Pengajaran": [
                "Guru menjelaskan materi dengan jelas dan mudah dipahami.",
                "Guru menguasai materi yang diajarkan.",
                "Guru menggunakan metode pembelajaran yang bervariasi dan menarik.",
                "Guru memberikan kesempatan kepada siswa untuk bertanya atau berdiskusi.",
                "Guru memberikan umpan balik terhadap tugas atau hasil belajar siswa."
            ],
            "Profesionalisme": [
                "Guru datang tepat waktu dan mengelola waktu pembelajaran dengan baik.",
                "Guru memberikan penilaian secara objektif dan transparan.",
                "Guru konsisten dalam menerapkan aturan di kelas."
            ],
            "Sikap dan Interaksi": [
                "Guru bersikap sopan dan menghargai siswa.",
                "Guru menciptakan suasana kelas yang aman dan nyaman.",
                "Guru responsif terhadap pertanyaan atau kesulitan siswa.",
                "Guru tidak membeda-bedakan siswa."
            ]
        }

        self.stdout.write("Menghapus data kuesioner lama (bila ada)...")
        KategoriPenilaian.objects.all().delete()
        
        self.stdout.write("Memasukkan master data pertanyaan (Indikator)...")
        
        for nama_kategori, indikators in data.items():
            kategori = KategoriPenilaian.objects.create(nama=nama_kategori)
            self.stdout.write(f"Kategori: {kategori.nama}")
            
            for index, deskripsi in enumerate(indikators, start=1):
                ind = Indikator.objects.create(
                    kategori=kategori,
                    deskripsi=deskripsi,
                    urutan=index
                )
                self.stdout.write(f"  - [{ind.id}] (Urutan {index}) {ind.deskripsi}")
                
        self.stdout.write(self.style.SUCCESS("Data berhasil dimasukkan ke database!"))
