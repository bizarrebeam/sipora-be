"""
Views module for the laporan_bullying application.

Contains API views to manage bullying report features:
creation, modification, cancellation, list retrieval, 
and specific detail retrieval for a report.
"""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework import status
from akun.decorators import role_required
from log_aktivitas.utils import catat_log
from .models import LaporanBullying, FotoBuktiBullying, RiwayatStatusBullying
from .serializers import (
    LaporanBullyingCreateUpdateSerializer,
    LaporanBullyingListSerializer,
    LaporanBullyingDetailSerializer,
    RiwayatStatusBullyingSerializer,
    UpdateStatusLaporanBullyingSerializer,
)
from django.db.models import Q

# Status display labels mapping
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
        return 'Pelapor mengonfirmasi laporan selesai'

    if status_current == 'menunggu_konfirmasi_selesai' and status_new == 'diproses':
        return 'Pelapor menyatakan laporan belum selesai dan dikembalikan ke Diproses'

    if note:
        return f"Status diperbarui ke {STATUS_LABELS.get(status_new, status_new)}. Catatan: {note}"

    return None


class BuatLaporanBullyingView(APIView):
    """
    API View for creating a new bullying report.
    
    Requires authentication. Only users with the 'siswa' (student) or 'guru' (teacher)
    role are permitted to create a report through this endpoint.
    """
    permission_classes = [IsAuthenticated]

    @role_required('siswa', 'guru')
    def post(self, request):
        """
        Handles HTTP POST requests to create a bullying report.
        
        Args:
            request: The HTTP request object containing report data and proof photo files.
            
        Returns:
            Response: DRF Response object containing the status of the report creation.
                     - 201 Created: If the report is successfully created.
                     - 400 Bad Request: If data is invalid, photo count exceeds 5, 
                                        file size exceeds 5MB, or file type is not an image.
        """
        serializer = LaporanBullyingCreateUpdateSerializer(data=request.data)

        if serializer.is_valid():
            laporan = serializer.save(
                pelapor=request.user,
                status='menunggu'
            )

            # Mengambil file dari request
            files = request.FILES.getlist('foto_bukti')

            # Validasi jumlah file
            if len(files) > 5:
                return Response({"error": "Maksimal 5 foto"}, status=400)

            for file in files:
                # Validasi ukuran file (maks 5MB)
                if file.size > 5 * 1024 * 1024:
                    return Response({"error": "Ukuran file maksimal 5MB"}, status=400)

                # Validasi tipe file
                if not file.content_type.startswith('image/'):
                    return Response({"error": "File harus berupa gambar"}, status=400)

            for file in files:
                FotoBuktiBullying.objects.create(
                    laporan=laporan,
                    foto=file
                )

            RiwayatStatusBullying.objects.create(
                laporan=laporan,
                status='menunggu',
                diubah_oleh=request.user,
                catatan="Laporan dibuat"
            )

            # Log activity
            ip = request.META.get('REMOTE_ADDR')
            if laporan.anonimitas:
                kelas = request.user.kelas or '-'
                catat_log(
                    None,
                    'BUAT_LAPORAN',
                    f"Anonim dari Kelas {kelas} membuat laporan bullying: {laporan.no_laporan}",
                    'laporan_bullying',
                    ip
                )
            else:
                catat_log(
                    request.user,
                    'BUAT_LAPORAN',
                    f"Membuat laporan bullying: {laporan.no_laporan}",
                    'laporan_bullying',
                    ip
                )

            return Response({
                "message": "Laporan berhasil dibuat",
                "data": serializer.data
            }, status=201)

        return Response(serializer.errors, status=400)

