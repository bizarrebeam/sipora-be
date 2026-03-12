from rest_framework import serializers
from .models import Artikel, JUDUL_MIN_CHARS, JUDUL_MAX_CHARS, KONTEN_MIN_CHARS, KONTEN_MAX_CHARS, RINGKASAN_MIN_CHARS, RINGKASAN_MAX_CHARS


class ArtikelSerializer(serializers.ModelSerializer):
    """Serializer untuk list dan detail artikel"""

    gambar_url = serializers.SerializerMethodField()

    class Meta:
        model = Artikel
        fields = [
            'id',
            'judul',
            'ringkasan',
            'konten',
            'gambar',
            'gambar_url',
            'status',
            'created_at',
            'updated_at'
        ]

        read_only_fields = [
            'id',
            'created_at',
            'updated_at'
        ]

        extra_kwargs = {
            'judul': {'min_length': JUDUL_MIN_CHARS, 'max_length': JUDUL_MAX_CHARS},
            'konten': {'min_length': KONTEN_MIN_CHARS, 'max_length': KONTEN_MAX_CHARS},
            'ringkasan': {'required': False, 'allow_null': True, 'min_length': RINGKASAN_MIN_CHARS, 'max_length': RINGKASAN_MAX_CHARS},
            'gambar': {'required': False, 'allow_null': True}
        }

    def validate_judul(self, value):
        """Validasi judul min/max characters"""
        if not value:
            raise serializers.ValidationError("Judul wajib diisi.")
        if len(value) < JUDUL_MIN_CHARS:
            raise serializers.ValidationError(f"Judul minimal {JUDUL_MIN_CHARS} karakter.")
        if len(value) > JUDUL_MAX_CHARS:
            raise serializers.ValidationError(f"Judul maksimal {JUDUL_MAX_CHARS} karakter.")
        return value

    def validate_konten(self, value):
        """Validasi konten min/max characters"""
        if not value or not value.strip():
            raise serializers.ValidationError("Konten wajib diisi.")
        if len(value) < KONTEN_MIN_CHARS:
            raise serializers.ValidationError(f"Konten minimal {KONTEN_MIN_CHARS} karakter.")
        if len(value) > KONTEN_MAX_CHARS:
            raise serializers.ValidationError(f"Konten maksimal {KONTEN_MAX_CHARS} karakter.")
        return value

    def validate_ringkasan(self, value):
        """Validasi ringkasan min/max characters (opsional)"""
        if value:
            if len(value) < RINGKASAN_MIN_CHARS:
                raise serializers.ValidationError(f"Ringkasan minimal {RINGKASAN_MIN_CHARS} karakter.")
            if len(value) > RINGKASAN_MAX_CHARS:
                raise serializers.ValidationError(f"Ringkasan maksimal {RINGKASAN_MAX_CHARS} karakter.")
        return value

    def get_gambar_url(self, obj):
        """Return URL gambar artikel"""
        request = self.context.get('request')

        if obj.gambar and hasattr(obj.gambar, 'url'):
            if request:
                return request.build_absolute_uri(obj.gambar.url)
            return obj.gambar.url

        return None