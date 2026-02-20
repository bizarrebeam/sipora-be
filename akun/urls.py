from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterSiswaView,
    LoginView,
    LogoutView,
    ProfilView,
    EditProfilView,
    UbahPasswordView,
    AdminBuatAkunView,
    AdminDaftarAkunView,
)

urlpatterns = [
    path('register/', RegisterSiswaView.as_view()),
    path('login/', LoginView.as_view()),
    path('logout/', LogoutView.as_view()),
    path('me/', ProfilView.as_view()),
    path('me/edit/', EditProfilView.as_view()),
    path('me/password/', UbahPasswordView.as_view()),
    path('admin/buat/', AdminBuatAkunView.as_view()),
    path('admin/daftar/', AdminDaftarAkunView.as_view()),
    path('token/refresh/', TokenRefreshView.as_view()),
]