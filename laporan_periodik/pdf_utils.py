"""
PDF utilities for generating periodic report exports using WeasyPrint.

Handles PDF generation with school header, report tables, and statistics.
"""

import os
from datetime import datetime
from io import BytesIO
from typing import List, Dict, Any

from django.template.loader import render_to_string


def get_month_name_indonesian(month: int) -> str:
    """
    Convert month number to Indonesian month name.
    
    Args:
        month: Month number (1-12)
        
    Returns:
        Indonesian month name
    """
    month_names = {
        1: 'Januari',
        2: 'Februari',
        3: 'Maret',
        4: 'April',
        5: 'Mei',
        6: 'Juni',
        7: 'Juli',
        8: 'Agustus',
        9: 'September',
        10: 'Oktober',
        11: 'November',
        12: 'Desember',
    }
    return month_names.get(month, '')


def format_date_indonesian(date_obj: datetime) -> str:
    """
    Format datetime object to Indonesian date string.
    
    Args:
        date_obj: datetime object
        
    Returns:
        Formatted date string (e.g., "12 Januari 2026")
    """
    month_name = get_month_name_indonesian(date_obj.month)
    return f"{date_obj.day} {month_name} {date_obj.year}"


def generate_pdf_filename(start_date: datetime, end_date: datetime) -> str:
    """
    Generate dynamic PDF filename based on date range.
    
    Args:
        start_date: Start date of report period
        end_date: End date of report period
        
    Returns:
        Filename in format: Laporan_Bulanan_[Bulan]_[Tahun].pdf
    """
    # Use start month for single-month reports, otherwise use range
    month_name = get_month_name_indonesian(start_date.month)
    year = start_date.year
    
    return f"Laporan_Bulanan_{month_name}_{year}.pdf"


def generate_report_pdf(
    reports: List[Dict[str, Any]],
    summary: Dict[str, Any],
    start_date: datetime,
    end_date: datetime,
    base_dir: str = None,
) -> tuple[bytes, str]:
    """
    Generate PDF report with school header, reports table, and statistics.
    
    Args:
        reports: List of report dictionaries
        summary: Summary statistics dictionary
        start_date: Start date of report period
        end_date: End date of report period
        base_dir: Base directory for Django static files
        
    Returns:
        Tuple of (PDF bytes, filename)
        
    Raises:
        Exception: If PDF generation fails
    """
    # Import WeasyPrint lazily to avoid blocking Django startup
    try:
        # Set up library paths for macOS Homebrew installations
        import sys
        if sys.platform == 'darwin':  # macOS
            homebrew_lib = '/opt/homebrew/lib'
            if os.path.exists(homebrew_lib):
                os.environ['DYLD_LIBRARY_PATH'] = homebrew_lib + ':' + os.environ.get('DYLD_LIBRARY_PATH', '')
        
        from weasyprint import HTML
    except ImportError as e:
        raise Exception(
            f"WeasyPrint is not installed or missing system dependencies. "
            f"Please install system dependencies: {str(e)}"
        )
    
    if base_dir is None:
        from django.conf import settings
        base_dir = settings.BASE_DIR
    
    # Prepare context for template
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'start_date_formatted': format_date_indonesian(start_date),
        'end_date_formatted': format_date_indonesian(end_date),
        'month_name': get_month_name_indonesian(start_date.month),
        'year': start_date.year,
        'reports': reports,
        'summary': summary,
        'has_reports': len(reports) > 0,
        'logo_path': os.path.join(base_dir, 'static', 'images', 'logo_dp.png'),
        'current_date': format_date_indonesian(datetime.today()),
    }
    
    # Render HTML template
    html_content = render_to_string('laporan_periodik/pdf_report.html', context)
    
    # Render CSS
    css_file = os.path.join(
        os.path.dirname(__file__),
        'templates',
        'laporan_periodik',
        'pdf_report.css'
    )
    
    # Create PDF
    try:
        # Generate PDF document using modern WeasyPrint API
        pdf_document = HTML(string=html_content)
        
        # Write to bytes
        pdf_bytes = pdf_document.write_pdf()
        
        # Generate filename
        filename = generate_pdf_filename(start_date, end_date)
        
        return pdf_bytes, filename
        
    except Exception as e:
        raise Exception(f"PDF generation failed: {str(e)}")
