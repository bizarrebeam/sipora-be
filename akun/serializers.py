from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Pengguna, get_tahun_ajaran, get_semester
from django.contrib.auth import authenticate


# ─── Public Registration (Siswa only) ─────────────────────────────────────────

class RegisterSiswaSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    konfirmasi_password = serializers.CharField(write_only=True)

    class Meta:
        model = Pengguna
        fields = ('nisn', 'nama_lengkap', 'kelas', 'password', 'konfirmasi_password')

    def validate_nisn(self, value):
        if not value.isdigit() or len(value) != 10:
            raise serializers.ValidationError("NISN harus terdiri dari 10 digit angka.")
        if Pengguna.objects.filter(nisn=value).exists():
            raise serializers.ValidationError("NISN sudah terdaftar.")
        return value

    def validate(self, data):
        if data['password'] != data['konfirmasi_password']:
            raise serializers.ValidationError("Password dan konfirmasi password tidak cocok.")
        return data

    def create(self, validated_data):
        validated_data.pop('konfirmasi_password')
        return Pengguna.objects.create_user(
            username=validated_data['nisn'],
            nisn=validated_data['nisn'],
            nama_lengkap=validated_data['nama_lengkap'],
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
            role='guru'
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
            role='guru_bk'
        )


# ─── Login ─────────────────────────────────────────────────────────────────────

class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        identifier = data.get('identifier')
        password = data.get('password')

        # Auto-detect identifier type
        if identifier.isdigit() and len(identifier) == 10:
            # NISN (siswa)
            try:
                user_obj = Pengguna.objects.get(nisn=identifier)
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
            # Username (kemahasiswaan, guru_bk, or other)
            username = identifier

        user = authenticate(username=username, password=password)

        if user and user.is_active:
            refresh = RefreshToken.for_user(user)
            return {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'role': user.role,
                'nama_lengkap': user.nama_lengkap,
                'nisn': user.nisn,
                'nuptk': user.nuptk,
                'kelas': user.kelas,
                'mata_pelajaran': user.mata_pelajaran,
            }
        raise serializers.ValidationError("Kredensial tidak valid.")


# ─── Profile ───────────────────────────────────────────────────────────────────

class PenggunaSerializer(serializers.ModelSerializer):
    tahun_ajaran = serializers.SerializerMethodField()
    semester = serializers.SerializerMethodField()

    class Meta:
        model = Pengguna
        fields = (
            'id', 'username', 'nisn', 'nuptk', 'nama_lengkap',
            'role', 'kelas', 'mata_pelajaran', 'is_active', 'date_joined',
            'tahun_ajaran', 'semester'
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