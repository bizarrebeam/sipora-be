from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import models

from .models import LaporanKerusakan, RiwayatStatusLaporan
from .serializers import (
    LaporanKerusakanSerializer,
    CreateLaporanKerusakanSerializer,
    EditLaporanKerusakanSerializer,
    CancelLaporanKerusakanSerializer
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

class EditLaporanKerusakanView(APIView):
    permission_classes = [IsAuthenticated]
    
    def put(self, request, id):
        user = request.user
        # only siswa and guru can edit laporan
        if user.role not in ['siswa', 'guru']:
            return Response(
                {
                    'status': 'error',
                    'message': 'Hanya pengirim yang dapat mengakses dan mengubah laporan',
                    'data': None
                },
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            laporan = LaporanKerusakan.objects.get(id=id)
        except LaporanKerusakan.DoesNotExist:
            return Response(
                {
                    'status': 'error',
                    'message': 'Laporan tidak ditemukan',
                    'data': None
                },
                status=status.HTTP_404_NOT_FOUND
            )

        # only creator can edit
        if laporan.pelapor != user:
            return Response(
                {
                    'status': 'error',
                    'message': 'Hanya pengirim yang dapat mengakses dan mengubah laporan',
                    'data': None
                },
                status=status.HTTP_403_FORBIDDEN
            )

        # cannot edit if status is not menunggu
        if laporan.status != 'menunggu':
            return Response(
                {
                    'status': 'error',
                    'message': 'Laporan tidak dapat diubah karena sudah diproses',
                    'data': None
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = EditLaporanKerusakanSerializer(
            laporan,
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            laporan = serializer.save()

            ip = request.META.get('REMOTE_ADDR')
            if laporan.anonimitas:
                kelas = user.kelas or '-'
                catat_log(
                    None,
                    'EDIT_LAPORAN',
                    f"Anonim dari Kelas {kelas} mengubah laporan kerusakan: {laporan.no_laporan}",
                    'kerusakan',
                    ip
                )
            else:
                catat_log(
                    user,
                    'EDIT_LAPORAN',
                    f"Mengubah laporan kerusakan: {laporan.no_laporan}",
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
                    'message': 'Laporan berhasil diperbarui',
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

    def get(self, request, id):
        user = request.user

        if user.role not in ['siswa', 'guru']:
            return Response(
                {
                    'status': 'error',
                    'message': 'Hanya pengirim yang dapat mengakses dan mengubah laporan',
                    'data': None
                },
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            laporan = LaporanKerusakan.objects.get(id=id)
        except LaporanKerusakan.DoesNotExist:
            return Response(
                {
                    'status': 'error',
                    'message': 'Laporan tidak ditemukan',
                    'data': None
                },
                status=status.HTTP_404_NOT_FOUND
            )

        # only creator can view edit form
        if laporan.pelapor != user:
            return Response(
                {
                    'status': 'error',
                    'message': 'Hanya pengirim yang dapat mengakses dan mengubah laporan',
                    'data': None
                },
                status=status.HTTP_403_FORBIDDEN
            )

        if laporan.status != 'menunggu':
            return Response(
                {
                    'status': 'error',
                    'message': 'Laporan tidak dapat diubah karena sudah diproses',
                    'data': None
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = LaporanKerusakanSerializer(
            laporan,
            context={'request': request}
        )

        return Response(
            {
                'status': 'success',
                'message': 'Berhasil mengambil data laporan untuk diedit',
                'data': serializer.data
            },
            status=status.HTTP_200_OK
        )

class CancelLaporanKerusakanView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, id):
        user = request.user

        # only siswa and guru can cancel
        if user.role not in ['siswa', 'guru']:
            return Response(
                {
                    'status': 'error',
                    'message': 'Hanya siswa atau guru yang dapat membatalkan laporan',
                    'data': None
                },
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            laporan = LaporanKerusakan.objects.get(id=id)
        except LaporanKerusakan.DoesNotExist:
            return Response(
                {
                    'status': 'error',
                    'message': 'Laporan tidak ditemukan',
                    'data': None
                },
                status=status.HTTP_404_NOT_FOUND
            )

        # only creator can cancel
        if laporan.pelapor != user:
            return Response(
                {
                    'status': 'error',
                    'message': 'Hanya pengirim yang dapat membatalkan laporan',
                    'data': None
                },
                status=status.HTTP_403_FORBIDDEN
            )

        # can only cancel when status is 'menunggu'
        if laporan.status != 'menunggu':
            return Response(
                {
                    'status': 'error',
                    'message': 'Laporan tidak dapat dibatalkan karena sudah diproses.',
                    'data': None
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = CancelLaporanKerusakanSerializer(data=request.data)
        if not serializer.is_valid():
            errors = serializer.errors
            if 'alasan' in errors and any('wajib' in str(e).lower() for e in errors['alasan']):
                return Response(
                    {
                        'status': 'error',
                        'message': 'Alasan pembatalan wajib diisi',
                        'data': errors
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            return Response(
                {
                    'status': 'error',
                    'message': 'Validasi gagal',
                    'data': errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        alasan = serializer.validated_data['alasan']

        laporan.status = 'dibatalkan'
        laporan.save()

        # catat riwayat status
        RiwayatStatusLaporan.objects.create(
            laporan=laporan,
            status='dibatalkan',
            catatan=alasan,
            diubah_oleh=user
        )

        ip = request.META.get('REMOTE_ADDR')
        if laporan.anonimitas:
            kelas = user.kelas or '-'
            catat_log(
                None,
                'CANCEL_LAPORAN',
                f"Anonim dari Kelas {kelas} membatalkan laporan kerusakan: {laporan.no_laporan}",
                'kerusakan',
                ip
            )
        else:
            catat_log(
                user,
                'CANCEL_LAPORAN',
                f"Membatalkan laporan kerusakan: {laporan.no_laporan}",
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
                'message': 'Laporan berhasil dibatalkan',
                'data': response_serializer.data
            },
            status=status.HTTP_200_OK
        )