from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import RegisterPelaporView, LoginView, LogoutView, ProfilView

urlpatterns = [
    path('register/', RegisterPelaporView.as_view()),
    path('login/', LoginView.as_view()),
    path('logout/', LogoutView.as_view()),
    path('me/', ProfilView.as_view()),
    path('token/refresh/', TokenRefreshView.as_view()),
]