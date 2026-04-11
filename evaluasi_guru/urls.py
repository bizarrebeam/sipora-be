from django.urls import path
from .views import EvaluasiCreateView

urlpatterns = [
    path('', EvaluasiCreateView.as_view(), name='evaluasi-create'),
]
