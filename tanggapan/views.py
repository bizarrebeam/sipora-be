"""
Views module for the tanggapan application.

Provides API endpoints for reading and creating response messages on damage reports.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404

from laporan_kerusakan.models import LaporanKerusakan
from .models import TanggapanLaporanKerusakan
from .serializers import (
    TanggapanLaporanKerusakanListSerializer,
    TanggapanLaporanKerusakanCreateSerializer,
)
from log_aktivitas.utils import catat_log


class ListCreateTanggapanLaporanKerusakanView(APIView):
    """
    API view for reading and creating responses to facility damage reports.
    
    GET: Retrieve all responses for a specific report.
    POST: Submit a new response to a specific report.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, laporan_id):
        """
        Retrieve all responses for the specified damage report.
        
        Args:
            request: The HTTP request object.
            laporan_id (UUID): The ID of the damage report.
        
        Returns:
            Response: List of responses with 200 OK, or error status.
        
        Access Rules:
            - Siswa/Guru: Can only view responses on their own reports.
            - Kemahasiswaan: Can view any report's responses.
        """
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
        is_kemahasiswaan = user.role == 'kemahasiswaan'
        is_owner = laporan.pelapor == user
        
        if not is_kemahasiswaan and not is_owner:
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
        """
        Submit a new response to the specified damage report.
        
        Args:
            request: The HTTP request object with pesan payload.
            laporan_id (UUID): The ID of the damage report.
        
        Returns:
            Response: Created response data with 201 Created, or error status.
        
        Validation Rules:
            - Authentication: User must be logged in (401 if not).
            - Authorization: Only Siswa, Guru, or Kemahasiswaan can respond (403).
            - Ownership: Siswa/Guru can only respond to their own reports (403).
            - Report Status: Report cannot be "Selesai" (400).
            - Anonymity: If report is anonymous, nama_pengirim becomes "Pengguna Anonim".
        """
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
        
        # Authorization check: only siswa, guru, kemahasiswaan can respond
        user = request.user
        allowed_roles = ['siswa', 'guru', 'kemahasiswaan']
        if user.role not in allowed_roles:
            return Response(
                {
                    'status': 'error',
                    'message': 'Akses ditolak',
                    'data': None
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Ownership check: siswa/guru can only respond to their own reports
        if user.role in ['siswa', 'guru'] and laporan.pelapor != user:
            return Response(
                {
                    'status': 'error',
                    'message': 'Akses ditolak',
                    'data': None
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Status check: cannot respond if report is closed (selesai)
        if laporan.status == 'selesai':
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
