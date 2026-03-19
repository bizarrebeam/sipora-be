from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.pagination import PageNumberPagination
from django.db import IntegrityError
from django.db.models import Q
from django.conf import settings

from .serializers import (
    RegisterSiswaSerializer,
    AdminBuatGuruSerializer,
    AdminBuatGuruBKSerializer,
    LoginSerializer,
    PenggunaSerializer,
    EditProfilSerializer,
    UbahPasswordSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
)
from .models import Pengguna
from .decorators import role_required
from log_aktivitas.utils import catat_log


from django.core.management import call_command

class SeedDatabaseView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        if not settings.DEBUG:
            return Response(
                {"error": "Endpoint ini hanya tersedia di mode development."},
                status=404
            )
        try:
            call_command('flush', interactive=False)
            call_command('seed_users')
            bk = Pengguna.objects.filter(role='guru_bk').first()
            return Response({
                "message": "Database berhasil direset dan diseed.",
                "bk_username": bk.username if bk else None,
                "bk_nuptk": bk.nuptk if bk else None
            })
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class RegisterSiswaView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSiswaSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            ip = request.META.get('REMOTE_ADDR')
            catat_log(
                user=user,
                aksi='BUAT_AKUN',
                deskripsi=f'Akun Siswa dibuat untuk {user.nama_lengkap} (NIS: {user.nis}).',
                modul='akun',
                ip_address=ip
            )
            return Response({"message": "Akun siswa berhasil dibuat."}, status=201)
        return Response(serializer.errors, status=400)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            
            access_token = data.pop('access')
            refresh_token = data.pop('refresh')
            
            response = Response(data)
            
            response.set_cookie(
                key=getattr(settings, 'AUTH_COOKIE', 'access_token'),
                value=access_token,
                expires=settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'],
                secure=getattr(settings, 'AUTH_COOKIE_SECURE', False),
                httponly=getattr(settings, 'AUTH_COOKIE_HTTP_ONLY', True),
                samesite=getattr(settings, 'AUTH_COOKIE_SAMESITE', 'Lax'),
            )
            
            response.set_cookie(
                key=getattr(settings, 'AUTH_COOKIE_REFRESH', 'refresh_token'),
                value=refresh_token,
                expires=settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'],
                secure=getattr(settings, 'AUTH_COOKIE_SECURE', False),
                httponly=getattr(settings, 'AUTH_COOKIE_HTTP_ONLY', True),
                samesite=getattr(settings, 'AUTH_COOKIE_SAMESITE', 'Lax'),
            )
            
            return response
        return Response(serializer.errors, status=400)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            cookie_name = getattr(settings, 'AUTH_COOKIE_REFRESH', 'refresh_token')
            refresh_token = request.COOKIES.get(cookie_name)
            
            if not refresh_token:
                return Response({"detail": "Refresh token diperlukan."}, status=400)

            token = RefreshToken(refresh_token)
            token.blacklist()

            response = Response({"message": "Logout berhasil."})
            
            response.delete_cookie(getattr(settings, 'AUTH_COOKIE', 'access_token'))
            response.delete_cookie(getattr(settings, 'AUTH_COOKIE_REFRESH', 'refresh_token'))
            
            return response
        except Exception:
            return Response({"detail": "Token tidak valid atau sudah kedaluwarsa."}, status=400)


