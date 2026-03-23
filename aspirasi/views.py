from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import models
from django.utils.dateparse import parse_date

from .models import Aspirasi, RiwayatStatusDitandai
from .serializers import (
    AspirasiSerializer,
    AspirasiListSerializer,
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
        
        aspirasi_list = aspirasi_list.select_related('pelapor')

        aspirasi_list = aspirasi_list.only(
            'id', 'no_laporan', 'judul', 'kategori', 'status_ditandai',
            'anonimitas', 'tanggal_aspirasi', 'updated_at',
            'pelapor__id', 'pelapor__username', 'pelapor__nama_lengkap',
            'pelapor__kelas', 'pelapor__role', 'pelapor__is_verified'
        )

        # optional filter: kategori
        kategori_filter = request.query_params.get('kategori')
        if kategori_filter and kategori_filter != 'semua':
            aspirasi_list = aspirasi_list.filter(kategori__iexact=kategori_filter)

        # optional filter: ditandai status
        ditandai_filter = request.query_params.get('ditandai')
        if ditandai_filter and ditandai_filter != 'semua':
            aspirasi_list = aspirasi_list.filter(status_ditandai=ditandai_filter)

        # Search (indexed fields only, no deskripsi)
        search = request.query_params.get('search')
        if search:
            aspirasi_list = aspirasi_list.filter(
                models.Q(no_laporan__icontains=search) |
                models.Q(judul__icontains=search) |
                models.Q(kategori__icontains=search)
            )

        # Date filter
        date_filter = request.query_params.get('date')
        if date_filter:
            parsed_date = parse_date(date_filter)
            if parsed_date:
                from django.utils import timezone
                from datetime import timedelta
                start_of_day = timezone.make_aware(
                    timezone.datetime.combine(parsed_date, timezone.datetime.min.time())
                )
                end_of_day = start_of_day + timedelta(days=1)
                aspirasi_list = aspirasi_list.filter(
                    tanggal_aspirasi__gte=start_of_day,
                    tanggal_aspirasi__lt=end_of_day
                )

        # Sort
        sort_order = request.query_params.get('sort')
        if sort_order == 'asc':
            aspirasi_list = aspirasi_list.order_by('tanggal_aspirasi')
        else:
            aspirasi_list = aspirasi_list.order_by('-tanggal_aspirasi')

        # Pagination
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 20)
        try:
            page = max(1, int(page))
            page_size = min(max(1, int(page_size)), 100)
        except (ValueError, TypeError):
            page = 1
            page_size = 20

        total = aspirasi_list.count()
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_data = aspirasi_list[start_idx:end_idx]
        
        serializer = AspirasiListSerializer(
            page_data, 
            many=True,
            context={'request': request}
        )
        
        return Response(
            {
                'status': 'success',
                'message': 'Berhasil mengambil data aspirasi',
                'data': {
                    'total': total,
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