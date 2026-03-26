"""
Serializers for the Account (Akun) Application.

This module provides data validation, serialization, and deserialization for the 
custom user model across various authentication and administrative workflows.
"""

from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Pengguna, get_tahun_ajaran, get_semester
from django.contrib.auth import authenticate
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
import threading
import re


# ─── Public Registration ────────────────────────────────────────────────────────

class RegisterSiswaSerializer(serializers.ModelSerializer):
    """
    Handles the public registration of Siswa (Student) accounts.
    Validates NIS uniqueness, presence of required demographic fields, and password strength.
    """
    password = serializers.CharField(
        write_only=True, min_length=8,
        error_messages={'min_length': 'Password harus minimal 8 karakter.', 'blank': 'Password wajib diisi.', 'required': 'Password wajib diisi.'}
    )
    konfirmasi_password = serializers.CharField(
        write_only=True,
        error_messages={'blank': 'Konfirmasi password wajib diisi.', 'required': 'Konfirmasi password wajib diisi.'}
    )

    class Meta:
        model = Pengguna
        fields = ('nis', 'nama_lengkap', 'email', 'kelas', 'password', 'konfirmasi_password')

    def validate_nis(self, value):
        if not value.isdigit() or len(value) != 4:
            raise serializers.ValidationError("NIS harus terdiri dari 4 digit angka.")
        if Pengguna.objects.filter(nis=value).exists():
            raise serializers.ValidationError("NIS sudah terdaftar.")
        return value

    def validate_nama_lengkap(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Nama lengkap wajib diisi.")
        return value.strip()

    def validate_email(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Email wajib diisi.")
        if Pengguna.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email sudah terdaftar.")
        return value.strip().lower()

    def validate_password(self, value):
        if not re.search(r'[a-zA-Z]', value) or not re.search(r'[0-9]', value):
            raise serializers.ValidationError("Password harus mengandung kombinasi huruf dan angka.")
        return value

    def validate(self, data):
        if data['password'] != data['konfirmasi_password']:
            raise serializers.ValidationError("Password dan konfirmasi password tidak cocok.")
        return data

    def create(self, validated_data):
        validated_data.pop('konfirmasi_password')
        return Pengguna.objects.create_user(
            username=validated_data['nis'],
            nis=validated_data['nis'],
            nama_lengkap=validated_data['nama_lengkap'],
            email=validated_data['email'],
            kelas=validated_data['kelas'],
            password=validated_data['password'],
            role='siswa'
        )


# ─── Administrative Account Creation ────────────────────────────────────────────

class AdminBuatGuruSerializer(serializers.ModelSerializer):
    """
    Serializer for administrators creating Teacher (Guru) accounts.
    Validates NUPTK formatting, uniqueness, and assigns the 'guru' role explicitly.
    """
    password = serializers.CharField(
        write_only=True, min_length=8,
        error_messages={'min_length': 'Password harus minimal 8 karakter.', 'blank': 'Password wajib diisi.', 'required': 'Password wajib diisi.'}
    )

    class Meta:
        model = Pengguna
        fields = ('nuptk', 'email', 'nama_lengkap', 'mata_pelajaran', 'password')

    def validate_nuptk(self, value):
        if not value.isdigit() or len(value) != 16:
            raise serializers.ValidationError("NUPTK harus terdiri dari 16 digit angka.")
        if Pengguna.objects.filter(nuptk=value).exists():
            raise serializers.ValidationError("NUPTK sudah terdaftar.")
        return value

    def validate_nama_lengkap(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Nama lengkap wajib diisi.")
        return value.strip()

    def validate_email(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Email wajib diisi.")
        if Pengguna.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email sudah terdaftar.")
        return value.strip().lower()

    def validate_mata_pelajaran(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Mata pelajaran wajib diisi.")
        return value.strip()

    def validate_password(self, value):
        if not re.search(r'[a-zA-Z]', value) or not re.search(r'[0-9]', value):
            raise serializers.ValidationError("Password harus mengandung kombinasi huruf dan angka.")
        return value

    def create(self, validated_data):
        return Pengguna.objects.create_user(
            username=validated_data['nuptk'],
            nuptk=validated_data['nuptk'],
            email=validated_data['email'],
            nama_lengkap=validated_data['nama_lengkap'],
            mata_pelajaran=validated_data['mata_pelajaran'],
            password=validated_data['password'],
            role='guru',
            is_verified=True,
        )


class AdminBuatGuruBKSerializer(serializers.ModelSerializer):
    """
    Serializer for administrators creating Guidance Counselor (Guru BK) accounts.
    Allows optional NUPTK and assigns the 'guru_bk' role explicitly.
    """
    password = serializers.CharField(
        write_only=True, min_length=8,
        error_messages={'min_length': 'Password harus minimal 8 karakter.', 'blank': 'Password wajib diisi.', 'required': 'Password wajib diisi.'}
    )

    class Meta:
        model = Pengguna
        fields = ('username', 'nuptk', 'email', 'nama_lengkap', 'password')
        extra_kwargs = {
            'username': {'required': True, 'error_messages': {'blank': 'Username wajib diisi.', 'required': 'Username wajib diisi.'}},
            'nuptk': {'required': False, 'allow_null': True, 'allow_blank': True},
            'email': {'required': True, 'error_messages': {'blank': 'Email wajib diisi.', 'required': 'Email wajib diisi.'}}
        }

    def validate_username(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Username wajib diisi.")
        return value.strip()

    def validate_nama_lengkap(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Nama lengkap wajib diisi.")
        return value.strip()

    def validate_nuptk(self, value):
        if not value:
            return None
        if not value.isdigit() or len(value) != 16:
            raise serializers.ValidationError("NUPTK harus terdiri dari 16 digit angka.")
        if Pengguna.objects.filter(nuptk=value).exists():
            raise serializers.ValidationError("NUPTK sudah terdaftar.")
        return value

    def validate_email(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Email wajib diisi.")
        if Pengguna.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email sudah terdaftar.")
        return value.strip().lower()

    def validate_password(self, value):
        if not re.search(r'[a-zA-Z]', value) or not re.search(r'[0-9]', value):
            raise serializers.ValidationError("Password harus mengandung kombinasi huruf dan angka.")
        return value

    def create(self, validated_data):
        return Pengguna.objects.create_user(
            username=validated_data['username'],
            nuptk=validated_data.get('nuptk'),
            email=validated_data['email'],
            nama_lengkap=validated_data['nama_lengkap'],
            mata_pelajaran='Bimbingan Konseling',
            password=validated_data['password'],
            role='guru_bk',
            is_verified=True,
        )


# ─── Authentication Workflows ───────────────────────────────────────────────────

class LoginSerializer(serializers.Serializer):
    """
    Handles user authentication. Accepts username, NIS, or NUPTK as an identifier.
    Returns access and refresh JWT tokens alongside authenticated user metadata.
    """
    identifier = serializers.CharField(
        error_messages={'blank': 'Identifier wajib diisi.', 'required': 'Identifier wajib diisi.'}
    )
    password = serializers.CharField(
        write_only=True,
        error_messages={'blank': 'Password wajib diisi.', 'required': 'Password wajib diisi.'}
    )

    def validate(self, data):
        identifier = data.get('identifier', '').strip()
        password = data.get('password')

        if not identifier:
            raise serializers.ValidationError("Identifier wajib diisi.")

        # Optimize lookup: resolve identity prior to authentication
        user = None
        if identifier.isdigit() and len(identifier) == 4:
            user = Pengguna.objects.filter(nis=identifier).first()
        elif identifier.isdigit() and len(identifier) == 16:
            user = Pengguna.objects.filter(nuptk=identifier).first()
        else:
            user = Pengguna.objects.filter(username=identifier).first()

        if user and user.is_active and user.check_password(password):
            refresh = RefreshToken.for_user(user)
            return {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'username': user.username,
                'role': user.role,
                'nama_lengkap': user.nama_lengkap,
                'nis': user.nis,
                'nuptk': user.nuptk,
                'kelas': user.kelas,
                'mata_pelajaran': user.mata_pelajaran,
                'is_verified': user.is_verified,
            }
        raise serializers.ValidationError("Kredensial tidak valid.")


# ─── Profile Management ─────────────────────────────────────────────────────────

class PenggunaSerializer(serializers.ModelSerializer):
    """
    Comprehensive user serializer used for transmitting authorized profile details.
    Includes dynamically computed academic year and semester fields.
    """
    tahun_ajaran = serializers.SerializerMethodField()
    semester = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Cache at serializer instance level (same for all objects)
        self._tahun_ajaran_cache = get_tahun_ajaran()
        self._semester_cache = get_semester()

    class Meta:
        model = Pengguna
        fields = (
            'id', 'username', 'nis', 'nuptk', 'nama_lengkap', 'email',
            'role', 'kelas', 'mata_pelajaran', 'is_active', 'is_verified',
            'date_joined', 'tahun_ajaran', 'semester'
        )

    def get_tahun_ajaran(self, obj):
        return self._tahun_ajaran_cache

    def get_semester(self, obj):
        return self._semester_cache


class PenggunaListSerializer(serializers.ModelSerializer):
    """Lean serializer for admin list view — no computed fields."""
    class Meta:
        model = Pengguna
        fields = (
            'id', 'username', 'nis', 'nuptk', 'nama_lengkap',
            'role', 'kelas', 'mata_pelajaran', 'is_verified', 'date_joined'
        )


class EditProfilSerializer(serializers.Serializer):
    """
    Validates profile update payloads based on the user's current role.
    Siswa must provide 'kelas', while Guru must provide 'mata_pelajaran'.
    """
    kelas = serializers.ChoiceField(
        choices=Pengguna.KELAS_CHOICES, required=False, allow_null=True
    )
    mata_pelajaran = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate(self, data):
        user = self.context['request'].user
        if user.role == 'siswa' and 'kelas' not in data:
            raise serializers.ValidationError("Kelas wajib diisi untuk siswa.")
        if user.role == 'guru' and 'mata_pelajaran' not in data:
            raise serializers.ValidationError("Mata pelajaran wajib diisi untuk guru.")
        return data

    def update(self, instance, validated_data):
        if instance.role == 'siswa' and 'kelas' in validated_data:
            instance.kelas = validated_data['kelas']
        if instance.role == 'guru' and 'mata_pelajaran' in validated_data:
            instance.mata_pelajaran = validated_data['mata_pelajaran']
        instance.save()
        return instance


class UbahPasswordSerializer(serializers.Serializer):
    """
    Validates authenticated password change requests.
    Enforces previous password verification and alphanumeric strength requirements.
    """
    password_lama = serializers.CharField(
        write_only=True,
        error_messages={'blank': 'Password lama wajib diisi.', 'required': 'Password lama wajib diisi.'}
    )
    password_baru = serializers.CharField(
        write_only=True, min_length=8,
        error_messages={'min_length': 'Password baru harus minimal 8 karakter.', 'blank': 'Password baru wajib diisi.', 'required': 'Password baru wajib diisi.'}
    )

    def validate_password_lama(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Password lama yang dimasukkan salah.")
        return value

    def validate_password_baru(self, value):
        if not re.search(r'[a-zA-Z]', value) or not re.search(r'[0-9]', value):
            raise serializers.ValidationError("Password baru harus mengandung kombinasi huruf dan angka.")
        return value

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['password_baru'])
        user.save()
        return user


# ─── Password Recovery Workflows ────────────────────────────────────────────────

def mask_email(email):
    """
    Constructs an obfuscated version of the user's email for privacy-safe UI display.
    Example: j***n@example.com
    """
    if not email:
        return ''
    local, domain = email.split('@')
    if len(local) <= 2:
        masked_local = local[0] + '***'
    else:
        masked_local = local[0] + '*' * (len(local) - 2) + local[-1]
    return f'{masked_local}@{domain}'


class ForgotPasswordSerializer(serializers.Serializer):
    """
    Validates NIS lookup during password recovery requests.
    Triggers an asynchronous SMTP email dispatch containing a time-sensitive reset token.
    """
    nis = serializers.CharField()

    def validate_nis(self, value):
        if not value.isdigit() or len(value) != 4:
            raise serializers.ValidationError("NIS harus terdiri dari 4 digit angka.")
        try:
            user = Pengguna.objects.get(nis=value, role='siswa')
        except Pengguna.DoesNotExist:
            raise serializers.ValidationError("NIS tidak ditemukan.")
        if not user.email:
            raise serializers.ValidationError("Akun ini belum memiliki email terdaftar.")
        self.user = user
        return value

    def save(self):
        user = self.user
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        frontend_url = settings.FRONTEND_URL.rstrip('/')
        reset_link = f"{frontend_url}/reset-password/{uid}/{token}"

        def send_email_thread():
            try:
                send_mail(
                    subject='[SIPORA] Reset Password Akunmu',
                    message=(
                        f'Halo {user.nama_lengkap},\n\n'
                        f'Kamu meminta reset password untuk akun SIPORA-mu.\n'
                        f'Klik link berikut untuk membuat password baru (berlaku 1 jam):\n\n'
                        f'{reset_link}\n\n'
                        f'Jika kamu tidak meminta reset password, abaikan email ini.\n\n'
                        f'Salam,\nTim SIPORA SMP Desa Putera'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
            except Exception as e:
                import traceback
                print(f"SMTP Background Task Error: {str(e)}")
                traceback.print_exc()

        threading.Thread(target=send_email_thread).start()

        return mask_email(user.email)


class ResetPasswordSerializer(serializers.Serializer):
    """
    Validates password reset token execution.
    Consumes the UID and Token payloads sent via email to forcibly overwrite the forgotten password.
    """
    uid = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(
        write_only=True, min_length=8,
        error_messages={'min_length': 'Password harus minimal 8 karakter.', 'blank': 'Password wajib diisi.', 'required': 'Password wajib diisi.'}
    )
    konfirmasi_password = serializers.CharField(
        write_only=True,
        error_messages={'blank': 'Konfirmasi password wajib diisi.', 'required': 'Konfirmasi password wajib diisi.'}
    )

    def validate_password(self, value):
        if not re.search(r'[a-zA-Z]', value) or not re.search(r'[0-9]', value):
            raise serializers.ValidationError("Password harus mengandung kombinasi huruf dan angka.")
        return value

    def validate(self, data):
        if data['password'] != data['konfirmasi_password']:
            raise serializers.ValidationError("Password dan konfirmasi password tidak cocok.")

        try:
            uid = force_str(urlsafe_base64_decode(data['uid']))
            user = Pengguna.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, Pengguna.DoesNotExist):
            raise serializers.ValidationError("Link reset password tidak valid.")

        if not default_token_generator.check_token(user, data['token']):
            raise serializers.ValidationError("Link reset password sudah kadaluarsa atau sudah digunakan.")

        self.user = user
        return data

    def save(self):
        self.user.set_password(self.validated_data['password'])
        self.user.save()
        return self.user