from django.urls import path
from .views import (
    CreateLaporanKerusakanView,
    LaporanKerusakanListView,
    LaporanKerusakanDetailView, 
    EditLaporanKerusakanView, 
    CancelLaporanKerusakanView,
)

urlpatterns = [
    path('tambah/', CreateLaporanKerusakanView.as_view(), name='create-laporan'),
    path('list/', LaporanKerusakanListView.as_view(), name='list-laporan'),
    path('<uuid:id>/', LaporanKerusakanDetailView.as_view(), name='detail-laporan'),
    path('<uuid:id>/edit/', EditLaporanKerusakanView.as_view(), name='edit-laporan'),
    path('<uuid:id>/cancel/', CancelLaporanKerusakanView.as_view(), name='cancel-laporan'),
]
