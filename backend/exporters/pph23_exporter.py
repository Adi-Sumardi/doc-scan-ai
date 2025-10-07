"""
PPh23 Exporter
Handles Excel and PDF export specifically for PPh23 (Tax on Services) documents
"""

from typing import Dict, Any
from datetime import datetime
import logging

from .base_exporter import BaseExporter

logger = logging.getLogger(__name__)

# Check for required libraries
try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False
    logger.warning("⚠️ openpyxl not installed - Excel export disabled")

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False
    logger.warning("⚠️ reportlab not installed - PDF export disabled")


class PPh23Exporter(BaseExporter):
    """Exporter for PPh23 (Tax on Services) documents"""
    
    def __init__(self):
        super().__init__("pph23")
        # Columns specific to PPh23
        self.columns = [
            "Nama Wajib Pajak", "NPWP", "Tanggal", "Nomor Bukti Potong",
            "Jenis Penghasilan", "Jumlah Bruto", "Tarif", "PPh Dipotong",
            "Keterangan"
        ]
    
    def export_to_excel(self, result: Dict[str, Any], output_path: str) -> bool:
        """Export single PPh23 to Excel with structured table format"""
        try:
            if not HAS_OPENPYXL:
                logger.error("❌ openpyxl not available for Excel export")
                return False
            
            wb = Workbook()
            ws = wb.active
            ws.title = "PPh23"
            
            self._populate_excel_sheet(ws, result)
            
            wb.save(output_path)
            logger.info(f"✅ PPh23 Excel export created: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ PPh23 Excel export failed: {e}", exc_info=True)
            return False
    
    def _populate_excel_sheet(self, ws, result: Dict[str, Any]):
        """Helper to populate worksheet with structured PPh23 data"""
        # Define styles
        header_fill = PatternFill(start_color="059669", end_color="059669", fill_type="solid")  # Green
        header_font = Font(bold=True, size=11, color="FFFFFF")
        data_fill = PatternFill(start_color="d1fae5", end_color="d1fae5", fill_type="solid")  # Light green
        border_thin = Border(
            left=Side(style='thin', color='000000'),
            right=Side(style='thin', color='000000'),
            top=Side(style='thin', color='000000'),
            bottom=Side(style='thin', color='000000')
        )
        center_align = Alignment(horizontal='center', vertical='center', wrap_text=True)
        left_align = Alignment(horizontal='left', vertical='center', wrap_text=True)
        
        # Get structured data
        extracted_data = result.get('extracted_data', {})
        structured = extracted_data.get('structured_data', {})
        
        # If no structured data, try to extract from text
        if not structured or not any(structured.values()):
            raw_text = extracted_data.get('raw_text', '')
            if raw_text:
                from ai_processor import IndonesianTaxDocumentParser
                temp_parser = IndonesianTaxDocumentParser()
                structured = temp_parser.extract_structured_fields(raw_text, "pph23")
        
        row = 1
        
        # ===== TITLE =====
        ws.merge_cells(f'A{row}:I{row}')
        ws[f'A{row}'] = "📋 PPh23 - PAJAK ATAS JASA"
        ws[f'A{row}'].font = Font(bold=True, size=14, color="FFFFFF")
        ws[f'A{row}'].fill = header_fill
        ws[f'A{row}'].alignment = center_align
        ws[f'A{row}'].border = border_thin
        row += 1
        
        # ===== TABLE HEADERS =====
        for col_idx, header in enumerate(self.columns, start=1):
            cell = ws.cell(row=row, column=col_idx, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_align
            cell.border = border_thin
        row += 1
        
        # ===== DATA ROW =====
        data_row = [
            structured.get('nama_wp', 'N/A'),
            structured.get('npwp', 'N/A'),
            structured.get('tanggal', 'N/A'),
            structured.get('nomor_bukti_potong', 'N/A'),
            structured.get('jenis_penghasilan', 'N/A'),
            structured.get('jumlah_bruto', 'N/A'),
            structured.get('tarif', 'N/A'),
            structured.get('pph_dipotong', 'N/A'),
            structured.get('keterangan', 'N/A')
        ]
        
        for col_idx, value in enumerate(data_row, start=1):
            cell = ws.cell(row=row, column=col_idx, value=value)
            cell.fill = data_fill
            cell.alignment = left_align
            cell.border = border_thin
            cell.font = Font(size=10)
        
        # Auto-adjust column widths
        ws.column_dimensions['A'].width = 25  # Nama WP
        ws.column_dimensions['B'].width = 20  # NPWP
        ws.column_dimensions['C'].width = 12  # Tanggal
        ws.column_dimensions['D'].width = 20  # Nomor Bukti Potong
        ws.column_dimensions['E'].width = 30  # Jenis Penghasilan
        ws.column_dimensions['F'].width = 15  # Jumlah Bruto
        ws.column_dimensions['G'].width = 10  # Tarif
        ws.column_dimensions['H'].width = 15  # PPh Dipotong
        ws.column_dimensions['I'].width = 30  # Keterangan
        
        ws.row_dimensions[3].height = 40
    
    def export_to_pdf(self, result: Dict[str, Any], output_path: str) -> bool:
        """Export single PPh23 to PDF with compact table"""
        try:
            if not HAS_REPORTLAB:
                logger.error("❌ reportlab not available for PDF export")
                return False
            
            doc = SimpleDocTemplate(output_path, pagesize=A4, 
                                    topMargin=0.5*inch, bottomMargin=0.5*inch,
                                    leftMargin=0.5*inch, rightMargin=0.5*inch)
            styles = getSampleStyleSheet()
            story = []
            
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                textColor=colors.HexColor('#059669'),
                spaceAfter=15,
                alignment=1
            )
            
            story.append(Paragraph("📋 PPh23 - PAJAK ATAS JASA", title_style))
            story.append(Spacer(1, 12))
            
            # Get structured data
            extracted_data = result.get('extracted_data', {})
            structured = extracted_data.get('structured_data', {})
            
            if not structured or not any(structured.values()):
                raw_text = extracted_data.get('raw_text', '')
                if raw_text:
                    from ai_processor import IndonesianTaxDocumentParser
                    temp_parser = IndonesianTaxDocumentParser()
                    structured = temp_parser.extract_structured_fields(raw_text, "pph23")
            
            # Table data
            table_data = [
                ["Nama WP", "NPWP", "Tgl", "No. Bukti", "Jenis", "Bruto", "Tarif", "PPh", "Ket"],
                [
                    structured.get('nama_wp', 'N/A')[:20],
                    structured.get('npwp', 'N/A'),
                    structured.get('tanggal', 'N/A'),
                    structured.get('nomor_bukti_potong', 'N/A')[:15],
                    structured.get('jenis_penghasilan', 'N/A')[:20],
                    structured.get('jumlah_bruto', 'N/A'),
                    structured.get('tarif', 'N/A'),
                    structured.get('pph_dipotong', 'N/A'),
                    structured.get('keterangan', 'N/A')[:20]
                ]
            ]
            
            col_widths = [1.0*inch, 0.9*inch, 0.6*inch, 0.8*inch, 1.0*inch, 0.7*inch, 0.5*inch, 0.7*inch, 0.8*inch]
            
            main_table = Table(table_data, colWidths=col_widths, repeatRows=1)
            main_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#059669')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 7),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#d1fae5')),
                ('FONTSIZE', (0, 1), (-1, 1), 6),
                ('ALIGN', (0, 1), (-1, 1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('LEFTPADDING', (0, 0), (-1, -1), 3),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(main_table)
            
            doc.build(story)
            logger.info(f"✅ PPh23 PDF export created: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ PPh23 PDF export failed: {e}", exc_info=True)
            return False
    
    def batch_export_to_excel(self, batch_id: str, results: list, output_path: str) -> bool:
        """Export multiple PPh23 documents to single Excel file"""
        try:
            if not HAS_OPENPYXL:
                logger.error("❌ openpyxl not available for batch Excel export")
                return False
            
            wb = Workbook()
            ws = wb.active
            ws.title = "Batch PPh23"
            
            # Styles
            header_fill = PatternFill(start_color="059669", end_color="059669", fill_type="solid")
            header_font = Font(bold=True, size=11, color="FFFFFF")
            data_fill_1 = PatternFill(start_color="d1fae5", end_color="d1fae5", fill_type="solid")
            data_fill_2 = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
            border_thin = Border(
                left=Side(style='thin', color='000000'),
                right=Side(style='thin', color='000000'),
                top=Side(style='thin', color='000000'),
                bottom=Side(style='thin', color='000000')
            )
            center_align = Alignment(horizontal='center', vertical='center', wrap_text=True)
            left_align = Alignment(horizontal='left', vertical='center', wrap_text=True)
            
            row = 1
            
            # Batch info
            ws.merge_cells(f'A{row}:I{row}')
            ws[f'A{row}'] = f"📦 BATCH PPh23: {batch_id} | Total: {len(results)} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            ws[f'A{row}'].font = Font(bold=True, size=12, color="FFFFFF")
            ws[f'A{row}'].fill = header_fill
            ws[f'A{row}'].alignment = center_align
            ws[f'A{row}'].border = border_thin
            row += 1
            
            # Headers
            for col_idx, header in enumerate(self.columns, start=1):
                cell = ws.cell(row=row, column=col_idx, value=header)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = center_align
                cell.border = border_thin
            row += 1
            
            # Data rows
            from ai_processor import IndonesianTaxDocumentParser
            temp_parser = IndonesianTaxDocumentParser()
            
            for idx, result_dict in enumerate(results):
                extracted_data = result_dict.get('extracted_data', {})
                structured = extracted_data.get('structured_data', {})
                
                if not structured or not any(structured.values()):
                    raw_text = extracted_data.get('raw_text', '')
                    if raw_text:
                        structured = temp_parser.extract_structured_fields(raw_text, "pph23")
                
                data_row = [
                    structured.get('nama_wp', 'N/A'),
                    structured.get('npwp', 'N/A'),
                    structured.get('tanggal', 'N/A'),
                    structured.get('nomor_bukti_potong', 'N/A'),
                    structured.get('jenis_penghasilan', 'N/A'),
                    structured.get('jumlah_bruto', 'N/A'),
                    structured.get('tarif', 'N/A'),
                    structured.get('pph_dipotong', 'N/A'),
                    structured.get('keterangan', 'N/A')
                ]
                
                fill = data_fill_1 if idx % 2 == 0 else data_fill_2
                
                for col_idx, value in enumerate(data_row, start=1):
                    cell = ws.cell(row=row, column=col_idx, value=value)
                    cell.fill = fill
                    cell.alignment = left_align
                    cell.border = border_thin
                    cell.font = Font(size=10)
                
                row += 1
            
            # Column widths
            ws.column_dimensions['A'].width = 25
            ws.column_dimensions['B'].width = 20
            ws.column_dimensions['C'].width = 12
            ws.column_dimensions['D'].width = 20
            ws.column_dimensions['E'].width = 30
            ws.column_dimensions['F'].width = 15
            ws.column_dimensions['G'].width = 10
            ws.column_dimensions['H'].width = 15
            ws.column_dimensions['I'].width = 30

            wb.save(output_path)
            logger.info(f"✅ Batch PPh23 Excel export created: {output_path} with {len(results)} documents")
            return True
            
        except Exception as e:
            logger.error(f"❌ Batch PPh23 Excel export failed: {e}", exc_info=True)
            return False
    
    def batch_export_to_pdf(self, batch_id: str, results: list, output_path: str) -> bool:
        """Export multiple PPh23 documents to single PDF file"""
        try:
            if not HAS_REPORTLAB:
                logger.error("❌ reportlab not available for batch PDF export")
                return False

            doc = SimpleDocTemplate(output_path, pagesize=A4,
                                    topMargin=0.5*inch, bottomMargin=0.5*inch,
                                    leftMargin=0.5*inch, rightMargin=0.5*inch)
            styles = getSampleStyleSheet()
            story = []
            
            batch_title_style = ParagraphStyle(
                'BatchTitle',
                parent=styles['Heading1'],
                fontSize=16,
                textColor=colors.HexColor('#059669'),
                spaceAfter=15,
                alignment=1
            )

            story.append(Paragraph(f"📦 BATCH PPh23: {batch_id}", batch_title_style))
            story.append(Paragraph(f"Total: {len(results)} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                                  ParagraphStyle('SubTitle', parent=styles['Normal'], fontSize=9, alignment=1, spaceAfter=15)))
            
            table_data = [
                ["Nama WP", "NPWP", "Tgl", "No. Bukti", "Jenis", "Bruto", "Tarif", "PPh", "Ket"]
            ]
            
            from ai_processor import IndonesianTaxDocumentParser
            temp_parser = IndonesianTaxDocumentParser()
            
            for result_dict in results:
                extracted_data = result_dict.get('extracted_data', {})
                structured = extracted_data.get('structured_data', {})
                
                if not structured or not any(structured.values()):
                    raw_text = extracted_data.get('raw_text', '')
                    if raw_text:
                        structured = temp_parser.extract_structured_fields(raw_text, "pph23")
                
                table_data.append([
                    structured.get('nama_wp', 'N/A')[:20],
                    structured.get('npwp', 'N/A'),
                    structured.get('tanggal', 'N/A'),
                    structured.get('nomor_bukti_potong', 'N/A')[:15],
                    structured.get('jenis_penghasilan', 'N/A')[:20],
                    structured.get('jumlah_bruto', 'N/A'),
                    structured.get('tarif', 'N/A'),
                    structured.get('pph_dipotong', 'N/A'),
                    structured.get('keterangan', 'N/A')[:20]
                ])
            
            col_widths = [1.0*inch, 0.9*inch, 0.6*inch, 0.8*inch, 1.0*inch, 0.7*inch, 0.5*inch, 0.7*inch, 0.8*inch]
            
            main_table = Table(table_data, colWidths=col_widths, repeatRows=1)
            
            style_list = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#059669')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 7),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('LEFTPADDING', (0, 0), (-1, -1), 3),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('FONTSIZE', (0, 1), (-1, -1), 6),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ]
            
            for i in range(1, len(table_data)):
                if i % 2 == 1:
                    style_list.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#d1fae5')))
                else:
                    style_list.append(('BACKGROUND', (0, i), (-1, i), colors.white))
            
            main_table.setStyle(TableStyle(style_list))
            story.append(main_table)
            
            doc.build(story)
            logger.info(f"✅ Batch PPh23 PDF export created: {output_path} with {len(results)} documents")
            return True
            
        except Exception as e:
            logger.error(f"❌ Batch PPh23 PDF export failed: {e}", exc_info=True)
            return False
