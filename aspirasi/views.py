from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import models

from .models import Aspirasi, RiwayatStatusDitandai
from .serializers import (
    AspirasiSerializer,
    CreateAspirasiSerializer,
)
from log_aktivitas.utils import catat_log


class CreateAspirasiView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # allow pelapor from siswa or guru
        if request.user.role not in ['siswa', 'guru']:
            return Response(
                {
                    'status': 'error',
                    'message': 'Hanya siswa atau guru yang dapat membuat aspirasi',
                    'data': None
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = CreateAspirasiSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            aspirasi = serializer.save()
            
            ip = request.META.get('REMOTE_ADDR')
            if aspirasi.anonimitas:
                kelas = request.user.kelas or '-'
                catat_log(
                    None,
                    'BUAT_ASPIRASI',
                    f"Anonim dari Kelas {kelas} membuat aspirasi: {aspirasi.no_laporan}",
                    'aspirasi',
                    ip
                )
            else:
                catat_log(
                    request.user,
                    'BUAT_ASPIRASI',
                    f"Membuat aspirasi: {aspirasi.no_laporan}",
                    'aspirasi',
                    ip
                )
            
            response_serializer = AspirasiSerializer(
                aspirasi,
                context={'request': request}
            )
            
            return Response(
                {
                    'status': 'success',
                    'message': 'Aspirasi berhasil dibuat',
                    'data': response_serializer.data
                },
                status=status.HTTP_200_OK
            )
        
        return Response(
            {
                'status': 'error',
                'message': 'Validasi gagal',
                'data': serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )


class AspirasiListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        if user.role == 'kemahasiswaan':
            aspirasi_list = Aspirasi.objects.all()
        else:
            aspirasi_list = Aspirasi.objects.filter(pelapor=user)
        
        # optional filter: kategori and ditandai flag (status_ditandai)
        kategori_filter = request.query_params.get('kategori')
        if kategori_filter:
            aspirasi_list = aspirasi_list.filter(kategori__iexact=kategori_filter)

        ditandai_filter = request.query_params.get('ditandai')
        if ditandai_filter:
            aspirasi_list = aspirasi_list.filter(status_ditandai=ditandai_filter)

        search = request.query_params.get('search')
        if search:
            aspirasi_list = aspirasi_list.filter(
                models.Q(no_laporan__icontains=search) |
                models.Q(judul__icontains=search) |
                models.Q(kategori__icontains=search) |
                models.Q(deskripsi__icontains=search)
            )
        
        aspirasi_list = aspirasi_list.order_by('-tanggal_aspirasi')
        
        serializer = AspirasiSerializer(
            aspirasi_list, 
            many=True,
            context={'request': request}
        )
        
        return Response(
            {
                'status': 'success',
                'message': 'Berhasil mengambil data aspirasi',
                'data': {
                    'total': aspirasi_list.count(),
                    'aspirasi': serializer.data
                }
            },
            status=status.HTTP_200_OK
        )


class AspirasiDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, id):
        try:
            aspirasi = Aspirasi.objects.get(id=id)
        except Aspirasi.DoesNotExist:
            return Response(
                {
                    'status': 'error',
                    'message': 'Aspirasi belum ditemukan',
                    'data': None
                },
                status=status.HTTP_404_NOT_FOUND
            )

        user = request.user
        if user.role != 'kemahasiswaan':
            if aspirasi.pelapor != user:
                return Response(
                    {
                        'status': 'error',
                        'message': 'Anda tidak memiliki akses ke aspirasi ini',
                        'data': None
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
        
        serializer = AspirasiSerializer(
            aspirasi,
            context={'request': request}
        )
        
        return Response(
            {
                'status': 'success',
                'message': 'Berhasil mengambil detail aspirasi',
                'data': serializer.data
            },
            status=status.HTTP_200_OK
        )

    def patch(self, request, id):
        # Only kemahasiswaan can mark/unmark aspirasi
        user = request.user
        if user.role != 'kemahasiswaan':
            return Response(
                {
                    'status': 'error',
                    'message': 'Hanya kemahasiswaan yang dapat menandai aspirasi',
                    'data': None
                },
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            aspirasi = Aspirasi.objects.get(id=id)
        except Aspirasi.DoesNotExist:
            return Response(
                {
                    'status': 'error',
                    'message': 'Aspirasi belum ditemukan',
                    'data': None
                },
                status=status.HTTP_404_NOT_FOUND
            )

        # Expect field 'status_ditandai' with values 'ditandai' or 'tidak_ditandai'
        new_status = request.data.get('status_ditandai') or request.data.get('status')
        if not new_status or new_status not in ['ditandai', 'tidak_ditandai']:
            return Response(
                {
                    'status': 'error',
                    'message': 'Field status_ditandai wajib diisi dengan nilai "ditandai" atau "tidak_ditandai"',
                    'data': None
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        catatan = request.data.get('catatan')
        ip = request.META.get('REMOTE_ADDR')

        aspirasi.status_ditandai = new_status
        aspirasi.ditandai_oleh = user if new_status == 'ditandai' else None
        aspirasi.save()

        # Save history
        RiwayatStatusDitandai.objects.create(
            laporan=aspirasi,
            status=new_status,
            catatan=catatan,
            diubah_oleh=user
        )

        catat_log(
            user,
            'TANDAL_APIRASI',
            f"Mengubah status ditandai {aspirasi.no_laporan} → {new_status}",
            'aspirasi',
            ip
        )

        serializer = AspirasiSerializer(aspirasi, context={'request': request})
        return Response(
            {
                'status': 'success',
                'message': 'Status ditandai berhasil diubah',
                'data': serializer.data
            },
            status=status.HTTP_200_OK
        )