class EditLaporanBullyingView(APIView):
    """
    API View for modifying or updating an existing bullying report.
    
    Only accessible by users with the 'siswa' or 'guru' role.
    Additionally, only the report creator (pelapor) has the right to modify their own report.
    """
    permission_classes = [IsAuthenticated]

    @role_required('siswa', 'guru')
    def put(self, request, id):
        """
        Handles PUT requests to partially or fully update a bullying report.
        
        Args:
            request (Request): Request object containing the update payload.
            id (int/str): ID/Primary Key of the LaporanBullying entry to be updated.
            
        Returns:
            Response:
                - 200 OK if the report is successfully updated.
                - 404 Not Found if the report is not found.
                - 403 Forbidden if the user attempts to modify someone else's report.
                - 400 Bad Request if the report has already been processed (not 'menunggu'),
                  or if the serializer data format is invalid.
        """
        try:
            laporan = LaporanBullying.objects.get(id=id)
        except LaporanBullying.DoesNotExist:
            return Response({"error": "Laporan tidak ditemukan"}, status=404)

        if laporan.pelapor != request.user:
            return Response({"error": "Hanya pengirim yang dapat mengakses dan mengubah laporan"}, status=403)

        if laporan.status != 'menunggu':
            return Response({"error": "Laporan tidak dapat diubah karena sudah diproses"}, status=400)

        # ── Update field langsung (pola aspirasi) ──
        judul = request.data.get('judul')
        deskripsi = request.data.get('deskripsi')
        lokasi = request.data.get('lokasi')
        tanggal_kejadian = request.data.get('tanggal_kejadian')
        waktu_kejadian = request.data.get('waktu_kejadian')
        jenis_bullying = request.data.get('jenis_bullying')
        anonimitas = request.data.get('anonimitas')

        changed = False
        if judul is not None:
            laporan.judul = judul
            changed = True
        if deskripsi is not None:
            laporan.deskripsi = deskripsi
            changed = True
        if lokasi is not None:
            laporan.lokasi = lokasi
            changed = True
        if tanggal_kejadian is not None:
            laporan.tanggal_kejadian = tanggal_kejadian
            changed = True
        if waktu_kejadian is not None:
            laporan.waktu_kejadian = waktu_kejadian or None
            changed = True
        if jenis_bullying is not None:
            laporan.jenis_bullying = jenis_bullying
            changed = True
        if anonimitas is not None:
            if isinstance(anonimitas, str):
                laporan.anonimitas = anonimitas.lower() in ['1', 'true', 'yes']
            else:
                laporan.anonimitas = bool(anonimitas)
            changed = True

        if changed:
            laporan.save()

        # ── Hapus foto spesifik (pola aspirasi: JSON parse + fallback comma-split) ──
        delete_ids_raw = request.data.get('deleted_foto_ids')
        ids_to_delete = []
        if delete_ids_raw:
            try:
                import json
                if isinstance(delete_ids_raw, str):
                    ids_to_delete = json.loads(delete_ids_raw)
                else:
                    ids_to_delete = list(delete_ids_raw)
            except Exception:
                if isinstance(delete_ids_raw, str):
                    ids_to_delete = [s.strip() for s in delete_ids_raw.split(',') if s.strip()]

        if ids_to_delete:
            laporan.foto_bukti.filter(id__in=ids_to_delete).delete()

        # ── Tambah foto baru ──
        files = request.FILES.getlist('foto_bukti')
        if files:
            current_count = laporan.foto_bukti.count()
            if current_count + len(files) > 5:
                return Response(
                    {"error": f"Maksimal 5 foto (saat ini {current_count} foto, tidak bisa menambah {len(files)} lagi)"},
                    status=400
                )
            for file in files:
                if file.size > 5 * 1024 * 1024:
                    return Response({"error": f"Ukuran {file.name} maksimal 5MB"}, status=400)
                if not file.content_type.startswith('image/'):
                    return Response({"error": f"File {file.name} harus berupa gambar"}, status=400)
            for file in files:
                FotoBuktiBullying.objects.create(laporan=laporan, foto=file)

        # Log activity
        ip = request.META.get('REMOTE_ADDR')
        if laporan.anonimitas:
            kelas = request.user.kelas or '-'
            catat_log(
                None,
                'EDIT_LAPORAN',
                f"Anonim dari Kelas {kelas} mengedit laporan bullying: {laporan.no_laporan}",
                'laporan_bullying',
                ip
            )
        else:
            catat_log(
                request.user,
                'EDIT_LAPORAN',
                f"Mengedit laporan bullying: {laporan.no_laporan}",
                'laporan_bullying',
                ip
            )

        return Response({"message": "Laporan berhasil diubah", "data": LaporanBullyingDetailSerializer(laporan, context={'request': request}).data})

