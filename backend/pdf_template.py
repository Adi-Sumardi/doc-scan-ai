"""
Enhanced PDF Template Generator
Professional PDF templates with logo, watermark, headers, and footers
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List
from pathlib import Path

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.platypus.flowables import HRFlowable
from reportlab.pdfgen import canvas

logger = logging.getLogger(__name__)

# Import FakturPajakExporter for Smart Mapper data conversion
try:
    from exporters.faktur_pajak_exporter import FakturPajakExporter
except ImportError:
    # Fallback if import fails
    FakturPajakExporter = None
    logger.warning("⚠️ FakturPajakExporter not available, Smart Mapper features disabled")


class PDFHeader(object):
    """Custom PDF header with logo and title"""
    
    def __init__(self, title: str, subtitle: str = None, logo_path: str = None):
        self.title = title
        self.subtitle = subtitle
        self.logo_path = logo_path
    
    def __call__(self, canvas_obj, doc):
        """Draw header on every page"""
        canvas_obj.saveState()
        
        # Logo
        if self.logo_path and Path(self.logo_path).exists():
            try:
                canvas_obj.drawImage(self.logo_path, 0.5*inch, doc.height + 1.5*inch, width=0.8*inch, height=0.8*inch, preserveAspectRatio=True)
            except Exception as e:
                logger.warning(f"⚠️ Failed to add logo to PDF: {e}")
        
        # Title
        canvas_obj.setFont('Helvetica-Bold', 16)
        canvas_obj.setFillColor(colors.HexColor('#1F4E78'))
        canvas_obj.drawString(1.5*inch, doc.height + 1.8*inch, self.title)
        
        # Subtitle
        if self.subtitle:
            canvas_obj.setFont('Helvetica', 10)
            canvas_obj.setFillColor(colors.HexColor('#666666'))
            canvas_obj.drawString(1.5*inch, doc.height + 1.6*inch, self.subtitle)
        
        # Line
        canvas_obj.setStrokeColor(colors.HexColor('#4472C4'))
        canvas_obj.setLineWidth(2)
        canvas_obj.line(0.5*inch, doc.height + 1.4*inch, doc.width + 0.5*inch, doc.height + 1.4*inch)
        
        # Footer
        canvas_obj.setFont('Helvetica', 8)
        canvas_obj.setFillColor(colors.HexColor('#999999'))
        footer_text = f"Generated on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} | Doc-Scan AI System | Page {doc.page}"
        canvas_obj.drawString(0.5*inch, 0.5*inch, footer_text)
        
        canvas_obj.restoreState()


class EnhancedPDFTemplate:
    """
    Create professional PDF templates with advanced styling
    """
    
    def __init__(self):
        self.elements = []
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1F4E78'),
            spaceAfter=12,
            alignment=1  # Center
        ))
        
        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#4472C4'),
            spaceAfter=12,
            alignment=1  # Center
        ))
        
        # Section header
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1F4E78'),
            spaceAfter=6,
            spaceBefore=12,
            borderColor=colors.HexColor('#4472C4'),
            borderWidth=0,
            borderPadding=5,
            backColor=colors.HexColor('#F2F2F2')
        ))
        
        # Info text
        self.styles.add(ParagraphStyle(
            name='InfoText',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#333333'),
            spaceAfter=4
        ))
    
    def add_title(self, title: str):
        """Add main title"""
        self.elements.append(Paragraph(title, self.styles['CustomTitle']))
        self.elements.append(Spacer(1, 0.2*inch))
    
    def add_subtitle(self, subtitle: str):
        """Add subtitle"""
        self.elements.append(Paragraph(subtitle, self.styles['CustomSubtitle']))
        self.elements.append(Spacer(1, 0.2*inch))
    
    def add_section_header(self, header: str):
        """Add section header"""
        self.elements.append(Spacer(1, 0.1*inch))
        self.elements.append(Paragraph(f"<b>{header}</b>", self.styles['SectionHeader']))
        self.elements.append(Spacer(1, 0.1*inch))
    
    def add_info_table(self, info: Dict[str, str]):
        """Add information table"""
        data = []
        for label, value in info.items():
            data.append([f"<b>{label}</b>", str(value)])
        
        table = Table(data, colWidths=[2*inch, 4*inch])
        table.setStyle(TableStyle([
            ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 10),
            ('FONT', (1, 0), (1, -1), 'Helvetica', 10),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#333333')),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#F9F9F9')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#DDDDDD'))
        ]))
        
        self.elements.append(table)
        self.elements.append(Spacer(1, 0.2*inch))
    
    def add_data_table(self, headers: List[str], data: List[List[Any]], col_widths: List[float] = None):
        """Add data table with headers"""
        # Prepare table data
        table_data = [headers] + data
        
        # Column widths
        if not col_widths:
            col_widths = [1.2*inch] * len(headers)
        
        # Create table
        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        
        # Style
        table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 10),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
            
            # Data rows
            ('FONT', (0, 1), (-1, -1), 'Helvetica', 9),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#333333')),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
            
            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F2F2F2')]),
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
            
            # Padding
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        self.elements.append(table)
        self.elements.append(Spacer(1, 0.2*inch))
    
    def add_summary_box(self, summary: Dict[str, Any]):
        """Add summary box with statistics"""
        self.add_section_header("📊 RINGKASAN")
        
        data = []
        for label, value in summary.items():
            data.append([f"<b>{label}</b>", str(value)])
        
        table = Table(data, colWidths=[3*inch, 3*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FFF9E6')),
            ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 11),
            ('FONT', (1, 0), (1, -1), 'Helvetica', 11),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#333333')),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#FFC000')),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        self.elements.append(table)
        self.elements.append(Spacer(1, 0.3*inch))
    
    def add_horizontal_line(self):
        """Add horizontal line separator"""
        self.elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#CCCCCC'), spaceBefore=0.1*inch, spaceAfter=0.1*inch))
    
    def add_page_break(self):
        """Add page break"""
        self.elements.append(PageBreak())
    
    def build(self, output_path: str, title: str, subtitle: str = None, logo_path: str = None, pagesize=A4):
        """Build and save PDF"""
        try:
            # Create document
            doc = SimpleDocTemplate(
                output_path,
                pagesize=pagesize,
                rightMargin=0.5*inch,
                leftMargin=0.5*inch,
                topMargin=2.5*inch,
                bottomMargin=1*inch
            )
            
            # Build with custom header
            header = PDFHeader(title, subtitle, logo_path)
            doc.build(self.elements, onFirstPage=header, onLaterPages=header)
            
            logger.info(f"✅ PDF file saved: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to save PDF: {e}")
            return False


# Helper function to create batch PDF export
def create_batch_pdf_export(batch_results: List[Dict[str, Any]], output_path: str, document_type: str = "faktur_pajak") -> bool:
    """
    Create professional batch PDF export
    
    Args:
        batch_results: List of processing results
        output_path: Path to save PDF file
        document_type: Type of documents
    
    Returns:
        True if successful
    """
    try:
        pdf = EnhancedPDFTemplate()
        
        # Title
        pdf.add_title(f"📄 {document_type.upper().replace('_', ' ')}")
        pdf.add_subtitle(f"Batch Processing Report | {len(batch_results)} Documents")
        
        # Info section
        info = {
            "Tanggal Export": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "Jumlah Dokumen": len(batch_results),
            "Tipe Dokumen": document_type.replace('_', ' ').title()
        }
        pdf.add_info_table(info)
        
        # Data table
        pdf.add_section_header("📋 DAFTAR DOKUMEN")
        
        if document_type == 'faktur_pajak':
            headers = ["No", "Nama Penjual", "Tgl", "NPWP", "No. Faktur", "DPP", "PPN", "Total"]
            col_widths = [0.3*inch, 1.8*inch, 0.8*inch, 1.2*inch, 1.2*inch, 0.9*inch, 0.9*inch, 0.9*inch]
            
            data = []
            faktur_exporter = FakturPajakExporter() if FakturPajakExporter else None
            
            for idx, result in enumerate(batch_results, start=1):
                extracted_data = result.get('extracted_data', {})
                
                # PRIORITY 1: Use Smart Mapper data if available (already clean from GPT-4o)
                smart_mapped = extracted_data.get('smart_mapped', {})
                if smart_mapped and faktur_exporter:
                    logger.info(f"✅ PDF Row {idx}: Using Smart Mapper GPT data (CLEAN)")
                    structured = faktur_exporter._convert_smart_mapped_to_structured(smart_mapped)
                else:
                    # FALLBACK: Use legacy structured_data with post-processing
                    logger.info(f"⚠️ PDF Row {idx}: Using legacy parser")
                    structured_data = extracted_data.get('structured_data', {})
                    if faktur_exporter:
                        structured = faktur_exporter._prepare_structured_fields(
                            structured_data,
                            extracted_data.get('raw_text', '')
                        )
                    else:
                        structured = structured_data
                
                # Format currency for display (remove "Rp" prefix, keep numbers)
                dpp_display = structured.get('dpp', 'N/A')
                ppn_display = structured.get('ppn', 'N/A')
                total_display = structured.get('total', 'N/A')
                
                data.append([
                    str(idx),
                    (structured.get('nama', 'N/A') or 'N/A')[:20],
                    (structured.get('tanggal', 'N/A') or 'N/A')[:10],
                    (structured.get('npwp', 'N/A') or 'N/A')[:15],
                    (structured.get('nomor_faktur', 'N/A') or 'N/A')[:15],
                    str(dpp_display)[:12],
                    str(ppn_display)[:12],
                    str(total_display)[:12]
                ])
        
        elif document_type == 'pph21':
            headers = ["No", "Filename", "Nomor", "Nama", "Bruto"]
            col_widths = [0.4*inch, 2.2*inch, 1.5*inch, 2*inch, 1*inch]
            
            data = []
            for idx, result in enumerate(batch_results, start=1):
                extracted_data = result.get('extracted_data', {})
                
                data.append([
                    str(idx),
                    result.get('filename', 'N/A')[:30],
                    extracted_data.get('nomor', 'N/A'),
                    extracted_data.get('identitas_penerima_penghasilan', {}).get('nama', 'N/A')[:25],
                    str(extracted_data.get('penghasilan_bruto', 0))
                ])
        
        else:
            headers = ["No", "Filename", "Type", "Confidence"]
            col_widths = [0.4*inch, 3*inch, 1.5*inch, 1*inch]
            
            data = []
            for idx, result in enumerate(batch_results, start=1):
                data.append([
                    str(idx),
                    result.get('filename', 'N/A')[:40],
                    result.get('document_type', 'N/A'),
                    f"{result.get('confidence', 0):.1%}"
                ])
        
        pdf.add_data_table(headers, data, col_widths)
        
        # Summary - REMOVED per user request
        # total_confidence = sum(r.get('confidence', 0) for r in batch_results)
        # summary = {
        #     "Total Dokumen Diproses": len(batch_results),
        #     "Rata-rata Confidence": f"{(total_confidence / len(batch_results)):.1%}" if batch_results else "0%",
        #     "Status Batch": "✓ Berhasil Diproses Semua"
        # }
        # pdf.add_summary_box(summary)
        
        # Build PDF
        return pdf.build(
            output_path,
            title=f"{document_type.upper().replace('_', ' ')} - BATCH REPORT",
            subtitle=f"{len(batch_results)} Documents Processed"
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to create batch PDF export: {e}")
        return False
