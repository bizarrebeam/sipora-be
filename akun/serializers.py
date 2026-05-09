"""
Serializers for the Account (Akun) Application.

This module provides data validation, serialization, and deserialization for the 
custom user model across various authentication and administrative workflows.
"""

from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Pengguna, MataPelajaranGuruSemester, get_tahun_ajaran, get_semester
from django.contrib.auth import authenticate
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
import threading
import re

import logging

logger = logging.getLogger(__name__)



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
    riwayat_mengajar = serializers.ListField(
        child=serializers.DictField(), required=False
    )

    class Meta:
        model = Pengguna
        fields = ('nuptk', 'email', 'nama_lengkap', 'mata_pelajaran', 'password', 'riwayat_mengajar')
        extra_kwargs = {
            'mata_pelajaran': {'required': False, 'allow_null': True, 'allow_blank': True}
        }

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

    def validate_riwayat_mengajar(self, value):
        if not value:
            raise serializers.ValidationError("Riwayat mengajar tidak boleh kosong.")
        
        cleaned_data = []
        for item in value:
            nama = item.get('nama_mata_pelajaran', '').strip()
            kelas = item.get('kelas_diajar', [])
            
            if not nama:
                raise serializers.ValidationError("Nama mata pelajaran tidak boleh kosong atau hanya berisi spasi.")
            if not kelas or not isinstance(kelas, list) or len(kelas) == 0:
                raise serializers.ValidationError(f"Mata pelajaran '{nama}' harus memiliki minimal satu kelas yang diajar.")
            
            cleaned_data.append({
                'nama_mata_pelajaran': nama,
                'kelas_diajar': kelas
            })
        return cleaned_data

    def create(self, validated_data):
        riwayat_data = validated_data.pop('riwayat_mengajar', [])
        
        # Consistent string fallback for old field
        mata_pelajaran_str = ", ".join([r['nama_mata_pelajaran'] for r in riwayat_data])
        
        user = Pengguna.objects.create_user(
            username=validated_data['nuptk'],
            nuptk=validated_data['nuptk'],
            email=validated_data['email'],
            nama_lengkap=validated_data['nama_lengkap'],
            mata_pelajaran=mata_pelajaran_str,
            password=validated_data['password'],
            role='guru',
            is_verified=True,
        )
        
        ta = get_tahun_ajaran()
        sem = get_semester()
        
        for item in riwayat_data:
            MataPelajaranGuruSemester.objects.create(
                guru=user,
                nama_mata_pelajaran=item.get("nama_mata_pelajaran"),
                kelas_diajar=item.get("kelas_diajar", []),
                tahun_ajaran=ta,
                semester=sem
            )
            
        return user


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


class AdminUpdateGuruSerializer(serializers.ModelSerializer):
    """
    Serializer for administrators updating Teacher (Guru) accounts.
    Allows updating name, email, and teaching history.
    Implements OCC via `updated_at` token — rejects update if the record has been
    modified since the client last fetched it, returning a 409-compatible message.
    """
    riwayat_mengajar = serializers.ListField(
        child=serializers.DictField(), required=False
    )
    # OCC version token — client must send the updated_at they received from GET
    updated_at = serializers.DateTimeField(write_only=True, required=False)

    class Meta:
        model = Pengguna
        fields = ('nama_lengkap', 'email', 'riwayat_mengajar', 'updated_at')

    def validate_nama_lengkap(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Nama lengkap wajib diisi.")
        return value.strip()

    def validate_email(self, value):
        instance = self.instance
        if not value or not value.strip():
            raise serializers.ValidationError("Email wajib diisi.")
        if Pengguna.objects.filter(email=value).exclude(pk=instance.pk).exists():
            raise serializers.ValidationError("Email sudah digunakan oleh akun lain.")
        return value.strip().lower()

    def validate_riwayat_mengajar(self, value):
        if value is None:
            return None
        if not value:
            raise serializers.ValidationError("Riwayat mengajar tidak boleh kosong.")
        
        cleaned_data = []
        for item in value:
            nama = item.get('nama_mata_pelajaran', '').strip()
            kelas = item.get('kelas_diajar', [])
            
            if not nama:
                raise serializers.ValidationError("Nama mata pelajaran tidak boleh kosong atau hanya berisi spasi.")
            if not kelas or not isinstance(kelas, list) or len(kelas) == 0:
                raise serializers.ValidationError(f"Mata pelajaran '{nama}' harus memiliki minimal satu kelas yang diajar.")
            
            cleaned_data.append({
                'nama_mata_pelajaran': nama,
                'kelas_diajar': kelas
            })
        return cleaned_data

    def validate(self, data):
        """
        OCC check: if client sent an updated_at token, verify it matches the current
        database value. A mismatch means another user has edited the record since the
        client last fetched it — reject with a 409-style validation error.
        """
        client_updated_at = data.pop('updated_at', None)
        if client_updated_at and self.instance:
            # Normalize both to UTC-aware for comparison
            from django.utils import timezone
            instance_ts = self.instance.updated_at
            if timezone.is_naive(instance_ts):
                instance_ts = timezone.make_aware(instance_ts)
            if timezone.is_naive(client_updated_at):
                client_updated_at = timezone.make_aware(client_updated_at)
            # Truncate to seconds for tolerance
            if abs((instance_ts - client_updated_at).total_seconds()) > 1:
                raise serializers.ValidationError(
                    "CONFLICT: Data ini sudah diubah oleh pengguna lain sejak kamu membuka form ini. "
                    "Silakan muat ulang halaman untuk melihat data terbaru sebelum menyimpan perubahan."
                )
        return data

    
    def update(self, instance, validated_data):
        riwayat_data = validated_data.pop('riwayat_mengajar', None)
        
        instance.nama_lengkap = validated_data.get('nama_lengkap', instance.nama_lengkap).strip()
        instance.email = validated_data.get('email', instance.email).strip().lower()
        
        if riwayat_data is not None:
            # Consistent string fallback for old field
            mata_pelajaran_str = ", ".join([r['nama_mata_pelajaran'] for r in riwayat_data])
            instance.mata_pelajaran = mata_pelajaran_str

            ta = get_tahun_ajaran()
            sem = get_semester()
            
            # Wipe current semester mapping and replace
            MataPelajaranGuruSemester.objects.filter(
                guru=instance, tahun_ajaran=ta, semester=sem
            ).delete()
            
            for item in riwayat_data:
                MataPelajaranGuruSemester.objects.create(
                    guru=instance,
                    nama_mata_pelajaran=item.get("nama_mata_pelajaran"),
                    kelas_diajar=item.get("kelas_diajar", []),
                    tahun_ajaran=ta,
                    semester=sem
                )
        
        instance.save()
        return instance


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
                'id': str(user.id),
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

class MataPelajaranGuruSemesterSerializer(serializers.ModelSerializer):
    class Meta:
        model = MataPelajaranGuruSemester
        fields = ('id', 'nama_mata_pelajaran', 'kelas_diajar', 'tahun_ajaran', 'semester')
        read_only_fields = ('id',)

class PenggunaSerializer(serializers.ModelSerializer):
    """
    Comprehensive user serializer used for transmitting authorized profile details.
    Includes dynamically computed academic year and semester fields.
    Exposes `updated_at` as an OCC version token for frontend concurrency control.
    """
    tahun_ajaran = serializers.SerializerMethodField()
    semester = serializers.SerializerMethodField()
    riwayat_mengajar = MataPelajaranGuruSemesterSerializer(many=True, read_only=True)

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
            'date_joined', 'updated_at', 'tahun_ajaran', 'semester', 'riwayat_mengajar'
        )

    def get_tahun_ajaran(self, obj):
        return self._tahun_ajaran_cache

    def get_semester(self, obj):
        return self._semester_cache


class PenggunaListSerializer(serializers.ModelSerializer):
    """Lean serializer for admin list view — no computed fields. Exposes `updated_at` for OCC tokens."""
    riwayat_mengajar = MataPelajaranGuruSemesterSerializer(many=True, read_only=True)

    class Meta:
        model = Pengguna
        fields = (
            'id', 'username', 'nis', 'nuptk', 'nama_lengkap', 'email',
            'role', 'kelas', 'mata_pelajaran', 'is_verified', 'date_joined', 'updated_at', 'riwayat_mengajar'
        )


