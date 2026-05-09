"""
Views module for the aspirasi application.

Contains API views to create, list, view detail, mark/unmark,
and edit aspirasi (user-submitted suggestions/complaints). Each view
includes access checks (roles), request validation, activity logging,
and uses corresponding serializers for input/output.
"""

from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import models
from django.utils.dateparse import parse_date

from .models import Aspirasi, RiwayatStatusDitandai, FotoBuktiPendukung
from .serializers import (
    AspirasiSerializer,
    AspirasiListSerializer,
    CreateAspirasiSerializer,
)
from log_aktivitas.utils import catat_log
from core.utils import sanitize_text


class CreateAspirasiView(APIView):
    """Handle creation of a new `Aspirasi`.

    Permissions: authenticated users with role `siswa` or `guru`.
    POST: validate input via `CreateAspirasiSerializer`, create record,
    log activity and return serialized response.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Create a new aspirasi.

        Args:
            request: DRF Request with fields accepted by `CreateAspirasiSerializer`.

        Returns:
            Response with created aspirasi data on success, or validation/errors.
        """
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
    """Return a paginated list of `Aspirasi` filtered by role and query params.

    GET supports filters: `kategori`, `ditandai`, `search`, `date`, `sort`,
    and pagination via `page` and `page_size`.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Retrieve list of aspirasi visible to the requester.

        Returns paginated summary items serialized with `AspirasiListSerializer`.
        """
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
    """Retrieve or update detail fields for a single `Aspirasi`.

    GET: returns full detail (restricted to owner or kemahasiswaan).
    PATCH: used by kemahasiswaan to toggle `status_ditandai` and record history.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, id):
        """Return full detail of an aspirasi if requester has access.

        Args:
            request: DRF Request
            id: primary key of the Aspirasi

        Returns:
            200 with `AspirasiSerializer` data, or 403/404 on access/exists errors.
        """
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
        """Toggle `status_ditandai` for an aspirasi (kemahasiswaan only).

        Expected payload: `status_ditandai` ("ditandai" | "tidak_ditandai").
        Records change in `RiwayatStatusDitandai` and logs the action.
        """
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

        ip = request.META.get('REMOTE_ADDR')

        aspirasi.status_ditandai = new_status
        aspirasi.ditandai_oleh = user if new_status == 'ditandai' else None
        aspirasi.save()

        # Save history
        RiwayatStatusDitandai.objects.create(
            laporan=aspirasi,
            status_ditandai=new_status,
            diubah_oleh=user
        )

        catat_log(
            user,
            'TANDAI_ASPIRASI',
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
    
class EditAspirasiView(APIView):
    """Allow the original sender to edit their aspirasi within time window.

    Supports: GET (prefill), PUT (update fields, add/delete photos).
    Accepts multipart form data for photo uploads (`foto_bukti`).
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def get(self, request, id):
        """Return aspirasi data for edit form prefill.

        Only accessible by the original `pelapor` and when status allows editing.
        """
        try:
            aspirasi = Aspirasi.objects.get(id=id)
        except Aspirasi.DoesNotExist:
            return Response({"error": "Laporan tidak ditemukan"}, status=404)

        if aspirasi.pelapor != request.user:
            return Response({"error": "Hanya pengirim yang dapat mengakses laporan ini"}, status=403)

        serializer = AspirasiSerializer(aspirasi, context={'request': request})
        return Response({"status": "success", "data": serializer.data}, status=200)

    def put(self, request, id):
        """Update an existing aspirasi.

        Fields allowed: `judul`, `kategori`, `deskripsi`, `anonimitas`.
        Additional behavior: remove photos via `delete_foto_ids` or upload new ones
        through `foto_bukti` file inputs. Edits allowed only within 7 days.
        """
        try:
            aspirasi = Aspirasi.objects.get(id=id)
        except Aspirasi.DoesNotExist:
            return Response({"status": "error", "message": "Laporan tidak ditemukan", "data": None}, status=404)

        if aspirasi.pelapor != request.user:
            return Response({"status": "error", "message": "Hanya pengirim yang dapat mengubah laporan", "data": None}, status=403)

        from django.utils import timezone
        from datetime import timedelta

        # perubahan hanya dapat dilakukan sebelum 7 hari 
        if timezone.now() - aspirasi.tanggal_aspirasi > timedelta(days=7):
            return Response({"status": "error", "message": "Waktu edit laporan sudah habis (lebih dari 7 hari)", "data": None}, status=403)

        # Update  fields if present
        judul = request.data.get('judul')
        kategori = request.data.get('kategori')
        deskripsi = request.data.get('deskripsi')
        anonimitas = request.data.get('anonimitas')

        changed = False
        if judul is not None:
            aspirasi.judul = sanitize_text(judul)
            changed = True
        if kategori is not None:
            aspirasi.kategori = kategori
            changed = True
        if deskripsi is not None:
            aspirasi.deskripsi = sanitize_text(deskripsi)
            changed = True
        if anonimitas is not None:
            # anonimitas may be string when sent via formdata
            if isinstance(anonimitas, str):
                aspirasi.anonimitas = anonimitas.lower() in ['1', 'true', 'yes']
            else:
                aspirasi.anonimitas = bool(anonimitas)
            changed = True

        if changed:
            aspirasi.save()

        # Handle deletion of existing photos
        delete_ids = request.data.get('delete_foto_ids')
        ids_to_delete = []
        if delete_ids:
            try:
                import json
                if isinstance(delete_ids, str):
                    ids_to_delete = json.loads(delete_ids)
                else:
                    ids_to_delete = list(delete_ids)
            except Exception:
                if isinstance(delete_ids, str):
                    ids_to_delete = [s for s in delete_ids.split(',') if s]

        if ids_to_delete:
            FotoBuktiPendukung.objects.filter(id__in=ids_to_delete, laporan=aspirasi).delete()

        # Handle new uploaded photos
        files = request.FILES.getlist('foto_bukti')
        if files:
            current_count = FotoBuktiPendukung.objects.filter(laporan=aspirasi).count()
            if current_count + len(files) > 5:
                return Response(
                    {"status": "error", "message": f"Maksimal 5 foto. Saat ini sudah ada {current_count} foto.", "data": None},
                    status=400
                )
            for f in files:
                if f.size > 5 * 1024 * 1024:
                    return Response({"status": "error", "message": "Ukuran file maksimal 5MB", "data": None}, status=400)
                if not f.content_type.startswith('image/'):
                    return Response({"status": "error", "message": "File harus berupa gambar", "data": None}, status=400)
            for f in files:
                FotoBuktiPendukung.objects.create(laporan=aspirasi, foto=f)

        ip = request.META.get('REMOTE_ADDR')
        if aspirasi.anonimitas:
            kelas = request.user.kelas or '-'
            catat_log(
                None,
                'EDIT_LAPORAN',
                f"Anonim dari Kelas {kelas} mengedit aspirasi: {aspirasi.no_laporan}",
                'aspirasi',
                ip
            )
        else:
            catat_log(
                request.user,
                'EDIT_ASPIRASI',
                f"Mengedit aspirasi: {aspirasi.no_laporan}",
                'aspirasi',
                ip
            )

        serializer = AspirasiSerializer(aspirasi, context={'request': request})
        return Response({"status": "success", "message": "Laporan berhasil diubah", "data": serializer.data}, status=200)

