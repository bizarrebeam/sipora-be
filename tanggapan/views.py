"""
Views for managing responses on damage and bullying reports.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from laporan_kerusakan.models import LaporanKerusakan
from laporan_bullying.models import LaporanBullying
from .models import TanggapanLaporanKerusakan, TanggapanLaporanBullying
from .serializers import (
    TanggapanLaporanKerusakanListSerializer,
    TanggapanLaporanKerusakanCreateSerializer,
    TanggapanLaporanBullyingListSerializer,
    TanggapanLaporanBullyingCreateSerializer,
)
from log_aktivitas.utils import catat_log


class ListCreateTanggapanLaporanKerusakanView(APIView):
    """List and create tanggapan for a laporan kerusakan."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, laporan_id):
        """Return tanggapan list for one laporan with role-based access checks."""
        try:
            laporan = LaporanKerusakan.objects.get(id=laporan_id)
        except LaporanKerusakan.DoesNotExist:
            return Response(
                {
                    'status': 'error',
                    'message': 'Laporan tidak ditemukan',
                    'data': None
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Access control
        user = request.user
        is_admin = user.role in ['kemahasiswaan', 'guru_bk']
        is_owner = laporan.pelapor == user
        
        if not is_admin and not is_owner:
            return Response(
                {
                    'status': 'error',
                    'message': 'Akses ditolak',
                    'data': None
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Fetch all responses ordered by creation time
        tanggapan_list = TanggapanLaporanKerusakan.objects.filter(laporan=laporan)
        serializer = TanggapanLaporanKerusakanListSerializer(tanggapan_list, many=True)
        
        return Response(
            {
                'status': 'success',
                'message': 'Berhasil mengambil data tanggapan',
                'data': serializer.data
            },
            status=status.HTTP_200_OK
        )
    
    def post(self, request, laporan_id):
        """Create a new tanggapan if user, ownership, and status checks pass."""
        try:
            laporan = LaporanKerusakan.objects.get(id=laporan_id)
        except LaporanKerusakan.DoesNotExist:
            return Response(
                {
                    'status': 'error',
                    'message': 'Laporan tidak ditemukan',
                    'data': None
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Authorization check: siswa/guru (own reports), kemahasiswaan, guru_bk (all reports)
        user = request.user
        allowed_roles = ['siswa', 'guru', 'kemahasiswaan', 'guru_bk']
        if user.role not in allowed_roles:
            return Response(
                {
                    'status': 'error',
                    'message': 'Akses ditolak',
                    'data': None
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Ownership check: siswa/guru can only respond to their own reports (admin can respond to all)
        if user.role in ['siswa', 'guru'] and laporan.pelapor != user:
            return Response(
                {
                    'status': 'error',
                    'message': 'Akses ditolak',
                    'data': None
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Status check: cannot respond if report is closed (selesai, ditolak, dibatalkan)
        closed_statuses = ['selesai', 'ditolak', 'dibatalkan']
        if laporan.status in closed_statuses:
            return Response(
                {
                    'status': 'error',
                    'message': 'Laporan telah ditutup dan tidak dapat menerima tanggapan',
                    'data': None
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate the response message
        serializer = TanggapanLaporanKerusakanCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    'status': 'error',
                    'message': 'Validasi gagal',
                    'data': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Store the actual sender name; display anonymity is resolved dynamically in the serializer.
        nama_pengirim = user.nama_lengkap or user.username
        
        # Create the response
        tanggapan = TanggapanLaporanKerusakan.objects.create(
            laporan=laporan,
            pengirim=user,
            nama_pengirim=nama_pengirim,
            pesan=serializer.validated_data['pesan']
        )
        
        # Log activity
        ip = request.META.get('REMOTE_ADDR')
        catat_log(
            user,
            'KIRIM_TANGGAPAN',
            f"Mengirim tanggapan pada laporan kerusakan: {laporan.no_laporan}",
            'kerusakan',
            ip
        )
        
        # Return created response
        response_serializer = TanggapanLaporanKerusakanListSerializer(tanggapan)
        return Response(
            {
                'status': 'success',
                'message': 'Tanggapan berhasil dikirim',
                'data': response_serializer.data
            },
            status=status.HTTP_201_CREATED
        )


class ListCreateTanggapanLaporanBullyingView(APIView):
    """List and create tanggapan for a laporan bullying."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, laporan_id):
        """Return tanggapan list for one laporan with role-based access checks."""
        try:
            laporan = LaporanBullying.objects.get(id=laporan_id)
        except LaporanBullying.DoesNotExist:
            return Response(
                {
                    'status': 'error',
                    'message': 'Laporan tidak ditemukan',
                    'data': None
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Access control
        user = request.user
        is_admin = user.role in ['kemahasiswaan', 'guru_bk']
        is_owner = laporan.pelapor == user
        
        if not is_admin and not is_owner:
            return Response(
                {
                    'status': 'error',
                    'message': 'Akses ditolak',
                    'data': None
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Fetch all responses ordered by creation time
        tanggapan_list = TanggapanLaporanBullying.objects.filter(laporan=laporan)
        serializer = TanggapanLaporanBullyingListSerializer(tanggapan_list, many=True)
        
        return Response(
            {
                'status': 'success',
                'message': 'Berhasil mengambil data tanggapan',
                'data': serializer.data
            },
            status=status.HTTP_200_OK
        )
    
    def post(self, request, laporan_id):
        """Create a new tanggapan if user, ownership, and status checks pass."""
        try:
            laporan = LaporanBullying.objects.get(id=laporan_id)
        except LaporanBullying.DoesNotExist:
            return Response(
                {
                    'status': 'error',
                    'message': 'Laporan tidak ditemukan',
                    'data': None
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Authorization check: siswa/guru (own reports), kemahasiswaan, guru_bk (all reports)
        user = request.user
        allowed_roles = ['siswa', 'guru', 'kemahasiswaan', 'guru_bk']
        if user.role not in allowed_roles:
            return Response(
                {
                    'status': 'error',
                    'message': 'Akses ditolak',
                    'data': None
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Ownership check: siswa/guru can only respond to their own reports (admin can respond to all)
        if user.role in ['siswa', 'guru'] and laporan.pelapor != user:
            return Response(
                {
                    'status': 'error',
                    'message': 'Akses ditolak',
                    'data': None
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Status check: cannot respond if report is closed (selesai, ditolak, dibatalkan)
        closed_statuses = ['selesai', 'ditolak', 'dibatalkan']
        if laporan.status in closed_statuses:
            return Response(
                {
                    'status': 'error',
                    'message': 'Laporan telah ditutup dan tidak dapat menerima tanggapan',
                    'data': None
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate the response message
        serializer = TanggapanLaporanBullyingCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    'status': 'error',
                    'message': 'Validasi gagal',
                    'data': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Store the actual sender name
        nama_pengirim = user.nama_lengkap or user.username
        
        # Create the response
        tanggapan = TanggapanLaporanBullying.objects.create(
            laporan=laporan,
            pengirim=user,
            nama_pengirim=nama_pengirim,
            pesan=serializer.validated_data['pesan']
        )
        
        # Log activity
        ip = request.META.get('REMOTE_ADDR')
        catat_log(
            user,
            'KIRIM_TANGGAPAN',
            f"Mengirim tanggapan pada laporan bullying: {laporan.no_laporan}",
            'bullying',
            ip
        )
        
        # Return created response
        response_serializer = TanggapanLaporanBullyingListSerializer(tanggapan)
        return Response(
            {
                'status': 'success',
                'message': 'Tanggapan berhasil dikirim',
                'data': response_serializer.data
            },
            status=status.HTTP_201_CREATED
        )
