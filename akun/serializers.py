from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Pengguna, get_tahun_ajaran, get_semester
from django.contrib.auth import authenticate
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
import re


# ─── Public Registration (Siswa only) ─────────────────────────────────────────

class RegisterSiswaSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    konfirmasi_password = serializers.CharField(write_only=True)

    class Meta:
        model = Pengguna
        fields = ('nis', 'nama_lengkap', 'email', 'kelas', 'password', 'konfirmasi_password')

    def validate_nis(self, value):
        if not value.isdigit() or len(value) != 4:
            raise serializers.ValidationError("NIS harus terdiri dari 4 digit angka.")
        if Pengguna.objects.filter(nis=value).exists():
            raise serializers.ValidationError("NIS sudah terdaftar.")
        return value

    def validate_email(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Email wajib diisi.")
        if Pengguna.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email sudah terdaftar.")
        return value.strip().lower()

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


# ─── Admin: Create Guru Account ───────────────────────────────────────────────

class AdminBuatGuruSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = Pengguna
        fields = ('nuptk', 'nama_lengkap', 'mata_pelajaran', 'password')

    def validate_nuptk(self, value):
        if not value.isdigit() or len(value) != 16:
            raise serializers.ValidationError("NUPTK harus terdiri dari 16 digit angka.")
        if Pengguna.objects.filter(nuptk=value).exists():
            raise serializers.ValidationError("NUPTK sudah terdaftar.")
        return value

    def validate_mata_pelajaran(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Mata pelajaran wajib diisi.")
        return value.strip()

    def create(self, validated_data):
        return Pengguna.objects.create_user(
            username=validated_data['nuptk'],
            nuptk=validated_data['nuptk'],
            nama_lengkap=validated_data['nama_lengkap'],
            mata_pelajaran=validated_data['mata_pelajaran'],
            password=validated_data['password'],
            role='guru',
            is_verified=True,
        )


# ─── Admin: Create Guru BK Account ────────────────────────────────────────────

class AdminBuatGuruBKSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = Pengguna
        fields = ('nuptk', 'nama_lengkap', 'password')

    def validate_nuptk(self, value):
        if not value.isdigit() or len(value) != 16:
            raise serializers.ValidationError("NUPTK harus terdiri dari 16 digit angka.")
        if Pengguna.objects.filter(nuptk=value).exists():
            raise serializers.ValidationError("NUPTK sudah terdaftar.")
        return value

    def create(self, validated_data):
        return Pengguna.objects.create_user(
            username=validated_data['nuptk'],
            nuptk=validated_data['nuptk'],
            nama_lengkap=validated_data['nama_lengkap'],
            mata_pelajaran='Bimbingan Konseling',
            password=validated_data['password'],
            role='guru_bk',
            is_verified=True,
        )


# ─── Login ─────────────────────────────────────────────────────────────────────

class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        identifier = data.get('identifier')
        password = data.get('password')

        # Auto-detect identifier type
        if identifier.isdigit() and len(identifier) == 4:
            # NIS (siswa)
            try:
                user_obj = Pengguna.objects.get(nis=identifier)
                username = user_obj.username
            except Pengguna.DoesNotExist:
                username = identifier
        elif identifier.isdigit() and len(identifier) == 16:
            # NUPTK (guru / guru_bk)
            try:
                user_obj = Pengguna.objects.get(nuptk=identifier)
                username = user_obj.username
            except Pengguna.DoesNotExist:
                username = identifier
        else:
            # Username (kemahasiswaan, or other)
            username = identifier

        user = authenticate(username=username, password=password)

        if user and user.is_active:
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


# ─── Profile ───────────────────────────────────────────────────────────────────

class PenggunaSerializer(serializers.ModelSerializer):
    tahun_ajaran = serializers.SerializerMethodField()
    semester = serializers.SerializerMethodField()

    class Meta:
        model = Pengguna
        fields = (
            'id', 'username', 'nis', 'nuptk', 'nama_lengkap', 'email',
            'role', 'kelas', 'mata_pelajaran', 'is_active', 'is_verified',
            'date_joined', 'tahun_ajaran', 'semester'
        )

    def get_tahun_ajaran(self, obj):
        return get_tahun_ajaran()

    def get_semester(self, obj):
        return get_semester()


# ─── Edit Profile ──────────────────────────────────────────────────────────────

class EditProfilSerializer(serializers.Serializer):
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


# ─── Change Password ──────────────────────────────────────────────────────────

class UbahPasswordSerializer(serializers.Serializer):
    password_lama = serializers.CharField(write_only=True)
    password_baru = serializers.CharField(write_only=True, min_length=6)

    def validate_password_lama(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Password lama yang dimasukkan salah.")
        return value

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['password_baru'])
        user.save()
        return user


# ─── Forgot Password ──────────────────────────────────────────────────────────

def mask_email(email):
    """Mask email for privacy: a****[REDACTED EMAIL]"""
    if not email:
        return ''
    local, domain = email.split('@')
    if len(local) <= 2:
        masked_local = local[0] + '***'
    else:
        masked_local = local[0] + '*' * (len(local) - 2) + local[-1]
    return f'{masked_local}@{domain}'


class ForgotPasswordSerializer(serializers.Serializer):
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
        reset_link = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}"

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

        return mask_email(user.email)


class ResetPasswordSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=6)
    konfirmasi_password = serializers.CharField(write_only=True)

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