from rest_framework.views import APIView
from rest_framework.response import Response
from .models import LogAktivitas
from .serializers import LogAktivitasSerializer
from akun.decorators import role_required
from rest_framework.pagination import PageNumberPagination

class DaftarLogView(APIView):
    @role_required('kemahasiswaan')
    def get(self, request):
        paginator = PageNumberPagination()
        paginator.page_size = 20
        queryset = LogAktivitas.objects.all()
        result_page = paginator.paginate_queryset(queryset, request)
        serializer = LogAktivitasSerializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)