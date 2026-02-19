from rest_framework import serializers
from .models import LogAktivitas
from akun.serializers import PenggunaSerializer

class LogAktivitasSerializer(serializers.ModelSerializer):
    pengguna = PenggunaSerializer(read_only=True)

    class Meta:
        model = LogAktivitas
        fields = '__all__'