class CancelLaporanBullyingView(APIView):
    """
    API View for canceling a submitted bullying report.
    
    Only the report creator ('siswa' or 'guru') is allowed to cancel it.
    Reports can only be canceled if they are still in the 'menunggu' (waiting) status.
    """
    permission_classes = [IsAuthenticated]

    @role_required('siswa', 'guru')
    def put(self, request, id):
        """
        Handles PUT requests to update the report status to 'dibatalkan' (canceled).
        
        Args:
            request (Request): Request object containing the 'alasan_pembatalan' payload.
            id (int/str): ID/Primary Key of the LaporanBullying entry to be canceled.
            
        Returns:
            Response:
                - 200 OK if the cancellation is successful.
                - 400 Bad Request if the reason has less than 50 characters, 
                  or if the report is no longer in the 'menunggu' status.
                - 403 Forbidden if the creator tries to cancel a report that isn't theirs.
                - 404 Not Found if the report ID does not exist in the database.
        """
        alasan = request.data.get('alasan_pembatalan')

        if not alasan or len(alasan) < 50:
            return Response({"error": "Alasan pembatalan wajib diisi minimal 50 karakter"}, status=400)

        try:
            laporan = LaporanBullying.objects.get(id=id)
        except LaporanBullying.DoesNotExist:
            return Response({"error": "Laporan tidak ditemukan"}, status=404)

        if laporan.pelapor != request.user:
            return Response({"error": "Hanya pembuat laporan yang bisa membatalkan"}, status=403)

        if laporan.status != 'menunggu':
            return Response({"error": "Laporan tidak dapat dibatalkan karena sudah diproses."}, status=400)

        laporan.status = 'dibatalkan'
        laporan.alasan_pembatalan = alasan
        laporan.save()

        RiwayatStatusBullying.objects.create(
            laporan=laporan,
            status='dibatalkan',
            diubah_oleh=request.user,
            catatan="Laporan dibatalkan"
        )

        # Log activity
        ip = request.META.get('REMOTE_ADDR')
        if laporan.anonimitas:
            kelas = request.user.kelas or '-'
            catat_log(
                None,
                'BATALKAN_LAPORAN',
                f"Anonim dari Kelas {kelas} membatalkan laporan bullying: {laporan.no_laporan}",
                'laporan_bullying',
                ip
            )
        else:
            catat_log(
                request.user,
                'BATALKAN_LAPORAN',
                f"Membatalkan laporan bullying: {laporan.no_laporan}",
                'laporan_bullying',
                ip
            )

        return Response({"message": "Laporan berhasil dibatalkan"})


