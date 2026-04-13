Kadek Savitri (2306203236)
Kelompok Propenat (C2H5COOH) Kelas B 

SIPORA (Sistem Pelaporan & Aspirasi)
Sistem ini dikembangkan untuk membantu sekolah dalam mengelola laporan kerusakan fasilitas, aspirasi siswa dan guru, serta monitoring laporan melalui dashboard. Sistem menggunakan UUID sebagai ID utama dan mendukung beberapa role: Siswa, Guru, Pelapor, dan Kemahasiswaan.

1. FITUR YANG DIKERJAKAN

MENGELOLA LAPORAN KERUSAKAN FASILITAS SEKOLAH

1.1 Mengedit Laporan Kerusakan (PBI - 17)
    Tujuan:
    Pelapor  dapat memperbarui laporan yang telah dibuat jika ada kesalahan atau tambahan informasi.
    Endpoint: PUT /api/laporan-kerusakan/{id}

    Aturan Backend: 
    Hanya pembuat laporan yang dapat mengedit laporannya sendiri. Laporan hanya bisa diedit jika status “Menunggu Konfirmasi”.

    Ketentuan Frontend:

    Form edit menampilkan data lama yang sudah tersimpan. Tombol “Ubah Laporan” aktif jika semua field valid. Setelah berhasil, muncul pesan sukses dan redirect ke halaman detail.

1.2 Membatalakn Laporan Kerusakan (PBI - 18)
    Tujuan: 
    Pelapor dapat membatalkan laporan yang sudah ia sampaikan sebelumnya agar tidak diproses lebih lanjut oleh kemahasiswaan.
    Aturan Backend: 
    Hanya pembuat laporan yang dapat mengedit laporannya sendiri. Laporan hanya bisa dibatalkan jika status “Menunggu Konfirmasi”.
    Terdapat tombol "Batalkan" pada halaman detail laporan. Setlah berhasil maka akan munucl pesan sukses dan kembali ke halaman kerusakan laporan. 

2. MENGELOLA ASPIRASI

2.1 Membuat Aspirasi (PBI-26)

    Tujuan:
    Pelapor dapat menyampaikan pendapat, masukan, dan saran kepada pihak sekolah.

    Endpoint:
    POST /api/aspirasi

    Aturan Backend: ID menggunakan UUID. Hanya siswa dan guru yang dapat membuat aspirasi. Mengembalikan status 200 jika berhasil.

    Ketentuan Frontend:
    Form input lengkap dengan field wajib. Tombol “Kirim Aspirasi” aktif jika field wajib terisi. Setelah berhasil, redirect ke halaman detail atau riwayat aspirasi.

2.2 Mengedit Aspirasi (PBI-27)
    Tujuan:
    Pelapor dapat memperbaiki atau melengkapi aspirasi yang telah diajukan.

    Endpoint:
    PUT /api/aspirasi/{id}

    Aturan Backend:
    Hanya pemilik aspirasi yang dapat mengedit. Mengembalikan status 200 jika berhasil.

    Ketentuan Frontend:
    Form edit terisi otomatis dengan data lama. Tombol “Simpan Perubahan” aktif jika ada perubahan dan data valid Menampilkan pesan sukses setelah berhasil.

2.3 Menandai Aspirasi (PBI-28)
    Tujuan:
    Kemahasiswaan dapat menandai aspirasi yang menarik untuk dipertimbangkan.

    Endpoint:
    GET /api/aspirasi/{id}

    Aturan Backend:
    Mengembalikan status 200 jika berhasil ditandai.

    Ketentuan Frontend:
    Tersedia toggle “Ditandai”. Menampilkan pesan sukses setelah toggle diaktifkan.

2.4 Melihat Riwayat Aspirasi Pribadi (PBI-29)
    Tujuan: 
    Pelapor dapat melihat seluruh aspirasi yang telah dibuatnya sebelumnya. 

    Aturan Backend: 
    Hanya role siswa/guru yang dapat melihat aspirasi tersebut. 

    Ketentuan Frontend: 
    Menampilkan keseluruhan aspirasi yang pernah di buat sebelumnya dalam bentuk cards yang memberikan informasi mengenai judul, tanggal, dan kategorinya. 

2.5 Melihat Daftar Aspirasi (PBI-30)

    Tujuan:
    Kemahasiswaan dapat melihat seluruh aspirasi.
    Pelapor dapat melihat aspirasi miliknya sendiri.

    Endpoint:
    GET /api/aspirasi

    Aturan Backend:
    Role kemahasiswaan melihat seluruh data. Role pelapor hanya melihat data miliknya.

    Ketentuan Frontend:
    Tampilan tabel untuk kemahasiswaan.Tampilan card/list untuk pelapor. Terdapat search bar berdasarkan kata kunci. Terdapat filter kategori.  Terdapat pagination jika data banyak. Data diurutkan berdasarkan tanggal terbaru. Jika kosong, menampilkan pesan “belum ada aspirasi yang tersedia”.

2.6 Melihat Detail Aspirasi (PBI-31)

    Tujuan:
    Pengguna (guru, siswa, dan kemahasiswaan) dapat melihat rincian detail dari aspirasi yang diajukan

    Endpoint:
    GET /api/aspirasi

    Aturan Backend:
    Guru dan siswa hanya dapat melihat detail dari laporan yang telah diajukan sebelumnya. Kemahasiswaan dapat melihat detail dari seluruh apsirasi yang ada dalam sistem. 

    Ketentuan Frontend:
    Tampilan rincian detail dari aspirasi tersebut. Kemahasiswaan dapat mempertimbangkan laporan dengan menandari laporan aspirasi di halam detail tersebut.

3. DASHBOARD MONITORING SEKOLAH

3.1 Dashboard Rekap Konsultasi (PBI-28)

    Tujuan:
    Kemahasiswaan dapat memantau seluruh laporan secara terpusat dalam periode tertentu.

    Endpoint:
    GET /api/dashboard-konsultasi

    Fitur Backend:
    Mendukung filter rentang waktu. Mengembalikan total laporan. Mengembalikan jumlah laporan berdasarkan status. Mengembalikan statistik harian.

    Ketentuan Frontend:
    Ringkasan dalam bentuk cards. Pie chart berdasarkan status konsultasi. Bar chart distribusi per periode. Filter tanggal (mingguan/bulanan). Default: ringkasan bulanan dan chart tahunan.

3.2 Dashboard Rekap Pelaporan dan Aspirasi (PBI-29)

    Tujuan:
    Kemahasiswaan dapat memantau jumlah, status, dan perkembangan laporan serta aspirasi secara keseluruhan.

    Endpoint: GET /api/dashboard-konsultasi

    Fitur Backend:
    Mendukung filter ascending dan descending. Mengembalikan total laporan Mengembalikan jumlah berdasarkan status. Mengembalikan statistik kategori terbanyak.

    Ketentuan Frontend:
    Cards berdasarkan status laporan. Pie chart aspirasi per kategori. Bar chart distribusi laporan berdasarkan kategori. Statistik aspirasi per periode. Filter periode waktu.Default tampilan bulanan dan tahunan.

