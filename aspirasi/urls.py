from django.urls import path
from .views import (
    CreateAspirasiView,
    AspirasiListView,
    AspirasiDetailView, 
)

urlpatterns = [
    path('tambah/', CreateAspirasiView.as_view(), name='create-aspirasi'),
    path('list/', AspirasiListView.as_view(), name='list-aspirasi'),
    path('<uuid:id>/', AspirasiDetailView.as_view(), name='detail-aspirasi'),
]
