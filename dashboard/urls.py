from django.urls import path
from .views import ( DashboardBullyingView, DashboardKerusakanAspirasiView)

urlpatterns = [
    path('dashboard-bullying/', DashboardBullyingView.as_view(), name='dashboard-bullying'),
    path('dashboard-kerusakan-aspirasi/', DashboardKerusakanAspirasiView.as_view(), name='dashboard-kerusakan-aspirasi'),
]
