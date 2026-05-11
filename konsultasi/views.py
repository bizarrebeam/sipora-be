"""
Views module for the konsultasi application.

PBI-38 : Mengelola jadwal ketersediaan Guru BK
PBI-39 : Membuat booking jadwal konsultasi (Siswa)
PBI-40 : Mengonfirmasi jadwal booking (Guru BK)
PBI-41 : Membatalkan jadwal booking konsultasi (Siswa & Guru BK)
PBI-42 : Melakukan reschedule jadwal booking konsultasi (Siswa)
PBI-43 : Melihat daftar booking konsultasi
"""

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone
from datetime import datetime

from akun.decorators import role_required
from log_aktivitas.utils import catat_log

from .models import JadwalKonsultasi, BookingKonsultasi
from .serializers import (
    JadwalKonsultasiSerializer,
    JadwalKonsultasiListSerializer,
    BookingKonsultasiCreateSerializer,
    BookingKonsultasiListSerializer,
    BookingKonsultasiDetailSerializer,
)


# =============================================================================
# PBI-38 — Mengelola Jadwal Ketersediaan Guru BK
# GET, POST  : /api/konsultasi/jadwal/
# PUT, DELETE: /api/konsultasi/jadwal/<uuid:id>/
# =============================================================================

class JadwalKonsultasiListCreateView(APIView):
    """
    API view untuk list dan create jadwal konsultasi (PBI-38).
    
    Permissions:
    - GET  : Guru BK dan Siswa (authenticated)
    - POST : Guru BK only
    
    GET - Daftar jadwal konsultasi dengan filter berdasarkan role:
        - Guru BK: jadwal milik sendiri (dengan info siswa yang booking jika ada)
        - Siswa  : jadwal yang status 'tersedia' saja
        
        Query params:
        - tanggal: Filter jadwal berdasarkan tanggal (format: YYYY-MM-DD)
        
    POST - Guru BK membuat slot jadwal ketersediaan baru.
        Akan divalidasi melalui JadwalKonsultasiSerializer:
        - Tanggal tidak boleh sebelum hari ini
        - Waktu mulai < waktu selesai
        - Tidak boleh tabrakan dengan jadwal lain
        - Untuk hari ini, waktu mulai harus >= sekarang
    """
    permission_classes = [IsAuthenticated]

    @role_required('guru_bk', 'siswa')
    def get(self, request):
        if request.user.role == 'guru_bk':
            jadwal_qs = JadwalKonsultasi.objects.filter(guru_bk=request.user).select_related('booking__siswa')
        else:
            jadwal_qs = JadwalKonsultasi.objects.filter(status='tersedia').select_related('booking__siswa')

        tanggal = request.query_params.get('tanggal')
        if tanggal:
            jadwal_qs = jadwal_qs.filter(tanggal=tanggal)

        serializer = JadwalKonsultasiListSerializer(jadwal_qs, many=True)
        return Response({
            "message": "Berhasil mengambil daftar jadwal.",
            "data": serializer.data
        })

    @role_required('guru_bk')
    def post(self, request):
        serializer = JadwalKonsultasiSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            jadwal = serializer.save(guru_bk=request.user)

            catat_log(
                user=request.user,
                aksi='BUAT_JADWAL_KONSULTASI',
                deskripsi=f'Membuat jadwal konsultasi pada {jadwal.tanggal} '
                          f'{jadwal.waktu_mulai}-{jadwal.waktu_selesai}',
                modul='konsultasi_bk'
            )

            return Response({
                "message": "Jadwal berhasil dibuat.",
                "data": JadwalKonsultasiSerializer(jadwal).data
            })

        return Response(serializer.errors, status=400)


