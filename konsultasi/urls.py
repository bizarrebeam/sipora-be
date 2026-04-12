"""
Konfigurasi URL routing untuk aplikasi konsultasi.

Endpoints yang tersedia:

1. PBI-38 — Jadwal Ketersediaan Guru BK:
   - GET    /api/konsultasi/jadwal/
     Daftar jadwal (filter by role: guru_bk lihat milik sendiri, siswa lihat yang tersedia)
   - POST   /api/konsultasi/jadwal/
     Guru BK membuat jadwal baru
   - PUT    /api/konsultasi/jadwal/<uuid:id>/
     Guru BK mengubah jadwal milik sendiri
   - DELETE /api/konsultasi/jadwal/<uuid:id>/
     Guru BK menghapus jadwal milik sendiri (hanya jika belum dipesan)

2. PBI-39 — Membuat Booking Konsultasi:
   - POST   /api/konsultasi/booking/
     Siswa membuat booking baru untuk slot jadwal
     Menggunakan atomic transaction + select_for_update untuk prevent race condition

3. PBI-43 — Daftar & Detail Booking:
   - GET    /api/konsultasi/booking/
     Daftar booking (filter by role: siswa lihat milik sendiri, guru_bk lihat semua)
   - GET    /api/konsultasi/booking/<uuid:id>/
     Detail satu booking (siswa hanya bisa lihat booking milik sendiri)
"""

from django.urls import path
from .views import (
    JadwalKonsultasiListCreateView,
    JadwalKonsultasiDetailView,
    BookingKonsultasiView,
    DetailBookingKonsultasiView,
)

urlpatterns = [
    # ════════════════════════════════════════════════════════════════════════
    # PBI-38 — Jadwal Ketersediaan Guru BK
    # ════════════════════════════════════════════════════════════════════════
    # GET, POST — /api/konsultasi/jadwal/
    path('jadwal/', JadwalKonsultasiListCreateView.as_view()),
    
    # PUT, DELETE — /api/konsultasi/jadwal/<uuid:id>/
    path('jadwal/<uuid:id>/', JadwalKonsultasiDetailView.as_view()),

    # ════════════════════════════════════════════════════════════════════════
    # PBI-39 & PBI-43 — Booking Konsultasi
    # ════════════════════════════════════════════════════════════════════════
    # GET — daftar booking (siswa: milik sendiri, guru_bk: semua)
    # POST — siswa membuat booking baru untuk slot jadwal
    path('booking/', BookingKonsultasiView.as_view()),
    
    # GET — detail satu booking berdasarkan ID
    # (siswa hanya bisa akses milik sendiri, guru_bk bisa akses semua)
    path('booking/<uuid:id>/', DetailBookingKonsultasiView.as_view()),
]