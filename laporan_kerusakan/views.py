from django.shortcuts import render

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import models

from .models import LaporanKerusakan
from .serializers import (
    LaporanKerusakanSerializer,
    CreateLaporanKerusakanSerializer
)
from akun.decorators import role_required
from log_aktivitas.utils import catat_log


class CreateLaporanKerusakanView(APIView):
    """
    POST /api/laporan-kerusakan/
    Create new laporan kerusakan
    Only for role: siswa, guru
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Check if user is siswa or guru
        if request.user.role not in ['siswa', 'guru']:
            return Response(
                {
                    'status': 'error',
                    'message': 'Hanya siswa dan guru yang dapat membuat laporan',
                    'data': None
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = CreateLaporanKerusakanSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            laporan = serializer.save()
            
            # Log activity
            ip = request.META.get('REMOTE_ADDR')
            catat_log(
                request.user,
                'BUAT_LAPORAN',
                f"Membuat laporan kerusakan: {laporan.no_laporan}",
                ip,
                {'laporan_id': str(laporan.id), 'no_laporan': laporan.no_laporan}
            )
            
            # Return full laporan data
            response_serializer = LaporanKerusakanSerializer(
                laporan,
                context={'request': request}
            )
            
            return Response(
                {
                    'status': 'success',
                    'message': 'Laporan berhasil dibuat',
                    'data': response_serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        
        return Response(
            {
                'status': 'error',
                'message': 'Validasi gagal',
                'data': serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )


class LaporanKerusakanListView(APIView):
    """
    GET /api/laporan-kerusakan/list/
    Get list of laporan kerusakan
    - Siswa/Guru: hanya melihat laporan sendiri
    - Admin: melihat semua laporan
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        if user.role in ['kemahasiswaan', 'guru_bk']:
            # Admin can see all laporan
            laporan_list = LaporanKerusakan.objects.all()
        else:
            # Siswa/Guru only see their own laporan
            laporan_list = LaporanKerusakan.objects.filter(pelapor=user)
        
        # Filter by status if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            laporan_list = laporan_list.filter(status=status_filter)
        
        # Search functionality
        search = request.query_params.get('search')
        if search:
            laporan_list = laporan_list.filter(
                models.Q(no_laporan__icontains=search) |
                models.Q(judul__icontains=search) |
                models.Q(lokasi__icontains=search) |
                models.Q(deskripsi__icontains=search)
            )
        
        # Order by tanggal_laporan descending (newest first)
        laporan_list = laporan_list.order_by('-tanggal_laporan')
        
        serializer = LaporanKerusakanSerializer(
            laporan_list, 
            many=True,
            context={'request': request}
        )
        
        return Response(
            {
                'status': 'success',
                'message': 'Berhasil mengambil data laporan',
                'data': {
                    'total': laporan_list.count(),
                    'laporan': serializer.data
                }
            },
            status=status.HTTP_200_OK
        )


class LaporanKerusakanDetailView(APIView):
    """
    GET /api/laporan-kerusakan/<id>/
    Get detail of specific laporan
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, id):
        laporan = get_object_or_404(LaporanKerusakan, id=id)
        
        # Check permission
        user = request.user
        if user.role not in ['kemahasiswaan', 'guru_bk']:
            # Siswa/Guru can only view their own laporan
            if laporan.pelapor != user:
                return Response(
                    {
                        'status': 'error',
                        'message': 'Anda tidak memiliki akses ke laporan ini',
                        'data': None
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
        
        serializer = LaporanKerusakanSerializer(
            laporan,
            context={'request': request}
        )
        
        return Response(
            {
                'status': 'success',
                'message': 'Berhasil mengambil detail laporan',
                'data': serializer.data
            },
            status=status.HTTP_200_OK
        )

