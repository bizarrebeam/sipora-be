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
    """PBI-52: Daftar artikel Draft & Published untuk Kemahasiswaan"""
    permission_classes = [IsAuthenticated]

    @role_required(['kemahasiswaan'])
    def get(self, request):
        artikel_list = Artikel.objects.all().order_by('-created_at')
        
        if not artikel_list.exists():
            return Response({
                "message": "Daftar artikel masih kosong",
                "data": []
            }, status=status.HTTP_200_OK)

        # TAMBAHKAN CONTEXT REQUEST
        serializer = ArtikelSerializer(artikel_list, many=True, context={'request': request})
        return Response({
            "message": "Berhasil mengambil daftar artikel",
            "data": serializer.data
        }, status=status.HTTP_200_OK)


class ArtikelListCreateView(APIView):
    
    # Override untuk allow unauthenticated GET (public articles) tapi restrict POST (create) ke authenticated admin
    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]
    
    # PBI-50: List artikel Published - dapat diakses publik
    def get(self, request):
        artikel_list = Artikel.objects.filter(status='published').order_by('-created_at')

        if not artikel_list.exists():
            return Response({
                "message": "Belum ada artikel yang dipublikasikan",
                "data": []
            }, status=status.HTTP_200_OK)

        # TAMBAHKAN CONTEXT REQUEST
        serializer = ArtikelSerializer(artikel_list, many=True, context={'request': request})
        return Response({
            "message": "Berhasil mengambil daftar artikel",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    # PBI-47: Create artikel - restricted to authenticated kemahasiswaan
    @role_required(['kemahasiswaan'])
    def post(self, request):
        # Use CreateArtikelSerializer for handling foto_artikel
        serializer = CreateArtikelSerializer(data=request.data, context={'request': request})


        if serializer.is_valid():
            artikel = serializer.save()
            
            # Return data with ArtikelSerializer to include foto_urls
            response_serializer = ArtikelSerializer(artikel, context={'request': request})

            catat_log(
                user=request.user,
                aksi="Membuat Artikel",
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

    # PBI-50: Detail artikel - dapat diakses oleh semua orang
    def get_permissions(self):
        """Override untuk memungkinkan unauthenticated access ke GET, tapi restrict PUT/DELETE"""
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    # PBI-50: Detail artikel
    def get(self, request, id):
        artikel = get_object_or_404(Artikel, pk=id)

        # PERBAIKAN: Gunakan 'published' atau 'draft' (lowercase sesuai model)
        # Hanya admin (kemahasiswaan) yang bisa melihat draft. Publik hanya bisa lihat published
        if artikel.status == 'draft':
            # Check apakah user authenticated dan memiliki role kemahasiswaan
            if not request.user.is_authenticated or request.user.role != 'kemahasiswaan':
                return Response({
                    "message": "Artikel tidak ditemukan"
                }, status=status.HTTP_404_NOT_FOUND)

        # TAMBAHKAN CONTEXT REQUEST
        serializer = ArtikelSerializer(artikel, context={'request': request})

        return Response({
            "message": "Berhasil mengambil detail artikel",
            "data": serializer.data
        }, status=status.HTTP_200_OK)


    # PBI-48: Update artikel
    @role_required(['kemahasiswaan'])
    def put(self, request, id):
        artikel = get_object_or_404(Artikel, pk=id)

        # Gunakan CreateArtikelSerializer yang sudah support update foto
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
                aksi="Mengedit Artikel",
                deskripsi=f"Mengedit artikel {artikel.judul}",
                modul="Artikel"
            )

            # Response pakai ArtikelSerializer untuk include gambar URL
            response_serializer = ArtikelSerializer(artikel, context={'request': request})
            return Response({
                "message": "Artikel berhasil diperbarui",
                "data": response_serializer.data
            }, status=status.HTTP_200_OK)

        return Response({
            "message": "Validasi gagal",
            "data": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)