from rest_framework import serializers
from .models import Artikel, FotoArtikel, JUDUL_MIN_CHARS, JUDUL_MAX_CHARS, KONTEN_MIN_CHARS, KONTEN_MAX_CHARS, RINGKASAN_MIN_CHARS, RINGKASAN_MAX_CHARS, MAX_FILE_SIZE


class FotoArtikelSerializer(serializers.ModelSerializer):
    """
    Serializer for FotoArtikel model.
    Serializes image ID, file, and upload timestamp.
    """

    class Meta:
        model = FotoArtikel
        fields = ['id', 'foto', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']


class ArtikelSerializer(serializers.ModelSerializer):
    """
    Serializer for listing and retrieving articles.
    Includes related images, image URLs, main image, and author name.
    Ensures image fields always return a list (empty if no images).
    """

    # Always return an empty list if there are no images
    foto_artikel = serializers.SerializerMethodField()
    foto_urls = serializers.SerializerMethodField()
    gambar = serializers.SerializerMethodField()
    nama_penulis = serializers.SerializerMethodField()

    class Meta:
        model = Artikel
        fields = [
            'id',
            'judul',
            'ringkasan',
            'konten',
            'foto_artikel',
            'foto_urls',
            'gambar',
            'nama_penulis',
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
        }

    def validate_judul(self, value):
        """
        Validate title for minimum and maximum character limits.
        """
        if not value:
            raise serializers.ValidationError("Judul wajib diisi.")
        if len(value) < JUDUL_MIN_CHARS:
            raise serializers.ValidationError(f"Judul minimal {JUDUL_MIN_CHARS} karakter.")
        if len(value) > JUDUL_MAX_CHARS:
            raise serializers.ValidationError(f"Judul maksimal {JUDUL_MAX_CHARS} karakter.")
        return value

    def validate_konten(self, value):
        """
        Validate content for minimum and maximum character limits.
        """
        if not value or not value.strip():
            raise serializers.ValidationError("Konten wajib diisi.")
        if len(value) < KONTEN_MIN_CHARS:
            raise serializers.ValidationError(f"Konten minimal {KONTEN_MIN_CHARS} karakter.")
        if len(value) > KONTEN_MAX_CHARS:
            raise serializers.ValidationError(f"Konten maksimal {KONTEN_MAX_CHARS} karakter.")
        return value

    def validate_ringkasan(self, value):
        """
        Validate summary for minimum and maximum character limits (optional).
        """
        if value:
            if len(value) < RINGKASAN_MIN_CHARS:
                raise serializers.ValidationError(f"Ringkasan minimal {RINGKASAN_MIN_CHARS} karakter.")
            if len(value) > RINGKASAN_MAX_CHARS:
                raise serializers.ValidationError(f"Ringkasan maksimal {RINGKASAN_MAX_CHARS} karakter.")
        return value

    def get_foto_artikel(self, obj):
        """
        Always return a list of related images (can be empty).
        """
        return FotoArtikelSerializer(obj.foto_artikel.all(), many=True, context=self.context).data

    def get_foto_urls(self, obj):
        """
        Always return a list of image URLs (can be empty).
        """
        request = self.context.get('request')
        foto_list = []
        for foto in obj.foto_artikel.all():
            if foto.foto and hasattr(foto.foto, 'url'):
                url = request.build_absolute_uri(foto.foto.url) if request else foto.foto.url
                foto_list.append(url)
        return foto_list

    def get_gambar(self, obj):
        """
        Return the URL of the first image as the main article image (or None).
        """
        request = self.context.get('request')
        foto = obj.foto_artikel.first()
        if foto and foto.foto and hasattr(foto.foto, 'url'):
            return request.build_absolute_uri(foto.foto.url) if request else foto.foto.url
        return None

    def get_nama_penulis(self, obj):
        """
        Return the author name (currently a placeholder: 'Tim Kemahasiswaan').
        """
        return 'Tim Kemahasiswaan'



class CreateArtikelSerializer(serializers.ModelSerializer):
    """
    Serializer for creating articles with a cover image (single image).
    Handles image validation, summary auto-generation, and field validation.
    """

    foto_artikel = serializers.ImageField(
        write_only=True,
        required=False,
        allow_null=True
    )

    class Meta:
        model = Artikel
        fields = [
            'judul', 'ringkasan', 'konten', 'status', 'foto_artikel'
        ]

        extra_kwargs = {
            'judul': {'min_length': JUDUL_MIN_CHARS, 'max_length': JUDUL_MAX_CHARS},
            'konten': {'min_length': KONTEN_MIN_CHARS, 'max_length': KONTEN_MAX_CHARS},
            'ringkasan': {'required': False, 'allow_null': True, 'min_length': RINGKASAN_MIN_CHARS, 'max_length': RINGKASAN_MAX_CHARS},
            'status': {'required': False}
        }

    def _auto_summary(self, konten, ringkasan):
        """
        Generate a summary from the first paragraph of content if not provided.
        Truncate and add ellipsis if too long.
        """
        if not ringkasan and konten:
            paragraphs = [p.strip() for p in konten.split('\n') if p.strip()]
            if paragraphs:
                summary = paragraphs[0]
                if len(summary) > RINGKASAN_MAX_CHARS:
                    summary = summary[:RINGKASAN_MAX_CHARS-3].rstrip() + '...'
                return summary
        if ringkasan and len(ringkasan) > RINGKASAN_MAX_CHARS:
            return ringkasan[:RINGKASAN_MAX_CHARS-3].rstrip() + '...'
        return ringkasan

    def to_internal_value(self, data):
        """
        Ensure summary is auto-generated and QueryDict is copied if needed.
        """
        if hasattr(data, 'copy'):
            data = data.copy()
        konten = data.get('konten', '')
        ringkasan = data.get('ringkasan', '')
        data['ringkasan'] = self._auto_summary(konten, ringkasan)
        return super().to_internal_value(data)

    def update(self, instance, validated_data):
        """
        Ensure summary is auto-generated or truncated on update.
        """
        konten = validated_data.get('konten', instance.konten)
        ringkasan = validated_data.get('ringkasan', validated_data.get('ringkasan', instance.ringkasan))
        validated_data['ringkasan'] = self._auto_summary(konten, ringkasan)
        return super().update(instance, validated_data)

    def validate_judul(self, value):
        """
        Validate title for minimum and maximum character limits.
        """
        if not value:
            raise serializers.ValidationError("Judul wajib diisi.")
        if len(value) < JUDUL_MIN_CHARS:
            raise serializers.ValidationError(f"Judul minimal {JUDUL_MIN_CHARS} karakter.")
        if len(value) > JUDUL_MAX_CHARS:
            raise serializers.ValidationError(f"Judul maksimal {JUDUL_MAX_CHARS} karakter.")
        return value

    def validate_konten(self, value):
        """
        Validate content for minimum and maximum character limits.
        """
        if not value or not value.strip():
            raise serializers.ValidationError("Konten wajib diisi.")
        if len(value) < KONTEN_MIN_CHARS:
            raise serializers.ValidationError(f"Konten minimal {KONTEN_MIN_CHARS} karakter.")
        if len(value) > KONTEN_MAX_CHARS:
            raise serializers.ValidationError(f"Konten maksimal {KONTEN_MAX_CHARS} karakter.")
        return value

    def validate_ringkasan(self, value):
        """
        Validate summary for minimum and maximum character limits (optional).
        """
        if value:
            if len(value) < RINGKASAN_MIN_CHARS:
                raise serializers.ValidationError(f"Ringkasan minimal {RINGKASAN_MIN_CHARS} karakter.")
            if len(value) > RINGKASAN_MAX_CHARS:
                raise serializers.ValidationError(f"Ringkasan maksimal {RINGKASAN_MAX_CHARS} karakter.")
        return value

    def validate_foto_artikel(self, value):
        """
        Validate cover image (single file, max 5MB, allowed types only).
        """
        if value is None:
            return value

        if value.size > MAX_FILE_SIZE:
            raise serializers.ValidationError(
                f"Ukuran file {value.name} maksimal 5 MB"
            )

        allowed_types = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp']
        if value.content_type not in allowed_types:
            raise serializers.ValidationError(
                f"Format file {value.name} tidak didukung. "
                "Hanya PNG, JPG, JPEG, dan WEBP yang diperbolehkan."
            )
        return value

    def create(self, validated_data):
        """
        Create an article and save the cover image to FotoArtikel.
        """
        foto = validated_data.pop('foto_artikel', None)
        artikel = Artikel.objects.create(**validated_data)

        if foto:
            FotoArtikel.objects.create(artikel=artikel, foto=foto)

        return artikel

    def update(self, instance, validated_data):
        """
        Update an article, replace cover image if a new one is provided.
        """
        foto = validated_data.pop('foto_artikel', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if foto:
            # Hapus foto lama, ganti dengan yang baru
            instance.foto_artikel.all().delete()
            FotoArtikel.objects.create(artikel=instance, foto=foto)

        return instance
