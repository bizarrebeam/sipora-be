from django.urls import path
from .views import ArtikelListCreateView, ArtikelDetailUpdateView, ArtikelKelolaView

urlpatterns = [
    path('', ArtikelListCreateView.as_view()), # List & Create
    path('kelola/', ArtikelKelolaView.as_view()), # PBI-52
    path('<uuid:id>/', ArtikelDetailUpdateView.as_view()), # Detail & Update
]