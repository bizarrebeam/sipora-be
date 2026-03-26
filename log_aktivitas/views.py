"""
API Views for Activity Logging.

This module provides robust REST controllers equipped with advanced filtering,
search, and pagination for querying the immutable systemic audit trails.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from .models import LogAktivitas
from .serializers import LogAktivitasSerializer
from akun.decorators import role_required
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated

class DaftarLogView(APIView):
    """
    Provides administrative read access to the global `LogAktivitas` records.
    Restricts access strictly to 'Kemahasiswaan' personnel. Supports dynamic slicing 
    via pagination, timeline extraction, and multi-vector search.
    """
    permission_classes = [IsAuthenticated]

    @role_required('kemahasiswaan')
    def get(self, request):
        search = request.query_params.get('search', '').strip()
        tanggal = request.query_params.get('tanggal', '').strip()
        modul = request.query_params.get('modul', '').strip()

        queryset = LogAktivitas.objects.select_related('pengguna').only(
            'id', 'aksi', 'deskripsi', 'waktu', 'modul',
            'pengguna__id', 'pengguna__nama_lengkap', 'pengguna__role',
            'pengguna__nis', 'pengguna__nuptk'
        ).all()

        if modul and modul != 'semua':
            queryset = queryset.filter(modul__iexact=modul)

        if search:
            queryset = queryset.filter(
                Q(pengguna__nama_lengkap__icontains=search) |
                Q(pengguna__nis__icontains=search) |
                Q(pengguna__nuptk__icontains=search) |
                Q(aksi__icontains=search) |
                Q(modul__icontains=search)
            )

        if tanggal:
            queryset = queryset.filter(waktu__date=tanggal)

        paginator = PageNumberPagination()
        page_size = int(request.query_params.get('page_size', 10))
        page_size = min(page_size, 100)  # Limit max to 100 per page
        paginator.page_size = page_size
        result_page = paginator.paginate_queryset(queryset, request)
        serializer = LogAktivitasSerializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)