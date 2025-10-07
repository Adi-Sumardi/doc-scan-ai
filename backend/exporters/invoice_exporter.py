"""
Invoice Exporter
Handles Excel and PDF export specifically for Standard Invoice documents
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


class InvoiceExporter(BaseExporter):
    """Exporter for Standard Invoice documents"""
    
    def __init__(self):
        super().__init__("invoice")
        # Columns specific to Invoice
        self.columns = [
            "No. Invoice", "Tanggal", "Kepada", "Alamat", "NPWP",
            "Deskripsi", "Qty", "Harga Satuan", "Subtotal", "Total"
        ]
    
    def export_to_excel(self, result: Dict[str, Any], output_path: str) -> bool:
        """Export single Invoice to Excel with structured table format"""
        try:
            if not HAS_OPENPYXL:
                logger.error("❌ openpyxl not available for Excel export")
                return False
            
            wb = Workbook()
            ws = wb.active
            ws.title = "Invoice"
            
            self._populate_excel_sheet(ws, result)
            
            wb.save(output_path)
            logger.info(f"✅ Invoice Excel export created: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Invoice Excel export failed: {e}", exc_info=True)
            return False
    
    def _populate_excel_sheet(self, ws, result: Dict[str, Any]):
        """Helper to populate worksheet with structured Invoice data"""
        # Define styles
        header_fill = PatternFill(start_color="dc2626", end_color="dc2626", fill_type="solid")  # Red
        header_font = Font(bold=True, size=11, color="FFFFFF")
        data_fill = PatternFill(start_color="fee2e2", end_color="fee2e2", fill_type="solid")  # Light red
        border_thin = Border(
            left=Side(style='thin', color='000000'),
            right=Side(style='thin', color='000000'),
            top=Side(style='thin', color='000000'),
            bottom=Side(style='thin', color='000000')
        )
        center_align = Alignment(horizontal='center', vertical='center', wrap_text=True)
        left_align = Alignment(horizontal='left', vertical='center', wrap_text=True)
        right_align = Alignment(horizontal='right', vertical='center', wrap_text=False)
        
        # Get structured data
        extracted_data = result.get('extracted_data', {})
        structured = extracted_data.get('structured_data', {})
        
        # If no structured data, try to extract from text
        if not structured or not any(structured.values()):
            raw_text = extracted_data.get('raw_text', '')
            if raw_text:
                from ai_processor import IndonesianTaxDocumentParser
                temp_parser = IndonesianTaxDocumentParser()
                structured = temp_parser.extract_structured_fields(raw_text, "invoice")
        
        row = 1
        
        # ===== TITLE =====
        ws.merge_cells(f'A{row}:J{row}')
        ws[f'A{row}'] = "📄 INVOICE - TAGIHAN"
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
            structured.get('invoice_number', 'N/A'),
            structured.get('tanggal', 'N/A'),
            structured.get('kepada', 'N/A'),
            structured.get('alamat', 'N/A'),
            structured.get('npwp', 'N/A'),
            structured.get('deskripsi', 'N/A'),
            structured.get('qty', 'N/A'),
            structured.get('harga_satuan', 'N/A'),
            structured.get('subtotal', 'N/A'),
            structured.get('total', 'N/A')
        ]
        
        for col_idx, value in enumerate(data_row, start=1):
            cell = ws.cell(row=row, column=col_idx, value=value)
            cell.fill = data_fill
            # Right align for numeric columns (Qty, Harga, Subtotal, Total)
            if col_idx in [7, 8, 9, 10]:
                cell.alignment = right_align
            else:
                cell.alignment = left_align
            cell.border = border_thin
            cell.font = Font(size=10)
        
        # Auto-adjust column widths
        ws.column_dimensions['A'].width = 18  # No. Invoice
        ws.column_dimensions['B'].width = 12  # Tanggal
        ws.column_dimensions['C'].width = 25  # Kepada
        ws.column_dimensions['D'].width = 35  # Alamat
        ws.column_dimensions['E'].width = 20  # NPWP
        ws.column_dimensions['F'].width = 30  # Deskripsi
        ws.column_dimensions['G'].width = 8   # Qty
        ws.column_dimensions['H'].width = 15  # Harga Satuan
        ws.column_dimensions['I'].width = 15  # Subtotal
        ws.column_dimensions['J'].width = 15  # Total
        
        ws.row_dimensions[3].height = 40
    
    def export_to_pdf(self, result: Dict[str, Any], output_path: str) -> bool:
        """Export single Invoice to PDF with compact table"""
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
                textColor=colors.HexColor('#dc2626'),
                spaceAfter=15,
                alignment=1
            )
            
            story.append(Paragraph("📄 INVOICE - TAGIHAN", title_style))
            story.append(Spacer(1, 12))
            
            # Get structured data
            extracted_data = result.get('extracted_data', {})
            structured = extracted_data.get('structured_data', {})
            
            if not structured or not any(structured.values()):
                raw_text = extracted_data.get('raw_text', '')
                if raw_text:
                    from ai_processor import IndonesianTaxDocumentParser
                    temp_parser = IndonesianTaxDocumentParser()
                    structured = temp_parser.extract_structured_fields(raw_text, "invoice")
            
            # Table data
            table_data = [
                ["No. Inv", "Tgl", "Kepada", "Alamat", "NPWP", "Desk", "Qty", "Harga", "Sub", "Total"],
                [
                    structured.get('invoice_number', 'N/A'),
                    structured.get('tanggal', 'N/A'),
                    structured.get('kepada', 'N/A')[:15],
                    structured.get('alamat', 'N/A')[:20],
                    structured.get('npwp', 'N/A'),
                    structured.get('deskripsi', 'N/A')[:15],
                    structured.get('qty', 'N/A'),
                    structured.get('harga_satuan', 'N/A'),
                    structured.get('subtotal', 'N/A'),
                    structured.get('total', 'N/A')
                ]
            ]
            
            col_widths = [0.8*inch, 0.6*inch, 0.9*inch, 1.0*inch, 0.9*inch, 0.9*inch, 0.4*inch, 0.7*inch, 0.7*inch, 0.7*inch]
            
            main_table = Table(table_data, colWidths=col_widths, repeatRows=1)
            main_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dc2626')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 7),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#fee2e2')),
                ('FONTSIZE', (0, 1), (-1, 1), 6),
                ('ALIGN', (0, 1), (5, 1), 'LEFT'),  # Text columns
                ('ALIGN', (6, 1), (9, 1), 'RIGHT'),  # Numeric columns
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('LEFTPADDING', (0, 0), (-1, -1), 3),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(main_table)
            
            doc.build(story)
            logger.info(f"✅ Invoice PDF export created: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Invoice PDF export failed: {e}", exc_info=True)
            return False
    
    def batch_export_to_excel(self, batch_id: str, results: list, output_path: str) -> bool:
        """Export multiple Invoices to single Excel file"""
        try:
            if not HAS_OPENPYXL:
                logger.error("❌ openpyxl not available for batch Excel export")
                return False
            
            wb = Workbook()
            ws = wb.active
            ws.title = "Batch Invoices"
            
            # Styles
            header_fill = PatternFill(start_color="dc2626", end_color="dc2626", fill_type="solid")
            header_font = Font(bold=True, size=11, color="FFFFFF")
            data_fill_1 = PatternFill(start_color="fee2e2", end_color="fee2e2", fill_type="solid")
            data_fill_2 = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
            border_thin = Border(
                left=Side(style='thin', color='000000'),
                right=Side(style='thin', color='000000'),
                top=Side(style='thin', color='000000'),
                bottom=Side(style='thin', color='000000')
            )
            center_align = Alignment(horizontal='center', vertical='center', wrap_text=True)
            left_align = Alignment(horizontal='left', vertical='center', wrap_text=True)
            right_align = Alignment(horizontal='right', vertical='center', wrap_text=False)
            
            row = 1
            
            # Batch info
            ws.merge_cells(f'A{row}:J{row}')
            ws[f'A{row}'] = f"📄 BATCH INVOICES: {batch_id} | Total: {len(results)} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
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
                        structured = temp_parser.extract_structured_fields(raw_text, "invoice")
                
                data_row = [
                    structured.get('invoice_number', 'N/A'),
                    structured.get('tanggal', 'N/A'),
                    structured.get('kepada', 'N/A'),
                    structured.get('alamat', 'N/A'),
                    structured.get('npwp', 'N/A'),
                    structured.get('deskripsi', 'N/A'),
                    structured.get('qty', 'N/A'),
                    structured.get('harga_satuan', 'N/A'),
                    structured.get('subtotal', 'N/A'),
                    structured.get('total', 'N/A')
                ]
                
                fill = data_fill_1 if idx % 2 == 0 else data_fill_2
                
                for col_idx, value in enumerate(data_row, start=1):
                    cell = ws.cell(row=row, column=col_idx, value=value)
                    cell.fill = fill
                    # Right align for numeric columns
                    if col_idx in [7, 8, 9, 10]:
                        cell.alignment = right_align
                    else:
                        cell.alignment = left_align
                    cell.border = border_thin
                    cell.font = Font(size=10)
                
                row += 1
            
            # Column widths
            ws.column_dimensions['A'].width = 18
            ws.column_dimensions['B'].width = 12
            ws.column_dimensions['C'].width = 25
            ws.column_dimensions['D'].width = 35
            ws.column_dimensions['E'].width = 20
            ws.column_dimensions['F'].width = 30
            ws.column_dimensions['G'].width = 8
            ws.column_dimensions['H'].width = 15
            ws.column_dimensions['I'].width = 15
            ws.column_dimensions['J'].width = 15

            wb.save(output_path)
            logger.info(f"✅ Batch Invoice Excel export created: {output_path} with {len(results)} invoices")
            return True
            
        except Exception as e:
            logger.error(f"❌ Batch Invoice Excel export failed: {e}", exc_info=True)
            return False
    
    def batch_export_to_pdf(self, batch_id: str, results: list, output_path: str) -> bool:
        """Export multiple Invoices to single PDF file"""
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
                textColor=colors.HexColor('#dc2626'),
                spaceAfter=15,
                alignment=1
            )

            story.append(Paragraph(f"📄 BATCH INVOICES: {batch_id}", batch_title_style))
            story.append(Paragraph(f"Total: {len(results)} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                                  ParagraphStyle('SubTitle', parent=styles['Normal'], fontSize=9, alignment=1, spaceAfter=15)))
            
            table_data = [
                ["No. Inv", "Tgl", "Kepada", "Alamat", "NPWP", "Desk", "Qty", "Harga", "Sub", "Total"]
            ]
            
            from ai_processor import IndonesianTaxDocumentParser
            temp_parser = IndonesianTaxDocumentParser()
            
            for result_dict in results:
                extracted_data = result_dict.get('extracted_data', {})
                structured = extracted_data.get('structured_data', {})
                
                if not structured or not any(structured.values()):
                    raw_text = extracted_data.get('raw_text', '')
                    if raw_text:
                        structured = temp_parser.extract_structured_fields(raw_text, "invoice")
                
                table_data.append([
                    structured.get('invoice_number', 'N/A'),
                    structured.get('tanggal', 'N/A'),
                    structured.get('kepada', 'N/A')[:15],
                    structured.get('alamat', 'N/A')[:20],
                    structured.get('npwp', 'N/A'),
                    structured.get('deskripsi', 'N/A')[:15],
                    structured.get('qty', 'N/A'),
                    structured.get('harga_satuan', 'N/A'),
                    structured.get('subtotal', 'N/A'),
                    structured.get('total', 'N/A')
                ])
            
            col_widths = [0.8*inch, 0.6*inch, 0.9*inch, 1.0*inch, 0.9*inch, 0.9*inch, 0.4*inch, 0.7*inch, 0.7*inch, 0.7*inch]
            
            main_table = Table(table_data, colWidths=col_widths, repeatRows=1)
            
            style_list = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dc2626')),
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
                ('ALIGN', (0, 1), (5, -1), 'LEFT'),  # Text columns
                ('ALIGN', (6, 1), (9, -1), 'RIGHT'),  # Numeric columns
            ]
            
            for i in range(1, len(table_data)):
                if i % 2 == 1:
                    style_list.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#fee2e2')))
                else:
                    style_list.append(('BACKGROUND', (0, i), (-1, i), colors.white))
            
            main_table.setStyle(TableStyle(style_list))
            story.append(main_table)
            
            doc.build(story)
            logger.info(f"✅ Batch Invoice PDF export created: {output_path} with {len(results)} invoices")
            return True
            
        except Exception as e:
            logger.error(f"❌ Batch Invoice PDF export failed: {e}", exc_info=True)
            return False
