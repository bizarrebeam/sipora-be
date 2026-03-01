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
from log_aktivitas.utils import catat_log


class CreateLaporanKerusakanView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # allow pelapor from siswa or guru
        if request.user.role not in ['siswa', 'guru']:
            return Response(
                {
                    'status': 'error',
                    'message': 'Hanya siswa atau guru yang dapat membuat laporan',
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
            
            ip = request.META.get('REMOTE_ADDR')
            if laporan.anonimitas:
                kelas = request.user.kelas or '-'
                catat_log(
                    None,
                    'BUAT_LAPORAN',
                    f"Anonim dari Kelas {kelas} membuat laporan kerusakan: {laporan.no_laporan}",
                    'kerusakan',
                    ip
                )
            else:
                catat_log(
                    request.user,
                    'BUAT_LAPORAN',
                    f"Membuat laporan kerusakan: {laporan.no_laporan}",
                    'kerusakan',
                    ip
                )
            
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
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        if user.role == 'kemahasiswaan':
            laporan_list = LaporanKerusakan.objects.all()
        else:
            laporan_list = LaporanKerusakan.objects.filter(pelapor=user)
        
        status_filter = request.query_params.get('status')
        if status_filter:
            laporan_list = laporan_list.filter(status=status_filter)
        
        search = request.query_params.get('search')
        if search:
            laporan_list = laporan_list.filter(
                models.Q(no_laporan__icontains=search) |
                models.Q(judul__icontains=search) |
                models.Q(lokasi__icontains=search) |
                models.Q(deskripsi__icontains=search)
            )
        
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
    permission_classes = [IsAuthenticated]
    
    def get(self, request, id):
        try:
            laporan = LaporanKerusakan.objects.get(id=id)
        except LaporanKerusakan.DoesNotExist:
            return Response(
                {
                    'status': 'error',
                    'message': 'Laporan belum ditemukan',
                    'data': None
                },
                status=status.HTTP_404_NOT_FOUND
            )

        user = request.user
        if user.role != 'kemahasiswaan':
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

