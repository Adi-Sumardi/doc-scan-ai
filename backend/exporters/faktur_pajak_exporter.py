"""
Faktur Pajak Exporter
Handles Excel and PDF export specifically for Indonesian Tax Invoice (Faktur Pajak) documents
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


class FakturPajakExporter(BaseExporter):
    """Exporter for Faktur Pajak (Indonesian Tax Invoice) documents"""
    
    def __init__(self):
        super().__init__("faktur_pajak")
        self.columns = [
            "Nama", "Tgl", "NPWP", "Nomor Faktur", "Alamat", 
            "DPP", "PPN", "Total", "Invoice", 
            "Nama Barang Kena Pajak / Jasa Kena Pajak"
        ]
    
    def export_to_excel(self, result: Dict[str, Any], output_path: str) -> bool:
        """Export single Faktur Pajak to Excel with 10-column table format"""
        try:
            if not HAS_OPENPYXL:
                logger.error("❌ openpyxl not available for Excel export")
                return False
            
            wb = Workbook()
            ws = wb.active
            ws.title = "Faktur Pajak"
            
            self._populate_excel_sheet(ws, result)
            
            wb.save(output_path)
            logger.info(f"✅ Faktur Pajak Excel export created: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Faktur Pajak Excel export failed: {e}", exc_info=True)
            return False
    
    def _populate_excel_sheet(self, ws, result: Dict[str, Any]):
        """Helper to populate worksheet with structured Faktur Pajak data"""
        # Define styles
        header_fill = PatternFill(start_color="1e40af", end_color="1e40af", fill_type="solid")
        header_font = Font(bold=True, size=11, color="FFFFFF")
        data_fill = PatternFill(start_color="dbeafe", end_color="dbeafe", fill_type="solid")
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
                structured = temp_parser.extract_structured_fields(raw_text, "faktur_pajak")
        
        row = 1
        
        # ===== TITLE =====
        ws.merge_cells(f'A{row}:J{row}')
        ws[f'A{row}'] = "📋 FAKTUR PAJAK - DATA TERSTRUKTUR"
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
            structured.get('nama', 'N/A'),
            structured.get('tanggal', 'N/A'),
            structured.get('npwp', 'N/A'),
            structured.get('nomor_faktur', 'N/A'),
            structured.get('alamat', 'N/A'),
            structured.get('dpp', 'N/A'),
            structured.get('ppn', 'N/A'),
            structured.get('total', 'N/A'),
            structured.get('invoice', 'N/A'),
            structured.get('nama_barang_jasa', 'N/A')
        ]
        
        for col_idx, value in enumerate(data_row, start=1):
            cell = ws.cell(row=row, column=col_idx, value=value)
            cell.fill = data_fill
            cell.alignment = left_align
            cell.border = border_thin
            cell.font = Font(size=10)
        
        # Auto-adjust column widths
        ws.column_dimensions['A'].width = 20  # Nama
        ws.column_dimensions['B'].width = 12  # Tgl
        ws.column_dimensions['C'].width = 20  # NPWP
        ws.column_dimensions['D'].width = 18  # Nomor Faktur
        ws.column_dimensions['E'].width = 35  # Alamat
        ws.column_dimensions['F'].width = 15  # DPP
        ws.column_dimensions['G'].width = 15  # PPN
        ws.column_dimensions['H'].width = 15  # Total
        ws.column_dimensions['I'].width = 15  # Invoice
        ws.column_dimensions['J'].width = 40  # Nama Barang/Jasa
        
        # Set row height for data row
        ws.row_dimensions[3].height = 40
    
    def export_to_pdf(self, result: Dict[str, Any], output_path: str) -> bool:
        """Export single Faktur Pajak to PDF with compact 10-column table"""
        try:
            if not HAS_REPORTLAB:
                logger.error("❌ reportlab not available for PDF export")
                return False
            
            doc = SimpleDocTemplate(output_path, pagesize=A4, 
                                    topMargin=0.5*inch, bottomMargin=0.5*inch,
                                    leftMargin=0.5*inch, rightMargin=0.5*inch)
            styles = getSampleStyleSheet()
            story = []
            
            # Custom title style
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                textColor=colors.HexColor('#1e40af'),
                spaceAfter=15,
                alignment=1  # Center
            )
            
            # ===== TITLE =====
            story.append(Paragraph("📋 FAKTUR PAJAK - DATA TERSTRUKTUR", title_style))
            story.append(Spacer(1, 12))
            
            # Get structured data
            extracted_data = result.get('extracted_data', {})
            structured = extracted_data.get('structured_data', {})
            
            # If no structured data, try to extract from text
            if not structured or not any(structured.values()):
                raw_text = extracted_data.get('raw_text', '')
                if raw_text:
                    from ai_processor import IndonesianTaxDocumentParser
                    temp_parser = IndonesianTaxDocumentParser()
                    structured = temp_parser.extract_structured_fields(raw_text, "faktur_pajak")
            
            # ===== STRUCTURED DATA TABLE =====
            # Headers
            data_header = [[
                "Nama", "Tgl", "NPWP", "Nomor Faktur", "Alamat", 
                "DPP", "PPN", "Total", "Invoice", "Nama Barang/Jasa"
            ]]
            
            # Data row
            data_row = [[
                structured.get('nama', 'N/A'),
                structured.get('tanggal', 'N/A'),
                structured.get('npwp', 'N/A'),
                structured.get('nomor_faktur', 'N/A'),
                structured.get('alamat', 'N/A')[:30],  # Truncate for PDF
                structured.get('dpp', 'N/A'),
                structured.get('ppn', 'N/A'),
                structured.get('total', 'N/A'),
                structured.get('invoice', 'N/A'),
                structured.get('nama_barang_jasa', 'N/A')[:30]  # Truncate for PDF
            ]]
            
            # Combine header and data
            table_data = data_header + data_row
            
            # Column widths (total = 7.5 inches for A4 with margins)
            col_widths = [0.9*inch, 0.6*inch, 0.9*inch, 0.8*inch, 1.1*inch, 
                         0.6*inch, 0.6*inch, 0.6*inch, 0.6*inch, 0.8*inch]
            
            main_table = Table(table_data, colWidths=col_widths, repeatRows=1)
            main_table.setStyle(TableStyle([
                # Header row
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 7),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
                # Data row
                ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#dbeafe')),
                ('FONTSIZE', (0, 1), (-1, 1), 6),
                ('ALIGN', (0, 1), (-1, 1), 'LEFT'),
                ('VALIGN', (0, 1), (-1, 1), 'TOP'),
                # Grid
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('LEFTPADDING', (0, 0), (-1, -1), 3),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(main_table)
            
            doc.build(story)
            logger.info(f"✅ Faktur Pajak PDF export created: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Faktur Pajak PDF export failed: {e}", exc_info=True)
            return False
    
    def batch_export_to_excel(self, batch_id: str, results: list, output_path: str) -> bool:
        """Export multiple Faktur Pajak documents to single Excel file with consolidated table"""
        try:
            if not HAS_OPENPYXL:
                logger.error("❌ openpyxl not available for batch Excel export")
                return False
            
            wb = Workbook()
            ws = wb.active
            ws.title = "Batch Faktur Pajak"
            
            # Define styles
            header_fill = PatternFill(start_color="1e40af", end_color="1e40af", fill_type="solid")
            header_font = Font(bold=True, size=11, color="FFFFFF")
            data_fill_1 = PatternFill(start_color="dbeafe", end_color="dbeafe", fill_type="solid")
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
            
            # ===== BATCH INFO =====
            ws.merge_cells(f'A{row}:J{row}')
            ws[f'A{row}'] = f"📦 BATCH: {batch_id} | Total: {len(results)} Documents | Export: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            ws[f'A{row}'].font = Font(bold=True, size=12, color="FFFFFF")
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
            
            # ===== DATA ROWS (One row per document) =====
            from ai_processor import IndonesianTaxDocumentParser
            temp_parser = IndonesianTaxDocumentParser()
            
            for idx, result_dict in enumerate(results):
                # Get structured data
                extracted_data = result_dict.get('extracted_data', {})
                structured = extracted_data.get('structured_data', {})
                
                # If no structured data, try to extract
                if not structured or not any(structured.values()):
                    raw_text = extracted_data.get('raw_text', '')
                    if raw_text:
                        structured = temp_parser.extract_structured_fields(raw_text, "faktur_pajak")
                
                # Data row
                data_row = [
                    structured.get('nama', 'N/A'),
                    structured.get('tanggal', 'N/A'),
                    structured.get('npwp', 'N/A'),
                    structured.get('nomor_faktur', 'N/A'),
                    structured.get('alamat', 'N/A'),
                    structured.get('dpp', 'N/A'),
                    structured.get('ppn', 'N/A'),
                    structured.get('total', 'N/A'),
                    structured.get('invoice', 'N/A'),
                    structured.get('nama_barang_jasa', 'N/A')
                ]
                
                fill = data_fill_1 if idx % 2 == 0 else data_fill_2
                
                for col_idx, value in enumerate(data_row, start=1):
                    cell = ws.cell(row=row, column=col_idx, value=value)
                    cell.fill = fill
                    cell.alignment = left_align
                    cell.border = border_thin
                    cell.font = Font(size=10)
                
                row += 1
            
            # Auto-adjust column widths
            ws.column_dimensions['A'].width = 20
            ws.column_dimensions['B'].width = 12
            ws.column_dimensions['C'].width = 20
            ws.column_dimensions['D'].width = 18
            ws.column_dimensions['E'].width = 35
            ws.column_dimensions['F'].width = 15
            ws.column_dimensions['G'].width = 15
            ws.column_dimensions['H'].width = 15
            ws.column_dimensions['I'].width = 15
            ws.column_dimensions['J'].width = 40

            wb.save(output_path)
            logger.info(f"✅ Batch Faktur Pajak Excel export created: {output_path} with {len(results)} documents")
            return True
            
        except Exception as e:
            logger.error(f"❌ Batch Faktur Pajak Excel export failed: {e}", exc_info=True)
            return False
    
    def batch_export_to_pdf(self, batch_id: str, results: list, output_path: str) -> bool:
        """Export multiple Faktur Pajak documents to single PDF file with consolidated table"""
        try:
            if not HAS_REPORTLAB:
                logger.error("❌ reportlab not available for batch PDF export")
                return False

            doc = SimpleDocTemplate(output_path, pagesize=A4,
                                    topMargin=0.5*inch, bottomMargin=0.5*inch,
                                    leftMargin=0.5*inch, rightMargin=0.5*inch)
            styles = getSampleStyleSheet()
            story = []
            
            # Custom title style
            batch_title_style = ParagraphStyle(
                'BatchTitle',
                parent=styles['Heading1'],
                fontSize=16,
                textColor=colors.HexColor('#1e40af'),
                spaceAfter=15,
                alignment=1  # Center
            )

            # ===== BATCH TITLE =====
            story.append(Paragraph(f"📦 BATCH: {batch_id}", batch_title_style))
            story.append(Paragraph(f"Total: {len(results)} Documents | Export: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                                  ParagraphStyle('SubTitle', parent=styles['Normal'], fontSize=9, alignment=1, spaceAfter=15)))
            
            # ===== CONSOLIDATED TABLE (All documents in one table) =====
            table_data = [
                # Header row
                ["Nama", "Tgl", "NPWP", "Nomor Faktur", "Alamat", "DPP", "PPN", "Total", "Invoice", "Nama Barang/Jasa"]
            ]
            
            # Extract structured data for all documents
            from ai_processor import IndonesianTaxDocumentParser
            temp_parser = IndonesianTaxDocumentParser()
            
            for result_dict in results:
                # Get structured data
                extracted_data = result_dict.get('extracted_data', {})
                structured = extracted_data.get('structured_data', {})
                
                # If no structured data, try to extract
                if not structured or not any(structured.values()):
                    raw_text = extracted_data.get('raw_text', '')
                    if raw_text:
                        structured = temp_parser.extract_structured_fields(raw_text, "faktur_pajak")
                
                # Add data row with truncation for PDF
                table_data.append([
                    structured.get('nama', 'N/A')[:25] if len(structured.get('nama', 'N/A')) > 25 else structured.get('nama', 'N/A'),
                    structured.get('tanggal', 'N/A'),
                    structured.get('npwp', 'N/A'),
                    structured.get('nomor_faktur', 'N/A'),
                    structured.get('alamat', 'N/A')[:30] if len(structured.get('alamat', 'N/A')) > 30 else structured.get('alamat', 'N/A'),
                    structured.get('dpp', 'N/A'),
                    structured.get('ppn', 'N/A'),
                    structured.get('total', 'N/A'),
                    structured.get('invoice', 'N/A'),
                    structured.get('nama_barang_jasa', 'N/A')[:30] if len(structured.get('nama_barang_jasa', 'N/A')) > 30 else structured.get('nama_barang_jasa', 'N/A')
                ])
            
            # Column widths (total = 7.5 inches for A4 with 0.5" margins)
            col_widths = [0.9*inch, 0.6*inch, 0.9*inch, 0.8*inch, 1.1*inch, 0.6*inch, 0.6*inch, 0.6*inch, 0.6*inch, 0.8*inch]
            
            main_table = Table(table_data, colWidths=col_widths, repeatRows=1)
            
            # Build styling with alternating row colors
            style_list = [
                # Header row
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 7),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                # Grid
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                # Padding
                ('LEFTPADDING', (0, 0), (-1, -1), 3),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                # Data rows font
                ('FONTSIZE', (0, 1), (-1, -1), 6),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ]
            
            # Alternating row colors for data rows
            for i in range(1, len(table_data)):
                if i % 2 == 1:
                    style_list.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#dbeafe')))
                else:
                    style_list.append(('BACKGROUND', (0, i), (-1, i), colors.white))
            
            main_table.setStyle(TableStyle(style_list))
            story.append(main_table)
            
            doc.build(story)
            logger.info(f"✅ Batch Faktur Pajak PDF export created: {output_path} with {len(results)} documents")
            return True
            
        except Exception as e:
            logger.error(f"❌ Batch Faktur Pajak PDF export failed: {e}", exc_info=True)
            return False
