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
        
        # Cek jika tidak ada data sama sekali
        if not artikel_list.exists():
            return Response({
                "message": "Daftar artikel masih kosong",
                "data": []
            }, status=status.HTTP_200_OK)

        serializer = ArtikelSerializer(artikel_list, many=True)
        return Response({
            "message": "Berhasil mengambil daftar artikel",
            "data": serializer.data
        }, status=status.HTTP_200_OK)


class ArtikelListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    
    # PBI-50: List artikel Published
    def get(self, request):
        # Menggunakan 'published' (huruf kecil) agar sesuai dengan models.py
        artikel_list = Artikel.objects.filter(status='published').order_by('-created_at')

        if not artikel_list.exists():
            return Response({
                "message": "Belum ada artikel yang dipublikasikan",
                "data": []
            }, status=status.HTTP_200_OK)

        serializer = ArtikelSerializer(artikel_list, many=True)
        return Response({
            "message": "Berhasil mengambil daftar artikel",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    # PBI-47: Create artikel
    @role_required(['kemahasiswaan'])
    def post(self, request):

        serializer = ArtikelSerializer(data=request.data)

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

        if artikel.status == 'Draft' and request.user.role != 'kemahasiswaan':
            return Response({
                "message": "Artikel tidak ditemukan"
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = ArtikelSerializer(artikel)

        return Response({
            "message": "Berhasil mengambil detail artikel",
            "data": serializer.data
        }, status=status.HTTP_200_OK)


    # PBI-48: Update artikel
    @role_required(['kemahasiswaan'])
    def put(self, request, id):

        artikel = get_object_or_404(Artikel, pk=id)

        serializer = ArtikelSerializer(
            artikel,
            data=request.data,
            partial=True
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