class JadwalKonsultasiDetailView(APIView):
    """
    API view untuk update dan delete jadwal konsultasi (PBI-38).
    
    Permissions:
    - PUT    : Guru BK yang membuat jadwal (hanya jika belum dipesan)
    - DELETE : Guru BK yang membuat jadwal (hanya jika belum dipesan)
    """
    permission_classes = [IsAuthenticated]

    def _get_jadwal(self, id, guru_bk):
        try:
            return JadwalKonsultasi.objects.get(id=id, guru_bk=guru_bk)
        except JadwalKonsultasi.DoesNotExist:
            return None

    @role_required('guru_bk')
    def put(self, request, id):
        jadwal = self._get_jadwal(id, request.user)
        if not jadwal:
            return Response({"error": "Jadwal tidak ditemukan."}, status=404)

        if jadwal.is_booked():
            return Response(
                {"error": "Jadwal tidak dapat diubah karena sudah dipesan oleh siswa."},
                status=400
            )

        serializer = JadwalKonsultasiSerializer(
            jadwal,
            data=request.data,
            partial=True,
            context={'request': request}
        )

        if serializer.is_valid():
            jadwal = serializer.save()

            catat_log(
                user=request.user,
                aksi='EDIT_JADWAL_KONSULTASI',
                deskripsi=f'Mengubah jadwal konsultasi ID {jadwal.id}',
                modul='konsultasi_bk'
            )

            return Response({
                "message": "Jadwal berhasil diperbarui.",
                "data": JadwalKonsultasiSerializer(jadwal).data
            })

        return Response(serializer.errors, status=400)

    @role_required('guru_bk')
    def delete(self, request, id):
        jadwal = self._get_jadwal(id, request.user)
        if not jadwal:
            return Response({"error": "Jadwal tidak ditemukan."}, status=404)

        if jadwal.is_booked():
            return Response(
                {"error": "Jadwal tidak dapat dihapus karena sudah dipesan oleh siswa."},
                status=400
            )

        jadwal_info = str(jadwal)
        jadwal.delete()

        catat_log(
            user=request.user,
            aksi='HAPUS_JADWAL_KONSULTASI',
            deskripsi=f'Menghapus jadwal konsultasi: {jadwal_info}',
            modul='konsultasi_bk'
        )

        return Response({"message": "Jadwal berhasil dihapus."})


# =============================================================================
# PBI-39 & PBI-43 — Booking Konsultasi
# PBI-39: Membuat booking (Siswa)
# PBI-43: Daftar & Detail booking (Siswa lihat milik sendiri, Guru BK lihat semua)
# =============================================================================