class EditProfilSerializer(serializers.Serializer):
    """
    Validates profile update payloads based on the user's current role.
    Siswa must provide 'kelas', while Guru must provide 'mata_pelajaran'.
    """
    kelas = serializers.ChoiceField(
        choices=Pengguna.KELAS_CHOICES, required=False, allow_null=True
    )
    riwayat_mengajar = serializers.ListField(
        child=serializers.DictField(), required=False
    )

    def validate(self, data):
        user = self.context['request'].user
        if user.role == 'siswa' and 'kelas' not in data:
            raise serializers.ValidationError("Kelas wajib diisi untuk siswa.")
        
        if user.role == 'guru':
            if 'riwayat_mengajar' not in data:
                raise serializers.ValidationError("Riwayat mengajar pelajar wajib diisi untuk guru.")
            
            riwayat = data.get('riwayat_mengajar', [])
            if not riwayat:
                raise serializers.ValidationError("Riwayat mengajar tidak boleh kosong.")
            
            cleaned_riwayat = []
            for item in riwayat:
                nama = item.get('nama_mata_pelajaran', '').strip()
                kelas = item.get('kelas_diajar', [])
                
                if not nama:
                    raise serializers.ValidationError("Nama mata pelajaran tidak boleh kosong.")
                if not kelas or len(kelas) == 0:
                    raise serializers.ValidationError(f"Mata pelajaran '{nama}' harus memiliki minimal 1 kelas.")
                
                cleaned_riwayat.append({
                    'nama_mata_pelajaran': nama,
                    'kelas_diajar': kelas
                })
            data['riwayat_mengajar'] = cleaned_riwayat

        return data

    def update(self, instance, validated_data):
        if instance.role == 'siswa' and 'kelas' in validated_data:
            instance.kelas = validated_data['kelas']
        
        if instance.role == 'guru' and 'riwayat_mengajar' in validated_data:
            riwayat_data = validated_data['riwayat_mengajar']
            # Simplified map names string for old field sync
            instance.mata_pelajaran = ", ".join([r['nama_mata_pelajaran'] for r in riwayat_data])

            ta = get_tahun_ajaran()
            sem = get_semester()
            
            # Wipe existing map for current semester to replace them cleanly
            MataPelajaranGuruSemester.objects.filter(
                guru=instance, tahun_ajaran=ta, semester=sem
            ).delete()
            
            for item in riwayat_data:
                MataPelajaranGuruSemester.objects.create(
                    guru=instance,
                    nama_mata_pelajaran=item.get("nama_mata_pelajaran"),
                    kelas_diajar=item.get("kelas_diajar", []),
                    tahun_ajaran=ta,
                    semester=sem
                )

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

        # Plaintext fallback for email clients that don't support HTML.
        plain_message = (
            f'Halo {user.nama_lengkap},\n\n'
            f'Kamu meminta reset password untuk akun SIPORA-mu.\n'
            f'Klik link berikut untuk membuat password baru (berlaku 1 jam):\n\n'
            f'{reset_link}\n\n'
            f'Jika kamu tidak meminta reset password, abaikan email ini.\n\n'
            f'Salam,\nTim SIPORA SMP Desa Putera'
        )

        # Branded HTML email template with inline CSS for maximum client compatibility.
        html_message = f'''<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {{ font-family: 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #F9FAFB; margin: 0; padding: 0; }}
  </style>
</head>
<body style="margin:0;padding:0;background-color:#F9FAFB;font-family:'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#F3F4F6;padding:40px 16px;">
    <tr><td align="center">
      
      <!-- Card Container matching SDialog -->
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:572px;background:#ffffff;border-radius:16px;border:1px solid #D9D9D9;box-shadow:0px 0px 10px 0px rgba(159, 160, 206, 0.50);overflow:hidden;">
        
        <!-- Header (Background from button var(--color-blue-500) and text white) -->
        <tr><td style="background-color:#2E3094;padding:24px 48px;text-align:center;border-bottom:1px solid #D9D9D9;">
          <h2 style="margin:0;font-size:24px;font-weight:800;color:#ffffff;line-height:32px;text-align:center;">Reset Password</h2>
        </td></tr>
        
        <!-- Body -->
        <tr><td style="padding:32px;text-align:center;">
          <!-- SVG Logo inside body -->
          <div style="margin-bottom: 24px;text-align:center;">
            <svg style="margin: 0 auto; display: block;" width="180" viewBox="0 0 665 288" fill="none" xmlns="http://www.w3.org/2000/svg">
<g filter="url(#filter0_g_18_133)">
<path d="M248.387 257.294L259.197 157.807C260.698 158.153 262.214 158.445 263.741 158.683C273.045 160.132 282.545 159.521 291.564 156.892C300.583 154.262 308.899 149.68 315.917 143.472C322.934 137.265 328.481 129.585 332.161 120.981L273.329 95.8176L239.36 55.8766C229.714 55.1851 216.179 65.5406 213.048 74.3592C210.753 80.8211 209.533 87.5993 209.416 94.4291L192.38 251.208L248.387 257.294Z" fill="#7374B7"/>
<mask id="path-2-inside-1_18_133" fill="white">
<path d="M222.866 31.1687C220.36 40.9834 242.165 60.8202 242.171 60.8254L269.148 41.0593C269.124 41.0107 256.139 14.0532 245.087 14.1779C234.026 14.3027 225.372 21.3529 222.866 31.1687ZM249.001 55.6767C249.001 55.6767 236.401 43.1228 237.038 37.8029C237.675 32.4832 241.674 29.122 247.381 29.7935C253.088 30.4651 261.615 46.4344 261.615 46.4344L249.001 55.6767Z"/>
</mask>
<path d="M222.866 31.1687C220.36 40.9834 242.165 60.8202 242.171 60.8254L269.148 41.0593C269.124 41.0107 256.139 14.0532 245.087 14.1779C234.026 14.3027 225.372 21.3529 222.866 31.1687ZM249.001 55.6767C249.001 55.6767 236.401 43.1228 237.038 37.8029C237.675 32.4832 241.674 29.122 247.381 29.7935C253.088 30.4651 261.615 46.4344 261.615 46.4344L249.001 55.6767Z" fill="#BEBFDE"/>

<path d="M222.866 31.1687L221.642 30.8563L221.642 30.8563L222.866 31.1687ZM242.171 60.8254L242.917 61.8441L242.084 62.4542L241.321 61.7596L242.171 60.8254ZM269.148 41.0593L270.286 40.5114L270.741 41.4575L269.894 42.0781L269.148 41.0593ZM245.087 14.1779L245.073 12.915L245.073 12.915L245.087 14.1779ZM249.001 55.6767L249.747 56.6954L248.875 57.3344L248.11 56.5713L249.001 55.6767ZM237.038 37.8029L235.784 37.6529L235.784 37.6528L237.038 37.8029ZM247.381 29.7935L247.529 28.5393L247.529 28.5393L247.381 29.7935ZM261.615 46.4344L262.729 45.8395L263.245 46.8057L262.361 47.4531L261.615 46.4344ZM222.866 31.1687L224.09 31.4811C223.585 33.4563 224.28 36.1715 225.944 39.3578C227.577 42.4843 230.004 45.8058 232.548 48.8686C237.63 54.9874 243.032 59.9014 243.02 59.8912L242.171 60.8254L241.321 61.7596C241.304 61.7442 235.8 56.7371 230.605 50.4825C228.01 47.3586 225.456 43.8804 223.705 40.527C221.985 37.2333 220.894 33.7884 221.642 30.8563L222.866 31.1687ZM242.171 60.8254L241.424 59.8066L268.401 40.0406L269.148 41.0593L269.894 42.0781L242.917 61.8441L242.171 60.8254ZM269.148 41.0593L268.01 41.6072C268.011 41.61 267.206 39.9372 265.826 37.4299C264.445 34.9208 262.497 31.589 260.212 28.2695C257.922 24.9411 255.326 21.6713 252.658 19.2547C249.951 16.8028 247.373 15.4151 245.102 15.4407L245.087 14.1779L245.073 12.915C248.327 12.8783 251.517 14.8135 254.353 17.3826C257.229 19.9869 259.953 23.4362 262.293 26.8377C266.979 33.6479 270.265 40.4682 270.286 40.5114L269.148 41.0593ZM245.087 14.1779L245.102 15.4407C234.603 15.5592 226.452 22.2286 224.09 31.4811L222.866 31.1687L221.642 30.8563C224.292 20.4773 233.45 13.0462 245.073 12.915L245.087 14.1779ZM249.001 55.6767C248.11 56.5713 248.109 56.5712 248.109 56.571C248.109 56.5709 248.109 56.5706 248.109 56.5703C248.108 56.5698 248.107 56.5691 248.106 56.5682C248.105 56.5664 248.102 56.5638 248.099 56.5605C248.092 56.5539 248.082 56.5443 248.07 56.5318C248.045 56.5067 248.008 56.4699 247.961 56.422C247.867 56.3263 247.729 56.1862 247.555 56.0065C247.206 55.6472 246.71 55.1294 246.117 54.4919C244.933 53.2182 243.357 51.4597 241.798 49.5281C240.244 47.6027 238.68 45.4739 237.54 43.463C236.97 42.4572 236.489 41.4529 236.171 40.497C235.857 39.5531 235.674 38.5747 235.784 37.6529L237.038 37.8029L238.292 37.953C238.243 38.3611 238.314 38.9387 238.568 39.6997C238.817 40.4486 239.216 41.2978 239.737 42.2171C240.78 44.0562 242.247 46.0634 243.763 47.9415C245.274 49.8133 246.809 51.5257 247.967 52.7722C248.546 53.3947 249.029 53.8992 249.367 54.2473C249.536 54.4213 249.668 54.556 249.758 54.6468C249.803 54.6922 249.837 54.7265 249.86 54.7493C249.871 54.7607 249.879 54.7691 249.885 54.7746C249.888 54.7774 249.89 54.7794 249.891 54.7806C249.891 54.7812 249.892 54.7817 249.892 54.7819C249.892 54.782 249.892 54.7821 249.892 54.7821C249.892 54.7821 249.892 54.7821 249.001 55.6767ZM237.038 37.8029L235.784 37.6528C236.136 34.7099 237.435 32.2182 239.524 30.5618C241.616 28.9032 244.391 28.17 247.529 28.5393L247.381 29.7935L247.234 31.0478C244.665 30.7455 242.586 31.3571 241.093 32.5411C239.597 33.7274 238.577 35.5762 238.292 37.9531L237.038 37.8029ZM247.381 29.7935L247.529 28.5393C249.413 28.761 251.281 30.1696 252.903 31.7811C254.582 33.4489 256.232 35.5772 257.674 37.643C259.121 39.7158 260.383 41.7622 261.282 43.2874C261.732 44.051 262.092 44.6862 262.34 45.1316C262.465 45.3544 262.561 45.5299 262.627 45.6504C262.66 45.7106 262.685 45.7572 262.702 45.789C262.711 45.8049 262.717 45.8172 262.722 45.8256C262.724 45.8298 262.726 45.8331 262.727 45.8354C262.728 45.8366 262.728 45.8375 262.728 45.8382C262.729 45.8385 262.729 45.8389 262.729 45.839C262.729 45.8393 262.729 45.8395 261.615 46.4344C260.501 47.0292 260.501 47.0293 260.501 47.0293C260.501 47.0292 260.501 47.0292 260.501 47.029C260.501 47.0287 260.5 47.0282 260.5 47.0274C260.499 47.0259 260.498 47.0234 260.496 47.0199C260.492 47.013 260.487 47.0024 260.479 46.988C260.463 46.9594 260.44 46.9162 260.409 46.8593C260.347 46.7455 260.255 46.5773 260.135 46.3621C259.894 45.9316 259.544 45.314 259.106 44.5699C258.227 43.0799 257.001 41.092 255.603 39.0886C254.199 37.078 252.648 35.0881 251.123 33.5729C249.541 32.0013 248.203 31.1618 247.234 31.0478L247.381 29.7935ZM261.615 46.4344L262.361 47.4531L249.747 56.6954L249.001 55.6767L248.254 54.658L260.869 45.4156L261.615 46.4344Z" fill="#9FA0CE" mask="url(#path-2-inside-1_18_133)"/>
<rect width="21.0504" height="47.57" transform="matrix(0.993802 0.111162 0.111162 -0.993802 202.904 153.778)" fill="#5859A9"/>
<mask id="path-5-inside-2_18_133" fill="white">
<path d="M264.142 258.996L274.951 159.521C304.547 166.375 335.628 151.411 347.916 122.683C361.722 90.4045 346.574 52.9722 314.082 39.0747C281.59 25.1774 244.057 40.0776 230.251 72.356C226.906 80.1785 225.259 88.304 225.149 96.3236L208.135 252.91L264.142 258.996Z"/>
</mask>
<path d="M264.142 258.996L274.951 159.521C304.547 166.375 335.628 151.411 347.916 122.683C361.722 90.4045 346.574 52.9722 314.082 39.0747C281.59 25.1774 244.057 40.0776 230.251 72.356C226.906 80.1785 225.259 88.304 225.149 96.3236L208.135 252.91L264.142 258.996Z" fill="#BEBFDE"/>
<path d="M264.142 258.996L265.397 259.133L265.261 260.388L264.005 260.252L264.142 258.996ZM274.951 159.521L273.695 159.384L273.849 157.969L275.236 158.29L274.951 159.521ZM347.916 122.683L349.077 123.18V123.18L347.916 122.683ZM314.082 39.0747L314.579 37.9136L314.579 37.9136L314.082 39.0747ZM230.251 72.356L229.09 71.8593V71.8593L230.251 72.356ZM225.149 96.3236L226.412 96.3409L226.411 96.4006L226.405 96.46L225.149 96.3236ZM208.135 252.91L207.998 254.165L206.743 254.029L206.879 252.773L208.135 252.91ZM264.142 258.996L262.886 258.86L273.695 159.384L274.951 159.521L276.207 159.657L265.397 259.133L264.142 258.996ZM274.951 159.521L275.236 158.29C304.252 165.01 334.714 150.337 346.755 122.186L347.916 122.683L349.077 123.18C336.542 152.486 304.842 167.739 274.666 160.751L274.951 159.521ZM347.916 122.683L346.755 122.186C360.283 90.5564 345.443 53.8622 313.585 40.2359L314.082 39.0747L314.579 37.9136C347.705 52.0823 363.16 90.2527 349.077 123.18L347.916 122.683ZM314.082 39.0747L313.585 40.2359C281.727 26.6097 244.941 41.2228 231.413 72.8526L230.251 72.356L229.09 71.8593C243.174 38.9325 281.452 23.745 314.579 37.9136L314.082 39.0747ZM230.251 72.356L231.413 72.8526C228.133 80.5209 226.52 88.4832 226.412 96.3409L225.149 96.3236L223.887 96.3063C223.999 88.1247 225.678 79.8361 229.09 71.8593L230.251 72.356ZM225.149 96.3236L226.405 96.46L209.39 253.046L208.135 252.91L206.879 252.773L223.894 96.1872L225.149 96.3236ZM208.135 252.91L208.271 251.654L264.278 257.741L264.142 258.996L264.005 260.252L207.998 254.165L208.135 252.91Z" fill="#9FA0CE" mask="url(#path-5-inside-2_18_133)"/>
<circle cx="48.6224" cy="48.6224" r="44.4127" transform="matrix(0.91943 0.393254 0.393254 -0.91943 225.369 123.38)" stroke="#5859A9" stroke-width="8.41946"/>
</g>
<g filter="url(#filter1_d_18_133)">
<path d="M204.521 56.6094L187.863 213.436L187.751 214.479L186.707 214.371L159.444 211.533L158.169 211.4L158.546 210.177C161.901 199.292 159.389 189.849 155.326 181.998C153.291 178.066 150.872 174.546 148.612 171.452C146.379 168.396 144.236 165.673 142.872 163.471C142.727 163.237 142.581 163.044 142.427 162.853C142.288 162.679 142.092 162.447 141.932 162.229C141.558 161.717 141.264 161.129 141.154 160.224C141.051 159.375 141.114 158.275 141.359 156.727C141.606 155.167 142.048 153.085 142.744 150.247L142.889 149.656L143.474 149.486C152.438 146.897 157.89 138.586 159.974 129.503C161.012 124.98 161.194 120.331 160.574 116.23C159.951 112.115 158.535 108.642 156.46 106.375C155.042 104.824 154.742 102.862 155.154 100.8C155.559 98.7716 156.662 96.5605 158.17 94.2969C161.194 89.7593 166.055 84.7107 171.138 80.0264C176.234 75.3302 181.609 70.9502 185.705 67.7471C187.754 66.1447 189.485 64.8345 190.706 63.9248C191.316 63.4699 191.798 63.1146 192.128 62.873C192.293 62.7525 192.42 62.6601 192.506 62.5977C192.549 62.5664 192.583 62.5424 192.605 62.5264C192.616 62.5184 192.625 62.5129 192.63 62.5088C192.633 62.5069 192.635 62.505 192.636 62.5039L192.638 62.5029C192.639 62.5026 192.639 62.5021 193.253 63.3564L192.639 62.502L192.653 62.4922L192.667 62.4824L202.888 55.624L204.759 54.3691L204.521 56.6094Z" fill="#2E3094" stroke="#212269" stroke-width="2.10487"/>
<path d="M83.8134 86.7615C95.9101 86.7615 107.855 88.5002 119.644 91.9753H119.645C131.505 95.3204 136.48 100.003 147.885 106.431C151.231 108.318 152.748 112.218 153.067 116.517C153.39 120.854 152.525 125.862 150.824 130.394C149.127 134.916 146.55 139.088 143.344 141.663C140.089 144.277 136.126 145.271 131.942 143.202C116.866 135.746 120.651 137.143 114.229 134.455C107.819 131.772 101.564 129.613 95.4648 127.976L95.4579 127.975C89.5177 126.342 84.3661 125.538 79.9892 125.538C76.2151 125.538 73.2782 126.265 71.0976 127.628C69.0448 128.911 67.9931 130.874 67.9931 133.71C67.9932 136.81 69.2484 139.356 71.8466 141.416C74.7231 143.423 78.5761 145.176 83.4433 146.651C88.3785 148.147 93.7638 149.717 99.5986 151.363L100.704 151.652C106.226 153.121 111.746 154.988 117.263 157.25L118.37 157.685C123.873 159.906 128.913 162.731 133.488 166.162C138.572 169.712 142.647 174.412 145.714 180.239H145.713C148.814 185.98 150.334 193.06 150.334 201.427C150.334 213.017 147.279 222.71 141.105 230.428L141.106 230.429C135.125 237.945 127.086 243.599 117.033 247.407L117.024 247.41C107.144 251.058 96.2194 252.875 84.2636 252.875C75.182 252.875 66.0285 251.815 56.8056 249.698C47.5915 247.583 38.7526 244.637 30.29 240.859L30.2831 240.856C26.1989 239 23.8169 238.034 20.8486 236.284C17.8822 234.535 14.3313 232.006 7.80658 227.01C6.9835 226.38 6.36889 225.867 5.9726 225.464C5.78189 225.27 5.58794 225.047 5.45599 224.811C5.36814 224.654 5.05244 224.031 5.49213 223.429C5.69014 223.158 5.95261 223.038 6.12885 222.984C6.30552 222.93 6.47255 222.918 6.59662 222.917C6.84456 222.915 7.1123 222.957 7.36224 223.01C7.87495 223.118 8.5438 223.321 9.31537 223.584C12.3712 224.625 17.8471 226.88 23.7812 229.067C29.7854 231.28 36.3634 233.464 41.8759 234.473C44.636 234.979 47.0649 235.177 48.9911 234.966C50.9318 234.753 52.1814 234.148 52.8505 233.23C54.3993 231.106 54.4191 228.107 53.3954 224.568C52.3813 221.062 50.4164 217.291 48.3974 213.88C47.3918 212.18 46.3825 210.586 45.4824 209.17C44.5887 207.764 43.7886 206.512 43.2275 205.533C42.9475 205.044 42.7099 204.592 42.5458 204.205C42.4638 204.011 42.3905 203.811 42.3417 203.614C42.2963 203.43 42.2523 203.174 42.2929 202.898C42.3385 202.59 42.503 202.213 42.8935 201.976C43.237 201.768 43.593 201.771 43.8124 201.797C44.2327 201.847 44.6949 202.051 45.1386 202.286L46.4785 202.949C53.1717 206.221 59.7942 208.902 66.3456 210.994C73.4819 213.075 79.5992 214.098 84.7138 214.098C89.7021 214.098 93.4479 213.215 96.0634 211.567C98.5845 209.833 99.8593 207.33 99.8593 203.902C99.8593 200.82 98.5473 198.357 95.8085 196.44L95.7949 196.43L95.7812 196.42C92.9093 194.266 89.0567 192.437 84.1835 190.961L84.1747 190.958C79.3985 189.465 74.0189 187.971 68.0351 186.475L68.0283 186.473C62.1463 184.965 56.2659 183.155 50.3867 181.045L50.371 181.04L50.3554 181.034C44.5812 178.755 39.1845 175.866 34.1669 172.369C29.0827 168.825 25.0004 164.279 21.9247 158.743L21.9189 158.733L21.914 158.723C18.9626 153.131 17.5175 146.201 17.5175 137.984C17.5175 127.589 20.2737 118.519 25.8154 110.822C31.3431 102.994 39.0833 97.0311 48.9882 92.9167C58.8928 88.8025 70.5097 86.7615 83.8134 86.7615Z" fill="#2E3094" stroke="#212269" stroke-width="2.10487"/>
<path d="M35.8096 201.225L12.6329 218.696C12.6329 218.696 42.3115 234.061 47.1527 228.799C51.9939 223.537 35.8096 201.225 35.8096 201.225Z" fill="#212269"/>
<mask id="path-11-outside-3_18_133" maskUnits="userSpaceOnUse" x="403.602" y="59.0934" width="257" height="219" fill="black">
<rect fill="white" x="403.602" y="59.0934" width="257" height="219"/>
<path d="M607.166 112.233L657.015 275.373L607.293 270.66L600.511 244.707L537.16 238.704L525.319 262.892L477.389 258.349C521.038 200.353 579.473 150.287 559.236 107.691L607.166 112.233ZM481.194 62.0934C502.491 62.0935 518.915 66.9676 530.463 76.7164C542.012 86.4654 547.787 100.189 547.787 117.887C547.787 136.785 542.012 151.484 530.463 161.983C527.454 164.679 524.114 167.023 520.443 169.017L525.319 179.124L499.91 212.171L480.446 177.506H454.421V215.959C454.421 215.959 408.582 219.693 407.626 215.959C406.672 212.219 433.629 119.236 407.626 62.0934H481.194ZM553.23 205.877L591.308 209.485L577.442 156.421L553.23 205.877ZM475.096 72.8278C471.678 72.8278 468.908 75.5611 468.908 78.9323V110.085C468.908 107.668 468.717 88.9621 466.653 81.4586C465.837 78.4927 463.706 76.8981 461.601 76.8981C458.184 76.8983 456.531 79.6306 456.531 83.0016L456.128 117.591C456.128 114.22 456.317 101.314 450.342 101.314C446.925 101.314 444.154 104.047 444.154 107.419V115.557C444.154 132.413 458.008 146.078 475.096 146.078C492.184 146.077 506.037 132.413 506.038 115.557V95.2096C506.037 91.8385 504.119 88.1942 499.849 89.1061C495.579 90.0181 493.661 104.047 493.661 107.419V83.0016C493.661 79.6305 489.386 76.4065 486.018 78.9323C482.65 81.4582 481.284 104.819 481.284 108.19V78.9323C481.284 75.5612 478.514 72.828 475.096 72.8278Z"/>
</mask>
<path d="M607.166 112.233L657.015 275.373L607.293 270.66L600.511 244.707L537.16 238.704L525.319 262.892L477.389 258.349C521.038 200.353 579.473 150.287 559.236 107.691L607.166 112.233ZM481.194 62.0934C502.491 62.0935 518.915 66.9676 530.463 76.7164C542.012 86.4654 547.787 100.189 547.787 117.887C547.787 136.785 542.012 151.484 530.463 161.983C527.454 164.679 524.114 167.023 520.443 169.017L525.319 179.124L499.91 212.171L480.446 177.506H454.421V215.959C454.421 215.959 408.582 219.693 407.626 215.959C406.672 212.219 433.629 119.236 407.626 62.0934H481.194ZM553.23 205.877L591.308 209.485L577.442 156.421L553.23 205.877ZM475.096 72.8278C471.678 72.8278 468.908 75.5611 468.908 78.9323V110.085C468.908 107.668 468.717 88.9621 466.653 81.4586C465.837 78.4927 463.706 76.8981 461.601 76.8981C458.184 76.8983 456.531 79.6306 456.531 83.0016L456.128 117.591C456.128 114.22 456.317 101.314 450.342 101.314C446.925 101.314 444.154 104.047 444.154 107.419V115.557C444.154 132.413 458.008 146.078 475.096 146.078C492.184 146.077 506.037 132.413 506.038 115.557V95.2096C506.037 91.8385 504.119 88.1942 499.849 89.1061C495.579 90.0181 493.661 104.047 493.661 107.419V83.0016C493.661 79.6305 489.386 76.4065 486.018 78.9323C482.65 81.4582 481.284 104.819 481.284 108.19V78.9323C481.284 75.5612 478.514 72.828 475.096 72.8278Z" fill="#2E3094"/>
<path d="M607.165 112.233L609.178 111.618L608.767 110.27L607.364 110.138L607.165 112.233ZM657.015 275.373L656.816 277.468L659.947 277.765L659.028 274.758L657.015 275.373ZM607.293 270.66L605.257 271.192L605.629 272.616L607.095 272.755L607.293 270.66ZM600.511 244.707L602.548 244.174L602.175 242.75L600.71 242.611L600.511 244.707ZM537.16 238.704L537.358 236.608L535.909 236.471L535.269 237.778L537.16 238.704ZM525.319 262.892L525.12 264.988L526.569 265.125L527.209 263.818L525.319 262.892ZM477.389 258.349L475.707 257.084L473.445 260.09L477.191 260.445L477.389 258.349ZM559.236 107.691L559.434 105.596L555.744 105.246L557.335 108.594L559.236 107.691ZM481.194 62.0934L481.194 59.9885H481.194V62.0934ZM530.463 76.7164L531.821 75.108L531.821 75.108L530.463 76.7164ZM547.787 117.887H549.891V117.887L547.787 117.887ZM530.463 161.983L531.868 163.551L531.874 163.546L531.879 163.541L530.463 161.983ZM520.443 169.017L519.438 167.168L517.675 168.125L518.547 169.932L520.443 169.017ZM525.319 179.124L526.987 180.407L527.778 179.378L527.215 178.209L525.319 179.124ZM499.91 212.171L498.074 213.201L499.635 215.981L501.578 213.454L499.91 212.171ZM480.446 177.506L482.281 176.476L481.678 175.402H480.446V177.506ZM454.421 177.506V175.402H452.316V177.506H454.421ZM454.421 215.959L454.592 218.057L456.526 217.899V215.959H454.421ZM407.626 215.959L405.587 216.479L405.587 216.48L407.626 215.959ZM407.626 62.0934V59.9885H404.356L405.711 62.9652L407.626 62.0934ZM553.23 205.877L551.339 204.951L550.001 207.685L553.031 207.972L553.23 205.877ZM591.308 209.485L591.109 211.58L594.105 211.864L593.345 208.953L591.308 209.485ZM577.442 156.421L579.478 155.888L578.045 150.402L575.551 155.495L577.442 156.421ZM475.096 72.8278L475.096 70.7229H475.096V72.8278ZM468.908 78.9323L466.803 78.9322V78.9323H468.908ZM466.653 81.4586L468.682 80.9002L468.682 80.9002L466.653 81.4586ZM461.601 76.8981V74.7932H461.601L461.601 76.8981ZM456.531 83.0016L458.635 83.0261L458.636 83.0138V83.0016L456.531 83.0016ZM456.128 117.591L454.024 117.591L458.233 117.616L456.128 117.591ZM450.342 101.314V99.2092H450.342L450.342 101.314ZM444.154 115.557H442.049V115.557L444.154 115.557ZM475.096 146.078V148.183H475.096L475.096 146.078ZM506.038 115.557L508.142 115.557V115.557H506.038ZM506.038 95.2096H508.142V95.2095L506.038 95.2096ZM499.849 89.1061L499.41 87.0476L499.409 87.0476L499.849 89.1061ZM493.661 83.0016H495.765V83.0015L493.661 83.0016ZM486.018 78.9323L484.755 77.2482L484.755 77.2483L486.018 78.9323ZM481.284 78.9323H483.389V78.9322L481.284 78.9323ZM607.165 112.233L605.153 112.848L655.002 275.988L657.015 275.373L659.028 274.758L609.178 111.618L607.165 112.233ZM657.015 275.373L657.214 273.277L607.492 268.564L607.293 270.66L607.095 272.755L656.816 277.468L657.015 275.373ZM607.293 270.66L609.33 270.128L602.548 244.174L600.511 244.707L598.475 245.239L605.257 271.192L607.293 270.66ZM600.511 244.707L600.71 242.611L537.358 236.608L537.16 238.704L536.961 240.799L600.313 246.802L600.511 244.707ZM537.16 238.704L535.269 237.778L523.428 261.967L525.319 262.892L527.209 263.818L539.05 239.629L537.16 238.704ZM525.319 262.892L525.517 260.797L477.588 256.254L477.389 258.349L477.191 260.445L525.12 264.988L525.319 262.892ZM477.389 258.349L479.071 259.615C489.943 245.169 501.739 231.213 513.053 217.682C524.346 204.175 535.168 191.082 543.995 178.451C561.542 153.344 571.805 129.243 561.137 106.788L559.236 107.691L557.335 108.594C566.904 128.736 558.068 150.966 540.544 176.04C531.837 188.499 521.13 201.459 509.823 214.982C498.536 228.481 486.659 242.532 475.707 257.084L477.389 258.349ZM559.236 107.691L559.037 109.787L606.967 114.329L607.165 112.233L607.364 110.138L559.434 105.596L559.236 107.691ZM481.194 62.0934V64.1982C502.195 64.1983 518.066 69.006 529.106 78.3248L530.463 76.7164L531.821 75.108C519.763 64.9292 502.787 59.9886 481.194 59.9885L481.194 62.0934ZM530.463 76.7164L529.106 78.3248C540.098 87.6037 545.682 100.692 545.682 117.887L547.787 117.887L549.891 117.887C549.891 99.6869 543.927 85.327 531.821 75.108L530.463 76.7164ZM547.787 117.887H545.682C545.682 136.328 540.066 150.408 529.047 160.426L530.463 161.983L531.879 163.541C543.958 152.56 549.891 137.243 549.891 117.887H547.787ZM530.463 161.983L529.059 160.415C526.176 162.999 522.97 165.249 519.438 167.168L520.443 169.017L521.447 170.867C525.257 168.798 528.733 166.36 531.868 163.551L530.463 161.983ZM520.443 169.017L518.547 169.932L523.423 180.038L525.319 179.124L527.215 178.209L522.339 168.103L520.443 169.017ZM525.319 179.124L523.65 177.841L498.241 210.888L499.91 212.171L501.578 213.454L526.987 180.407L525.319 179.124ZM499.91 212.171L501.745 211.14L482.281 176.476L480.446 177.506L478.61 178.537L498.074 213.201L499.91 212.171ZM480.446 177.506V175.402H454.421V177.506V179.611H480.446V177.506ZM454.421 177.506H452.316V215.959H454.421H456.526V177.506H454.421ZM454.421 215.959C454.25 213.861 454.25 213.861 454.25 213.861C454.25 213.861 454.249 213.861 454.249 213.861C454.247 213.861 454.245 213.861 454.243 213.861C454.237 213.862 454.229 213.862 454.219 213.863C454.197 213.865 454.165 213.868 454.122 213.871C454.036 213.878 453.908 213.888 453.741 213.901C453.407 213.928 452.917 213.966 452.291 214.013C451.041 214.107 449.252 214.238 447.102 214.384C442.8 214.675 437.061 215.024 431.297 215.256C425.522 215.489 419.77 215.603 415.424 215.431C413.238 215.345 411.493 215.189 410.304 214.963C409.698 214.848 409.348 214.735 409.186 214.66C408.901 214.53 409.473 214.683 409.666 215.437L407.626 215.959L405.587 216.48C405.9 217.701 406.941 218.263 407.433 218.488C408.047 218.769 408.78 218.959 409.519 219.099C411.019 219.384 413.013 219.549 415.258 219.637C419.776 219.816 425.664 219.696 431.467 219.462C437.283 219.228 443.063 218.876 447.386 218.584C449.549 218.438 451.348 218.306 452.608 218.211C453.238 218.163 453.733 218.125 454.071 218.098C454.24 218.085 454.37 218.074 454.458 218.067C454.502 218.064 454.535 218.061 454.558 218.059C454.569 218.058 454.577 218.058 454.583 218.057C454.586 218.057 454.588 218.057 454.59 218.057C454.591 218.057 454.591 218.057 454.592 218.057C454.592 218.057 454.592 218.057 454.421 215.959ZM407.626 215.959L409.666 215.438C409.732 215.697 409.692 215.814 409.715 215.513C409.731 215.302 409.769 214.991 409.835 214.563C409.967 213.71 410.187 212.529 410.484 211.025C411.061 208.102 411.964 203.793 412.946 198.78C414.939 188.615 417.418 174.791 419.112 159.28C422.489 128.356 422.792 90.3381 409.542 61.2216L407.626 62.0934L405.711 62.9652C418.464 90.991 418.289 128.036 414.927 158.823C413.252 174.169 410.796 187.863 408.815 197.97C407.811 203.093 406.967 207.108 406.354 210.209C406.056 211.717 405.821 212.974 405.675 213.922C405.602 214.393 405.546 214.824 405.518 215.188C405.497 215.462 405.461 215.986 405.587 216.479L407.626 215.959ZM407.626 62.0934V64.1982H481.194V62.0934V59.9885H407.626V62.0934ZM553.23 205.877L553.031 207.972L591.109 211.58L591.308 209.485L591.507 207.39L553.429 203.781L553.23 205.877ZM591.308 209.485L593.345 208.953L579.478 155.888L577.442 156.421L575.405 156.953L589.272 210.017L591.308 209.485ZM577.442 156.421L575.551 155.495L551.339 204.951L553.23 205.877L555.12 206.802L579.332 157.346L577.442 156.421ZM475.096 72.8278V70.7229C470.543 70.7229 466.803 74.3716 466.803 78.9322L468.908 78.9323L471.013 78.9323C471.013 76.7505 472.814 74.9326 475.096 74.9326V72.8278ZM468.908 78.9323H466.803V110.085H468.908H471.013V78.9323H468.908ZM468.908 110.085H471.013C471.013 108.85 470.964 103.532 470.656 97.5708C470.352 91.6845 469.785 84.9068 468.682 80.9002L466.653 81.4586L464.623 82.017C465.585 85.5139 466.145 91.8411 466.452 97.788C466.756 103.66 466.803 108.903 466.803 110.085H468.908ZM466.653 81.4586L468.682 80.9002C467.671 77.2232 464.848 74.7932 461.601 74.7932V76.8981V79.0029C462.564 79.0029 464.003 79.7621 464.623 82.017L466.653 81.4586ZM461.601 76.8981L461.601 74.7932C459.26 74.7933 457.362 75.7642 456.109 77.4112C454.911 78.9856 454.426 81.0054 454.426 83.0016L456.531 83.0016L458.636 83.0016C458.636 81.6268 458.977 80.5948 459.459 79.9603C459.887 79.3984 460.525 79.003 461.601 79.0029L461.601 76.8981ZM456.531 83.0016L454.426 82.9771L454.024 117.567L456.128 117.591L458.233 117.616L458.635 83.0261L456.531 83.0016ZM456.128 117.591L458.233 117.591C458.233 115.95 458.287 111.672 457.543 107.792C457.174 105.865 456.573 103.834 455.531 102.234C454.447 100.57 452.753 99.2092 450.342 99.2092V101.314V103.419C450.919 103.419 451.442 103.671 452.003 104.532C452.607 105.458 453.079 106.864 453.409 108.585C454.064 112 454.024 115.861 454.024 117.591L456.128 117.591ZM450.342 101.314L450.342 99.2092C445.789 99.2094 442.049 102.858 442.049 107.419H444.154H446.259C446.259 105.237 448.06 103.419 450.342 103.419L450.342 101.314ZM444.154 107.419H442.049V115.557H444.154H446.259V107.419H444.154ZM444.154 115.557L442.049 115.557C442.049 133.603 456.873 148.183 475.096 148.183V146.078V143.973C459.143 143.973 446.259 131.224 446.259 115.557L444.154 115.557ZM475.096 146.078L475.096 148.183C493.32 148.182 508.142 133.603 508.142 115.557L506.038 115.557L503.933 115.557C503.933 131.223 491.049 143.973 475.096 143.973L475.096 146.078ZM506.038 115.557H508.142V95.2096H506.038H503.933V115.557H506.038ZM506.038 95.2096L508.142 95.2095C508.142 93.1864 507.577 90.9059 506.163 89.2058C504.639 87.3741 502.294 86.4315 499.41 87.0476L499.849 89.1061L500.289 91.1645C501.674 90.8688 502.423 91.2924 502.926 91.8976C503.539 92.6345 503.933 93.8617 503.933 95.2097L506.038 95.2096ZM499.849 89.1061L499.409 87.0476C497.342 87.4891 496.031 89.3382 495.214 90.9047C494.324 92.612 493.636 94.7378 493.112 96.8284C492.066 101.001 491.556 105.525 491.556 107.419H493.661H495.765C495.765 105.941 496.214 101.765 497.195 97.8519C497.685 95.8998 498.277 94.1365 498.947 92.8515C499.691 91.4256 500.221 91.179 500.289 91.1645L499.849 89.1061ZM493.661 107.419H495.765V83.0016H493.661H491.556V107.419H493.661ZM493.661 83.0016L495.765 83.0015C495.765 80.4569 494.2 78.1835 492.201 76.9603C490.116 75.6841 487.252 75.376 484.755 77.2482L486.018 78.9323L487.281 80.6163C488.152 79.9628 489.11 80.0038 490.004 80.5509C490.984 81.151 491.556 82.1752 491.556 83.0017L493.661 83.0016ZM486.018 78.9323L484.755 77.2483C483.844 77.9319 483.278 79.0461 482.897 79.9854C482.479 81.017 482.12 82.2692 481.807 83.6204C481.179 86.331 480.682 89.6831 480.297 93.0018C479.528 99.6324 479.179 106.4 479.179 108.19H481.284H483.389C483.389 106.609 483.722 100.011 484.479 93.4866C484.856 90.228 485.332 87.0556 485.908 84.5703C486.197 83.3235 486.497 82.3099 486.798 81.5673C487.137 80.7325 487.35 80.5641 487.281 80.6162L486.018 78.9323ZM481.284 108.19H483.389V78.9323H481.284H479.179V108.19H481.284ZM481.284 78.9323L483.389 78.9322C483.388 74.372 479.649 70.7232 475.096 70.7229L475.096 72.8278L475.096 74.9326C477.378 74.9328 479.179 76.7504 479.179 78.9323L481.284 78.9323Z" fill="#212269" mask="url(#path-11-outside-3_18_133)"/>
<path fill-rule="evenodd" clip-rule="evenodd" d="M355.328 132.607C361.222 126.713 390.396 137.175 396.905 143.856C403.543 150.536 408.76 158.612 407.084 167.337C405.408 176.062 404.165 185.86 399.718 201.857C395.271 217.854 399.511 227.957 410.663 227.957C407.001 237.185 402.898 244.402 396.167 251.18C389.565 257.957 381.752 263.301 372.728 267.212C363.833 270.985 354.05 272.911 343.381 272.989C332.712 273.068 322.891 271.287 313.918 267.645C305.075 263.865 297.334 258.634 290.696 251.954C284.187 245.273 279.1 237.346 275.436 228.172C271.9 218.997 272.817 175.757 286.709 170.915C300.601 166.074 314.915 166.284 328.386 157.023C341.857 147.761 349.435 138.5 355.328 132.607ZM345.506 165.621C344.626 165.382 344.139 165.382 343.26 165.621C342.426 165.848 341.36 166.678 339.229 168.339C334.785 171.802 329.924 174.197 323.595 175.524C317.852 176.727 314.981 177.329 313.516 178.37C312.027 179.429 311.303 180.326 310.577 182.01C309.863 183.667 309.863 186.001 309.863 190.669V207.188C309.863 228.525 332.965 244.045 341.371 248.986C342.326 249.547 342.804 249.827 343.478 249.973C344.001 250.086 344.764 250.086 345.287 249.973C345.961 249.827 346.439 249.547 347.395 248.986C355.8 244.045 378.902 228.525 378.902 207.188V190.669C378.902 186.001 378.903 183.667 378.189 182.01C377.463 180.326 376.739 179.429 375.25 178.37C373.785 177.328 370.914 176.727 365.171 175.524C358.841 174.197 353.98 171.802 349.536 168.339C347.405 166.678 346.34 165.848 345.506 165.621Z" fill="#2E3094"/>
<path d="M355.328 132.607L354.584 131.862V131.862L355.328 132.607ZM396.905 143.856L396.152 144.59L396.159 144.597L396.905 143.856ZM407.084 167.337L406.051 167.139V167.139L407.084 167.337ZM399.718 201.857L398.704 201.575V201.575L399.718 201.857ZM410.663 227.957L411.641 228.345C411.77 228.021 411.73 227.655 411.534 227.366C411.338 227.078 411.012 226.905 410.663 226.905V227.957ZM396.167 251.18L395.42 250.438L395.413 250.445L396.167 251.18ZM372.728 267.212L373.139 268.181L373.146 268.178L372.728 267.212ZM343.381 272.989L343.389 274.042H343.389L343.381 272.989ZM313.918 267.645L313.504 268.612C313.51 268.615 313.516 268.617 313.522 268.62L313.918 267.645ZM290.696 251.954L289.943 252.689L289.95 252.696L290.696 251.954ZM275.436 228.172L274.454 228.551L274.458 228.562L275.436 228.172ZM286.709 170.915L286.363 169.921L286.363 169.921L286.709 170.915ZM328.386 157.023L328.982 157.89L328.982 157.89L328.386 157.023ZM345.506 165.621L345.782 164.606L345.782 164.606L345.506 165.621ZM343.26 165.621L342.984 164.606L342.984 164.606L343.26 165.621ZM339.229 168.339L339.876 169.169L339.876 169.169L339.229 168.339ZM323.595 175.524L323.811 176.554L323.811 176.554L323.595 175.524ZM313.516 178.37L312.906 177.513L312.906 177.513L313.516 178.37ZM310.577 182.01L309.611 181.593L309.611 181.593L310.577 182.01ZM341.371 248.986L341.905 248.078V248.078L341.371 248.986ZM343.478 249.973L343.255 251.002L343.255 251.002L343.478 249.973ZM345.287 249.973L345.509 251.002L345.509 251.002L345.287 249.973ZM347.395 248.986L347.928 249.893V249.893L347.395 248.986ZM378.189 182.01L379.155 181.593L379.155 181.593L378.189 182.01ZM375.25 178.37L375.86 177.513L375.86 177.513L375.25 178.37ZM365.171 175.524L364.955 176.554V176.554L365.171 175.524ZM349.536 168.339L348.889 169.169L349.536 168.339ZM355.328 132.607L356.072 133.351C356.604 132.819 357.475 132.401 358.739 132.157C359.993 131.916 361.543 131.864 363.322 131.988C366.879 132.237 371.198 133.178 375.577 134.522C379.95 135.864 384.339 137.594 388.03 139.396C391.751 141.214 394.657 143.056 396.152 144.59L396.905 143.856L397.659 143.121C395.899 141.315 392.717 139.344 388.954 137.505C385.159 135.651 380.666 133.882 376.195 132.51C371.73 131.14 367.244 130.153 363.469 129.889C361.583 129.757 359.836 129.802 358.341 130.09C356.856 130.377 355.526 130.92 354.584 131.862L355.328 132.607ZM396.905 143.856L396.159 144.597C402.754 151.234 407.621 158.963 406.051 167.139L407.084 167.337L408.118 167.536C409.899 158.26 404.333 149.838 397.652 143.114L396.905 143.856ZM407.084 167.337L406.051 167.139C404.365 175.914 403.136 185.633 398.704 201.575L399.718 201.857L400.732 202.139C405.194 186.087 406.452 176.211 408.118 167.536L407.084 167.337ZM399.718 201.857L398.704 201.575C396.452 209.674 396.34 216.473 398.37 221.313C399.393 223.752 400.962 225.694 403.061 227.019C405.156 228.341 407.715 229.01 410.663 229.01V227.957V226.905C408.035 226.905 405.883 226.311 404.185 225.239C402.491 224.169 401.187 222.585 400.311 220.499C398.545 216.288 398.536 210.036 400.732 202.138L399.718 201.857ZM410.663 227.957L409.685 227.569C406.057 236.709 402.021 243.79 395.42 250.438L396.167 251.18L396.914 251.921C403.774 245.013 407.944 237.66 411.641 228.345L410.663 227.957ZM396.167 251.18L395.413 250.445C388.911 257.12 381.213 262.388 372.309 266.246L372.728 267.212L373.146 268.178C382.291 264.214 390.22 258.793 396.921 251.914L396.167 251.18ZM372.728 267.212L372.317 266.243C363.562 269.957 353.918 271.86 343.373 271.937L343.381 272.989L343.389 274.042C354.182 273.963 364.103 272.014 373.139 268.181L372.728 267.212ZM343.381 272.989L343.373 271.937C332.828 272.014 323.146 270.254 314.314 266.67L313.918 267.645L313.522 268.62C322.636 272.319 332.595 274.121 343.389 274.042L343.381 272.989ZM313.918 267.645L314.332 266.677C305.61 262.949 297.984 257.794 291.443 251.212L290.696 251.954L289.95 252.696C296.685 259.474 304.54 264.78 313.504 268.612L313.918 267.645ZM290.696 251.954L291.45 251.22C285.043 244.644 280.029 236.835 276.413 227.782L275.436 228.172L274.458 228.562C278.171 237.857 283.331 245.903 289.943 252.689L290.696 251.954ZM275.436 228.172L276.418 227.794C275.602 225.678 274.998 221.41 274.804 215.998C274.611 210.631 274.827 204.27 275.582 198.046C276.338 191.812 277.629 185.769 279.565 181.011C281.521 176.201 284.03 172.964 287.056 171.909L286.709 170.915L286.363 169.921C282.443 171.288 279.627 175.271 277.615 180.218C275.582 185.216 274.26 191.463 273.492 197.792C272.723 204.13 272.504 210.601 272.7 216.074C272.895 221.501 273.501 226.079 274.454 228.551L275.436 228.172ZM286.709 170.915L287.055 171.909C293.941 169.51 300.851 168.385 307.955 166.649C315.006 164.926 322.094 162.625 328.982 157.89L328.386 157.023L327.79 156.155C321.207 160.681 314.402 162.906 307.456 164.604C300.562 166.289 293.37 167.48 286.363 169.921L286.709 170.915ZM328.386 157.023L328.982 157.89C342.558 148.556 350.246 139.177 356.072 133.351L355.328 132.607L354.584 131.862C348.623 137.823 341.156 146.966 327.79 156.155L328.386 157.023ZM345.506 165.621L345.782 164.606C345.296 164.474 344.854 164.39 344.383 164.39C343.911 164.39 343.47 164.474 342.984 164.606L343.26 165.621L343.536 166.637C343.93 166.53 344.171 166.495 344.383 166.495C344.595 166.495 344.836 166.53 345.23 166.637L345.506 165.621ZM343.26 165.621L342.984 164.606C342.383 164.769 341.784 165.123 341.13 165.578C340.463 166.042 339.638 166.686 338.582 167.509L339.229 168.339L339.876 169.169C340.951 168.331 341.724 167.729 342.332 167.306C342.952 166.875 343.303 166.7 343.536 166.637L343.26 165.621ZM339.229 168.339L338.582 167.509C334.261 170.876 329.547 173.201 323.379 174.494L323.595 175.524L323.811 176.554C330.301 175.194 335.309 172.728 339.876 169.169L339.229 168.339ZM323.595 175.524L323.379 174.494C320.52 175.093 318.333 175.55 316.68 175.99C315.046 176.426 313.803 176.875 312.906 177.513L313.516 178.37L314.126 179.228C314.693 178.824 315.619 178.451 317.222 178.024C318.807 177.602 320.927 177.158 323.811 176.554L323.595 175.524ZM313.516 178.37L312.906 177.513C312.112 178.077 311.478 178.63 310.942 179.295C310.405 179.959 309.998 180.696 309.611 181.593L310.577 182.01L311.544 182.427C311.883 181.64 312.2 181.086 312.579 180.617C312.958 180.148 313.431 179.722 314.126 179.228L313.516 178.37ZM310.577 182.01L309.611 181.593C309.183 182.585 308.994 183.724 308.902 185.142C308.81 186.558 308.811 188.349 308.811 190.669H309.863H310.916C310.916 188.321 310.916 186.611 311.003 185.279C311.089 183.949 311.257 183.092 311.544 182.427L310.577 182.01ZM309.863 190.669H308.811V207.188H309.863H310.916V190.669H309.863ZM309.863 207.188H308.811C308.811 218.246 314.793 227.708 321.703 234.962C328.625 242.226 336.595 247.399 340.838 249.893L341.371 248.986L341.905 248.078C337.742 245.632 329.958 240.574 323.227 233.51C316.485 226.433 310.916 217.467 310.916 207.188H309.863ZM341.371 248.986L340.838 249.893C341.76 250.435 342.386 250.814 343.255 251.002L343.478 249.973L343.7 248.944C343.222 248.841 342.893 248.659 341.905 248.078L341.371 248.986ZM343.478 249.973L343.255 251.002C343.925 251.146 344.84 251.146 345.509 251.002L345.287 249.973L345.065 248.944C344.688 249.025 344.076 249.025 343.7 248.944L343.478 249.973ZM345.287 249.973L345.509 251.002C346.379 250.814 347.005 250.435 347.928 249.893L347.395 248.986L346.861 248.078C345.873 248.659 345.544 248.841 345.065 248.944L345.287 249.973ZM347.395 248.986L347.928 249.893C352.171 247.399 360.141 242.226 367.063 234.962C373.973 227.708 379.955 218.246 379.955 207.188H378.902H377.85C377.85 217.467 372.281 226.433 365.539 233.51C358.808 240.574 351.024 245.632 346.861 248.078L347.395 248.986ZM378.902 207.188H379.955V190.669H378.902H377.85V207.188H378.902ZM378.902 190.669H379.955C379.955 188.349 379.955 186.559 379.864 185.142C379.771 183.724 379.583 182.585 379.155 181.593L378.189 182.01L377.222 182.426C377.509 183.092 377.677 183.949 377.763 185.279C377.85 186.611 377.85 188.321 377.85 190.669H378.902ZM378.189 182.01L379.155 181.593C378.768 180.696 378.361 179.959 377.824 179.295C377.288 178.63 376.654 178.077 375.86 177.513L375.25 178.37L374.64 179.228C375.335 179.722 375.808 180.148 376.187 180.617C376.565 181.086 376.883 181.64 377.222 182.427L378.189 182.01ZM375.25 178.37L375.86 177.513C374.963 176.875 373.72 176.426 372.086 175.99C370.433 175.55 368.246 175.093 365.387 174.494L365.171 175.524L364.955 176.554C367.839 177.158 369.959 177.602 371.544 178.024C373.147 178.451 374.072 178.824 374.64 179.228L375.25 178.37ZM365.171 175.524L365.387 174.494C359.218 173.201 354.504 170.876 350.183 167.509L349.536 168.339L348.889 169.169C353.457 172.729 358.464 175.194 364.955 176.554L365.171 175.524ZM349.536 168.339L350.183 167.509C349.127 166.686 348.302 166.042 347.636 165.579C346.982 165.123 346.383 164.769 345.782 164.606L345.506 165.621L345.23 166.637C345.463 166.7 345.814 166.874 346.433 167.306C347.042 167.729 347.814 168.331 348.889 169.169L349.536 168.339Z" fill="#212269"/>
</g>
<defs>
<filter id="filter0_g_18_133" x="192.38" y="14.1775" width="160.643" height="244.819" filterUnits="userSpaceOnUse" color-interpolation-filters="sRGB">
<feFlood flood-opacity="0" result="BackgroundImageFix"/>
<feBlend mode="normal" in="SourceGraphic" in2="BackgroundImageFix" result="shape"/>
<feTurbulence type="fractalNoise" baseFrequency="0.59386211633682251 0.59386211633682251" numOctaves="3" seed="1459" />
<feDisplacementMap in="shape" scale="0" xChannelSelector="R" yChannelSelector="G" result="displacedImage" width="100%" height="100%" />
<feMerge result="effect1_texture_18_133">
<feMergeNode in="displacedImage"/>
</feMerge>
</filter>
<filter id="filter1_d_18_133" x="-1.4782e-05" y="49.7135" width="664.157" height="233.945" filterUnits="userSpaceOnUse" color-interpolation-filters="sRGB">
<feFlood flood-opacity="0" result="BackgroundImageFix"/>
<feColorMatrix in="SourceAlpha" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 127 0" result="hardAlpha"/>
<feOffset dy="1.68389"/>
<feGaussianBlur stdDeviation="2.10487"/>
<feComposite in2="hardAlpha" operator="out"/>
<feColorMatrix type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0.25 0"/>
<feBlend mode="normal" in2="BackgroundImageFix" result="effect1_dropShadow_18_133"/>
<feBlend mode="normal" in="SourceGraphic" in2="effect1_dropShadow_18_133" result="shape"/>
</filter>
</defs>
</svg>

          </div>
          
          <p style="margin:0 0 24px;font-size:16px;color:#333333;font-weight:600;line-height:24px;text-align:center;">
            Halo {user.nama_lengkap},<br><br>
            Kami menerima permintaan untuk mereset password akun SIPORA-mu. Klik tombol di bawah untuk membuat password baru:
          </p>
          
          <!-- Modal Action Button (btn-dialog confirm-primary) -->
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
            <tr><td align="center" style="padding:8px 0 32px;text-align:center;">
              <a href="{reset_link}" target="_blank" style="display:inline-block;padding:16px 20px;background-color:#2E3094;color:#ffffff;font-size:16px;font-weight:600;text-decoration:none;border-radius:8px;min-width:200px;text-align:center;">
                Reset Password Sekarang
              </a>
            </td></tr>
          </table>
          
          <!-- Warning Chip Time remaining (Match SChip warning variant) -->
          <div style="padding:10px 16px;background-color:#FFF8E1;border:1px solid #F59E0B;border-radius:12px;margin-bottom:24px;display:inline-block;text-align:center;">
             <table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 auto;">
              <tr>
                <td width="20" valign="middle" style="padding-right:8px;text-align:center;">
                  <!-- Feather Clock SVG replacing the emoji -->
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#F59E0B" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="10"></circle>
                    <polyline points="12 6 12 12 16 14"></polyline>
                  </svg>
                </td>
                <td style="font-size:13px;color:#F59E0B;line-height:1.5;font-weight:600;text-align:center;">
                  Link ini berlaku selama <strong>1 jam</strong>. Setelah itu, kamu perlu meminta link baru.
                </td>
              </tr>
            </table>
          </div>
          
          <!-- Fallback Link -->
           <div style="text-align:center;">
            <p style="margin:0 0 8px;font-size:13px;color:#6B7280;font-weight:500;text-align:center;">Tombol tidak berfungsi? Salin link ini ke browser:</p>
            <p style="margin:0;font-size:12px;color:#2E3094;word-break:break-all;line-height:1.5;text-align:center;">{reset_link}</p>
          </div>
        </td></tr>
        
        <!-- Footer Info -->
        <tr><td style="padding:24px 32px;border-top:1px solid #D9D9D9;background-color:#F9FAFB;text-align:center;">
          <p style="margin:0 0 12px;font-size:12px;color:#6B7280;line-height:1.5;text-align:center;">
            Jika kamu tidak meminta reset password, abaikan email ini. Akunmu tetap aman.
          </p>
          <p style="margin:0;font-size:12px;color:#9CA3AF;font-weight:600;text-align:center;">
            &copy; 2026 SIPORA &mdash; SMP Desa Putera
          </p>
        </td></tr>
        
      </table>
    </td></tr>
  </table>
</body>
</html>'''

        def send_email_thread():
            try:
                send_mail(
                    subject='[SIPORA] Reset Password Akunmu',
                    message=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    html_message=html_message,
                    fail_silently=False,
                )
            except Exception as e:
                import traceback
                logger.error(f"Email Dispatch Error: {str(e)}")
                traceback.print_exc()

        threading.Thread(target=send_email_thread).start()

        return mask_email(user.email)


