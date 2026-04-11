from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Evaluasi, NilaiEvaluasi, Indikator, get_tahun_ajaran, get_semester

User = get_user_model()

class EvaluasiCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        
        # Validasi role siswa
        if user.role != "siswa":
            return Response(
                {"detail": "Hanya siswa yang dapat memberikan evaluasi."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        # Validasi staff_id / guru
        staff_id = request.data.get("staff_id")
        if not staff_id or str(staff_id).strip() == "":
            return Response(
                {"detail": "Staff/Guru harus dipilih."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validasi existence guru
        try:
            guru = User.objects.get(id=staff_id, role="guru")
        except User.DoesNotExist:
            return Response(
                {"detail": "Guru tidak ditemukan."}, 
                status=status.HTTP_404_NOT_FOUND
            )

        # Validasi rating (harus array/list dari object dgn indikator_id dan nilai)
        ratings = request.data.get("rating")
        if not ratings or not isinstance(ratings, list) or len(ratings) == 0:
            return Response(
                {"detail": "Rating harus antara 1 sampai 5."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        validated_ratings = []
        for r in ratings:
            if not isinstance(r, dict):
                continue
                
            indikator_id = r.get("indikator_id")
            nilai_val = r.get("nilai")
            
            if nilai_val is None:
                return Response(
                    {"detail": "Rating harus antara 1 sampai 5."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            try:
                nilai_int = int(nilai_val)
                if nilai_int < 1 or nilai_int > 5:
                    return Response(
                        {"detail": "Rating harus antara 1 sampai 5."}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except ValueError:
                return Response(
                    {"detail": "Rating harus antara 1 sampai 5."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            if not indikator_id or not Indikator.objects.filter(id=indikator_id).exists():
                return Response(
                    {"detail": f"Indikator dengan ID {indikator_id} tidak valid."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            validated_ratings.append({
                "indikator_id": indikator_id,
                "nilai": nilai_int
            })

        # Pastikan tidak ada missing rating dari payload yg array
        if len(validated_ratings) != len(ratings):
            return Response(
                {"detail": "Terdapat komponen rating yang tidak terformat dengan benar."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validasi komentar
        komentar = request.data.get("komentar", "")
        if komentar:
            komentar_str = str(komentar).strip()
            if len(komentar_str) > 0 and len(komentar_str) < 20:
                return Response(
                    {"detail": "Komentar terlalu singkat."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            komentar_str = ""

        # Validasi 1 pengisian per periode
        now = timezone.now()
        tahun_ajaran = get_tahun_ajaran(now)
        semester = get_semester(now)

        if Evaluasi.objects.filter(siswa=user, guru=guru, tahun_ajaran=tahun_ajaran, semester=semester).exists():
            return Response(
                {"detail": "Anda sudah memberikan evaluasi untuk guru ini pada periode ini."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Proses penyimpanan
        try:
            evaluasi = Evaluasi.objects.create(
                siswa=user,
                guru=guru,
                komentar=komentar_str,
                tahun_ajaran=tahun_ajaran,
                semester=semester
            )

            for r_data in validated_ratings:
                indikator = Indikator.objects.get(id=r_data["indikator_id"])
                NilaiEvaluasi.objects.create(
                    evaluasi=evaluasi,
                    indikator=indikator,
                    nilai=r_data["nilai"]
                )

            return Response(
                {"detail": "Evaluasi berhasil disimpan."}, 
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
