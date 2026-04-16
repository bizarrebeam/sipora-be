from django.urls import path
from .views import ( dashboardBullyingView, dashboardKerusakanAspirasiView)

urlpatterns = [
    path('dashboard-bullying/', dashboardBullyingView.as_view(), name='dashboard-bullying'),
    path('dashboard-kerusakan-aspirasi/', dashboardKerusakanAspirasiView.as_view(), name='dashboard-kerusakan-aspirasi'),
]