class CookieTokenRefreshView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        cookie_name = getattr(settings, 'AUTH_COOKIE_REFRESH', 'refresh_token')
        refresh_token = request.COOKIES.get(cookie_name)
        
        if not refresh_token:
            return Response({"detail": "Refresh token tidak ditemukan di cookie."}, status=401)
            
        try:
            token = RefreshToken(refresh_token)
            
            access_token = str(token.access_token)
            
            if getattr(settings.SIMPLE_JWT, 'ROTATE_REFRESH_TOKENS', False):
                user_id = token.get('user_id')
                from django.contrib.auth import get_user_model
                User = get_user_model()
                user = User.objects.get(id=user_id)
                new_token_set = RefreshToken.for_user(user)
                access_token = str(new_token_set.access_token)
                new_refresh_token = str(new_token_set)
                
                if getattr(settings.SIMPLE_JWT, 'BLACKLIST_AFTER_ROTATION', False):
                    try:
                        token.blacklist()
                    except:
                        pass
            else:
                new_refresh_token = refresh_token
                
            response = Response({"message": "Token berhasil diperbarui."})
            
            response.set_cookie(
                key=getattr(settings, 'AUTH_COOKIE', 'access_token'),
                value=access_token,
                expires=settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'],
                secure=getattr(settings, 'AUTH_COOKIE_SECURE', False),
                httponly=getattr(settings, 'AUTH_COOKIE_HTTP_ONLY', True),
                samesite=getattr(settings, 'AUTH_COOKIE_SAMESITE', 'Lax'),
            )
            
            if getattr(settings.SIMPLE_JWT, 'ROTATE_REFRESH_TOKENS', False):
                response.set_cookie(
                    key=getattr(settings, 'AUTH_COOKIE_REFRESH', 'refresh_token'),
                    value=new_refresh_token,
                    expires=settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'],
                    secure=getattr(settings, 'AUTH_COOKIE_SECURE', False),
                    httponly=getattr(settings, 'AUTH_COOKIE_HTTP_ONLY', True),
                    samesite=getattr(settings, 'AUTH_COOKIE_SAMESITE', 'Lax'),
                )
                
            return response
            
        except Exception as e:
            return Response({"detail": "Refresh token tidak valid atau kadaluarsa."}, status=401)


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
            old_kelas = request.user.kelas
            
            serializer.update(request.user, serializer.validated_data)
            
            new_kelas = request.user.kelas
            
            diff_msg = ""
            if old_kelas != new_kelas:
                diff_msg += f"kelas='{old_kelas or '-'}' → '{new_kelas or '-'}'. "
                
            catat_log(
                user=request.user,
                aksi='EDIT_PROFIL',
                deskripsi=f'Profil diedit. Perubahan: {diff_msg}'.strip(),
                modul='akun',
                ip_address=request.META.get('REMOTE_ADDR')
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
            return Response({"message": "Password berhasil diubah."})
        return Response(serializer.errors, status=400)


# ─── Forgot Password ──────────────────────────────────────────────────────────

class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if serializer.is_valid():
            masked_email = serializer.save()
            return Response({
                "message": f"Email reset password sudah dikirimkan ke {masked_email}",
                "masked_email": masked_email,
            })
        return Response(serializer.errors, status=400)


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            catat_log(
                user=user,
                aksi='RESET_PASSWORD',
                deskripsi=f'Password direset melalui email untuk {user.nama_lengkap} (NIS: {user.nis}).',
                modul='akun',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            return Response({"message": "Password berhasil diubah. Silakan login dengan password baru."})
        return Response(serializer.errors, status=400)


# ─── Admin Account Management ─────────────────────────────────────────────────

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
            try:
                user = serializer.save()
            except IntegrityError as e:
                error_msg = str(e).lower()
                if 'email' in error_msg:
                    return Response({"email": ["Email sudah terdaftar."]}, status=400)
                if 'username' in error_msg:
                    return Response({"username": ["Username sudah terdaftar."]}, status=400)
                if 'nuptk' in error_msg:
                    return Response({"nuptk": ["NUPTK sudah terdaftar."]}, status=400)
                return Response({"detail": "Gagal membuat akun karena konflik data di database."}, status=400)

            catat_log(
                user=request.user,
                aksi='BUAT_AKUN',
                deskripsi=f'Admin membuat akun {role_type}: {user.nama_lengkap} ({user.nuptk})',
                modul='akun',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            label = 'Guru BK' if role_type == 'guru_bk' else 'Guru'
            return Response({"message": f"Akun {label} berhasil dibuat."}, status=201)
        return Response(serializer.errors, status=400)


class AdminDaftarAkunView(APIView):
    permission_classes = [IsAuthenticated]

    @role_required('kemahasiswaan', 'guru_bk')
    def get(self, request):
        search = request.query_params.get('search', '').strip()
        role = request.query_params.get('role', '').strip()
        is_verified = request.query_params.get('is_verified', '').strip()

        base_qs = Pengguna.objects.only(
            'id', 'nama_lengkap', 'nis', 'nuptk', 'username', 'role', 'kelas', 
            'mata_pelajaran', 'is_verified', 'date_joined'
        ).all()
        if search:
            base_qs = base_qs.filter(
                Q(nama_lengkap__icontains=search) |
                Q(nis__icontains=search) |
                Q(nuptk__icontains=search) |
                Q(username__icontains=search)
            )

        # Apply role filter
        if role:
            base_qs = base_qs.filter(role=role)
        
        # Apply is_verified filter
        if is_verified:
            # handle 'true'/'false' strings
            base_qs = base_qs.filter(is_verified=(is_verified.lower() == 'true'))

        # If guru_bk, can only see students
        if request.user.role == 'guru_bk':
            base_qs = base_qs.filter(role='siswa')

        # Sorting
        ordering = request.query_params.get('ordering', '-date_joined')
        base_qs = base_qs.order_by(ordering)

        paginator = PageNumberPagination()
        # Allow dynamic page size if present, but default to 10, max 100
        page_size = int(request.query_params.get('page_size', 10))
        page_size = min(page_size, 100)  # Limit max to 100 per page
        paginator.page_size = page_size
        
        result_page = paginator.paginate_queryset(base_qs, request)
        serializer = PenggunaSerializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)


# ─── Admin: Verify Student ────────────────────────────────────────────────────

class AdminVerifikasiSiswaView(APIView):
    permission_classes = [IsAuthenticated]

    @role_required('kemahasiswaan')
    def post(self, request, user_id):
        try:
            siswa = Pengguna.objects.get(pk=user_id, role='siswa')
        except Pengguna.DoesNotExist:
            return Response({"detail": "Siswa tidak ditemukan."}, status=404)

        if siswa.is_verified:
            return Response({"detail": "Siswa ini sudah terverifikasi."}, status=400)

        siswa.is_verified = True
        siswa.save()

        catat_log(
            user=request.user,
            aksi='VERIFIKASI_AKUN',
            deskripsi=f'Admin memverifikasi akun siswa: {siswa.nama_lengkap} (NIS: {siswa.nis}, Kelas: {siswa.kelas or "-"}).',
            modul='akun',
            ip_address=request.META.get('REMOTE_ADDR')
        )

        return Response({
            "message": f"Akun siswa {siswa.nama_lengkap} berhasil diverifikasi.",
            "data": PenggunaSerializer(siswa).data,
        })