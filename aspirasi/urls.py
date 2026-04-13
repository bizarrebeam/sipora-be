from django.urls import path
from .views import (
    CreateAspirasiView,
    AspirasiListView,
    AspirasiDetailView, 
    EditAspirasiView,
)

urlpatterns = [
    path('tambah/', CreateAspirasiView.as_view(), name='create-aspirasi'),
    path('list/', AspirasiListView.as_view(), name='list-aspirasi'),
    path('<uuid:id>/', AspirasiDetailView.as_view(), name='detail-aspirasi'),
    path('<uuid:id>/edit/', EditAspirasiView.as_view(), name='edit-aspirasi'),
]
