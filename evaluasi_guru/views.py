from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Evaluasi, NilaiEvaluasi, Indikator, get_tahun_ajaran, get_semester
from .serializers import IndikatorSerializer, GuruSimpleSerializer, sanitize_text
from log_aktivitas.utils import catat_log
from akun.models import MataPelajaranGuruSemester
import json
from collections import defaultdict
from rest_framework.pagination import PageNumberPagination

User = get_user_model()

class EvaluasiCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        
        # Validasi role siswa
        if user.role != "siswa":
            return Response(
                {"detail": "Menu tidak tersedia"}, 
                status=status.HTTP_404_NOT_FOUND
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

        now = timezone.now()
        tahun_ajaran = get_tahun_ajaran(now)
        semester = get_semester(now)

        if not user.kelas:
            return Response(
                {"detail": "Data kelas Anda tidak ditemukan."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        riwayat_guru = MataPelajaranGuruSemester.objects.filter(
            guru=guru,
            tahun_ajaran=tahun_ajaran,
            semester=semester
        )
        
        mengajar_di_kelas = False
        for r in riwayat_guru:
            kd = r.kelas_diajar
            if isinstance(kd, str):
                try:
                    kd = json.loads(kd)
                except Exception:
                    kd = []
            if isinstance(kd, list) and user.kelas in kd:
                mengajar_di_kelas = True
                break
                
        if not mengajar_di_kelas:
            return Response(
                {"detail": "Anda hanya dapat memberikan evaluasi kepada guru yang mengajar di kelas Anda pada semester ini."},
                status=status.HTTP_400_BAD_REQUEST
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
        if len(str(komentar)) > 0:
            komentar_str = sanitize_text(str(komentar))
            if len(komentar_str) < 20:
                return Response(
                    {"detail": "Komentar terlalu singkat."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            komentar_str = ""

        # Validasi 1 pengisian per periode
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

            # Log aktivitas
            ip = request.META.get('REMOTE_ADDR')
            catat_log(
                request.user,
                'BUAT_EVALUASI',
                f"Memberikan evaluasi untuk guru: {guru.nama_lengkap}",
                'evaluasi_guru',
                ip
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

class IndikatorListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        indikators = Indikator.objects.all().order_by('urutan')
        serializer = IndikatorSerializer(indikators, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class GuruListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        gurus = User.objects.filter(role='guru', is_verified=True).order_by('nama_lengkap')

        if user.role == 'siswa' and user.kelas:
            from akun.models import MataPelajaranGuruSemester
            from .models import get_tahun_ajaran, get_semester
            from django.utils import timezone

            now = timezone.now()
            ta = get_tahun_ajaran(now)
            sem = get_semester(now)

            # Retrieve all teaching assignments for the current semester
            riwayat = MataPelajaranGuruSemester.objects.filter(
                tahun_ajaran=ta,
                semester=sem
            )
            
            # Filter teaching assignments manually in Python to ensure compatibility across databases
            valid_guru_ids = []
            import json
            for r in riwayat:
                kd = r.kelas_diajar
                if isinstance(kd, str):
                    try:
                        kd = json.loads(kd)
                    except Exception:
                        kd = []
                if isinstance(kd, list) and user.kelas in kd:
                    valid_guru_ids.append(r.guru_id)
            
            gurus = gurus.filter(id__in=valid_guru_ids)

        serializer = GuruSimpleSerializer(gurus, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DaftarHasilEvaluasiPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class DaftarHasilEvaluasiView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if user.role not in ["kemahasiswaan", "guru"]:
            return Response(
                {"detail": "Menu tidak tersedia"}, 
                status=status.HTTP_404_NOT_FOUND
            )

        guru_name = request.query_params.get("guru", "")
        tahun_ajaran = request.query_params.get("tahun_ajaran", "")
        semester = request.query_params.get("semester", "")

        queryset = Evaluasi.objects.all()

        if user.role == "guru":
            queryset = queryset.filter(guru=user)
        elif guru_name:
            queryset = queryset.filter(guru__nama_lengkap__icontains=guru_name)

        if tahun_ajaran:
            queryset = queryset.filter(tahun_ajaran=tahun_ajaran)

        if semester:
            queryset = queryset.filter(semester__iexact=semester)

        if not queryset.exists():
            return Response([], status=status.HTTP_200_OK)

        queryset = queryset.select_related('guru', 'siswa').prefetch_related('nilai__indikator__kategori')

        grouped_data = {}

        for ev in queryset:
            key = (ev.guru.id, ev.tahun_ajaran, ev.semester)
            if key not in grouped_data:
                grouped_data[key] = {
                    "guru_id": ev.guru.id,
                    "guru_nama": ev.guru.nama_lengkap,
                    "tahun_ajaran": ev.tahun_ajaran,
                    "semester": ev.semester,
                    "total_responden": 0,
                    "komentar": [],
                    "kategori_scores": defaultdict(lambda: {"scores": [], "indikator_scores": defaultdict(list)}),
                    "all_scores": []
                }
            
            group = grouped_data[key]
            group["total_responden"] += 1
            
            if ev.komentar and str(ev.komentar).strip():
                kelas_siswa = ev.siswa.kelas if ev.siswa and getattr(ev.siswa, 'kelas', None) else "Tidak diketahui"
                group["komentar"].append({
                    "kelas": kelas_siswa,
                    "komentar": ev.komentar
                })
                
            for nilai_ev in ev.nilai.all():
                kategori = nilai_ev.indikator.kategori
                kat_id = kategori.id
                kat_nama = kategori.nama
                
                ind_id = nilai_ev.indikator.id
                ind_deskripsi = nilai_ev.indikator.deskripsi
                
                score = nilai_ev.nilai
                
                group["kategori_scores"][(kat_id, kat_nama)]["scores"].append(score)
                group["kategori_scores"][(kat_id, kat_nama)]["indikator_scores"][(ind_id, ind_deskripsi)].append(score)
                group["all_scores"].append(score)

        results = []
        for key, data in grouped_data.items():
            overall_avg = sum(data["all_scores"]) / len(data["all_scores"]) if data["all_scores"] else 0
            overall_avg = round(overall_avg, 2)
            
            detail_kategori = []
            for (kat_id, kat_nama), kat_data in data["kategori_scores"].items():
                kat_avg = sum(kat_data["scores"]) / len(kat_data["scores"]) if kat_data["scores"] else 0
                
                detail_indikator = []
                for (ind_id, ind_deskripsi), ind_scores in kat_data["indikator_scores"].items():
                    ind_avg = sum(ind_scores) / len(ind_scores) if ind_scores else 0
                    detail_indikator.append({
                        "indikator_id": ind_id,
                        "deskripsi": ind_deskripsi,
                        "rata_rata": round(ind_avg, 2)
                    })
                
                detail_indikator.sort(key=lambda x: x["indikator_id"])
                
                detail_kategori.append({
                    "kategori_id": kat_id,
                    "kategori_nama": kat_nama,
                    "rata_rata": round(kat_avg, 2),
                    "detail_indikator": detail_indikator
                })
            
            detail_kategori.sort(key=lambda x: x["kategori_id"])

            results.append({
                "guru_id": data["guru_id"],
                "guru_nama": data["guru_nama"],
                "tahun_ajaran": data["tahun_ajaran"],
                "semester": data["semester"],
                "rata_rata_rating": overall_avg,
                "total_responden": data["total_responden"],
                "detail_kategori": detail_kategori,
                "komentar": data["komentar"]
            })

        results.sort(key=lambda x: (x["guru_nama"], x["tahun_ajaran"], x["semester"]), reverse=True)

        paginator = DaftarHasilEvaluasiPagination()
        paginated_results = paginator.paginate_queryset(results, request, view=self)
        
        return paginator.get_paginated_response(paginated_results)