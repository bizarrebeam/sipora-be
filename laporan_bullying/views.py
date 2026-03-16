from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from akun.decorators import role_required
from log_aktivitas.utils import catat_log
from .models import LaporanBullying, FotoBuktiBullying, RiwayatStatusBullying
from .serializers import LaporanBullyingCreateUpdateSerializer, LaporanBullyingListSerializer, LaporanBullyingDetailSerializer, RiwayatStatusBullyingSerializer

# Fungsi untuk membuat laporan bullying
class BuatLaporanBullyingView(APIView):
    permission_classes = [IsAuthenticated]

    @role_required('siswa', 'guru')
    def post(self, request):
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

            return Response({
                "message": "Laporan berhasil dibuat",
                "data": serializer.data
            }, status=201)

        return Response(serializer.errors, status=400)

# Fungsi untuk mengedit laporan bullying
class EditLaporanBullyingView(APIView):
    permission_classes = [IsAuthenticated]

    @role_required('siswa', 'guru')
    def put(self, request, id):
        try:
            laporan = LaporanBullying.objects.get(id=id)
        except LaporanBullying.DoesNotExist:
            return Response({"error": "Laporan tidak ditemukan"}, status=404)

        if laporan.pelapor != request.user:
            return Response({"error": "Hanya pengirim yang dapat mengakses dan mengubah laporan"}, status=403)

        if laporan.status != 'menunggu':
            return Response({"error": "Laporan tidak dapat diubah karena sudah diproses"}, status=400)

        serializer = LaporanBullyingCreateUpdateSerializer(laporan, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()

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

            return Response({"message": "Laporan berhasil diubah", "data": serializer.data})

        return Response(serializer.errors, status=400)

# Fungsi untuk membatalkan laporan bullying
class CancelLaporanBullyingView(APIView):
    permission_classes = [IsAuthenticated]

    @role_required('siswa', 'guru')
    def put(self, request, id):
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

# Fungsi untuk melihat list laporan bullying
class ListLaporanBullyingView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if user.role in ['kemahasiswaan', 'guru_bk']:
            laporan = LaporanBullying.objects.all()
        elif user.role in ['siswa', 'guru']:
            laporan = LaporanBullying.objects.filter(pelapor=user)
        else:
            return Response({"error": "Forbidden"}, status=403)

        # Filter berdasarkan status
        status_filter = request.query_params.get('status')
        if status_filter and status_filter != 'semua':
            laporan = laporan.filter(status=status_filter)

        # Filter berdasarkan pencarian
        search_query = request.query_params.get('search')
        if search_query:
            from django.db.models import Q
            laporan = laporan.filter(
                Q(judul__icontains=search_query) |
                Q(lokasi__icontains=search_query) |
                Q(no_laporan__icontains=search_query)
            )

        # Filter berdasarkan tanggal kejadian
        date_filter = request.query_params.get('date')
        if date_filter:
            laporan = laporan.filter(tanggal_kejadian__date=date_filter)

        # Sort berdasarkan keterbaharuan
        sort_order = request.query_params.get('sort')
        if sort_order == 'asc':
            laporan = laporan.order_by('tanggal_laporan')
        elif sort_order == 'desc':
            laporan = laporan.order_by('-tanggal_laporan')

        if not laporan.exists():
            return Response({"message": "Belum ada laporan yang dikirimkan."}, status=200)

        serializer = LaporanBullyingListSerializer(laporan, many=True)
        return Response(serializer.data)

# Fungsi untuk melihat detail laporan bullying
class DetailLaporanBullyingView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        try:
            laporan = LaporanBullying.objects.get(id=id)
        except LaporanBullying.DoesNotExist:
            return Response({"error": "Laporan belum ditemukan"}, status=404)

        if request.user.role in ['siswa', 'guru'] and laporan.pelapor != request.user:
            return Response({"error": "Akses ditolak"}, status=403)

        serializer = LaporanBullyingDetailSerializer(
            laporan,
            context={'request': request}
        )
        return Response(serializer.data)