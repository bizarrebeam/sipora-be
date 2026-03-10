from rest_framework import serializers
from .models import Artikel


class ArtikelSerializer(serializers.ModelSerializer):

    class Meta:
        model = Artikel
        fields = [
            'id',
            'judul',
            'ringkasan',
            'konten',
            'gambar',
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
            # Gunakan check 'in data' agar partial update tidak error
            # Jika sedang PUT dan konten tidak dikirim, dia tidak akan protes
            
            if 'judul' in data and not data.get('judul'):
                raise serializers.ValidationError("Judul wajib diisi.")

            if 'konten' in data and not data.get('konten'):
                raise serializers.ValidationError("Konten wajib diisi.")

            return data