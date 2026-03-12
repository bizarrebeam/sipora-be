from rest_framework import serializers
from .models import Artikel, FotoArtikel, JUDUL_MIN_CHARS, JUDUL_MAX_CHARS, KONTEN_MIN_CHARS, KONTEN_MAX_CHARS, RINGKASAN_MIN_CHARS, RINGKASAN_MAX_CHARS, MAX_FILE_SIZE

class FotoArtikelSerializer(serializers.ModelSerializer):
    """Serializer untuk foto artikel"""

    class Meta:
        model = FotoArtikel
        fields = ['id', 'foto', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']

class ArtikelSerializer(serializers.ModelSerializer):
    """Serializer untuk list dan detail artikel"""

    foto_artikel = FotoArtikelSerializer(many=True, read_only=True)
    foto_urls = serializers.SerializerMethodField()

    class Meta:
        model = Artikel
        fields = [
            'id',
            'judul',
            'ringkasan',
            'konten',
            'foto_artikel',
            'foto_urls',
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


class CreateArtikelSerializer(serializers.ModelSerializer):
    """Serializer untuk create artikel dengan foto"""

    foto_artikel = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
        max_length=5
    )

    class Meta:
        model = Artikel
        fields = [
            'judul', 'ringkasan', 'konten', 'status', 'foto_artikel'
        ]

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

    def validate_foto_artikel(self, value):
        """Validate foto artikel (max 5 files, max 5MB each)"""
        if len(value) > 5:
            raise serializers.ValidationError("Maksimal 5 foto")

        for foto in value:
            if foto.size > MAX_FILE_SIZE:
                raise serializers.ValidationError(
                    f"Ukuran file {foto.name} maksimal 5 MB"
                )

            # Check file type
            allowed_types = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp']
            content_type = foto.content_type
            if content_type not in allowed_types:
                raise serializers.ValidationError(
                    f"Format file {foto.name} tidak didukung. "
                    "Hanya PNG, JPG, JPEG, dan WEBP yang diperbolehkan."
                )
        return value

    def create(self, validated_data):
        """Create artikel dan foto terkait"""
        foto_artikel = validated_data.pop('foto_artikel', [])
        artikel = Artikel.objects.create(**validated_data)

        for foto in foto_artikel:
            FotoArtikel.objects.create(artikel=artikel, foto=foto)

        return artikel

    def get_foto_urls(self, obj):
        """Return list URL foto artikel"""
        request = self.context.get('request')
        foto_list = []
        for foto in obj.foto_artikel.all():
            if foto.foto and hasattr(foto.foto, 'url'):
                url = request.build_absolute_uri(foto.foto.url) if request else foto.foto.url
                foto_list.append(url)
        return foto_list if foto_list else None