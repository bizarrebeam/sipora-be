"""
URL Configuration for the Account (Akun) Application.

This module maps account-related API endpoints to their respective views, handling 
authentication, profile management, and role-based administration routes.
"""

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
    AdminUpdateGuruView,
    AdminDaftarAkunView,
    CookieTokenRefreshView,
    SeedDatabaseView,
    ForgotPasswordView,
    ForgotPasswordGuruView,
    ResetPasswordView,
    AdminVerifikasiSiswaView,
    AdminJumlahAkunView,
    AdminResetPasswordBKView,
)

urlpatterns = [
    # General Authentication & Base Endpoints
    path('seed/', SeedDatabaseView.as_view(), name='database-seed'),
    path('register/', RegisterSiswaView.as_view(), name='register-siswa'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    
    # Profile Management
    path('me/', ProfilView.as_view(), name='profil'),
    path('me/edit/', EditProfilView.as_view(), name='profil-edit'),
    path('me/password/', UbahPasswordView.as_view(), name='ubah-password'),
    
    # Role-Based Administrative Endpoints
    path('admin/buat/', AdminBuatAkunView.as_view(), name='admin-buat-akun'),
    path('admin/update-guru/<uuid:user_id>/', AdminUpdateGuruView.as_view(), name='admin-update-guru'),
    path('admin/daftar/', AdminDaftarAkunView.as_view(), name='admin-daftar-akun'),
    path('admin/verifikasi-siswa/<uuid:user_id>/', AdminVerifikasiSiswaView.as_view(), name='admin-verifikasi-siswa'),
    path('admin/jumlah/', AdminJumlahAkunView.as_view(), name='admin-jumlah-akun'),
    path('admin/reset-password-bk/<uuid:user_id>/', AdminResetPasswordBKView.as_view(), name='admin-reset-password-bk'),
    
    # Password Reset Workflows
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('forgot-password-guru/', ForgotPasswordGuruView.as_view(), name='forgot-password-guru'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('token/refresh/', CookieTokenRefreshView.as_view(), name='token-refresh'),
]