"""
URL routing for the tanggapan application.

Maps API endpoints for response management.
"""

from django.urls import path
from .views import ListCreateTanggapanLaporanKerusakanView

urlpatterns = [
    path('laporan-kerusakan/<uuid:laporan_id>/tanggapan/', 
            ListCreateTanggapanLaporanKerusakanView.as_view(), 
            name='list-create-tanggapan-kerusakan'),
]
