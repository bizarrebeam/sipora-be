"""
Views module for the laporan_kerusakan application.

Provides API endpoints for creating, listing, viewing detail,
editing, and canceling facility-damage reports.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.db import models
from django.utils.dateparse import parse_date

from .models import LaporanKerusakan, RiwayatStatusLaporan
from .serializers import (
    LaporanKerusakanSerializer,
    LaporanKerusakanListSerializer,
    CreateLaporanKerusakanSerializer,
    EditLaporanKerusakanSerializer,
    CancelLaporanKerusakanSerializer,
    UpdateStatusLaporanKerusakanSerializer
)
from log_aktivitas.utils import catat_log


STATUS_LABELS = {
    'menunggu': 'Menunggu Konfirmasi',
    'diproses': 'Diproses',
    'menunggu_konfirmasi_selesai': 'Menunggu Konfirmasi Selesai',
    'selesai': 'Selesai',
    'ditolak': 'Ditolak',
    'dibatalkan': 'Dibatalkan',
}


def build_status_change_catatan(status_current, status_new, reason='', note=''):
    """Return a consistent history note for status transitions."""

    reason = (reason or '').strip()
    note = (note or '').strip()

    if status_new == 'ditolak' and reason:
        return f"Status diperbarui ke {STATUS_LABELS['ditolak']}. Alasan: {reason}"

    if status_new == 'menunggu_konfirmasi_selesai':
        return (
            f"Status diperbarui ke {STATUS_LABELS['menunggu_konfirmasi_selesai']}. "
            f"Catatan tindak lanjut: {note}"
        )

    if status_current == 'menunggu_konfirmasi_selesai' and status_new == 'selesai':
        if note:
            return f"Pelapor mengonfirmasi laporan selesai. Catatan: {note}"
        return 'Pelapor mengonfirmasi laporan selesai.'

    if status_current == 'menunggu_konfirmasi_selesai' and status_new == 'diproses':
        return 'Pelapor menyatakan laporan belum selesai dan dikembalikan ke Diproses.'

    if note:
        return f"Status diperbarui ke {STATUS_LABELS.get(status_new, status_new)}. Catatan: {note}"

    return None


class CreateLaporanKerusakanView(APIView):
    """API view for creating a new facility damage report."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Handle POST request to create a report with optional photo evidence."""
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
    """API view for listing reports with filtering, search, sorting, and pagination."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Return report list scope based on user role and query parameters."""
        user = request.user

        if user.role not in ['siswa', 'guru', 'kemahasiswaan']:
            return Response(
                {
                    'status': 'success',
                    'message': 'Anda tidak memiliki akses untuk melakukan aksi ini.',
                    'data': {
                        'total': 0,
                        'laporan': [],
                        'access_denied': True,
                        'access_message': 'Anda tidak memiliki akses untuk melakukan aksi ini.'
                    }
                },
                status=status.HTTP_200_OK
            )
        
        if user.role == 'kemahasiswaan':
            laporan_list = LaporanKerusakan.objects.all()
        else:
            laporan_list = LaporanKerusakan.objects.filter(pelapor=user)
        
        # select_related to avoid N+1 on pelapor fields
        laporan_list = laporan_list.select_related('pelapor')

        # Only fetch fields needed for list view
        laporan_list = laporan_list.only(
            'id', 'no_laporan', 'judul', 'lokasi', 'tanggal_kejadian',
            'status', 'anonimitas', 'tanggal_laporan', 'updated_at',
            'pelapor__id', 'pelapor__username', 'pelapor__nama_lengkap',
            'pelapor__kelas', 'pelapor__role', 'pelapor__is_verified'
        )

        status_filter = request.query_params.get('status')
        if status_filter and status_filter != 'semua':
            laporan_list = laporan_list.filter(status=status_filter)
        
        search = request.query_params.get('search')
        if search:
            laporan_list = laporan_list.filter(
                models.Q(no_laporan__icontains=search) |
                models.Q(judul__icontains=search) |
                models.Q(lokasi__icontains=search)
            )

        date_filter = request.query_params.get('date')
        if date_filter:
            parsed_date = parse_date(date_filter)
            if not parsed_date:
                return Response(
                    {
                        'status': 'error',
                        'message': 'Parameter date harus berformat YYYY-MM-DD',
                        'data': None
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            laporan_list = laporan_list.filter(tanggal_kejadian=parsed_date)

        start_date = request.query_params.get('start_date')
        if start_date:
            parsed_start_date = parse_date(start_date)
            if not parsed_start_date:
                return Response(
                    {
                        'status': 'error',
                        'message': 'Parameter start_date harus berformat YYYY-MM-DD',
                        'data': None
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            laporan_list = laporan_list.filter(tanggal_kejadian__gte=parsed_start_date)

        end_date = request.query_params.get('end_date')
        if end_date:
            parsed_end_date = parse_date(end_date)
            if not parsed_end_date:
                return Response(
                    {
                        'status': 'error',
                        'message': 'Parameter end_date harus berformat YYYY-MM-DD',
                        'data': None
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            laporan_list = laporan_list.filter(tanggal_kejadian__lte=parsed_end_date)

        sort_order = request.query_params.get('sort')
        if sort_order == 'asc':
            laporan_list = laporan_list.order_by('tanggal_laporan')
        else:
            laporan_list = laporan_list.order_by('-tanggal_laporan')

        # Pagination
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 20)
        try:
            page = max(1, int(page))
            page_size = min(max(1, int(page_size)), 100)
        except (ValueError, TypeError):
            page = 1
            page_size = 20

        total = laporan_list.count()
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_data = laporan_list[start_idx:end_idx]
        
        serializer = LaporanKerusakanListSerializer(
            page_data, 
            many=True,
            context={'request': request}
        )
        
        return Response(
            {
                'status': 'success',
                'message': 'Berhasil mengambil data laporan',
                'data': {
                    'total': total,
                    'laporan': serializer.data,
                    'access_denied': False,
                    'access_message': None
                }
            },
            status=status.HTTP_200_OK
        )


class LaporanKerusakanDetailView(APIView):
    """API view for retrieving full detail of a single report."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, id):
        """Return report detail if requester has access rights."""
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
    """API view for editing reports that are still in waiting status."""
    permission_classes = [IsAuthenticated]
    
    def put(self, request, id):
        """Handle PUT request to update a report owned by the authenticated user."""
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
        """Return report data for edit form prefill with access validation."""
        user = request.user

        if user.role not in ['siswa', 'guru']:
            return Response(
                {
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
    """API view for canceling reports with mandatory reason validation."""
    permission_classes = [IsAuthenticated]

    def patch(self, request, id):
        """Handle PATCH request to cancel a report in waiting status."""
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


class UpdateStatusLaporanKerusakanView(APIView):
    """API view for updating report status by authorized admin/staff users."""
    permission_classes = [IsAuthenticated]

    def put(self, request, id):
        """Handle PUT request to update report status."""
        user = request.user

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

        # cannot update status if already cancelled
        if laporan.status in ['dibatalkan']:
            return Response(
                {
                    'status': 'error',
                    'message': 'Laporan yang dibatalkan tidak dapat diubah statusnya',
                    'data': None
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = UpdateStatusLaporanKerusakanSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    'status': 'error',
                    'message': 'Validasi gagal',
                    'data': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        status_new = serializer.validated_data['status']
        reason = serializer.validated_data.get('reason', '').strip()
        note = serializer.validated_data.get('note', '').strip()

        is_admin = user.role == 'kemahasiswaan'
        is_pelapor = laporan.pelapor == user

        # Validate status transitions
        status_current = laporan.status
        valid_transitions = {
            'menunggu': ['diproses', 'ditolak'],
            'diproses': ['menunggu_konfirmasi_selesai', 'ditolak'],
            'menunggu_konfirmasi_selesai': ['selesai', 'diproses'],
            'selesai': [],
            'ditolak': [],
            'dibatalkan': []
        }

        if status_new not in valid_transitions.get(status_current, []):
            return Response(
                {
                    'status': 'error',
                    'message': f'Tidak dapat mengubah status dari {status_current} ke {status_new}',
                    'data': None
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if status_current == 'menunggu_konfirmasi_selesai':
            if not is_pelapor:
                return Response(
                    {
                        'status': 'error',
                        'message': 'Hanya pelapor yang dapat mengonfirmasi penyelesaian laporan',
                        'data': None
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
        else:
            if not is_admin:
                return Response(
                    {
                        'status': 'error',
                        'message': 'Hanya Kemahasiswaan yang dapat mengubah status laporan',
                        'data': None
                    },
                    status=status.HTTP_403_FORBIDDEN
                )

        # Update status
        laporan.status = status_new
        laporan.save()

        # Create history entry
        catatan = build_status_change_catatan(status_current, status_new, reason, note)

        RiwayatStatusLaporan.objects.create(
            laporan=laporan,
            status=status_new,
            catatan=catatan,
            diubah_oleh=user
        )

        ip = request.META.get('REMOTE_ADDR')
        catat_log(
            user,
            'UPDATE_STATUS_LAPORAN',
            f"Mengubah status laporan kerusakan {laporan.no_laporan} menjadi {status_new}",
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
                'message': 'Status laporan berhasil diperbarui',
                'data': response_serializer.data
            },
            status=status.HTTP_200_OK
        )
