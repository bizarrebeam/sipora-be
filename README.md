# SIPORA Backend

Proyek ini adalah bagian Backend dari Sistem Informasi Portal Akademik (SIPORA), yang dibangun menggunakan Django REST Framework.

## 📂 Struktur Direktori

Berikut penjelasan singkat mengenai folder-folder utama dalam direktori `sipora-be`:

- **`manage.py`**: Skrip utilitas bawaan Django untuk menjalankan *development server*, migrasi database, dan perintah-perintah *command line* lainnya.
- **`requirements.txt`**: Daftar libary dan dependensi Python yang dubutuhkan aplikasi, di-*install* lewat `pip`.
- **`sipora_be/`**: Direktori ini adalah tempat konfigurasi inti dari proyek Django.
  - Berisi `settings.py` (pengaturan aplikasi, database, *middleware*, dll).
  - Berisi `urls.py` (kumpulan *routing endpoint* utama aplikasi).
- **`core/`**: *App* Django *generic*. Umumnya berisi *base model*, kustomisasi *exception handler*, *middleware*, kustom *permission*, atau *renderer class* yang digunakan pada *app* lain.
- **`akun/`**: Aplikasi Django khusus yang menangani entitas/model `Pengguna` beserta logika autentikasinya (registrasi, dan penanganan JWT *toke*n).
- **`log_aktivitas/`**: Aplikasi Django untuk me-*log*, merekam, dan melacak riwayat *action*/*request* yang dieksekusi oleh setiap pengguna pada *endpoint* SIPORA.
- **`.env` / `.env.prod`**: File *environment variable*. Di file inilah letak nilai-nilai konfigurasi yang bersifat rahasia seperti `SECRET_KEY`, kredensial *database* (*Host*, *Port*, *User*, *Password*), dan flag `DEBUG`.

---

## 🚀 Panduan Instalasi (Development)

Untuk menyalakan *server backend* lokal di laptop Anda, ikuti langkah-langkah di bawah ini:

### 1. Prasyarat Sistem
Pastikan Anda sudah menginstal **Python** (versi 3.9+) dan **pip**.

### 2. Buat dan Aktifkan Virtual Environment
Virtual environment sangat disarankan agar *package* Python dari proyek ini terisolasi dan sistem operasi Anda tetap bersih.

Di dalam terminal (pastikan *path*-nya sedang berada di root folder `sipora-be` ini):
- **Bagi Pengguna Windows:**
  ```bash
  python -m venv env
  .\env\Scripts\activate
  ```
- **Bagi Pengguna MacOS / Linux:**
  ```bash
  python3 -m venv env
  source env/bin/activate
  ```

### 3. Install Dependensi
Setelah `env` aktif (ditandai dengan awalan `(env)` di terminal), jalankan instalasi *package*:
```bash
pip install -r requirements.txt
```

### 4. Setup Environment Variable
Buat file baru di direktori root dengan nama `.env`. Isikan setidaknya kunci `SECRET_KEY` (bersifat acak, gunakan *string* bebas yang panjang dan sulit ditebak) agar *setting* Django bisa berjalan. Jika Anda menggunakan *database local* NeonDB/Supabase, lengkapi *credentials* *database* Anda juga, contohnya:
```env
SECRET_KEY=isi_dengan_random_string_panjang_sekali_minimal_50_karakter
DB_NAME=postgres
# dst...
```

### 5. Jalankan Database Migrations (opsional tapi disarankan)
Jika *database* baru, buat tabel-tabel *default* yang dibutuhkan Django (seperti Auth, Sessions) ke dalam *database*:
```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Jalankan Server!
Nyalakan *development server* Django:
```bash
python manage.py runserver
```
Secara *default*, *backend API* Anda akan berjalan pada `http://127.0.0.1:8000/`.
