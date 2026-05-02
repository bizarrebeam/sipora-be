from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from django.shortcuts import get_object_or_404

from .models import Artikel
from .serializers import ArtikelSerializer, CreateArtikelSerializer
from akun.decorators import role_required
from log_aktivitas.utils import catat_log


class ArtikelKelolaView(APIView):
    """
    API endpoint for admin to list all articles (draft and published).
    Only accessible by authenticated users with the 'kemahasiswaan' role.
    """
    permission_classes = [IsAuthenticated]

    @role_required(['kemahasiswaan'])
    def get(self, request):
        """
        Return a list of all articles (draft and published) for admin management.
        """
        artikel_list = Artikel.objects.all().prefetch_related('foto_artikel').order_by('-created_at')
        serializer = ArtikelSerializer(artikel_list, many=True, context={'request': request})
        return Response({
            "message": "Berhasil mengambil daftar artikel",
            "data": serializer.data
        }, status=status.HTTP_200_OK)



class ArtikelListCreateView(APIView):
    """
    API endpoint for listing published articles (public) and creating new articles (admin only).
    GET: List published articles (accessible to everyone).
    POST: Create a new article (restricted to 'kemahasiswaan' role).
    """
    def get_permissions(self):
        """
        Allow unauthenticated GET requests, restrict POST to authenticated users.
        """
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get(self, request):
        """
        Return a list of published articles for public view.
        """
        artikel_list = Artikel.objects.filter(status='published').prefetch_related('foto_artikel').order_by('-created_at')
        serializer = ArtikelSerializer(artikel_list, many=True, context={'request': request})
        return Response({
            "message": "Berhasil mengambil daftar artikel",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    @role_required(['kemahasiswaan'])
    def post(self, request):
        """
        Create a new article. Only accessible by users with the 'kemahasiswaan' role.
        """
        serializer = CreateArtikelSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            artikel = serializer.save()
            response_serializer = ArtikelSerializer(artikel, context={'request': request})
            catat_log(
                user=request.user,
                aksi="MEMBUAT_ARTIKEL",
                deskripsi=f"Membuat artikel {artikel.judul}",
                modul="Artikel"
            )
            return Response({
                "message": "Artikel berhasil dibuat",
                "data": response_serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )



class ArtikelDetailUpdateView(APIView):
    """
    API endpoint for retrieving and updating a specific article.
    GET: Retrieve article details (public for published, restricted for draft).
    PUT: Update article (restricted to 'kemahasiswaan' role).
    """
    def get_permissions(self):
        """
        Allow unauthenticated GET requests, restrict PUT/DELETE to authenticated users.
        """
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get(self, request, id):
        """
        Retrieve article details. Drafts are only visible to 'kemahasiswaan' role.
        """
        artikel = get_object_or_404(Artikel, pk=id)
        if artikel.status == 'draft':
            if not request.user.is_authenticated or request.user.role != 'kemahasiswaan':
                return Response({
                    "message": "Artikel tidak ditemukan"
                }, status=status.HTTP_404_NOT_FOUND)
        serializer = ArtikelSerializer(artikel, context={'request': request})
        return Response({
            "message": "Berhasil mengambil detail artikel",
            "data": serializer.data
        }, status=status.HTTP_200_OK)


    @role_required(['kemahasiswaan'])
    def put(self, request, id):
        """
        Update an article. Only accessible by users with the 'kemahasiswaan' role.
        """
        artikel = get_object_or_404(Artikel, pk=id)
        serializer = CreateArtikelSerializer(
            artikel,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        if serializer.is_valid():
            artikel = serializer.save()
            catat_log(
                user=request.user,
                aksi="MENGEDIT_ARTIKEL",
                deskripsi=f"Mengedit artikel {artikel.judul}",
                modul="Artikel"
            )
            response_serializer = ArtikelSerializer(artikel, context={'request': request})
            return Response({
                "message": "Artikel berhasil diperbarui",
                "data": response_serializer.data
            }, status=status.HTTP_200_OK)
        return Response({
            "message": "Validasi gagal",
            "data": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    @role_required(['kemahasiswaan'])
    def delete(self, request, id):
        """
        Delete an article (hard delete). Only accessible by users with the 'kemahasiswaan' role.
        """
        artikel = get_object_or_404(Artikel, pk=id)
        judul = artikel.judul
        artikel.delete()
        catat_log(
            user=request.user,
            aksi="MENGHAPUS_ARTIKEL",
            deskripsi=f"Menghapus artikel {judul}",
            modul="Artikel"
        )
        return Response({
            "message": "Artikel berhasil dihapus"
        }, status=status.HTTP_200_OK)