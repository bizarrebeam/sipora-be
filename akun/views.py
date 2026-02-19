from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import RegisterPelaporSerializer, LoginSerializer, PenggunaSerializer
from .models import Pengguna

class RegisterPelaporView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterPelaporSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Akun pelapor berhasil dibuat."})
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
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response({"detail": "Refresh token diperlukan."}, status=400)
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"message": "Logout berhasil."})
        except Exception:
            return Response({"detail": "Token tidak valid atau sudah kedaluwarsa."}, status=400)

class ProfilView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = PenggunaSerializer(request.user)
        return Response(serializer.data)