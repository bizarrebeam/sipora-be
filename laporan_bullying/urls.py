from django.urls import path
from .views import *

urlpatterns = [
    path('', ListLaporanBullyingView.as_view()),
    path('create/', BuatLaporanBullyingView.as_view()),
    path('<uuid:id>/', DetailLaporanBullyingView.as_view()),
    path('<uuid:id>/edit/', EditLaporanBullyingView.as_view()),
    path('<uuid:id>/cancel/', CancelLaporanBullyingView.as_view()),
]