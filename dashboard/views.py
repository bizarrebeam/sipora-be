"""
Views module for the dashboard application.

Contains API views to aggregate and retrieve statistical metrics, trends, 
and differences for various dashboard interfaces (Bullying, Kerusakan, and Aspirasi).
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.utils.dateparse import parse_date
from django.db.models import Count
from datetime import datetime, date, timedelta

from laporan_bullying.models import LaporanBullying
from laporan_kerusakan.models import LaporanKerusakan
from aspirasi.models import Aspirasi
from .serializer import ( DashboardBullyingSerializer, DashboardKerusakanAspirasiSerializer,)

class DashboardBullyingView(APIView):
    """
    API View for retrieving Bullying Report dashboard metrics.
    
    Provides aggregated data including total reports, completion status, 
    types of bullying, top locations, and reporting trends based on a specific period.
    Accessible only by authenticated users.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Handles GET requests to calculate and return metrics for the Bullying dashboard.
        
        Args:
            request (Request): The API request object containing query parameters:
                - period (str): The time filter ('week', 'month', 'semester'). Defaults to 'week'.
                - year (int): The selected year. Defaults to current year.
                - semester (int): The selected semester (1 or 2). Defaults to 1.
                
        Returns:
            Response: 
                - 200 OK with serialized dashboard metrics, trend data, and status breakdowns.
                - 400 Bad Request if an error occurs during date parsing or calculation.
        """

        period = request.query_params.get('period', 'week')
        year = int(request.query_params.get('year', datetime.now().year))
        semester = int(request.query_params.get('semester', 1))

        base_qs = LaporanBullying.objects.all()

        labels = []
        data_points = []
        qs_current = base_qs.none()
        qs_prev = base_qs.none()

        try:
            if period == 'semester':
                # semester 1: Jul-Dec (Ganjil), semester 2: Jan-Jun (Genap)
                if semester == 1:
                    start = date(year, 7, 1)
                    end = date(year, 12, 31)
                    prev_start = date(year, 1, 1)
                    prev_end = date(year, 6, 30)
                else:
                    start = date(year, 1, 1)
                    end = date(year, 6, 30)
                    prev_start = date(year - 1, 7, 1)
                    prev_end = date(year - 1, 12, 31)

                qs_current = base_qs.filter(tanggal_kejadian__range=(start, end))
                qs_prev = base_qs.filter(tanggal_kejadian__range=(prev_start, prev_end))

                cur = start
                while cur <= end:
                    labels.append(cur.strftime('%b %Y'))
                    month_start = cur.replace(day=1)
                    next_month = (month_start + timedelta(days=32)).replace(day=1)
                    data_points.append(
                        base_qs.filter(tanggal_kejadian__gte=month_start, tanggal_kejadian__lt=next_month).count()
                    )
                    cur = next_month

            elif period == 'month':
                month_str = request.query_params.get('month') or datetime.now().strftime('%Y-%m')
                y, m = [int(x) for x in month_str.split('-')]
                start = date(y, m, 1)
                next_month = (start + timedelta(days=32)).replace(day=1)
                end = next_month - timedelta(days=1)

                prev_end = start - timedelta(days=1)
                prev_start = prev_end.replace(day=1)

                qs_current = base_qs.filter(tanggal_kejadian__range=(start, end))
                qs_prev = base_qs.filter(tanggal_kejadian__range=(prev_start, prev_end))

                cur = start
                while cur <= end:
                    labels.append(cur.strftime('%d %b'))
                    data_points.append(base_qs.filter(tanggal_kejadian=cur).count())
                    cur = cur + timedelta(days=1)

            elif period == 'week':
                start_str = request.query_params.get('start_date')
                if start_str:
                    start = parse_date(start_str)
                else:
                    today = date.today()
                    start = today - timedelta(days=today.weekday())

                end = start + timedelta(days=6)
                prev_start = start - timedelta(days=7)
                prev_end = end - timedelta(days=7)

                qs_current = base_qs.filter(tanggal_kejadian__range=(start, end))
                qs_prev = base_qs.filter(tanggal_kejadian__range=(prev_start, prev_end))

                cur = start
                while cur <= end:
                    labels.append(cur.strftime('%a %d'))
                    data_points.append(base_qs.filter(tanggal_kejadian=cur).count())
                    cur = cur + timedelta(days=1)

            else:
                # default: last 6 months
                end = date.today()
                start = end - timedelta(days=180)
                prev_start = start - timedelta(days=180)
                prev_end = start - timedelta(days=1)

                qs_current = base_qs.filter(tanggal_kejadian__range=(start, end))
                qs_prev = base_qs.filter(tanggal_kejadian__range=(prev_start, prev_end))

                cur = start.replace(day=1)
                while cur <= end:
                    labels.append(cur.strftime('%b %Y'))
                    month_start = cur
                    next_month = (month_start + timedelta(days=32)).replace(day=1)
                    data_points.append(
                        base_qs.filter(tanggal_kejadian__gte=month_start, tanggal_kejadian__lt=next_month).count()
                    )
                    cur = next_month

        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


        def get_metrics(queryset):
            return {
                'total': queryset.count(),
                'selesai': queryset.filter(status='selesai').count(),
                'diproses': queryset.filter(status='diproses').count(),
                'belum_selesai': queryset.exclude(status__in=['menunggu', 'diproses', 'menunggu_konfirmasi_selesai']).count()
            }

        curr_metrics = get_metrics(qs_current)
        prev_metrics = get_metrics(qs_prev)

        def calc_diff(curr, prev):
            return curr - prev

        differences = {
            'total': calc_diff(curr_metrics['total'], prev_metrics['total']),
            'selesai': calc_diff(curr_metrics['selesai'], prev_metrics['selesai']),
            'diproses': calc_diff(curr_metrics['diproses'], prev_metrics['diproses']),
            'belum_selesai': calc_diff(curr_metrics['belum_selesai'], prev_metrics['belum_selesai']),
        }

        status_counts = qs_current.values('status').annotate(count=Count('id'))
        by_status = {s['status']: s['count'] for s in status_counts}

        jenis_counts = qs_current.values('jenis_bullying').annotate(count=Count('id'))
        by_jenis = {j['jenis_bullying']: j['count'] for j in jenis_counts}

        loc_qs = qs_current.values('lokasi').annotate(count=Count('id')).order_by('-count')[:5]
        top_locations = [{'label': l.get('lokasi') or 'Unknown', 'count': l.get('count', 0)} for l in loc_qs]

        class_qs = qs_current.values('pelapor__kelas').annotate(count=Count('id')).order_by('-count')[:5]
        top_classes = [{'label': c.get('pelapor__kelas') or 'Unknown', 'count': c.get('count', 0)} for c in class_qs]

        payload = {
            'metrics': curr_metrics,
            'differences': differences,
            'by_status': by_status,
            'by_jenis': by_jenis,
            'top_locations': top_locations,
            'top_classes': top_classes,
            'trend': {'labels': labels, 'series': [{'name': 'Laporan', 'data': data_points}]},
        }

        serializer = DashboardBullyingSerializer(payload)
        return Response({'status': 'success', 'message': 'OK', 'data': serializer.data})


class DashboardKerusakanAspirasiView(APIView):
    """
    API View for retrieving combined dashboard metrics for Laporan Kerusakan and Aspirasi.
    
    Provides statistical summaries, trend comparisons, and category distributions 
    specifically for facility damages and student aspirations.
    Accessible only by authenticated users.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Handles GET requests to return aggregated data for Kerusakan and Aspirasi.
        
        Args:
            request (Request): The API request object containing query parameters:
                - period (str): 'week', 'month', or 'semester'. Defaults to 'week'.
                - year (int): Target year. Defaults to current year.
                - semester (int): Target semester. Defaults to 1.
                
        Returns:
            Response: 
                - 200 OK with combined metrics (totals, unfinished reports, flagged aspirations),
                  trend charts, and category distributions.
                - 400 Bad Request if date parsing or filtering fails.
        """
        period = request.query_params.get('period', 'week')
        year = int(request.query_params.get('year', datetime.now().year))
        semester = int(request.query_params.get('semester', 1))

        k_qs = LaporanKerusakan.objects.all()
        a_qs = Aspirasi.objects.all()

        labels = []
        kerusakan_points = []
        qs_k = k_qs.none()
        start = date.today()
        end = date.today()

        try:
            if period == 'week':
                today = date.today()
                start = today - timedelta(days=today.weekday())
                end = start + timedelta(days=6)
                qs_k = k_qs.filter(tanggal_kejadian__range=(start, end))
                cur = start
                while cur <= end:
                    labels.append(cur.strftime('%a %d'))
                    kerusakan_points.append(qs_k.filter(tanggal_kejadian=cur).count())
                    cur = cur + timedelta(days=1)

            elif period == 'month':
                month_str = request.query_params.get('month') or datetime.now().strftime('%Y-%m')
                y, m = [int(x) for x in month_str.split('-')]
                start = date(y, m, 1)
                next_month = (start + timedelta(days=32)).replace(day=1)
                end = next_month - timedelta(days=1)
                qs_k = k_qs.filter(tanggal_kejadian__range=(start, end))
                cur = start
                while cur <= end:
                    labels.append(cur.strftime('%d %b'))
                    kerusakan_points.append(qs_k.filter(tanggal_kejadian=cur).count())
                    cur = cur + timedelta(days=1)

            else:
                # semester or fallback
                if period == 'semester':
                    if semester == 1:
                        start = date(year, 7, 1)
                        end = date(year, 12, 31)
                    else:
                        start = date(year, 1, 1)
                        end = date(year, 6, 30)
                else:
                    end = date.today()
                    start = end - timedelta(days=30)

                qs_k = k_qs
                cur = start.replace(day=1)
                while cur <= end:
                    labels.append(cur.strftime('%b %Y'))
                    month_start = cur
                    next_month = (month_start + timedelta(days=32)).replace(day=1)
                    kerusakan_points.append(qs_k.filter(tanggal_kejadian__gte=month_start, tanggal_kejadian__lt=next_month).count())
                    cur = next_month

        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Filter aspirasi by the computed start/end when possible
        try:
            a_qs_filtered = a_qs.filter(tanggal_aspirasi__date__range=(start, end))
        except Exception:
            a_qs_filtered = a_qs

        kerusakan_total = qs_k.count()
        kerusakan_belum = qs_k.exclude(status__in=['menunggu', 'diproses', 'menunggu_konfirmasi_selesai']).count()
        aspirasi_total = a_qs_filtered.count()
        aspirasi_ditandai = a_qs_filtered.filter(status_ditandai='ditandai').count()

        # compute previous-period ranges and differences
        try:
            period_days = (end - start).days + 1
            prev_end = start - timedelta(days=1)
            prev_start = prev_end - timedelta(days=period_days - 1)

            qs_k_prev = k_qs.filter(tanggal_kejadian__range=(prev_start, prev_end))
            prev_kerusakan_total = qs_k_prev.count()
            prev_kerusakan_belum = qs_k_prev.exclude(status__in=['selesai', 'dibatalkan', 'ditolak']).count()

            a_qs_prev = a_qs.filter(tanggal_aspirasi__date__range=(prev_start, prev_end))
            prev_aspirasi_total = a_qs_prev.count()
            prev_aspirasi_ditandai = a_qs_prev.filter(status_ditandai='ditandai').count()
        except Exception:
            prev_kerusakan_total = 0
            prev_kerusakan_belum = 0
            prev_aspirasi_total = 0
            prev_aspirasi_ditandai = 0

        differences = {
            'total': kerusakan_total - prev_kerusakan_total,
            'belum_selesai': kerusakan_belum - prev_kerusakan_belum,
            'aspirasi_total': aspirasi_total - prev_aspirasi_total,
            'ditandai': aspirasi_ditandai - prev_aspirasi_ditandai,
        }

        kategori_qs = a_qs_filtered.values('kategori').annotate(count=Count('id')).order_by('-count')
        aspirasi_distribution = [(k['kategori'], k['count']) for k in kategori_qs]

        payload = {
            'metrics': {
                'kerusakan_total': kerusakan_total,
                'kerusakan_belum_selesai': kerusakan_belum,
                'aspirasi_total': aspirasi_total,
                'aspirasi_ditandai': aspirasi_ditandai,
            },
            'differences': differences,
            'by_status_kerusakan': {s['status']: s['count'] for s in qs_k.values('status').annotate(count=Count('id'))},
            'kerusakan_trend': {'labels': labels, 'series': [{'name': 'Kerusakan', 'data': kerusakan_points}]},
            'aspirasi_distribution': {'categories': [c for c, _ in aspirasi_distribution], 'counts': [n for _, n in aspirasi_distribution]},
        }

        serializer = DashboardKerusakanAspirasiSerializer(payload)
        return Response({'status': 'success', 'message': 'OK', 'data': serializer.data})