from django.contrib import admin
from django.urls import path, include
from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['GET'])
def api_status(request):
    return Response({
        'message': 'SIPORA Backend is running',
        'data': {
            'version': '1.0.0'
        }
    })

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api_status),
    path('api/akun/', include('akun.urls')),
    path('api/logs/', include('log_aktivitas.urls')),
    path('api/laporan-bullying/', include('laporan_bullying.urls')),
]