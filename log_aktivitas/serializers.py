from rest_framework import serializers
from .models import LogAktivitas
from akun.models import Pengguna

class LogAktivitasSerializer(serializers.ModelSerializer):
    pengguna = serializers.SerializerMethodField(read_only=True)
    
    def get_pengguna(self, obj):
        if obj.pengguna:
            return {
                'id': str(obj.pengguna.id),
                'nama_lengkap': obj.pengguna.nama_lengkap,
                'role': obj.pengguna.role,
            }
        return None

    class Meta:
        model = LogAktivitas
        fields = ['id', 'aksi', 'deskripsi', 'waktu', 'modul', 'pengguna']