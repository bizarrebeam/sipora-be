from rest_framework import serializers
from .models import Artikel


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
            'ringkasan': {'required': False, 'allow_null': True},
            'gambar': {'required': False, 'allow_null': True}
        }

    def validate(self, data):
        """Validasi judul dan konten"""
        if 'judul' in data and not data.get('judul'):
            raise serializers.ValidationError("Judul wajib diisi.")

        if 'konten' in data and not data.get('konten'):
            raise serializers.ValidationError("Konten wajib diisi.")

        return data

    def get_gambar_url(self, obj):
        """Return URL gambar artikel"""
        request = self.context.get('request')

        if obj.gambar and hasattr(obj.gambar, 'url'):
            if request:
                return request.build_absolute_uri(obj.gambar.url)
            return obj.gambar.url

        return None