"""
Serializers module for the tanggapan application.

Provides validation and serialization logic for response messages to damage reports.
"""

import re

from rest_framework import serializers

from .models import TanggapanLaporanKerusakan, TanggapanLaporanBullying


FORBIDDEN_SPECIAL_CHARS_REGEX = re.compile(r'[@!~`#$%^*+]')
MIN_TANGGAPAN_LENGTH = 5
MAX_TANGGAPAN_LENGTH = 2000


def normalize_text(value):
    """Normalize text input by removing zero-width chars and trimming spaces."""
    if value is None:
        return ''
    text = str(value)
    text = re.sub(r'[\u200B-\u200D\uFEFF]', '', text)
    return text.strip()


class TanggapanLaporanKerusakanListSerializer(serializers.ModelSerializer):
    """Serializer for displaying response messages in a thread."""
    
    pengirim_id = serializers.IntegerField(source='pengirim.id', read_only=True)
    pengirim_role = serializers.CharField(source='pengirim.role', read_only=True, allow_null=True)
    nama_pengirim = serializers.SerializerMethodField()
    
    class Meta:
        model = TanggapanLaporanKerusakan
        fields = [
            'id',
            'laporan',
            'nama_pengirim',
            'pengirim_id',
            'pengirim_role',
            'pesan',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'laporan',
            'created_at',
        ]

    def get_nama_pengirim(self, obj):
        """Return a dynamic display name based on the report's current anonymity setting."""
        if obj.laporan and obj.laporan.anonimitas and obj.pengirim_id == obj.laporan.pelapor_id:
            return 'Pengguna Anonim'

        if obj.pengirim:
            return obj.pengirim.nama_lengkap or obj.pengirim.username

        return obj.nama_pengirim or 'Sistem'


class TanggapanLaporanKerusakanCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new response messages."""
    
    class Meta:
        model = TanggapanLaporanKerusakan
        fields = [
            'pesan',
        ]
    
    def validate_pesan(self, value):
        """Validate response message field."""
        normalized = normalize_text(value)
        
        if not normalized:
            raise serializers.ValidationError('Pesan wajib diisi')
        
        if FORBIDDEN_SPECIAL_CHARS_REGEX.search(normalized):
            raise serializers.ValidationError('Pesan mengandung karakter yang tidak diperbolehkan')
        
        if len(normalized) < MIN_TANGGAPAN_LENGTH:
            raise serializers.ValidationError(
                f'Pesan minimal {MIN_TANGGAPAN_LENGTH} karakter'
            )
        
        if len(normalized) > MAX_TANGGAPAN_LENGTH:
            raise serializers.ValidationError(
                f'Pesan maksimal {MAX_TANGGAPAN_LENGTH} karakter'
            )
        
        return normalized


class TanggapanLaporanBullyingListSerializer(serializers.ModelSerializer):
    """Serializer for displaying response messages in a bullying report thread."""
    
    pengirim_id = serializers.IntegerField(source='pengirim.id', read_only=True)
    pengirim_role = serializers.CharField(source='pengirim.role', read_only=True, allow_null=True)
    nama_pengirim = serializers.SerializerMethodField()
    
    class Meta:
        model = TanggapanLaporanBullying
        fields = [
            'id',
            'laporan',
            'nama_pengirim',
            'pengirim_id',
            'pengirim_role',
            'pesan',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'laporan',
            'created_at',
        ]

    def get_nama_pengirim(self, obj):
        """Return display name respecting anonymity setting."""
        if obj.laporan and obj.laporan.anonimitas and obj.pengirim_id == obj.laporan.pelapor_id:
            return 'Pengguna Anonim'

        if obj.pengirim:
            return obj.pengirim.nama_lengkap or obj.pengirim.username

        return obj.nama_pengirim or 'Sistem'


class TanggapanLaporanBullyingCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new response messages on bullying reports."""
    
    class Meta:
        model = TanggapanLaporanBullying
        fields = [
            'pesan',
        ]
    
    def validate_pesan(self, value):
        """Validate response message field."""
        normalized = normalize_text(value)
        
        if not normalized:
            raise serializers.ValidationError('Pesan wajib diisi')
        
        if FORBIDDEN_SPECIAL_CHARS_REGEX.search(normalized):
            raise serializers.ValidationError('Pesan mengandung karakter yang tidak diperbolehkan')
        
        if len(normalized) < MIN_TANGGAPAN_LENGTH:
            raise serializers.ValidationError(
                f'Pesan minimal {MIN_TANGGAPAN_LENGTH} karakter'
            )
        
        if len(normalized) > MAX_TANGGAPAN_LENGTH:
            raise serializers.ValidationError(
                f'Pesan maksimal {MAX_TANGGAPAN_LENGTH} karakter'
            )
        
        return normalized
