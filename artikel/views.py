from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404

from .models import Artikel
from .serializers import ArtikelSerializer
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
    permission_classes = [IsAuthenticated]
    
    # PBI-50: List artikel Published
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

    # PBI-47: Create artikel
    @role_required(['kemahasiswaan'])
    def post(self, request):
        # TAMBAHKAN CONTEXT REQUEST SAAT INISIALISASI
        serializer = ArtikelSerializer(data=request.data, context={'request': request})

        if serializer.is_valid():
            artikel = serializer.save()

            catat_log(
                user=request.user,
                aksi="Membuat Artikel",
                deskripsi=f"Membuat artikel {artikel.judul}",
                modul="Artikel"
            )

            return Response({
                "message": "Artikel berhasil dibuat",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)

        return Response({
            "message": "Validasi gagal",
            "data": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class ArtikelDetailUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    # PBI-50: Detail artikel
    def get(self, request, id):
        artikel = get_object_or_404(Artikel, pk=id)

        # PERBAIKAN: Gunakan 'published' atau 'draft' (lowercase sesuai model)
        if artikel.status == 'draft' and request.user.role != 'kemahasiswaan':
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

        # TAMBAHKAN CONTEXT REQUEST
        serializer = ArtikelSerializer(
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

            return Response({
                "message": "Artikel berhasil diperbarui",
                "data": serializer.data
            }, status=status.HTTP_200_OK)

        return Response({
            "message": "Validasi gagal",
            "data": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)