from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

@api_view(['GET'])
@permission_classes([AllowAny])
def api_status(request):
    return Response({
        'message': 'SIPORA Backend is running',
        'data': {
            'version': '1.0.0'
        }
    })

urlpatterns = [
    path('api/', api_status),
    path('api/akun/', include('akun.urls')),
    path('api/logs/', include('log_aktivitas.urls')),
    path('api/laporan-kerusakan/', include('laporan_kerusakan.urls')),
]

# Only enable Django Admin in development
if settings.DEBUG:
    urlpatterns.insert(0, path('admin/', admin.site.urls))

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
