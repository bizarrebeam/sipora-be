from django.urls import path
from .views import DaftarLogView

urlpatterns = [
    path('', DaftarLogView.as_view()),
]