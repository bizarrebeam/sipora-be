"""
PDF utilities for generating periodic report exports using ReportLab.

Pure Python PDF generation - no system dependencies required.
Handles PDF generation with school header, report tables, and statistics.
"""

import os
from datetime import datetime
from io import BytesIO
from typing import List, Dict, Any

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


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
    month_name = get_month_name_indonesian(start_date.month)
    year = start_date.year
    
    return f"Laporan_Bulanan_{month_name}_{year}.pdf"


def format_status(status: str) -> str:
    """
    Format status code to display text with proper capitalization.
    
    Args:
        status: Status code/string
        
    Returns:
        Formatted status text
    """
    status_map = {
        'menunggu': 'Menunggu',
        'menunggu_konfirmasi_selesai': 'Menunggu Konfirmasi Selesai',
        'diproses': 'Diproses',
        'selesai': 'Selesai',
        'ditolak': 'Ditolak',
        'ditandai': 'Ditandai',
    }
    
    status_lower = str(status).lower().strip() if status else ''
    return status_map.get(status_lower, status_lower.title() if status_lower else '-')


def generate_report_pdf(
    reports: List[Dict[str, Any]],
    summary: Dict[str, Any],
    start_date: datetime,
    end_date: datetime,
    base_dir: str = None,
) -> tuple[bytes, str]:
    """
    Generate PDF report with school header, reports table, and statistics.
    
    Uses ReportLab for pure Python PDF generation (no system dependencies).
    
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
    try:
        if base_dir is None:
            from django.conf import settings
            base_dir = settings.BASE_DIR
        
        # Create PDF buffer
        pdf_buffer = BytesIO()
        
        # Create PDF document
        doc = SimpleDocTemplate(
            pdf_buffer,
            pagesize=A4,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch,
        )
        
        # Get styles
        styles = getSampleStyleSheet()
        
        # Define custom styles
        header_school_name = ParagraphStyle(
            'HeaderSchoolName',
            parent=styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor('#333333'),
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        header_small = ParagraphStyle(
            'HeaderSmall',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#000000'),
            alignment=TA_CENTER,
        )
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=6,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#333333'),
            spaceAfter=10,
            alignment=TA_LEFT,
            fontName='Helvetica-Bold'
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#333333'),
            spaceAfter=4,
            alignment=TA_LEFT,
        )
        
        period_style = ParagraphStyle(
            'PeriodStyle',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#555555'),
            alignment=TA_CENTER,
            spaceAfter=0,
        )
        
        # Build story (document elements)
        story = []
        
        # Header with Logo
        logo_path = os.path.join(base_dir, 'static', 'images', 'logo_dp.png')
        
        # School info text - centered
        school_info_text = f"""<font color="black"><b>YAYASAN BUDI MULIA LOURDES</b><br/>
        Unit<br/>
        <b style="font-size: 12">SMP DESA PUTERA</b><br/>
        STATUS : TERAKREDITASI "A"<br/>
        NPSN : 20106947 &nbsp;&nbsp;&nbsp; NPYP : AH9883<br/>
        Jalan Desa Putera, Srengseng Sawah, Jagakarsa, Jakarta Selatan - 12640 Telp. (021)-7867202<br/>
        e-mail : [REDACTED EMAIL] website : https://www.smpdesaputera.com</font>
        """
        
        # Create a table for the header to handle centering properly within margins
        # We'll use a single column table that spans the full width of the margins
        header_table = Table([[Paragraph(school_info_text, header_small)]], colWidths=[7.0*inch])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))

        # Special handling for Logo: We'll put it in a separate table but 
        # use a negative spacer or overlap technique that doesn't push the text off-center
        if os.path.exists(logo_path):
            try:
                logo_img = Image(logo_path, width=0.7*inch, height=0.905*inch)
                logo_img.hAlign = 'LEFT'
                
                # We place the logo first
                story.append(logo_img)
                # Move the cursor back up by the height of the logo to overlay the text
                story.append(Spacer(1, -0.905*inch))
            except Exception:
                pass

        story.append(header_table)
        story.append(Spacer(1, 0.14*inch))
        
        # Header line (3px solid black border)
        line_table = Table([['']],  colWidths=[7*inch])
        line_table.setStyle(TableStyle([
            ('LINEBELOW', (0, 0), (-1, -1), 3, colors.HexColor('#000000')),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(line_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Title
        story.append(Paragraph("LAPORAN PERIODIK", title_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Date range
        story.append(Paragraph(
            f"<b>Periode:</b> {format_date_indonesian(start_date)} - {format_date_indonesian(end_date)}",
            period_style
        ))
        story.append(Spacer(1, 0.3*inch))
        
        # Summary statistics
        story.append(Paragraph("<b>Ringkasan Statistik</b>", heading_style))
        
        summary_data = [
            ['Deskripsi', 'Jumlah'],
            ['Total Laporan', str(summary.get('total_reports', 0))],
            ['Laporan Bullying', str(summary.get('bullying_count', 0))],
            ['Laporan Kerusakan', str(summary.get('kerusakan_count', 0))],
        ]
        
        summary_table = Table(summary_data, colWidths=[3.5*inch, 1.5*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f5f5f5')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cccccc')),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
        ]))
        
        story.append(summary_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Reports detail
        if reports:
            story.append(Paragraph("<b>Rincian Laporan</b>", heading_style))
            
            # Build reports table
            reports_data = [
                ['No. Laporan', 'Judul', 'Kategori', 'Tanggal', 'Status']
            ]
            
            for idx, report in enumerate(reports, 1):
                reports_data.append([
                    str(idx),
                    str(report.get('judul', '-'))[:30],
                    str(report.get('kategori', '-')),
                    str(report.get('tanggal', '-'))[:10],
                    format_status(report.get('status', '-')),
                ])
            
            reports_table = Table(
                reports_data,
                colWidths=[0.7*inch, 2.0*inch, 1.8*inch, 1.3*inch, 1.7*inch]
            )
            reports_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('ALIGN', (4, 0), (4, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ffffff')),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cccccc')),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
            ]))
            
            story.append(reports_table)
        else:
            story.append(Paragraph("Tidak ada laporan untuk periode ini.", normal_style))
        
        # Footer - Signature space and print date
        story.append(Spacer(1, 0.5*inch))
        
        # Signature section
        footer_right_style = ParagraphStyle(
            'FooterRightStyle',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#333333'),
            alignment=TA_CENTER,
        )
        
        footer_left_style = ParagraphStyle(
            'FooterLeftStyle',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#333333'),
            alignment=TA_LEFT,
        )
        
        # Print date footer
        today_date = format_date_indonesian(datetime.today())
        story.append(Paragraph(f"Jakarta, {today_date}", footer_left_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Signature line
        story.append(Paragraph("Staff Kemahasiswaan", footer_right_style))
        story.append(Spacer(1, 1.8*inch))
        story.append(Paragraph("_____________________", footer_right_style))
        
        # Build PDF
        doc.build(story)
        
        # Get PDF bytes
        pdf_bytes = pdf_buffer.getvalue()
        pdf_buffer.close()
        
        # Generate filename
        filename = generate_pdf_filename(start_date, end_date)
        
        return pdf_bytes, filename
        
    except Exception as e:
        raise Exception(f"PDF generation failed: {str(e)}")
