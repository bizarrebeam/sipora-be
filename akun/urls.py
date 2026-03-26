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
    CookieTokenRefreshView,
    SeedDatabaseView,
    ForgotPasswordView,
    ResetPasswordView,
    AdminVerifikasiSiswaView,
    AdminJumlahAkunView,
)

urlpatterns = [
    path('seed/', SeedDatabaseView.as_view()),
    path('register/', RegisterSiswaView.as_view()),
    path('login/', LoginView.as_view()),
    path('logout/', LogoutView.as_view()),
    path('me/', ProfilView.as_view()),
    path('me/edit/', EditProfilView.as_view()),
    path('me/password/', UbahPasswordView.as_view()),
    path('admin/buat/', AdminBuatAkunView.as_view()),
    path('admin/daftar/', AdminDaftarAkunView.as_view()),
    path('admin/verifikasi-siswa/<uuid:user_id>/', AdminVerifikasiSiswaView.as_view()),
    path('admin/jumlah/', AdminJumlahAkunView.as_view()),
    path('forgot-password/', ForgotPasswordView.as_view()),
    path('reset-password/', ResetPasswordView.as_view()),
    path('token/refresh/', CookieTokenRefreshView.as_view()),
]