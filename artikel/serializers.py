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

    # Selalu kembalikan list kosong jika tidak ada foto
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

    def get_foto_artikel(self, obj):
        """Selalu kembalikan list foto artikel (bisa kosong)"""
        return FotoArtikelSerializer(obj.foto_artikel.all(), many=True, context=self.context).data

    def get_foto_urls(self, obj):
        """Selalu kembalikan list URL foto artikel (bisa kosong)"""
        request = self.context.get('request')
        foto_list = []
        for foto in obj.foto_artikel.all():
            if foto.foto and hasattr(foto.foto, 'url'):
                url = request.build_absolute_uri(foto.foto.url) if request else foto.foto.url
                foto_list.append(url)
        return foto_list

    def get_gambar(self, obj):
        """Return URL foto pertama sebagai gambar utama artikel (atau None)"""
        request = self.context.get('request')
        foto = obj.foto_artikel.first()
        if foto and foto.foto and hasattr(foto.foto, 'url'):
            return request.build_absolute_uri(foto.foto.url) if request else foto.foto.url
        return None

    def get_nama_penulis(self, obj):
        """Return nama penulis (placeholder: Tim Kemahasiswaan)"""
        return 'Tim Kemahasiswaan'


class CreateArtikelSerializer(serializers.ModelSerializer):
    """Serializer untuk create artikel dengan foto cover (single image)"""

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
        """Ambil ringkasan dari paragraf pertama konten, potong jika perlu."""
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
        # Fix QueryDict immutable error by copying data if needed
        if hasattr(data, 'copy'):
            data = data.copy()
        konten = data.get('konten', '')
        ringkasan = data.get('ringkasan', '')
        data['ringkasan'] = self._auto_summary(konten, ringkasan)
        return super().to_internal_value(data)

    def update(self, instance, validated_data):
        # Otomatis isi ringkasan jika kosong atau terlalu panjang saat update
        konten = validated_data.get('konten', instance.konten)
        ringkasan = validated_data.get('ringkasan', validated_data.get('ringkasan', instance.ringkasan))
        validated_data['ringkasan'] = self._auto_summary(konten, ringkasan)
        return super().update(instance, validated_data)

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
        """Validate foto cover artikel (single file, max 5MB)"""
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
        """Create artikel dan simpan foto cover ke FotoArtikel"""
        foto = validated_data.pop('foto_artikel', None)
        artikel = Artikel.objects.create(**validated_data)

        if foto:
            FotoArtikel.objects.create(artikel=artikel, foto=foto)

        return artikel

    def update(self, instance, validated_data):
        """Update artikel, ganti foto cover jika ada yang baru"""
        foto = validated_data.pop('foto_artikel', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if foto:
            # Hapus foto lama, ganti dengan yang baru
            instance.foto_artikel.all().delete()
            FotoArtikel.objects.create(artikel=instance, foto=foto)

        return instance
