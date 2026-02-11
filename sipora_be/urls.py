from django.contrib import admin
from django.urls import path
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
]