"""
Konfigurasi URL routing untuk aplikasi konsultasi.

Endpoints yang tersedia:

1. PBI-38 — Jadwal Ketersediaan Guru BK:
   - GET    /api/konsultasi/jadwal/
   - POST   /api/konsultasi/jadwal/
   - PUT    /api/konsultasi/jadwal/<uuid:id>/
   - DELETE /api/konsultasi/jadwal/<uuid:id>/

2. PBI-39 — Membuat Booking Konsultasi:
   - POST   /api/konsultasi/booking/

3. PBI-40 — Mengonfirmasi Jadwal Booking (Guru BK):
   - PATCH  /api/konsultasi/booking/<uuid:id>/confirm/
     Body: { aksi: 'setujui'|'tolak', alasan?: str }

4. PBI-41 — Membatalkan Jadwal Booking (Siswa & Guru BK):
   - PATCH  /api/konsultasi/booking/<uuid:id>/cancel/
     Body: { alasan: str }

5. PBI-42 — Reschedule Jadwal Booking (Siswa):
   - PATCH  /api/konsultasi/booking/<uuid:id>/reschedule/
     Body: { jadwal_baru: UUID }

6. PBI-43 — Daftar & Detail Booking:
   - GET    /api/konsultasi/booking/
   - GET    /api/konsultasi/booking/<uuid:id>/
"""

from django.urls import path
from .views import (
    JadwalKonsultasiListCreateView,
    JadwalKonsultasiDetailView,
    BookingKonsultasiView,
    DetailBookingKonsultasiView,
    KonfirmasiBookingView,
    BatalkanBookingView,
    RescheduleBookingView,
    SelesaiBookingView, 
    TidakHadirBookingView, 
)

urlpatterns = [
    # ════════════════════════════════════════════════════════════════════════
    # PBI-38 — Jadwal Ketersediaan Guru BK
    # ════════════════════════════════════════════════════════════════════════
    path('jadwal/', JadwalKonsultasiListCreateView.as_view()),
    path('jadwal/<uuid:id>/', JadwalKonsultasiDetailView.as_view()),

    # ════════════════════════════════════════════════════════════════════════
    # PBI-39 & PBI-43 — Booking Konsultasi
    # ════════════════════════════════════════════════════════════════════════
    path('booking/', BookingKonsultasiView.as_view()),
    path('booking/<uuid:id>/', DetailBookingKonsultasiView.as_view()),

    # ════════════════════════════════════════════════════════════════════════
    # PBI-40 — Konfirmasi Booking (Guru BK)
    # ════════════════════════════════════════════════════════════════════════
    path('booking/<uuid:id>/confirm/', KonfirmasiBookingView.as_view()),

    # ════════════════════════════════════════════════════════════════════════
    # PBI-41 — Batalkan Booking (Siswa & Guru BK)
    # ════════════════════════════════════════════════════════════════════════
    path('booking/<uuid:id>/cancel/', BatalkanBookingView.as_view()),

    # ════════════════════════════════════════════════════════════════════════
    # PBI-42 — Reschedule Booking (Siswa)
    # ════════════════════════════════════════════════════════════════════════
    path('booking/<uuid:id>/reschedule/', RescheduleBookingView.as_view()),

    # Tandai Selesai (Guru BK)
    path('booking/<uuid:id>/selesai/', SelesaiBookingView.as_view()),

    # Tandai Tidak Hadir (Guru BK)
    path('booking/<uuid:id>/tidak-hadir/', TidakHadirBookingView.as_view()),
]