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
    """
    riwayat_mengajar = serializers.ListField(
        child=serializers.DictField(), required=False
    )

    class Meta:
        model = Pengguna
        fields = ('nama_lengkap', 'email', 'riwayat_mengajar')

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
            'date_joined', 'tahun_ajaran', 'semester', 'riwayat_mengajar'
        )

    def get_tahun_ajaran(self, obj):
        return self._tahun_ajaran_cache

    def get_semester(self, obj):
        return self._semester_cache


class PenggunaListSerializer(serializers.ModelSerializer):
    """Lean serializer for admin list view — no computed fields."""
    riwayat_mengajar = MataPelajaranGuruSemesterSerializer(many=True, read_only=True)

    class Meta:
        model = Pengguna
        fields = (
            'id', 'username', 'nis', 'nuptk', 'nama_lengkap', 'email',
            'role', 'kelas', 'mata_pelajaran', 'is_verified', 'date_joined', 'riwayat_mengajar'
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
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background-color:#f3f4f6;font-family:'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f3f4f6;padding:32px 16px;">
    <tr><td align="center">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:480px;background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.06);">
        
        <!-- Header -->
        <tr><td style="background:linear-gradient(135deg,#2A2C87 0%,#4F46E5 100%);padding:32px 24px;text-align:center;">
          <h1 style="margin:0;font-size:28px;font-weight:800;color:#ffffff;letter-spacing:1px;">SIPORA</h1>
          <p style="margin:6px 0 0;font-size:12px;color:rgba(255,255,255,0.8);letter-spacing:0.5px;">Sistem Informasi Pelaporan SMP Desa Putera</p>
        </td></tr>
        
        <!-- Body -->
        <tr><td style="padding:32px 24px;">
          <h2 style="margin:0 0 8px;font-size:20px;font-weight:700;color:#1f2937;">Reset Password</h2>
          <p style="margin:0 0 20px;font-size:14px;color:#6b7280;line-height:1.6;">
            Halo <strong style="color:#1f2937;">{user.nama_lengkap}</strong>,
          </p>
          <p style="margin:0 0 24px;font-size:14px;color:#6b7280;line-height:1.6;">
            Kami menerima permintaan untuk mereset password akun SIPORA-mu. Klik tombol di bawah untuk membuat password baru:
          </p>
          
          <!-- CTA Button -->
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
            <tr><td align="center" style="padding:4px 0 24px;">
              <a href="{reset_link}" target="_blank" style="display:inline-block;padding:14px 32px;background:linear-gradient(135deg,#2A2C87 0%,#4F46E5 100%);color:#ffffff;font-size:14px;font-weight:700;text-decoration:none;border-radius:10px;letter-spacing:0.3px;">
                Reset Password Sekarang
              </a>
            </td></tr>
          </table>
          
          <!-- Expiry Notice -->
          <div style="padding:12px 16px;background:#fef3c7;border:1px solid #fde68a;border-radius:8px;margin-bottom:20px;">
            <p style="margin:0;font-size:12px;color:#92400e;line-height:1.5;">
              ⏰ Link ini berlaku selama <strong>1 jam</strong>. Setelah itu, kamu perlu meminta link baru.
            </p>
          </div>
          
          <!-- Fallback Link -->
          <p style="margin:0 0 4px;font-size:12px;color:#9ca3af;">Tombol tidak berfungsi? Salin link ini ke browser:</p>
          <p style="margin:0;font-size:11px;color:#6366f1;word-break:break-all;line-height:1.5;">{reset_link}</p>
        </td></tr>
        
        <!-- Security Footer -->
        <tr><td style="padding:0 24px 24px;">
          <div style="border-top:1px solid #e5e7eb;padding-top:16px;">
            <p style="margin:0;font-size:11px;color:#9ca3af;line-height:1.5;">
              Jika kamu tidak meminta reset password, abaikan email ini. Akunmu tetap aman.
            </p>
          </div>
        </td></tr>
        
        <!-- Brand Footer -->
        <tr><td style="background:#f9fafb;padding:16px 24px;text-align:center;border-top:1px solid #e5e7eb;">
          <p style="margin:0;font-size:11px;color:#9ca3af;">
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
                print(f"Email Dispatch Error: {str(e)}")
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

