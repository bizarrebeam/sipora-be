from django.urls import path
from .views import (
    CreateLaporanKerusakanView,
    LaporanKerusakanListView,
    LaporanKerusakanDetailView
)

urlpatterns = [
    path('tambah/', CreateLaporanKerusakanView.as_view(), name='create-laporan'),
    path('list/', LaporanKerusakanListView.as_view(), name='list-laporan'),
    path('<uuid:id>/', LaporanKerusakanDetailView.as_view(), name='detail-laporan'),
]
