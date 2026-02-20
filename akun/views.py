from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from .serializers import (
    RegisterSiswaSerializer,
    AdminBuatGuruSerializer,
    AdminBuatGuruBKSerializer,
    LoginSerializer,
    PenggunaSerializer,
    EditProfilSerializer,
    UbahPasswordSerializer,
)
from .models import Pengguna
from .decorators import role_required
from log_aktivitas.helpers import catat_log


class RegisterSiswaView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSiswaSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Akun siswa berhasil dibuat."}, status=201)
        return Response(serializer.errors, status=400)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.validated_data)
        return Response(serializer.errors, status=400)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        import time
        try:
            t0 = time.perf_counter()
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response({"detail": "Refresh token diperlukan."}, status=400)

            t1 = time.perf_counter()
            token = RefreshToken(refresh_token)
            t2 = time.perf_counter()
            token.blacklist()
            t3 = time.perf_counter()

            print(f"[LOGOUT DETAIL] parse_data: {(t1-t0)*1000:.0f}ms | RefreshToken(): {(t2-t1)*1000:.0f}ms | blacklist(): {(t3-t2)*1000:.0f}ms | TOTAL: {(t3-t0)*1000:.0f}ms")

            return Response({"message": "Logout berhasil."})
        except Exception:
            return Response({"detail": "Token tidak valid atau sudah kedaluwarsa."}, status=400)


class ProfilView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = PenggunaSerializer(request.user)
        return Response(serializer.data)


class EditProfilView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        serializer = EditProfilSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.update(request.user, serializer.validated_data)
            catat_log(
                request=request,
                aksi='Edit Profil',
                deskripsi=f'{request.user.nama_lengkap} mengubah profil.',
                modul='akun'
            )
            return Response({
                "message": "Profil berhasil diperbarui.",
                "data": PenggunaSerializer(request.user).data
            })
        return Response(serializer.errors, status=400)


class UbahPasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        serializer = UbahPasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            catat_log(
                request=request,
                aksi='Ubah Password',
                deskripsi=f'{request.user.nama_lengkap} mengubah password.',
                modul='akun'
            )
            return Response({"message": "Password berhasil diubah."})
        return Response(serializer.errors, status=400)


class AdminBuatAkunView(APIView):
    permission_classes = [IsAuthenticated]

    @role_required('kemahasiswaan')
    def post(self, request):
        role_type = request.data.get('role_type')

        if role_type == 'guru':
            serializer = AdminBuatGuruSerializer(data=request.data)
        elif role_type == 'guru_bk':
            serializer = AdminBuatGuruBKSerializer(data=request.data)
        else:
            return Response({"detail": "role_type harus 'guru' atau 'guru_bk'."}, status=400)

        if serializer.is_valid():
            user = serializer.save()
            catat_log(
                request=request,
                aksi='Buat Akun',
                deskripsi=f'Admin membuat akun {role_type}: {user.nama_lengkap}',
                modul='akun'
            )
            label = 'Guru BK' if role_type == 'guru_bk' else 'Guru'
            return Response({"message": f"Akun {label} berhasil dibuat."}, status=201)
        return Response(serializer.errors, status=400)


class AdminDaftarAkunView(APIView):
    permission_classes = [IsAuthenticated]

    @role_required('kemahasiswaan')
    def get(self, request):
        search = request.query_params.get('search', '').strip()

        base_qs = Pengguna.objects.all()
        if search:
            base_qs = base_qs.filter(
                Q(nama_lengkap__icontains=search) |
                Q(nisn__icontains=search) |
                Q(nuptk__icontains=search) |
                Q(username__icontains=search)
            )

        siswa_qs = base_qs.filter(role='siswa').order_by('nama_lengkap')
        guru_qs = base_qs.filter(role='guru').order_by('nama_lengkap')
        guru_bk_qs = base_qs.filter(role='guru_bk').order_by('nama_lengkap')

        return Response({
            "siswa": {
                "total": siswa_qs.count(),
                "data": PenggunaSerializer(siswa_qs, many=True).data,
            },
            "guru": {
                "total": guru_qs.count(),
                "data": PenggunaSerializer(guru_qs, many=True).data,
            },
            "guru_bk": {
                "total": guru_bk_qs.count(),
                "data": PenggunaSerializer(guru_bk_qs, many=True).data,
            },
        })