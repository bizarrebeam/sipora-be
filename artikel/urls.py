
from django.urls import path
from .views import ArtikelListCreateView, ArtikelDetailUpdateView, ArtikelKelolaView

# URL patterns for the artikel app API endpoints.
# - ''           : List published articles (GET), create article (POST)
# - 'kelola/'    : List all articles for admin (GET)
# - '<uuid:id>/' : Retrieve or update a specific article
urlpatterns = [
    path('', ArtikelListCreateView.as_view()),  # List & Create
    path('kelola/', ArtikelKelolaView.as_view()),  # Admin management
    path('<uuid:id>/', ArtikelDetailUpdateView.as_view()),  # Detail & Update
]