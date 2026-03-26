"""
API Serializers for Activity Logging.

This module prepares complex database queries of the audit trail for frontend transmission,
including lightweight hydration of relational user metadata.
"""

from rest_framework import serializers
from .models import LogAktivitas
from akun.models import Pengguna

class LogAktivitasSerializer(serializers.ModelSerializer):
    """
    Read-only serializer mapping the `LogAktivitas` model into JSON format.
    Dynamically binds related user context (ID, Name, Role) when available.
    """
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