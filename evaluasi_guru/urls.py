from django.urls import path
from .views import EvaluasiCreateView, IndikatorListView, GuruListView, DaftarHasilEvaluasiView

urlpatterns = [
    path('indikator/', IndikatorListView.as_view(), name='indikator-list'),
    path('guru/', GuruListView.as_view(), name='guru-list'),
    path('rekap/', DaftarHasilEvaluasiView.as_view(), name='evaluasi-rekap'),
    path('', EvaluasiCreateView.as_view(), name='evaluasi-create'),
]