class UpdateStatusLaporanBullyingView(APIView):
    """API view for updating report status by authorized admin/staff users."""
    permission_classes = [IsAuthenticated]

    def put(self, request, id):
        """Handle PUT request to update report status."""
        user = request.user

        try:
            laporan = LaporanBullying.objects.get(id=id)
        except LaporanBullying.DoesNotExist:
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

        serializer = UpdateStatusLaporanBullyingSerializer(data=request.data)
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

        is_admin = user.role in ['kemahasiswaan', 'guru_bk']
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
                    'message': f'Tidak dapat mengubah status dari {STATUS_LABELS.get(status_current, status_current)} ke {STATUS_LABELS.get(status_new, status_new)}',
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
                        'message': 'Hanya Kemahasiswaan atau Guru BK yang dapat mengubah status laporan',
                        'data': None
                    },
                    status=status.HTTP_403_FORBIDDEN
                )

            # Check if pelapor account is verified (only for admin status updates)
            if not laporan.pelapor.is_verified:
                # Log the failed verification attempt
                ip = request.META.get('REMOTE_ADDR')
                catat_log(
                    user,
                    'ATTEMPT_UPDATE_STATUS_UNVERIFIED_USER',
                    f"Percobaan mengubah status laporan bullying untuk akun belum terverifikasi: {laporan.no_laporan}",
                    'bullying',
                    ip
                )

                return Response(
                    {
                        'status': 'error',
                        'message': 'AKUN_BELUM_TERVERIFIKASI',
                        'data': {
                            'nama': laporan.pelapor.nama_lengkap,
                            'nis': laporan.pelapor.nis or '-',
                            'kelas': laporan.pelapor.kelas or '-',
                            'pelapor_id': str(laporan.pelapor.id)
                        }
                    },
                    status=status.HTTP_403_FORBIDDEN
                )

        # Update status
        laporan.status = status_new
        laporan.save()

        # Create history entry
        catatan = build_status_change_catatan(status_current, status_new, reason, note)

        RiwayatStatusBullying.objects.create(
            laporan=laporan,
            status=status_new,
            catatan=catatan,
            diubah_oleh=user
        )

        # Log activity
        ip = request.META.get('REMOTE_ADDR')
        catat_log(
            user,
            'UPDATE_STATUS_LAPORAN',
            f"Mengubah status laporan bullying {laporan.no_laporan} dari {STATUS_LABELS.get(status_current, status_current)} ke {STATUS_LABELS.get(status_new, status_new)}",
            'bullying',
            ip
        )

        response_serializer = LaporanBullyingDetailSerializer(
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

class ListLaporanBullyingView(APIView):
    """
    API View to retrieve a list of bullying reports with filtering, 
    searching, sorting, and pagination features.
    
    Access and scope of displayed data:
    - 'kemahasiswaan' / 'guru_bk': Can view all reports from all creators.
    - 'siswa' / 'guru': Can only view reports created by themselves.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Handles GET requests to retrieve a collection of reports based on
        the user's role and query parameters.
        
        Query Parameters Scenario:
        - status: Filters based on report status.
        - search: Searches text-based fields (judul, lokasi, no_laporan).
        - date: Filters based on tanggal_kejadian (incident date).
        - sort: 'asc' to order oldest-first; otherwise defaults to newest-first.
        - page, page_size: Used to handle pagination.
        
        Returns:
            Response: List of reports along with pagination metadata (count, results).
        """
        user = request.user

        if user.role in ['kemahasiswaan', 'guru_bk']:
            laporan = LaporanBullying.objects.all()
        elif user.role in ['siswa', 'guru']:
            laporan = LaporanBullying.objects.filter(pelapor=user)
        else:
            return Response({"error": "Forbidden"}, status=403)

        # select_related to avoid N+1 on pelapor fields
        laporan = laporan.select_related('pelapor')

        # Only fetch fields needed for list serializer
        laporan = laporan.only(
            'id', 'no_laporan', 'judul', 'tanggal_kejadian', 'lokasi',
            'status', 'tanggal_laporan', 'anonimitas',
            'pelapor__id', 'pelapor__nama_lengkap', 'pelapor__kelas',
            'pelapor__is_verified', 'pelapor__role', 'jenis_bullying'
        )

        # Filter berdasarkan status
        status_filter = request.query_params.get('status')
        if status_filter and status_filter != 'semua':
            laporan = laporan.filter(status=status_filter)

        # Filter berdasarkan pencarian (indexed fields only, no deskripsi)
        search_query = request.query_params.get('search')
        if search_query:
            laporan = laporan.filter(
                Q(judul__icontains=search_query) |
                Q(lokasi__icontains=search_query) |
                Q(no_laporan__icontains=search_query)
            )

        # Filter berdasarkan tanggal kejadian
        date_filter = request.query_params.get('date')
        if date_filter:
            laporan = laporan.filter(tanggal_kejadian=date_filter)

        # Sort berdasarkan keterbaharuan
        sort_order = request.query_params.get('sort')
        if sort_order == 'asc':
            laporan = laporan.order_by('tanggal_laporan')
        else:
            laporan = laporan.order_by('-tanggal_laporan')

        # Pagination
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)
        try:
            page = max(1, int(page))
            page_size = min(max(1, int(page_size)), 100)
        except (ValueError, TypeError):
            page = 1
            page_size = 10

        total = laporan.count()
        start = (page - 1) * page_size
        end = start + page_size
        page_data = laporan[start:end]

        serializer = LaporanBullyingListSerializer(page_data, many=True)
        return Response({
            "count": total,
            "results": serializer.data
        })

class DetailLaporanBullyingView(APIView):
    """
    API View to view the full details of a specific bullying report.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        """
        Handles GET requests to return detailed data of a single LaporanBullying entry,
        including its relations.
        
        Args:
            request (Request): The API request object.
            id (int/str): Unique ID/Primary Key of the requested LaporanBullying.
            
        Returns:
            Response: 
                - 200 OK with the comprehensive details of the report.
                - 404 Not Found if the entry does not exist, or if a user attempts 
                  to view someone else's report (unless they are Kemahasiswaan/BK staff).
        """
        try:
            laporan = LaporanBullying.objects.get(id=id)
        except LaporanBullying.DoesNotExist:
            return Response({"error": "Laporan belum ditemukan"}, status=404)

        if request.user.role in ['siswa', 'guru'] and laporan.pelapor != request.user:
            return Response({"error": "Laporan belum ditemukan"}, status=404)

        serializer = LaporanBullyingDetailSerializer(
            laporan,
            context={'request': request}
        )
        return Response(serializer.data)