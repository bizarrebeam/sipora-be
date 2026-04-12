from django.urls import path
from .views import EvaluasiCreateView, IndikatorListView, GuruListView

urlpatterns = [
    path('indikator/', IndikatorListView.as_view(), name='indikator-list'),
    path('guru/', GuruListView.as_view(), name='guru-list'),
    path('', EvaluasiCreateView.as_view(), name='evaluasi-create'),
]