class ForgotPasswordGuruSerializer(serializers.Serializer):
    """
    Validates NUPTK lookup during password recovery requests for Guru (Teacher) accounts.
    Triggers an asynchronous SMTP email dispatch containing a time-sensitive reset token.
    Reuses the same branded email template as the Siswa forgot-password flow.
    """
    nuptk = serializers.CharField()

    def validate_nuptk(self, value):
        if not value.isdigit() or len(value) != 16:
            raise serializers.ValidationError("NUPTK harus terdiri dari 16 digit angka.")
        try:
            user = Pengguna.objects.get(nuptk=value, role='guru')
        except Pengguna.DoesNotExist:
            raise serializers.ValidationError("NUPTK tidak ditemukan.")
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

        plain_message = (
            f'Halo {user.nama_lengkap},\n\n'
            f'Kami menerima permintaan untuk mereset password akun Guru SIPORA-mu.\n'
            f'Klik link berikut untuk membuat password baru (berlaku 1 jam):\n\n'
            f'{reset_link}\n\n'
            f'Jika kamu tidak meminta reset password, abaikan email ini.\n\n'
            f'Salam,\nTim SIPORA SMP Desa Putera'
        )

        html_message = f'''<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {{ font-family: 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #F9FAFB; margin: 0; padding: 0; }}
  </style>
</head>
<body style="margin:0;padding:0;background-color:#F9FAFB;font-family:'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#F3F4F6;padding:40px 16px;">
    <tr><td align="center">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:572px;background:#ffffff;border-radius:16px;border:1px solid #D9D9D9;box-shadow:0px 0px 10px 0px rgba(159, 160, 206, 0.50);overflow:hidden;">
        <tr><td style="background-color:#2E3094;padding:24px 48px;text-align:center;border-bottom:1px solid #D9D9D9;">
          <h2 style="margin:0;font-size:24px;font-weight:800;color:#ffffff;line-height:32px;text-align:center;">Reset Password</h2>
        </td></tr>
        <tr><td style="padding:32px;text-align:center;">
          <p style="margin:0 0 24px;font-size:16px;color:#333333;font-weight:600;line-height:24px;text-align:center;">
            Halo {user.nama_lengkap},<br><br>
            Kami menerima permintaan untuk mereset password akun Guru SIPORA-mu. Klik tombol di bawah untuk membuat password baru:
          </p>
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
            <tr><td align="center" style="padding:8px 0 32px;text-align:center;">
              <a href="{reset_link}" target="_blank" style="display:inline-block;padding:16px 20px;background-color:#2E3094;color:#ffffff;font-size:16px;font-weight:600;text-decoration:none;border-radius:8px;min-width:200px;text-align:center;">
                Reset Password Sekarang
              </a>
            </td></tr>
          </table>
          <div style="padding:10px 16px;background-color:#FFF8E1;border:1px solid #F59E0B;border-radius:12px;margin-bottom:24px;display:inline-block;text-align:center;">
             <table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 auto;">
              <tr>
                <td width="20" valign="middle" style="padding-right:8px;text-align:center;">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#F59E0B" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="10"></circle>
                    <polyline points="12 6 12 12 16 14"></polyline>
                  </svg>
                </td>
                <td style="font-size:13px;color:#F59E0B;line-height:1.5;font-weight:600;text-align:center;">
                  Link ini berlaku selama <strong>1 jam</strong>. Setelah itu, kamu perlu meminta link baru.
                </td>
              </tr>
            </table>
          </div>
           <div style="text-align:center;">
            <p style="margin:0 0 8px;font-size:13px;color:#6B7280;font-weight:500;text-align:center;">Tombol tidak berfungsi? Salin link ini ke browser:</p>
            <p style="margin:0;font-size:12px;color:#2E3094;word-break:break-all;line-height:1.5;text-align:center;">{reset_link}</p>
          </div>
        </td></tr>
        <tr><td style="padding:24px 32px;border-top:1px solid #D9D9D9;background-color:#F9FAFB;text-align:center;">
          <p style="margin:0 0 12px;font-size:12px;color:#6B7280;line-height:1.5;text-align:center;">
            Jika kamu tidak meminta reset password, abaikan email ini. Akunmu tetap aman.
          </p>
          <p style="margin:0;font-size:12px;color:#9CA3AF;font-weight:600;text-align:center;">
            &copy; 2026 SIPORA &mdash; SMP Desa Putera
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>'''

        def send_email_thread():
            try:
                send_mail(
                    subject='[SIPORA] Reset Password Akun Guru',
                    message=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    html_message=html_message,
                    fail_silently=False,
                )
            except Exception as e:
                import traceback
                logger.error(f"Email Dispatch Error: {str(e)}")
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
