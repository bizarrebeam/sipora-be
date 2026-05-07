from django.urls import path
from .views import EvaluasiCreateView, IndikatorListView, GuruListView, DaftarHasilEvaluasiView, TahunAjaranListView

urlpatterns = [
    path('indikator/', IndikatorListView.as_view(), name='indikator-list'),
    path('guru/', GuruListView.as_view(), name='guru-list'),
    path('rekap/', DaftarHasilEvaluasiView.as_view(), name='evaluasi-rekap'),
    path('tahun-ajaran/', TahunAjaranListView.as_view(), name='tahun-ajaran-list'),
    path('', EvaluasiCreateView.as_view(), name='evaluasi-create'),
]
