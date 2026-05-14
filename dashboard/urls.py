from django.urls import path
from .views import ( DashboardBullyingView, DashboardKerusakanAspirasiView, DashboardKonsultasiView)

urlpatterns = [
    path('dashboard-bullying/', DashboardBullyingView.as_view(), name='dashboard-bullying'),
    path('dashboard-kerusakan-aspirasi/', DashboardKerusakanAspirasiView.as_view(), name='dashboard-kerusakan-aspirasi'),
    path('dashboard-konsultasi/', DashboardKonsultasiView.as_view(), name='dashboard-konsultasi'),
]
