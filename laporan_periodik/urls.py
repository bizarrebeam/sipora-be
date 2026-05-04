"""
URL routing configuration for the laporan_periodik application.

Maps API endpoints to their corresponding view handlers.
"""

from django.urls import path
from . import views

app_name = 'laporan_periodik'

urlpatterns = [
    path('periodik/', views.LaporanPeriodikView.as_view(), name='laporan-periodik-retrieve'),
    path('export/', views.laporan_periodik_export, name='laporan-periodik-export'),
]
