"""
Views module for the laporan_periodik application.

Contains API views for retrieving and filtering periodic reports with
summary statistics across multiple report types, and PDF export functionality.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.utils.dateparse import parse_date
from django.http import FileResponse, HttpResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, date
import logging

from laporan_bullying.models import LaporanBullying
from laporan_kerusakan.models import LaporanKerusakan
from .serializers import AggregatedReportSerializer, LaporanPeriodikResponseSerializer
from .pdf_utils import generate_report_pdf
from akun.decorators import role_required
from core.authentication import CookieJWTAuthentication

logger = logging.getLogger(__name__)


class LaporanPeriodikView(APIView):
    """
    API View for retrieving aggregated periodic reports.
    
    Provides access to combined reports from Bullying, Kerusakan, and Aspirasi
    modules, with summary statistics and filtering by date range.
    Accessible only by authenticated Kemahasiswaan staff.
    """
    
    permission_classes = [IsAuthenticated]

    @role_required()
    def get(self, request):
        """
        Handles GET requests to retrieve periodic reports.
        
        Query Parameters:
            - start_date (str): Start date in YYYY-MM-DD format. Defaults to first day of current month.
            - end_date (str): End date in YYYY-MM-DD format. Defaults to today.
            - kategori_laporan (str): Filter by report type - 'bullying' or 'kerusakan'. Optional.
            
        Returns:
            Response:
                - 200 OK with aggregated reports and summary statistics
                - 400 Bad Request if start_date > end_date or invalid date format
        """

        # Parse date parameters
        today = date.today()
        first_day_of_month = date(today.year, today.month, 1)
        
        start_date_param = request.query_params.get('start_date')
        end_date_param = request.query_params.get('end_date')
        kategori_param = request.query_params.get('kategori_laporan', '').lower()

        try:
            if start_date_param:
                start_date = parse_date(start_date_param)
                if start_date is None:
                    return Response(
                        {'detail': 'Format start_date tidak valid. Gunakan YYYY-MM-DD.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                start_date = first_day_of_month

            if end_date_param:
                end_date = parse_date(end_date_param)
                if end_date is None:
                    return Response(
                        {'detail': 'Format end_date tidak valid. Gunakan YYYY-MM-DD.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                end_date = today

            # Validate date range
            if start_date > end_date:
                return Response(
                    {'detail': 'start_date tidak boleh lebih besar dari end_date.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        except Exception as e:
            return Response(
                {'detail': f'Error parsing dates: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Fetch reports based on category filter
        bullying_reports = []
        kerusakan_reports = []

        if not kategori_param or kategori_param == 'bullying':
            bullying_reports = LaporanBullying.objects.filter(
                tanggal_laporan__date__gte=start_date,
                tanggal_laporan__date__lte=end_date
            ).values(
                'id',
                'judul',
                'tanggal_laporan',
                'jenis_bullying',
                'status',
                'no_laporan'
            )

        if not kategori_param or kategori_param == 'kerusakan':
            kerusakan_reports = LaporanKerusakan.objects.filter(
                tanggal_laporan__date__gte=start_date,
                tanggal_laporan__date__lte=end_date
            ).values(
                'id',
                'judul',
                'tanggal_laporan',
                'status',
                'no_laporan'
            )

        # Aggregate reports
        aggregated_reports = []

        for report in bullying_reports:
            aggregated_reports.append({
                'id': str(report['id']),
                'judul': report['judul'],
                'tanggal': report['tanggal_laporan'],
                'kategori': f"Bullying - {report['jenis_bullying']}",
                'status': report['status'],
                'no_laporan': report['no_laporan'],
                'tipe_laporan': 'bullying',
            })

        for report in kerusakan_reports:
            aggregated_reports.append({
                'id': str(report['id']),
                'judul': report['judul'],
                'tanggal': report['tanggal_laporan'],
                'kategori': 'Kerusakan Fasilitas',
                'status': report['status'],
                'no_laporan': report['no_laporan'],
                'tipe_laporan': 'kerusakan',
            })

        # Sort by date descending
        aggregated_reports.sort(key=lambda x: x['tanggal'], reverse=True)

        # Build summary statistics
        status_distribution = {}
        kategori_distribution = {}

        for report in aggregated_reports:
            # Count by status
            status_key = report['status']
            status_distribution[status_key] = status_distribution.get(status_key, 0) + 1

            # Count by kategori
            kategori_key = report['kategori']
            kategori_distribution[kategori_key] = kategori_distribution.get(kategori_key, 0) + 1

        summary = {
            'total_reports': len(aggregated_reports),
            'bullying_count': len(list(bullying_reports)),
            'kerusakan_count': len(list(kerusakan_reports)),
            'status_distribution': status_distribution,
            'kategori_distribution': kategori_distribution,
        }

        response_data = {
            'summary': summary,
            'reports': aggregated_reports,
        }

        serializer = LaporanPeriodikResponseSerializer(response_data)
        return Response(serializer.data, status=status.HTTP_200_OK)


@csrf_exempt
def laporan_periodik_export(request):
    """
    Function-based view for exporting aggregated periodic reports as PDF.
    
    Bypasses DRF to return raw PDF file without content negotiation issues.
    Requires authentication and kemahasiswaan role.
    
    Query Parameters:
        - start_date (str): Start date in YYYY-MM-DD format. Defaults to first day of current month.
        - end_date (str): End date in YYYY-MM-DD format. Defaults to today.
        - kategori_laporan (str): Filter by report type - 'bullying' or 'kerusakan'. Optional.
        
    Returns:
        HttpResponse: PDF file with appropriate headers
        JsonResponse: Error messages if validation fails
    """
    # Authenticate using JWT (from Authorization header or cookies)
    auth = CookieJWTAuthentication()
    auth_result = auth.authenticate(request)
    
    if auth_result is None:
        return HttpResponse(
            '{"error": "Autentikasi diperlukan."}',
            content_type='application/json',
            status=401
        )
    
    user, _ = auth_result
    
    # Check role
    if user.role != 'kemahasiswaan':
        return HttpResponse(
            '{"error": "Tidak ada akses."}',
            content_type='application/json',
            status=403
        )
    
    # Parse date parameters
    today = date.today()
    first_day_of_month = date(today.year, today.month, 1)
    
    start_date_param = request.GET.get('start_date')
    end_date_param = request.GET.get('end_date')
    kategori_param = request.GET.get('kategori_laporan', '').lower()

    try:
        if start_date_param:
            start_date = parse_date(start_date_param)
            if start_date is None:
                return HttpResponse(
                    '{"error": "Format start_date tidak valid. Gunakan YYYY-MM-DD."}',
                    content_type='application/json',
                    status=400
                )
        else:
            start_date = first_day_of_month

        if end_date_param:
            end_date = parse_date(end_date_param)
            if end_date is None:
                return HttpResponse(
                    '{"error": "Format end_date tidak valid. Gunakan YYYY-MM-DD."}',
                    content_type='application/json',
                    status=400
                )
        else:
            end_date = today

        # Validate date range
        if start_date > end_date:
            return HttpResponse(
                '{"error": "start_date tidak boleh lebih besar dari end_date."}',
                content_type='application/json',
                status=400
            )

    except Exception as e:
        logger.error(f"Error parsing dates: {str(e)}")
        return HttpResponse(
            f'{{"error": "Error parsing dates: {str(e)}"}}',
            content_type='application/json',
            status=400
        )

    try:
        # Fetch reports based on category filter
        bullying_reports = []
        kerusakan_reports = []

        if not kategori_param or kategori_param == 'bullying':
            bullying_reports = LaporanBullying.objects.filter(
                tanggal_laporan__date__gte=start_date,
                tanggal_laporan__date__lte=end_date
            ).values(
                'id',
                'judul',
                'tanggal_laporan',
                'jenis_bullying',
                'status',
                'no_laporan'
            ).order_by('-tanggal_laporan')

        if not kategori_param or kategori_param == 'kerusakan':
            kerusakan_reports = LaporanKerusakan.objects.filter(
                tanggal_laporan__date__gte=start_date,
                tanggal_laporan__date__lte=end_date
            ).values(
                'id',
                'judul',
                'tanggal_laporan',
                'status',
                'no_laporan'
            ).order_by('-tanggal_laporan')

        # Aggregate reports
        aggregated_reports = []

        for report in bullying_reports:
            aggregated_reports.append({
                'id': str(report['id']),
                'judul': report['judul'],
                'tanggal': report['tanggal_laporan'],
                'kategori': f"Bullying {report['jenis_bullying']}",
                'status': report['status'],
                'no_laporan': report['no_laporan'],
                'tipe_laporan': 'bullying',
            })

        for report in kerusakan_reports:
            aggregated_reports.append({
                'id': str(report['id']),
                'judul': report['judul'],
                'tanggal': report['tanggal_laporan'],
                'kategori': 'Kerusakan Fasilitas',
                'status': report['status'],
                'no_laporan': report['no_laporan'],
                'tipe_laporan': 'kerusakan',
            })

        # Sort by date descending
        aggregated_reports.sort(key=lambda x: x['tanggal'], reverse=True)

        # Build summary statistics
        status_distribution = {}
        kategori_distribution = {}

        for report in aggregated_reports:
            # Count by status
            status_key = report['status']
            status_distribution[status_key] = status_distribution.get(status_key, 0) + 1

            # Count by kategori
            kategori_key = report['kategori']
            kategori_distribution[kategori_key] = kategori_distribution.get(kategori_key, 0) + 1

        summary = {
            'total_reports': len(aggregated_reports),
            'bullying_count': len(list(bullying_reports)),
            'kerusakan_count': len(list(kerusakan_reports)),
            'status_distribution': status_distribution,
            'kategori_distribution': kategori_distribution,
        }

        # Generate PDF
        pdf_bytes, filename = generate_report_pdf(
            reports=aggregated_reports,
            summary=summary,
            start_date=start_date,
            end_date=end_date,
            base_dir=settings.BASE_DIR
        )

        # Return PDF directly as HttpResponse (bypassing DRF)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Access-Control-Allow-Origin'] = '*'
        return response

    except Exception as e:
        logger.error(f"PDF generation error: {str(e)}")
        return HttpResponse(
            f'{{"error": "Gagal membuat laporan. Error: {str(e)}"}}',
            content_type='application/json',
            status=500
        )
