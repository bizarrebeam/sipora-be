from rest_framework import serializers
from .models import Evaluasi, NilaiEvaluasi, Indikator
from django.contrib.auth import get_user_model
import re

User = get_user_model()

class NilaiEvaluasiSerializer(serializers.Serializer):
    indikator_id = serializers.IntegerField()
    nilai = serializers.IntegerField(
        min_value=1, 
        max_value=5,
        error_messages={
            "min_value": "Rating harus antara 1 sampai 5.",
            "max_value": "Rating harus antara 1 sampai 5.",
            "invalid": "Rating harus antara 1 sampai 5.",
            "required": "Rating harus antara 1 sampai 5.",
            "null": "Rating harus antara 1 sampai 5."
        }
    )

    def validate_indikator_id(self, value):
        if not Indikator.objects.filter(id=value).exists():
            raise serializers.ValidationError(f"Indikator dengan ID {value} tidak valid.")
        return value

def sanitize_text(value):
    """
    Sanitize user input to prevent XSS and other injection attacks by 
    removing HTML tags and potentially dangerous characters from a string.
    """
    if not value:
        return value
    # Delete HTML elements
    value = re.sub(r'<.*?>', '', value)
    # Delete dangerous characters
    value = re.sub(r'[<>"\'%;()&+]', '', value)
    return value.strip()

class EvaluasiCreateSerializer(serializers.Serializer):
    staff_id = serializers.UUIDField(
        required=True,
        error_messages={
            "required": "Staff/Guru harus dipilih.",
            "null": "Staff/Guru harus dipilih.",
            "invalid": "Staff/Guru harus dipilih."
        }
    )
    rating = NilaiEvaluasiSerializer(many=True, required=True, allow_empty=False)
    komentar = serializers.CharField(
        required=False, 
        allow_blank=True,
        min_length=20,
        error_messages={
            "min_length": "Komentar terlalu singkat."
        }
    )

    def validate_komentar(self, value):
        if len(str(value)) > 0:
            s_value = sanitize_text(value)
            if len(s_value) < 20:
                raise serializers.ValidationError("Komentar terlalu singkat setelah disanitasi.")
            return s_value
        return value

class IndikatorSerializer(serializers.ModelSerializer):
    kategori_nama = serializers.CharField(source='kategori.nama', read_only=True)
    
    class Meta:
        model = Indikator
        fields = ['id', 'deskripsi', 'kategori_nama']

class GuruSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'nama_lengkap']