class BookingKonsultasiView(APIView):
    """
    API view untuk list dan create booking konsultasi (PBI-39, PBI-43).
    
    Permissions:
    - GET  : Siswa dan Guru BK (authenticated)
    - POST : Siswa only
    """
    permission_classes = [IsAuthenticated]

    @role_required('siswa', 'guru_bk')
    def get(self, request):
        user = request.user

        if user.role == 'siswa':
            booking_qs = BookingKonsultasi.objects.filter(
                siswa=user
            ).select_related('jadwal', 'siswa')
        else:
            booking_qs = BookingKonsultasi.objects.all().select_related(
                'jadwal', 'siswa'
            )

        tanggal = request.query_params.get('tanggal')
        if tanggal:
            booking_qs = booking_qs.filter(jadwal__tanggal=tanggal)

        status_filter = request.query_params.get('status')
        if status_filter:
            booking_qs = booking_qs.filter(status=status_filter)

        serializer = BookingKonsultasiListSerializer(booking_qs, many=True)
        return Response({
            "message": "Berhasil mengambil daftar booking.",
            "data": serializer.data
        })

    @role_required('siswa')
    def post(self, request):
        serializer = BookingKonsultasiCreateSerializer(
            data=request.data,
            context={'request': request}
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        jadwal_id = serializer.validated_data['jadwal'].id

        try:
            with transaction.atomic():
                jadwal = JadwalKonsultasi.objects.select_for_update().get(id=jadwal_id)

                if jadwal.status != 'tersedia':
                    return Response(
                        {"error": "Slot jadwal sudah tidak tersedia. Silakan pilih slot lain."},
                        status=400
                    )

                slot_datetime = datetime.combine(jadwal.tanggal, jadwal.waktu_mulai)
                slot_datetime = timezone.make_aware(slot_datetime)
                if slot_datetime <= timezone.now():
                    return Response(
                        {"error": "Waktu slot yang dipilih sudah melewati waktu saat ini."},
                        status=400
                    )

                booking = BookingKonsultasi.objects.create(
                    siswa=request.user,
                    jadwal=jadwal,
                    deskripsi=serializer.validated_data['deskripsi'],
                    status='menunggu_konfirmasi'
                )

                jadwal.status = 'menunggu_konfirmasi'
                jadwal.save()

        except JadwalKonsultasi.DoesNotExist:
            return Response({"error": "Slot jadwal tidak ditemukan."}, status=404)

        catat_log(
            user=request.user,
            aksi='BUAT_BOOKING_KONSULTASI',
            deskripsi=f'Membuat booking konsultasi ID {booking.id} '
                      f'untuk jadwal {jadwal.tanggal} {jadwal.waktu_mulai}',
            modul='konsultasi_bk'
        )

        return Response({
            "message": "Booking berhasil dibuat.",
            "data": BookingKonsultasiDetailSerializer(booking).data
        })


class DetailBookingKonsultasiView(APIView):
    """
    API view untuk mengambil detail satu booking konsultasi (PBI-43).
    
    Permissions:
    - GET: Siswa (hanya booking milik sendiri) dan Guru BK (semua booking)
    """
    permission_classes = [IsAuthenticated]

    @role_required('siswa', 'guru_bk')
    def get(self, request, id):
        user = request.user

        try:
            if user.role == 'siswa':
                booking = BookingKonsultasi.objects.select_related(
                    'jadwal', 'siswa'
                ).get(id=id, siswa=user)
            else:
                booking = BookingKonsultasi.objects.select_related(
                    'jadwal', 'siswa'
                ).get(id=id)
        except BookingKonsultasi.DoesNotExist:
            return Response({"error": "Data booking tidak ditemukan."}, status=404)

        serializer = BookingKonsultasiDetailSerializer(booking)
        return Response({
            "message": "Berhasil mengambil detail booking.",
            "data": serializer.data
        })


# =============================================================================
# PBI-40 — Mengonfirmasi Jadwal Booking
# PATCH: /api/konsultasi/booking/<uuid:id>/confirm/
# =============================================================================

class KonfirmasiBookingView(APIView):
    """
    API view untuk konfirmasi atau penolakan booking oleh Guru BK (PBI-40).

    Permissions:
    - PATCH: Guru BK only

    PATCH - Guru BK menyetujui atau menolak booking siswa.
        Body:
        - aksi   : 'setujui' | 'tolak'  (REQUIRED)
        - alasan : str                   (REQUIRED jika aksi == 'tolak')

        Validasi:
        - Booking harus berstatus 'menunggu_konfirmasi'
        - Jika aksi 'setujui' → status booking menjadi 'dikonfirmasi', jadwal tetap terkunci
        - Jika aksi 'tolak'   → status booking menjadi 'ditolak', jadwal dikembalikan ke 'tersedia'
        - alasan_penolakan wajib diisi saat menolak
    """
    permission_classes = [IsAuthenticated]

    @role_required('guru_bk')
    def patch(self, request, id):
        aksi = request.data.get('aksi', '').strip()
        alasan = request.data.get('alasan', '').strip()

        if aksi not in ('setujui', 'tolak'):
            return Response(
                {"error": "Field 'aksi' harus bernilai 'setujui' atau 'tolak'."},
                status=400
            )

        try:
            booking = BookingKonsultasi.objects.select_related('jadwal', 'siswa').get(id=id)
        except BookingKonsultasi.DoesNotExist:
            return Response({"error": "Data booking tidak ditemukan."}, status=404)

        # Guru BK hanya bisa memproses booking di jadwal miliknya sendiri
        if booking.jadwal.guru_bk != request.user:
            return Response({"error": "Anda tidak memiliki akses ke booking ini."}, status=403)

        if booking.status != 'menunggu_konfirmasi':
            return Response(
                {"error": "Booking hanya dapat diproses jika berstatus 'Menunggu Konfirmasi'."},
                status=400
            )

        with transaction.atomic():
            jadwal = JadwalKonsultasi.objects.select_for_update().get(id=booking.jadwal.id)

            if aksi == 'setujui':
                booking.status = 'dikonfirmasi'
                booking.save()

                jadwal.status = 'dikonfirmasi'
                jadwal.save()

                catat_log(
                    user=request.user,
                    aksi='KONFIRMASI_BOOKING_KONSULTASI',
                    deskripsi=f'Menyetujui booking ID {booking.id} dari siswa {booking.siswa}',
                    modul='konsultasi_bk'
                )

                return Response({
                    "message": "Booking berhasil dikonfirmasi.",
                    "data": BookingKonsultasiDetailSerializer(booking).data
                })

            else:  # tolak
                if not alasan:
                    return Response(
                        {"error": "Alasan penolakan wajib diisi saat menolak booking."},
                        status=400
                    )

                booking.status = 'ditolak'
                booking.alasan_penolakan = alasan
                booking.save()

                jadwal.status = 'tersedia'
                jadwal.save()

                catat_log(
                    user=request.user,
                    aksi='TOLAK_BOOKING_KONSULTASI',
                    deskripsi=f'Menolak booking ID {booking.id} dari siswa {booking.siswa}. '
                              f'Alasan: {alasan}',
                    modul='konsultasi_bk'
                )

                return Response({
                    "message": "Booking berhasil ditolak.",
                    "data": BookingKonsultasiDetailSerializer(booking).data
                })


# =============================================================================
# PBI-41 — Membatalkan Jadwal Booking Konsultasi
# PATCH: /api/konsultasi/booking/<uuid:id>/cancel/
# =============================================================================

class BatalkanBookingView(APIView):
    """
    API view untuk pembatalan booking konsultasi (PBI-41).

    Permissions:
    - PATCH: Siswa pemilik booking dan Guru BK

    PATCH - Siswa atau Guru BK membatalkan booking.
        Body:
        - alasan : str (REQUIRED)

        Validasi:
        - Booking harus berstatus 'menunggu_konfirmasi' atau 'dikonfirmasi'
        - Pembatalan tidak bisa dilakukan jika waktu konsultasi sudah lewat
        - Jika pembatalan oleh Siswa  → status 'dibatalkan_siswa'
        - Jika pembatalan oleh Guru BK → status 'dibatalkan_guru_bk'
        - Setelah dibatalkan, status slot jadwal kembali ke 'tersedia'
    """
    permission_classes = [IsAuthenticated]

    @role_required('siswa', 'guru_bk')
    def patch(self, request, id):
        alasan = request.data.get('alasan', '').strip()

        if not alasan:
            return Response(
                {"error": "Alasan pembatalan wajib diisi."},
                status=400
            )

        user = request.user

        try:
            if user.role == 'siswa':
                booking = BookingKonsultasi.objects.select_related('jadwal', 'siswa').get(
                    id=id, siswa=user
                )
            else:
                # Guru BK hanya bisa membatalkan booking yang ada di jadwal miliknya
                booking = BookingKonsultasi.objects.select_related('jadwal', 'siswa').get(id=id)
                if booking.jadwal.guru_bk != user:
                    return Response(
                        {"error": "Anda tidak memiliki akses ke booking ini."},
                        status=403
                    )
        except BookingKonsultasi.DoesNotExist:
            return Response({"error": "Data booking tidak ditemukan."}, status=404)

        if booking.status not in ('menunggu_konfirmasi', 'dikonfirmasi'):
            return Response(
                {"error": "Booking hanya dapat dibatalkan jika berstatus 'Menunggu Konfirmasi' atau 'Dikonfirmasi'."},
                status=400
            )

        # Cegah pembatalan jika waktu konsultasi sudah lewat
        slot_datetime = datetime.combine(booking.jadwal.tanggal, booking.jadwal.waktu_mulai)
        slot_datetime = timezone.make_aware(slot_datetime)
        if slot_datetime <= timezone.now():
            return Response(
                {"error": "Pembatalan tidak dapat dilakukan karena waktu konsultasi sudah lewat."},
                status=400
            )

        with transaction.atomic():
            jadwal = JadwalKonsultasi.objects.select_for_update().get(id=booking.jadwal.id)

            if user.role == 'siswa':
                booking.status = 'dibatalkan_siswa'
                aksi_log = 'BATAL_BOOKING_SISWA'
                deskripsi_log = f'Siswa membatalkan booking ID {booking.id}. Alasan: {alasan}'
                pesan = 'Booking berhasil dibatalkan oleh siswa.'
            else:
                booking.status = 'dibatalkan_guru_bk'
                aksi_log = 'BATAL_BOOKING_GURU_BK'
                deskripsi_log = f'Guru BK membatalkan booking ID {booking.id} dari siswa {booking.siswa}. Alasan: {alasan}'
                pesan = 'Booking berhasil dibatalkan oleh Guru BK.'

            booking.alasan_pembatalan = alasan
            booking.save()

            jadwal.status = 'tersedia'
            jadwal.save()

        catat_log(
            user=request.user,
            aksi=aksi_log,
            deskripsi=deskripsi_log,
            modul='konsultasi_bk'
        )

        return Response({
            "message": pesan,
            "data": BookingKonsultasiDetailSerializer(booking).data
        })


# =============================================================================
# PBI-42 — Melakukan Reschedule Jadwal Booking Konsultasi
# PATCH: /api/konsultasi/booking/<uuid:id>/reschedule/
# =============================================================================

class RescheduleBookingView(APIView):
    """
    API view untuk reschedule booking konsultasi oleh Siswa (PBI-42).

    Permissions:
    - PATCH: Siswa pemilik booking only

    PATCH - Siswa mengganti slot jadwal booking ke slot lain yang tersedia.
        Body:
        - jadwal_baru : UUID (REQUIRED) — ID slot jadwal baru yang berstatus 'tersedia'

        Validasi:
        - Booking harus berstatus 'menunggu_konfirmasi' (belum dikonfirmasi)
        - Slot baru harus berstatus 'tersedia'
        - Slot baru waktu mulai tidak boleh sudah lewat
        - Slot baru tidak boleh bertabrakan dengan booking aktif siswa lain di hari yang sama
        - Setelah berhasil, slot lama dikembalikan ke 'tersedia', slot baru menjadi 'menunggu_konfirmasi'
    """
    permission_classes = [IsAuthenticated]

    @role_required('siswa')
    def patch(self, request, id):
        jadwal_baru_id = request.data.get('jadwal_baru', '').strip()

        if not jadwal_baru_id:
            return Response(
                {"error": "Field 'jadwal_baru' wajib diisi."},
                status=400
            )

        try:
            booking = BookingKonsultasi.objects.select_related('jadwal', 'siswa').get(
                id=id, siswa=request.user
            )
        except BookingKonsultasi.DoesNotExist:
            return Response({"error": "Data booking tidak ditemukan."}, status=404)

        if booking.status != 'menunggu_konfirmasi':
            return Response(
                {"error": "Reschedule hanya dapat dilakukan jika status booking adalah 'Menunggu Konfirmasi'."},
                status=400
            )

        # After retrieving the booking and checking status == 'menunggu_konfirmasi',
        # add this check:

        # Cegah reschedule jika waktu slot LAMA sudah lewat
        slot_lama_datetime = datetime.combine(booking.jadwal.tanggal, booking.jadwal.waktu_mulai)
        slot_lama_datetime = timezone.make_aware(slot_lama_datetime)
        if slot_lama_datetime <= timezone.now():
            return Response(
                {"error": "Reschedule tidak dapat dilakukan karena waktu konsultasi yang dipesan sudah lewat."},
                status=400
            )

        try:
            jadwal_baru = JadwalKonsultasi.objects.get(id=jadwal_baru_id)
        except JadwalKonsultasi.DoesNotExist:
            return Response({"error": "Slot jadwal baru tidak ditemukan."}, status=404)

        # Slot baru tidak boleh sama dengan slot lama
        if jadwal_baru.id == booking.jadwal.id:
            return Response(
                {"error": "Slot baru tidak boleh sama dengan slot yang sedang dipesan."},
                status=400
            )

        if jadwal_baru.status != 'tersedia':
            return Response(
                {"error": "Slot jadwal baru tidak berstatus 'Tersedia'."},
                status=400
            )

        # Cek waktu slot baru tidak sudah lewat
        slot_baru_datetime = datetime.combine(jadwal_baru.tanggal, jadwal_baru.waktu_mulai)
        slot_baru_datetime = timezone.make_aware(slot_baru_datetime)
        if slot_baru_datetime <= timezone.now():
            return Response(
                {"error": "Waktu slot baru sudah melewati waktu saat ini."},
                status=400
            )

        # Cek tabrakan dengan booking aktif siswa di hari yang sama
        # (kecualikan booking yang sedang di-reschedule ini)
        booking_aktif = BookingKonsultasi.objects.filter(
            siswa=request.user,
            status__in=['menunggu_konfirmasi', 'dikonfirmasi']
        ).exclude(id=booking.id).select_related('jadwal')

        for b in booking_aktif:
            j = b.jadwal
            if j.tanggal == jadwal_baru.tanggal:
                if (jadwal_baru.waktu_mulai < j.waktu_selesai and
                        jadwal_baru.waktu_selesai > j.waktu_mulai):
                    return Response(
                        {"error": "Slot baru bertabrakan dengan booking lain yang sudah ada."},
                        status=400
                    )

        with transaction.atomic():
            jadwal_lama = JadwalKonsultasi.objects.select_for_update().get(id=booking.jadwal.id)
            jadwal_baru_locked = JadwalKonsultasi.objects.select_for_update().get(id=jadwal_baru.id)

            # Re-validasi status slot baru setelah lock
            if jadwal_baru_locked.status != 'tersedia':
                return Response(
                    {"error": "Slot jadwal baru sudah tidak tersedia. Silakan pilih slot lain."},
                    status=400
                )

            # Kembalikan slot lama ke tersedia
            jadwal_lama.status = 'tersedia'
            jadwal_lama.save()

            # Kunci slot baru
            jadwal_baru_locked.status = 'menunggu_konfirmasi'
            jadwal_baru_locked.save()

            # Update booking ke slot baru
            booking.jadwal = jadwal_baru_locked
            booking.save()

        catat_log(
            user=request.user,
            aksi='RESCHEDULE_BOOKING_KONSULTASI',
            deskripsi=(
                f'Reschedule booking ID {booking.id} '
                f'dari jadwal {jadwal_lama.tanggal} {jadwal_lama.waktu_mulai} '
                f'ke jadwal {jadwal_baru_locked.tanggal} {jadwal_baru_locked.waktu_mulai}'
            ),
            modul='konsultasi_bk'
        )

        return Response({
            "message": "Booking berhasil dijadwalkan ulang.",
            "data": BookingKonsultasiDetailSerializer(booking).data
        })
    
# =============================================================================
# Tandai Selesai + Catatan Hasil Konsultasi (Guru BK)
# PATCH: /api/konsultasi/booking/<uuid:id>/selesai/
# =============================================================================

class SelesaiBookingView(APIView):
    """
    Guru BK menandai sesi konsultasi sebagai selesai dan mengisi catatan hasil.

    Permissions:
    - PATCH: Guru BK pemilik jadwal

    Body:
    - catatan_hasil : str (REQUIRED) — ringkasan/tindak lanjut hasil konsultasi

    Validasi:
    - Booking harus berstatus 'dikonfirmasi'
    - Waktu mulai konsultasi harus sudah lewat (sesi memang sudah berlangsung)
    - catatan_hasil wajib diisi, min 10 karakter
    """
    permission_classes = [IsAuthenticated]

    @role_required('guru_bk')
    def patch(self, request, id):
        catatan_hasil = request.data.get('catatan_hasil', '').strip()

        if not catatan_hasil:
            return Response(
                {"error": "Catatan hasil konsultasi wajib diisi."},
                status=400
            )

        if len(catatan_hasil) < 10:
            return Response(
                {"error": "Catatan hasil konsultasi minimal 10 karakter."},
                status=400
            )

        try:
            booking = BookingKonsultasi.objects.select_related('jadwal', 'siswa').get(id=id)
        except BookingKonsultasi.DoesNotExist:
            return Response({"error": "Data booking tidak ditemukan."}, status=404)

        # Hanya Guru BK pemilik jadwal yang bisa menandai selesai
        if booking.jadwal.guru_bk != request.user:
            return Response({"error": "Anda tidak memiliki akses ke booking ini."}, status=403)

        if booking.status != 'dikonfirmasi':
            return Response(
                {"error": "Hanya booking berstatus 'Dikonfirmasi' yang dapat ditandai selesai."},
                status=400
            )

        # Waktu konsultasi harus sudah lewat
        slot_datetime = datetime.combine(booking.jadwal.tanggal, booking.jadwal.waktu_mulai)
        slot_datetime = timezone.make_aware(slot_datetime)
        #tandai selesai atur di sini
        if slot_datetime > timezone.now():
            return Response(
                {"error": "Sesi konsultasi belum dimulai, tidak dapat ditandai selesai."},
                status=400
            )

        with transaction.atomic():
            jadwal = JadwalKonsultasi.objects.select_for_update().get(id=booking.jadwal.id)

            booking.status = 'selesai'
            booking.catatan_hasil = catatan_hasil
            booking.save()

            jadwal.status = 'selesai'
            jadwal.save()

        catat_log(
            user=request.user,
            aksi='SELESAI_KONSULTASI',
            deskripsi=(
                f'Menandai konsultasi selesai untuk booking ID {booking.id} '
                f'dari siswa {booking.siswa}. Catatan: {catatan_hasil[:100]}'
            ),
            modul='konsultasi_bk'
        )

        return Response({
            "message": "Konsultasi berhasil ditandai selesai.",
            "data": BookingKonsultasiDetailSerializer(booking).data
        })


# =============================================================================
# Tandai Tidak Hadir (Guru BK)
# PATCH: /api/konsultasi/booking/<uuid:id>/tidak-hadir/
# =============================================================================

class TidakHadirBookingView(APIView):
    """
    Guru BK menandai siswa tidak hadir pada sesi yang sudah dikonfirmasi.

    Permissions:
    - PATCH: Guru BK pemilik jadwal

    Validasi:
    - Booking harus berstatus 'dikonfirmasi'
    - Waktu mulai konsultasi harus sudah lewat
    """
    permission_classes = [IsAuthenticated]

    @role_required('guru_bk')
    def patch(self, request, id):
        try:
            booking = BookingKonsultasi.objects.select_related('jadwal', 'siswa').get(id=id)
        except BookingKonsultasi.DoesNotExist:
            return Response({"error": "Data booking tidak ditemukan."}, status=404)

        if booking.jadwal.guru_bk != request.user:
            return Response({"error": "Anda tidak memiliki akses ke booking ini."}, status=403)

        if booking.status != 'dikonfirmasi':
            return Response(
                {"error": "Hanya booking berstatus 'Dikonfirmasi' yang dapat ditandai tidak hadir."},
                status=400
            )

        # Waktu konsultasi harus sudah lewat
        slot_datetime = datetime.combine(booking.jadwal.tanggal, booking.jadwal.waktu_mulai)
        slot_datetime = timezone.make_aware(slot_datetime)
        #atur di sini biar bisa selesai pas testing
        if slot_datetime > timezone.now():
            return Response(
                {"error": "Waktu konsultasi belum lewat, tidak dapat ditandai tidak hadir."},
                status=400
            )

        with transaction.atomic():
            jadwal = JadwalKonsultasi.objects.select_for_update().get(id=booking.jadwal.id)

            booking.status = 'tidak_hadir'
            booking.save()

            jadwal.status = 'tidak_hadir'
            jadwal.save()

        catat_log(
            user=request.user,
            aksi='TIDAK_HADIR_KONSULTASI',
            deskripsi=f'Menandai siswa {booking.siswa} tidak hadir pada booking ID {booking.id}',
            modul='konsultasi_bk'
        )

        return Response({
            "message": "Siswa ditandai tidak hadir.",
            "data": BookingKonsultasiDetailSerializer(booking).data
        })