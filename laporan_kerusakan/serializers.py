from rest_framework import serializers
from .models import LaporanKerusakan, FotoBuktiPendukung
from akun.models import Pengguna


class FotoBuktiSerializer(serializers.ModelSerializer):
    """Serializer untuk foto bukti pendukung"""
    
    class Meta:
        model = FotoBuktiPendukung
        fields = ['id', 'foto', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']


class PelaporSerializer(serializers.ModelSerializer):
    """Serializer untuk info pelapor"""
    
    class Meta:
        model = Pengguna
        fields = ['id', 'username', 'nama_lengkap', 'role']


class LaporanKerusakanSerializer(serializers.ModelSerializer):
    """Serializer untuk list dan detail laporan"""
    
    foto_bukti = FotoBuktiSerializer(many=True, read_only=True)
    pelapor_info = serializers.SerializerMethodField()
    pengirim_username = serializers.SerializerMethodField()
    nama_lengkap = serializers.SerializerMethodField()
    foto_pendukung = serializers.SerializerMethodField()
    
    class Meta:
        model = LaporanKerusakan
        fields = [
            'id', 'no_laporan', 'judul', 'deskripsi', 'lokasi',
            'tanggal_kejadian', 'status', 'catatan_admin',
            'anonimitas', 'pelapor_info', 'pengirim_username', 'nama_lengkap',
            'tanggal_laporan', 'updated_at', 'foto_bukti', 'foto_pendukung'
        ]
        read_only_fields = [
            'id', 'no_laporan', 'tanggal_laporan', 'updated_at'
        ]
    
    def get_pelapor_info(self, obj):
        """Return pelapor info or 'Anonim dari Kelas XX' based on anonimitas setting"""
        if obj.anonimitas:
            kelas = obj.pelapor.kelas or '-'
            return {
                'nama_lengkap': f'Anonim dari Kelas {kelas}',
                'kelas': kelas,
                'role': obj.pelapor.role
            }
        return {
            'id': str(obj.pelapor.id),
            'username': obj.pelapor.username,
            'nama_lengkap': obj.pelapor.nama_lengkap,
            'role': obj.pelapor.role
        }
    
    def get_pengirim_username(self, obj):
        """Return username jika tidak anonim, None jika anonim"""
        if obj.anonimitas:
            return None
        return obj.pelapor.username if obj.pelapor else None
    
    def get_nama_lengkap(self, obj):
        """Return nama lengkap or 'Anonim dari Kelas XX' if anonim"""
        if obj.anonimitas:
            kelas = obj.pelapor.kelas or '-'
            return f'Anonim dari Kelas {kelas}'
        return obj.pelapor.nama_lengkap if obj.pelapor else None
    
    def get_foto_pendukung(self, obj):
        """Return URL foto pendukung"""
        request = self.context.get('request')
        foto_list = []
        for foto in obj.foto_bukti.all():
            if foto.foto and hasattr(foto.foto, 'url'):
                url = request.build_absolute_uri(foto.foto.url) if request else foto.foto.url
                foto_list.append(url)
        return foto_list if foto_list else None


class CreateLaporanKerusakanSerializer(serializers.ModelSerializer):
    """Serializer untuk create laporan kerusakan"""
    
    foto_bukti = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
        max_length=5
    )
    
    class Meta:
        model = LaporanKerusakan
        fields = [
            'judul', 'deskripsi', 'lokasi', 'tanggal_kejadian',
            'anonimitas', 'foto_bukti'
        ]
    
    def validate_foto_bukti(self, value):
        """Validate foto bukti (max 5 files, max 5MB each)"""
        if len(value) > 5:
            raise serializers.ValidationError("Maksimal 5 foto")
        
        for foto in value:
            if foto.size > 5 * 1024 * 1024:  # 5MB
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
        """Create laporan with foto bukti"""
        foto_bukti_list = validated_data.pop('foto_bukti', [])
        pelapor = self.context['request'].user
        
        # Create laporan
        laporan = LaporanKerusakan.objects.create(
            pelapor=pelapor,
            **validated_data
        )
        
        # Create foto bukti
        for foto in foto_bukti_list:
            FotoBuktiPendukung.objects.create(
                laporan=laporan,
                foto=foto
            )
        
        return laporan
