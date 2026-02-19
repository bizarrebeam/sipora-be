from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Pengguna
from django.contrib.auth import authenticate

class RegisterPelaporSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    konfirmasi_password = serializers.CharField(write_only=True)

    class Meta:
        model = Pengguna
        fields = ('nisn', 'nama_lengkap', 'password', 'konfirmasi_password')

    def validate(self, data):
        if data['password'] != data['konfirmasi_password']:
            raise serializers.ValidationError("Password dan konfirmasi password tidak cocok.")
        return data

    def create(self, validated_data):
        pengguna = Pengguna.objects.create_user(
            username=validated_data['nisn'],
            nisn=validated_data['nisn'],
            nama_lengkap=validated_data['nama_lengkap'],
            password=validated_data['password'],
            role='pelapor'
        )
        return pengguna

class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        identifier = data.get('identifier')
        password = data.get('password')

        if identifier.isdigit() and len(identifier) == 10:
            try:
                user_obj = Pengguna.objects.get(nisn=identifier)
                username = user_obj.username
            except Pengguna.DoesNotExist:
                username = identifier
        else:
            username = identifier

        user = authenticate(username=username, password=password)

        if user and user.is_active:
            refresh = RefreshToken.for_user(user)
            return {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'role': user.role,
                'nama_lengkap': user.nama_lengkap
            }
        raise serializers.ValidationError("Kredensial tidak valid.")

class PenggunaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pengguna
        fields = ('id', 'username', 'nisn', 'nama_lengkap', 'role', 'is_active', 'date_joined')