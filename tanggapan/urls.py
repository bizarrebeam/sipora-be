"""
URL routing for the tanggapan application.

Maps API endpoints for response management on damage and bullying reports.
"""

from django.urls import path
from .views import ListCreateTanggapanLaporanKerusakanView, ListCreateTanggapanLaporanBullyingView

urlpatterns = [
    path('laporan-kerusakan/<uuid:laporan_id>/tanggapan/', 
            ListCreateTanggapanLaporanKerusakanView.as_view(), 
            name='list-create-tanggapan-kerusakan'),
    path('laporan-bullying/<uuid:laporan_id>/tanggapan/', 
            ListCreateTanggapanLaporanBullyingView.as_view(), 
            name='list-create-tanggapan-bullying'),
]
