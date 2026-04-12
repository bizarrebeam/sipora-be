"""
Views module for the konsultasi application.

PBI-38 : Mengelola jadwal ketersediaan Guru BK
PBI-39 : Membuat booking jadwal konsultasi (Siswa)
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
        """
        GET endpoint untuk mengambil daftar jadwal.
        
        Args:
            request: HTTP request dengan user terautentikasi
            
        Returns:
            Response: JSON dengan daftar jadwal berdasarkan role user
        """
        """
        GET endpoint untuk mengambil daftar jadwal.
        
        Args:
            request: HTTP request dengan user terautentikasi
            
        Returns:
            Response: JSON dengan daftar jadwal berdasarkan role user
        """
        # Filter jadwal berdasarkan role pengguna
        if request.user.role == 'guru_bk':
            # Guru BK hanya lihat jadwal milik sendiri saja
            jadwal_qs = JadwalKonsultasi.objects.filter(guru_bk=request.user).select_related('booking__siswa')
        else:
            # Siswa hanya dapat melihat slot yang masih tersedia (belum dipesan)
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
        """
        POST endpoint untuk Guru BK membuat jadwal konsultasi baru.
        
        Args:
            request: HTTP request dengan user Guru BK terautentikasi
                    body harus berisi: tanggal, waktu_mulai, waktu_selesai, catatan (opsional)
            
        Returns:
            Response: JSON dengan data jadwal yang baru dibuat atau error validation
        """
        serializer = JadwalKonsultasiSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            jadwal = serializer.save(guru_bk=request.user)

            catat_log(
                user=request.user,
                aksi='Buat Jadwal Konsultasi',
                deskripsi=f'Membuat jadwal konsultasi pada {jadwal.tanggal} '
                          f'{jadwal.waktu_mulai}-{jadwal.waktu_selesai}',
                modul='Konsultasi'
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
    
    PUT - Guru BK mengubah jadwal yang sudah ada (partial update diizinkan).
        Jadwal tidak dapat diubah jika sudah ada booking (status != 'tersedia').
        Akan divalidasi melalui JadwalKonsultasiSerializer.
        
    DELETE - Guru BK menghapus jadwal (hanya jika belum dipesan siswa).
        Jika sudah ada booking, akan return 400 error.
    """
    permission_classes = [IsAuthenticated]

    def _get_jadwal(self, id, guru_bk):
        """
        Helper method untuk mengambil jadwal milik guru_bk tertentu.
        
        Args:
            id (UUID): ID jadwal yang dicari
            guru_bk (User): User Guru BK yang pemilik jadwal
            
        Returns:
            JadwalKonsultasi atau None: Jadwal jika ditemukan dan milik guru_bk, None jika tidak ada
        """
        try:
            return JadwalKonsultasi.objects.get(id=id, guru_bk=guru_bk)
        except JadwalKonsultasi.DoesNotExist:
            return None

    @role_required('guru_bk')
    def put(self, request, id):
        """
        PUT endpoint untuk Guru BK mengubah jadwal konsultasi.
        
        Args:
            request: HTTP request dengan user Guru BK terautentikasi
                    body bisa berisi: tanggal, waktu_mulai, waktu_selesai, catatan (partial update OK)
            id (UUID): ID jadwal yang akan diubah
            
        Returns:
            Response: JSON dengan data jadwal yang sudah diubah atau error
            
        Restrictions:
            - Jadwal tidak dapat diubah jika sudah ada booking (status != 'tersedia')
        """
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
                aksi='Edit Jadwal Konsultasi',
                deskripsi=f'Mengubah jadwal konsultasi ID {jadwal.id}',
                modul='Konsultasi'
            )

            return Response({
                "message": "Jadwal berhasil diperbarui.",
                "data": JadwalKonsultasiSerializer(jadwal).data
            })

        return Response(serializer.errors, status=400)

    @role_required('guru_bk')
    def delete(self, request, id):
        """
        DELETE endpoint untuk Guru BK menghapus jadwal konsultasi.
        
        Args:
            request: HTTP request dengan user Guru BK terautentikasi
            id (UUID): ID jadwal yang akan dihapus
            
        Returns:
            Response: JSON dengan pesan success atau error
            
        Restrictions:
            - Jadwal tidak dapat dihapus jika sudah ada booking (status != 'tersedia')
        """
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
            aksi='Hapus Jadwal Konsultasi',
            deskripsi=f'Menghapus jadwal konsultasi: {jadwal_info}',
            modul='Konsultasi'
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
    
    GET - Daftar booking dengan filter berdasarkan role:
        - Siswa  : hanya booking milik sendiri
        - Guru BK: seluruh booking dari semua siswa
        
        Query params (optional):
        - tanggal: Filter berdasarkan tanggal slot (format: YYYY-MM-DD)
        - status : Filter berdasarkan status booking (menunggu_konfirmasi, dikonfirmasi, dll)
        
    POST - Siswa membuat booking baru untuk slot jadwal yang tersedia.
        Menggunakan select_for_update() + atomic transaction untuk prevent race condition:
        Jika 2 siswa mencoba booking slot sama bersamaan, hanya 1 yang berhasil.
        
        Validasi:
        - Slot harus berstatus 'tersedia'
        - Waktu slot tidak boleh sudah lewat
        - Deskripsi harus diisi
        - Tidak boleh tabrakan dengan booking aktif siswa lain pada hari/waktu yang sama
    """
    permission_classes = [IsAuthenticated]

    @role_required('siswa', 'guru_bk')
    def get(self, request):
        """
        GET endpoint untuk mengambil daftar booking.
        
        Args:
            request: HTTP request dengan user terautentikasi
            
        Returns:
            Response: JSON dengan daftar booking berdasarkan role user
        """
        """
        GET endpoint untuk mengambil daftar booking.
        
        Args:
            request: HTTP request dengan user terautentikasi
            
        Returns:
            Response: JSON dengan daftar booking berdasarkan role user
        """
        user = request.user

        # Filter booking berdasarkan role pengguna
        if user.role == 'siswa':
            # Siswa hanya lihat booking milik sendiri
            booking_qs = BookingKonsultasi.objects.filter(
                siswa=user
            ).select_related('jadwal', 'siswa')
        else:
            # Guru BK lihat semua booking
            booking_qs = BookingKonsultasi.objects.all().select_related(
                'jadwal', 'siswa'
            )

        tanggal = request.query_params.get('tanggal')
        if tanggal:
            booking_qs = booking_qs.filter(jadwal__tanggal=tanggal)

        status = request.query_params.get('status')
        if status:
            booking_qs = booking_qs.filter(status=status)

        serializer = BookingKonsultasiListSerializer(booking_qs, many=True)
        return Response({
            "message": "Berhasil mengambil daftar booking.",
            "data": serializer.data
        })

    @role_required('siswa')
    def post(self, request):
        """
        POST endpoint untuk Siswa membuat booking konsultasi baru.
        
        Menggunakan atomic transaction + select_for_update untuk prevent race condition
        ketika 2 siswa mencoba booking slot yang sama bersamaan.
        
        Args:
            request: HTTP request dengan user Siswa terautentikasi
                    body harus berisi: jadwal (UUID), deskripsi (string)
            
        Returns:
            Response: JSON dengan data booking yang baru dibuat atau error
        """
        serializer = BookingKonsultasiCreateSerializer(
            data=request.data,
            context={'request': request}
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        jadwal_id = serializer.validated_data['jadwal'].id

        try:
            with transaction.atomic():
                # CRITICAL: Lock baris jadwal untuk mencegah race condition
                # select_for_update() memastikan hanya satu transaksi yang bisa update slot ini
                jadwal = JadwalKonsultasi.objects.select_for_update().get(id=jadwal_id)

                # Re-validasi status setelah lock (untuk memastikan status masih 'tersedia')
                # Status mungkin berubah jika ada siswa lain yang berhasil booking lebih dulu
                if jadwal.status != 'tersedia':
                    return Response(
                        {"error": "Slot jadwal sudah tidak tersedia. Silakan pilih slot lain."},
                        status=400
                    )

                # Re-validasi waktu setelah lock (untuk memastikan waktu belum lewat)
                slot_datetime = datetime.combine(jadwal.tanggal, jadwal.waktu_mulai)
                slot_datetime = timezone.make_aware(slot_datetime)
                if slot_datetime <= timezone.now():
                    return Response(
                        {"error": "Waktu slot yang dipilih sudah melewati waktu saat ini."},
                        status=400
                    )

                # Buat booking dengan status menunggu_konfirmasi
                booking = BookingKonsultasi.objects.create(
                    siswa=request.user,
                    jadwal=jadwal,
                    deskripsi=serializer.validated_data['deskripsi'],
                    status='menunggu_konfirmasi'
                )

                # Update status jadwal menjadi menunggu_konfirmasi (slot sudah dipesan)
                jadwal.status = 'menunggu_konfirmasi'
                jadwal.save()

        except JadwalKonsultasi.DoesNotExist:
            return Response({"error": "Slot jadwal tidak ditemukan."}, status=404)

        catat_log(
            user=request.user,
            aksi='Buat Booking Konsultasi',
            deskripsi=f'Membuat booking konsultasi ID {booking.id} '
                      f'untuk jadwal {jadwal.tanggal} {jadwal.waktu_mulai}',
            modul='Konsultasi'
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
    
    GET - Menampilkan detail lengkap satu booking berdasarkan ID.
        Siswa hanya bisa melihat booking miliknya sendiri.
        Guru BK bisa melihat semua booking.
        
        Serializer yang digunakan: BookingKonsultasiDetailSerializer
        (termasuk nested serializer untuk jadwal detail)
    """
    permission_classes = [IsAuthenticated]

    @role_required('siswa', 'guru_bk')
    def get(self, request, id):
        """
        GET endpoint untuk mengambil detail satu booking.
        
        Args:
            request: HTTP request dengan user terautentikasi
            id (UUID): ID booking yang ingin dilihat
            
        Returns:
            Response: JSON dengan detail lengkap booking atau error 404
            
        Access Control:
            - Siswa hanya bisa akses booking milik sendiri
            - Guru BK bisa akses semua booking
        """
        """
        GET endpoint untuk mengambil detail satu booking.
        
        Args:
            request: HTTP request dengan user terautentikasi
            id (UUID): ID booking yang ingin dilihat
            
        Returns:
            Response: JSON dengan detail lengkap booking atau error 404
            
        Access Control:
            - Siswa hanya bisa akses booking milik sendiri
            - Guru BK bisa akses semua booking
        """
        user = request.user

        try:
            # Filter berdasarkan role: siswa hanya bisa akses milik sendiri
            if user.role == 'siswa':
                booking = BookingKonsultasi.objects.select_related(
                    'jadwal', 'siswa'
                ).get(id=id, siswa=user)
            else:
                # Guru BK bisa akses semua booking
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