"""
Rekening Koran Exporter
Handles Excel and PDF export specifically for Bank Statement (Rekening Koran) documents
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
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False
    logger.warning("⚠️ reportlab not installed - PDF export disabled")


class RekeningKoranExporter(BaseExporter):
    """Exporter for Bank Statement (Rekening Koran) documents"""

    def __init__(self):
        super().__init__("rekening_koran")
        # Columns specific to Rekening Koran - Updated format
        self.columns = [
            "Tanggal",
            "Nilai Uang Masuk",
            "Nilai Uang Keluar",
            "Saldo",
            "Sumber Uang Masuk",
            "Tujuan Uang Keluar",
            "Keterangan"
        ]

    def _clean_keterangan(self, keterangan: str) -> str:
        """
        Clean transaction description by removing bank prefixes and codes
        Example:
        - "TRSF E-BANKING DB 0307/FTSCY/WS95051 TRUCKING UNICER S1232 IKMAL MAULANA HARA"
          -> "TRUCKING UNICER S1232 IKMAL MAULANA HARA"
        - "TRF CN-SKN MSK/TRF CN-SKN MSK PAYMENT FROM VENDOR"
          -> "PAYMENT FROM VENDOR"
        """
        if not keterangan or not isinstance(keterangan, str):
            return keterangan

        import re

        # Common bank transaction prefixes to remove (case insensitive)
        prefixes_to_remove = [
            r'TRSF E-BANKING (DB|CR)\s+\d+/[A-Z]+/[A-Z0-9]+\s+',  # TRSF E-BANKING DB 0307/FTSCY/WS95051
            r'TRF CN-SKN MSK/TRF CN-SKN MSK\s+',  # TRF CN-SKN MSK/TRF CN-SKN MSK
            r'TRF CN-SKN (MSK|KLR)\s+',  # TRF CN-SKN MSK or TRF CN-SKN KLR
            r'BYR VIA E-BANKING\s+[A-Z\s]+\d+/\d+\s+\d+\s+',  # BYR VIA E-BANKING SUSI SUSANTO 01/07 95051
            r'KR OTOMATIS LLG-[A-Z\s]+\d+\s+',  # KR OTOMATIS LLG-OCBC NISP 0938
            r'TRSF\s+E-BANKING\s+(CR|DB)\s+',  # TRSF E-BANKING CR/DB
            r'DB OTOMATIS\s+',  # DB OTOMATIS
            r'CR OTOMATIS\s+',  # CR OTOMATIS
            r'TRANSFER\s+E-BANKING\s+',  # TRANSFER E-BANKING
            r'PEMBY VIA E-BANKING\s+',  # PEMBY VIA E-BANKING
            r'BIAYA\s+ADM\s+E-BANKING\s+',  # BIAYA ADM E-BANKING
        ]

        cleaned = keterangan
        for pattern in prefixes_to_remove:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)

        # Remove multiple spaces
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        # If cleaning removed everything, return original
        if not cleaned:
            return keterangan

        return cleaned

    def _convert_smart_mapped_to_structured(self, smart_mapped: dict) -> dict:
        """Convert Smart Mapper output to structured format for Rekening Koran"""
        if not smart_mapped or not isinstance(smart_mapped, dict):
            return {}

        structured = {}

        # Extract bank info (with more field variations)
        bank_info = smart_mapped.get('bank_info', {}) or {}
        structured['nama_bank'] = bank_info.get('nama_bank') or bank_info.get('bank_name') or 'N/A'
        structured['nomor_rekening'] = bank_info.get('nomor_rekening') or bank_info.get('account_number') or 'N/A'
        structured['nama_pemilik'] = bank_info.get('nama_pemilik') or bank_info.get('account_holder') or bank_info.get('nama') or 'N/A'
        structured['periode'] = bank_info.get('periode') or bank_info.get('period') or 'N/A'
        structured['jenis_rekening'] = bank_info.get('jenis_rekening') or bank_info.get('account_type') or ''
        structured['cabang'] = bank_info.get('cabang') or bank_info.get('branch') or ''
        structured['alamat'] = bank_info.get('alamat') or bank_info.get('address') or ''

        # Extract saldo info
        saldo_info = smart_mapped.get('saldo_info', {}) or {}
        structured['saldo_awal'] = saldo_info.get('saldo_awal') or saldo_info.get('opening_balance') or ''
        structured['saldo_akhir'] = saldo_info.get('saldo_akhir') or saldo_info.get('closing_balance') or saldo_info.get('ending_balance') or ''
        structured['saldo'] = structured['saldo_akhir']  # Alias
        structured['total_kredit'] = saldo_info.get('total_kredit') or saldo_info.get('total_credit') or ''
        structured['total_debet'] = saldo_info.get('total_debet') or saldo_info.get('total_debit') or ''

        # Extract transactions with support for 'mutasi' field
        transactions = smart_mapped.get('transactions', []) or smart_mapped.get('transaksi', [])
        if transactions and isinstance(transactions, list):
            structured['transaksi'] = []
            for trans in transactions:
                if isinstance(trans, dict):
                    # Handle 'mutasi' field (some banks use single column with +/-)
                    mutasi = trans.get('mutasi') or trans.get('mutation') or ''
                    kredit = trans.get('kredit') or trans.get('credit') or ''
                    debet = trans.get('debet') or trans.get('debit') or ''

                    # If mutasi exists and kredit/debet are empty, parse mutasi
                    if mutasi and not kredit and not debet:
                        # Remove currency symbols and clean
                        mutasi_clean = str(mutasi).replace('Rp', '').replace('IDR', '').replace(',', '').replace('.', '').strip()
                        if mutasi_clean.startswith('+'):
                            kredit = mutasi_clean.replace('+', '')
                        elif mutasi_clean.startswith('-'):
                            debet = mutasi_clean.replace('-', '')
                        elif mutasi_clean:
                            # Try to determine from value (negative = debet)
                            try:
                                val = float(mutasi_clean)
                                if val > 0:
                                    kredit = mutasi_clean
                                else:
                                    debet = str(abs(val))
                            except:
                                # If parsing fails, store as-is in kredit
                                kredit = mutasi

                    transaction_item = {
                        'tanggal': trans.get('tanggal') or trans.get('date') or trans.get('transaction_date') or 'N/A',
                        'keterangan': trans.get('keterangan') or trans.get('description') or trans.get('remarks') or trans.get('details') or 'N/A',
                        'kredit': kredit,
                        'debet': debet,
                        'saldo': trans.get('saldo') or trans.get('balance') or trans.get('running_balance') or 'N/A',
                        'referensi': trans.get('referensi') or trans.get('reference') or trans.get('ref') or '',
                        'cabang': trans.get('cabang') or trans.get('branch') or ''
                    }
                    structured['transaksi'].append(transaction_item)

        logger.info(f"✅ Rekening Koran Smart Mapper data converted to structured format with {len(structured.get('transaksi', []))} transactions")

        return structured
    
    def export_to_excel(self, result: Dict[str, Any], output_path: str) -> bool:
        """Export single Rekening Koran to Excel with structured table format"""
        try:
            if not HAS_OPENPYXL:
                logger.error("❌ openpyxl not available for Excel export")
                return False
            
            wb = Workbook()
            ws = wb.active
            ws.title = "Rekening Koran"
            
            self._populate_excel_sheet(ws, result)
            
            wb.save(output_path)
            logger.info(f"✅ Rekening Koran Excel export created: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Rekening Koran Excel export failed: {e}", exc_info=True)
            return False
    
    def _populate_excel_sheet(self, ws, result: Dict[str, Any]):
        """Helper to populate worksheet with structured Rekening Koran data"""
        # Define styles
        header_fill = PatternFill(start_color="7c3aed", end_color="7c3aed", fill_type="solid")  # Purple
        header_font = Font(bold=True, size=11, color="FFFFFF")
        data_fill = PatternFill(start_color="ede9fe", end_color="ede9fe", fill_type="solid")  # Light purple
        border_thin = Border(
            left=Side(style='thin', color='000000'),
            right=Side(style='thin', color='000000'),
            top=Side(style='thin', color='000000'),
            bottom=Side(style='thin', color='000000')
        )
        center_align = Alignment(horizontal='center', vertical='center', wrap_text=True)
        left_align = Alignment(horizontal='left', vertical='center', wrap_text=True)
        right_align = Alignment(horizontal='right', vertical='center', wrap_text=False)

        # Get structured data with Smart Mapper priority
        extracted_data = result.get('extracted_data', {})

        # DEBUG: Log what keys are available
        logger.info(f"🔍 Excel Export - Available keys in extracted_data: {list(extracted_data.keys())}")
        logger.info(f"🔍 Excel Export - Has smart_mapped: {'smart_mapped' in extracted_data}")
        logger.info(f"🔍 Excel Export - Has structured_data: {'structured_data' in extracted_data}")

        if 'smart_mapped' in extracted_data:
            smart_mapped_data = extracted_data['smart_mapped']
            logger.info(f"🔍 Excel Export - smart_mapped type: {type(smart_mapped_data)}")
            if isinstance(smart_mapped_data, dict):
                logger.info(f"🔍 Excel Export - smart_mapped keys: {list(smart_mapped_data.keys())}")
                if 'transactions' in smart_mapped_data:
                    logger.info(f"🔍 Excel Export - smart_mapped transactions count: {len(smart_mapped_data.get('transactions', []))}")

        # Priority: smart_mapped > structured_data > extracted_data itself
        if 'smart_mapped' in extracted_data and extracted_data['smart_mapped']:
            structured = self._convert_smart_mapped_to_structured(extracted_data['smart_mapped'])
            logger.info("✅ Using smart_mapped data for Rekening Koran Excel")
        elif 'structured_data' in extracted_data:
            structured = extracted_data['structured_data']
            logger.info("✅ Using structured_data for Rekening Koran Excel")
        else:
            structured = extracted_data
            logger.info("⚠️ Using raw extracted_data for Rekening Koran Excel")

        # DEBUG: Log structured data after conversion
        logger.info(f"🔍 Excel Export - After conversion, transaksi count: {len(structured.get('transaksi', []))}")
        logger.info(f"🔍 Excel Export - saldo_awal: {structured.get('saldo_awal', 'NOT FOUND')}")
        logger.info(f"🔍 Excel Export - saldo_akhir: {structured.get('saldo_akhir', 'NOT FOUND')}")
        logger.info(f"🔍 Excel Export - saldo: {structured.get('saldo', 'NOT FOUND')}")

        row = 1

        # ===== TITLE =====
        ws.merge_cells(f'A{row}:G{row}')
        nama_bank = structured.get('nama_bank', 'N/A')
        ws[f'A{row}'] = f"🏦 REKENING KORAN - {nama_bank.upper()}"
        ws[f'A{row}'].font = Font(bold=True, size=14, color="FFFFFF")
        ws[f'A{row}'].fill = header_fill
        ws[f'A{row}'].alignment = center_align
        ws[f'A{row}'].border = border_thin
        row += 1

        # ===== BANK INFO =====
        info_fill = PatternFill(start_color="f3f4f6", end_color="f3f4f6", fill_type="solid")

        # Row 1: Nomor Rekening & Nama Pemilik
        ws.merge_cells(f'A{row}:C{row}')
        ws[f'A{row}'] = f"Nomor Rekening: {structured.get('nomor_rekening', 'N/A')}"
        ws[f'A{row}'].font = Font(bold=True, size=10)
        ws[f'A{row}'].fill = info_fill
        ws[f'A{row}'].alignment = left_align
        ws[f'A{row}'].border = border_thin

        ws.merge_cells(f'D{row}:G{row}')
        ws[f'D{row}'] = f"Nama: {structured.get('nama_pemilik', 'N/A')}"
        ws[f'D{row}'].font = Font(bold=True, size=10)
        ws[f'D{row}'].fill = info_fill
        ws[f'D{row}'].alignment = left_align
        ws[f'D{row}'].border = border_thin
        row += 1

        # Row 2: Periode & Saldo
        ws.merge_cells(f'A{row}:C{row}')
        ws[f'A{row}'] = f"Periode: {structured.get('periode', 'N/A')}"
        ws[f'A{row}'].font = Font(size=10)
        ws[f'A{row}'].fill = info_fill
        ws[f'A{row}'].alignment = left_align
        ws[f'A{row}'].border = border_thin

        saldo_akhir = structured.get('saldo_akhir', structured.get('saldo', 'N/A'))
        ws.merge_cells(f'D{row}:G{row}')
        ws[f'D{row}'] = f"Saldo Akhir: Rp {saldo_akhir}"
        ws[f'D{row}'].font = Font(bold=True, size=10, color="7c3aed")
        ws[f'D{row}'].fill = info_fill
        ws[f'D{row}'].alignment = left_align
        ws[f'D{row}'].border = border_thin
        row += 1

        # ===== TABLE HEADERS =====
        for col_idx, header in enumerate(self.columns, start=1):
            cell = ws.cell(row=row, column=col_idx, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_align
            cell.border = border_thin
        row += 1

        # ===== DATA ROWS =====
        # Handle array of transactions if exists
        transaksi = structured.get('transaksi', [])

        if isinstance(transaksi, list) and transaksi:
            # Multiple transactions - iterate through array
            logger.info(f"📊 Processing {len(transaksi)} transactions for Excel export")

            for idx, trans in enumerate(transaksi):
                if not isinstance(trans, dict):
                    logger.warning(f"⚠️ Transaction {idx} is not a dict, skipping")
                    continue

                # Get kredit/debet - handle multiple field names and mutasi
                kredit = trans.get('kredit', trans.get('credit', ''))
                debet = trans.get('debet', trans.get('debit', ''))

                # Handle 'mutasi' field (some banks use single column with +/-)
                # This should already be handled by _convert_smart_mapped_to_structured
                # but add fallback just in case
                if not kredit and not debet:
                    mutasi = trans.get('mutasi', trans.get('mutation', ''))
                    if mutasi:
                        mutasi_str = str(mutasi).strip()
                        # Remove Rp, IDR, etc
                        mutasi_clean = mutasi_str.replace('Rp', '').replace('IDR', '').replace('.', '').replace(',', '').strip()
                        if mutasi_clean.startswith('+') or (mutasi_clean and not mutasi_clean.startswith('-')):
                            kredit = mutasi_clean.replace('+', '')
                        elif mutasi_clean.startswith('-'):
                            debet = mutasi_clean.replace('-', '')

                # Get other fields with fallbacks
                tanggal = trans.get('tanggal', trans.get('date', trans.get('transaction_date', 'N/A')))
                keterangan_raw = trans.get('keterangan', trans.get('description', trans.get('remarks', trans.get('details', 'N/A'))))
                saldo = trans.get('saldo', trans.get('balance', trans.get('running_balance', 'N/A')))

                # Clean keterangan to remove bank prefixes
                keterangan = self._clean_keterangan(keterangan_raw)

                # Clean values - convert to string and handle empty
                kredit = str(kredit).strip() if kredit and str(kredit).strip() not in ['', '0', 'None', 'N/A'] else '-'
                debet = str(debet).strip() if debet and str(debet).strip() not in ['', '0', 'None', 'N/A'] else '-'

                # Determine sumber/tujuan based on transaction type
                sumber_masuk = keterangan if kredit != '-' else '-'
                tujuan_keluar = keterangan if debet != '-' else '-'

                data_row = [
                    tanggal,
                    kredit,
                    debet,
                    saldo,
                    sumber_masuk,
                    tujuan_keluar,
                    keterangan
                ]

                for col_idx, value in enumerate(data_row, start=1):
                    cell = ws.cell(row=row, column=col_idx, value=value)
                    cell.fill = data_fill
                    # Right align for numeric columns (Nilai Uang Masuk, Keluar, Saldo)
                    if col_idx in [2, 3, 4]:
                        cell.alignment = right_align
                    else:
                        cell.alignment = left_align
                    cell.border = border_thin
                    cell.font = Font(size=10)

                row += 1

            logger.info(f"✅ Exported {len(transaksi)} transactions to Excel")

        elif structured.get('transaksi') is not None and not isinstance(structured.get('transaksi'), list):
            logger.warning(f"⚠️ 'transaksi' field exists but is not a list: {type(structured.get('transaksi'))}")
        else:
            # Single transaction - legacy support
            kredit = structured.get('kredit', structured.get('credit', 'N/A'))
            debet = structured.get('debet', structured.get('debit', 'N/A'))
            keterangan = structured.get('keterangan', structured.get('description', 'N/A'))

            sumber_masuk = keterangan if kredit not in ['N/A', '', 0, '0'] else '-'
            tujuan_keluar = keterangan if debet not in ['N/A', '', 0, '0'] else '-'

            data_row = [
                structured.get('tanggal', 'N/A'),
                kredit if kredit not in ['N/A', '', 0, '0'] else '-',
                debet if debet not in ['N/A', '', 0, '0'] else '-',
                structured.get('saldo', 'N/A'),
                sumber_masuk,
                tujuan_keluar,
                keterangan
            ]

            for col_idx, value in enumerate(data_row, start=1):
                cell = ws.cell(row=row, column=col_idx, value=value)
                cell.fill = data_fill
                if col_idx in [2, 3, 4]:
                    cell.alignment = right_align
                else:
                    cell.alignment = left_align
                cell.border = border_thin
                cell.font = Font(size=10)

        # Auto-adjust column widths
        ws.column_dimensions['A'].width = 12  # Tanggal
        ws.column_dimensions['B'].width = 18  # Nilai Uang Masuk
        ws.column_dimensions['C'].width = 18  # Nilai Uang Keluar
        ws.column_dimensions['D'].width = 18  # Saldo
        ws.column_dimensions['E'].width = 30  # Sumber Uang Masuk
        ws.column_dimensions['F'].width = 30  # Tujuan Uang Keluar
        ws.column_dimensions['G'].width = 30  # Keterangan
        
        ws.row_dimensions[3].height = 40
    
    def export_to_pdf(self, result: Dict[str, Any], output_path: str) -> bool:
        """Export single Rekening Koran to formatted PDF (simple format, no table)"""
        try:
            if not HAS_REPORTLAB:
                logger.error("❌ reportlab not available for PDF export")
                return False

            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import mm
            from reportlab.platypus import Paragraph, Spacer
            from reportlab.lib.enums import TA_CENTER
            from datetime import datetime, timezone

            # Get structured data with Smart Mapper priority
            extracted_data = result.get('extracted_data', {})

            # Priority: smart_mapped > structured_data > extracted_data itself
            if 'smart_mapped' in extracted_data and extracted_data['smart_mapped']:
                structured = self._convert_smart_mapped_to_structured(extracted_data['smart_mapped'])
                logger.info("✅ Using smart_mapped data for Rekening Koran PDF")
            elif 'structured_data' in extracted_data:
                structured = extracted_data['structured_data']
                logger.info("✅ Using structured_data for Rekening Koran PDF")
            else:
                structured = extracted_data
                logger.info("⚠️ Using raw extracted_data for Rekening Koran PDF")

            # Create PDF document
            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                rightMargin=20*mm,
                leftMargin=20*mm,
                topMargin=15*mm,
                bottomMargin=15*mm
            )

            story = []
            styles = getSampleStyleSheet()

            # Title style
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                textColor=colors.HexColor('#1F4E78'),
                spaceAfter=4*mm,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            )

            # Section header style
            section_style = ParagraphStyle(
                'SectionHeader',
                parent=styles['Heading2'],
                fontSize=11,
                textColor=colors.HexColor('#1F4E78'),
                spaceAfter=2*mm,
                spaceBefore=6*mm,
                fontName='Helvetica-Bold'
            )

            # Field style
            field_style = ParagraphStyle(
                'Field',
                parent=styles['Normal'],
                fontSize=9,
                textColor=colors.HexColor('#333333'),
                spaceAfter=2*mm,
                leading=12
            )

            # Highlight style for amounts
            amount_style = ParagraphStyle(
                'Amount',
                parent=field_style,
                fontSize=10,
                fontName='Helvetica-Bold',
                textColor=colors.HexColor('#1F4E78')
            )

            # Add title
            story.append(Paragraph("REKENING KORAN - MUTASI BANK", title_style))
            story.append(Paragraph("Bank Statement Summary",
                                 ParagraphStyle('Subtitle', parent=styles['Normal'],
                                              fontSize=9, alignment=TA_CENTER,
                                              textColor=colors.HexColor('#666666'))))
            story.append(Spacer(1, 10*mm))

            # Section 1: Informasi Rekening
            story.append(Paragraph("INFORMASI REKENING", section_style))
            story.append(Paragraph(f"<b>Nomor Rekening:</b> {structured.get('nomor_rekening', 'N/A')}", field_style))
            story.append(Paragraph(f"<b>Nama Pemilik:</b> {structured.get('nama_pemilik', 'N/A')}", field_style))
            story.append(Paragraph(f"<b>Periode:</b> {structured.get('periode', 'N/A')}", field_style))

            # Section 2: Ringkasan Saldo
            story.append(Paragraph("RINGKASAN SALDO", section_style))
            story.append(Paragraph(f"<b>Saldo Awal:</b> Rp {structured.get('saldo_awal', 'N/A')}", field_style))

            # Calculate totals if transactions available
            transaksi = structured.get('transaksi', [])
            if transaksi and isinstance(transaksi, list):
                try:
                    total_masuk = 0
                    total_keluar = 0

                    for t in transaksi:
                        # Safely convert kredit to float
                        kredit = t.get('kredit', 0)
                        if kredit and kredit not in ['', 'N/A', '-', 0, '0']:
                            try:
                                kredit_str = str(kredit).replace(',', '').replace('Rp', '').replace('.', '').strip()
                                if kredit_str and kredit_str.replace('.', '').isdigit():
                                    total_masuk += float(kredit_str)
                            except (ValueError, AttributeError):
                                logger.warning(f"⚠️ Failed to convert kredit value: {kredit}")

                        # Safely convert debet to float
                        debet = t.get('debet', 0)
                        if debet and debet not in ['', 'N/A', '-', 0, '0']:
                            try:
                                debet_str = str(debet).replace(',', '').replace('Rp', '').replace('.', '').strip()
                                if debet_str and debet_str.replace('.', '').isdigit():
                                    total_keluar += float(debet_str)
                            except (ValueError, AttributeError):
                                logger.warning(f"⚠️ Failed to convert debet value: {debet}")

                    story.append(Paragraph(f"<b>Total Pemasukan:</b> Rp {total_masuk:,.0f}", field_style))
                    story.append(Paragraph(f"<b>Total Pengeluaran:</b> Rp {total_keluar:,.0f}", field_style))
                except Exception as e:
                    logger.error(f"❌ Failed to calculate totals: {e}")
                    story.append(Paragraph(f"<b>Total Pemasukan:</b> N/A", field_style))
                    story.append(Paragraph(f"<b>Total Pengeluaran:</b> N/A", field_style))

            story.append(Paragraph(f"<b>Saldo Akhir:</b> Rp {structured.get('saldo_akhir', structured.get('saldo', 'N/A'))}", amount_style))

            # Section 3: Transaksi
            if transaksi and isinstance(transaksi, list) and len(transaksi) > 0:
                story.append(Paragraph("TRANSAKSI", section_style))

                for idx, trans in enumerate(transaksi[:20], start=1):  # Limit to 20 transactions
                    story.append(Spacer(1, 3*mm))
                    story.append(Paragraph(f"<b>Transaksi {idx} - {trans.get('tanggal', 'N/A')}</b>", field_style))

                    # Check if it's credit (uang masuk) or debit (uang keluar)
                    kredit = trans.get('kredit', trans.get('credit', ''))
                    debet = trans.get('debet', trans.get('debit', ''))

                    if kredit and kredit not in ['', '0', 0, 'N/A']:
                        story.append(Paragraph(f"<b>Nilai Uang Masuk:</b> Rp {kredit}", amount_style))
                        story.append(Paragraph(f"<b>Sumber:</b> {trans.get('keterangan', 'N/A')}", field_style))
                    elif debet and debet not in ['', '0', 0, 'N/A']:
                        story.append(Paragraph(f"<b>Nilai Uang Keluar:</b> Rp {debet}", amount_style))
                        story.append(Paragraph(f"<b>Tujuan:</b> {trans.get('keterangan', 'N/A')}", field_style))

                    story.append(Paragraph(f"<b>Saldo:</b> Rp {trans.get('saldo', 'N/A')}", field_style))

                    if idx < len(transaksi[:20]):
                        story.append(Spacer(1, 2*mm))
            else:
                # Single transaction format (if not array)
                story.append(Paragraph("TRANSAKSI", section_style))
                story.append(Paragraph(f"<b>Tanggal:</b> {structured.get('tanggal', 'N/A')}", field_style))

                kredit = structured.get('kredit', structured.get('credit', ''))
                debet = structured.get('debet', structured.get('debit', ''))

                if kredit and kredit not in ['', '0', 0, 'N/A']:
                    story.append(Paragraph(f"<b>Nilai Uang Masuk:</b> Rp {kredit}", amount_style))
                    story.append(Paragraph(f"<b>Sumber:</b> {structured.get('keterangan', 'N/A')}", field_style))
                elif debet and debet not in ['', '0', 0, 'N/A']:
                    story.append(Paragraph(f"<b>Nilai Uang Keluar:</b> Rp {debet}", amount_style))
                    story.append(Paragraph(f"<b>Tujuan:</b> {structured.get('keterangan', 'N/A')}", field_style))

                story.append(Paragraph(f"<b>Saldo:</b> Rp {structured.get('saldo', 'N/A')}", field_style))

            # Footer
            story.append(Spacer(1, 10*mm))
            footer_text = f"<i>Dokumen ini dibuat secara otomatis oleh Doc-Scan AI System pada {datetime.now(timezone.utc).strftime('%d-%m-%Y %H:%M:%S UTC')}</i>"
            story.append(Paragraph(footer_text, ParagraphStyle('Footer', parent=styles['Normal'],
                                                              fontSize=8, alignment=TA_CENTER,
                                                              textColor=colors.HexColor('#999999'))))

            # Build PDF
            doc.build(story)
            logger.info(f"✅ Rekening Koran PDF export created: {output_path}")
            return True

        except Exception as e:
            logger.error(f"❌ Rekening Koran PDF export failed: {e}", exc_info=True)
            return False
    
    def batch_export_to_excel(self, batch_id: str, results: list, output_path: str) -> bool:
        """Export multiple Rekening Koran entries to single Excel file"""
        try:
            if not HAS_OPENPYXL:
                logger.error("❌ openpyxl not available for batch Excel export")
                return False
            
            wb = Workbook()
            ws = wb.active
            ws.title = "Batch Mutasi Bank"
            
            # Styles
            header_fill = PatternFill(start_color="7c3aed", end_color="7c3aed", fill_type="solid")
            header_font = Font(bold=True, size=11, color="FFFFFF")
            data_fill_1 = PatternFill(start_color="ede9fe", end_color="ede9fe", fill_type="solid")
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
            ws.merge_cells(f'A{row}:G{row}')
            ws[f'A{row}'] = f"🏦 BATCH MUTASI BANK: {batch_id} | Total: {len(results)} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
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
            
            # Data rows - handle multiple documents and their transactions
            transaction_row_idx = 0  # For alternating colors

            for doc_idx, result_dict in enumerate(results):
                extracted_data = result_dict.get('extracted_data', {})

                # Priority: smart_mapped > structured_data > extracted_data itself
                if 'smart_mapped' in extracted_data and extracted_data['smart_mapped']:
                    structured = self._convert_smart_mapped_to_structured(extracted_data['smart_mapped'])
                    logger.info(f"✅ Using smart_mapped data for Rekening Koran batch item {doc_idx}")
                elif 'structured_data' in extracted_data:
                    structured = extracted_data['structured_data']
                    logger.info(f"✅ Using structured_data for Rekening Koran batch item {doc_idx}")
                else:
                    structured = extracted_data
                    logger.info(f"⚠️ Using raw extracted_data for Rekening Koran batch item {doc_idx}")

                # Get transactions array
                transaksi = structured.get('transaksi', [])

                if isinstance(transaksi, list) and transaksi:
                    # Multiple transactions from this document
                    logger.info(f"📊 Processing {len(transaksi)} transactions from document {doc_idx+1}")

                    for trans in transaksi:
                        if not isinstance(trans, dict):
                            continue

                        # Get kredit/debet with mutasi handling
                        kredit = trans.get('kredit', trans.get('credit', ''))
                        debet = trans.get('debet', trans.get('debit', ''))

                        # Fallback mutasi handling
                        if not kredit and not debet:
                            mutasi = trans.get('mutasi', trans.get('mutation', ''))
                            if mutasi:
                                mutasi_str = str(mutasi).strip()
                                mutasi_clean = mutasi_str.replace('Rp', '').replace('IDR', '').replace('.', '').replace(',', '').strip()
                                if mutasi_clean.startswith('+') or (mutasi_clean and not mutasi_clean.startswith('-')):
                                    kredit = mutasi_clean.replace('+', '')
                                elif mutasi_clean.startswith('-'):
                                    debet = mutasi_clean.replace('-', '')

                        # Get other fields
                        tanggal = trans.get('tanggal', trans.get('date', 'N/A'))
                        keterangan_raw = trans.get('keterangan', trans.get('description', trans.get('remarks', 'N/A')))
                        saldo = trans.get('saldo', trans.get('balance', 'N/A'))

                        # Clean keterangan to remove bank prefixes
                        keterangan = self._clean_keterangan(keterangan_raw)

                        # Clean values
                        kredit = str(kredit).strip() if kredit and str(kredit).strip() not in ['', '0', 'None', 'N/A'] else '-'
                        debet = str(debet).strip() if debet and str(debet).strip() not in ['', '0', 'None', 'N/A'] else '-'

                        # Determine sumber/tujuan
                        sumber_masuk = keterangan if kredit != '-' else '-'
                        tujuan_keluar = keterangan if debet != '-' else '-'

                        data_row = [
                            tanggal,
                            kredit,
                            debet,
                            saldo,
                            sumber_masuk,
                            tujuan_keluar,
                            keterangan
                        ]

                        fill = data_fill_1 if transaction_row_idx % 2 == 0 else data_fill_2

                        for col_idx, value in enumerate(data_row, start=1):
                            cell = ws.cell(row=row, column=col_idx, value=value)
                            cell.fill = fill
                            # Right align for numeric columns
                            if col_idx in [2, 3, 4]:
                                cell.alignment = right_align
                            else:
                                cell.alignment = left_align
                            cell.border = border_thin
                            cell.font = Font(size=10)

                        row += 1
                        transaction_row_idx += 1

                else:
                    # Legacy: Single transaction per document (fallback)
                    kredit = structured.get('kredit', structured.get('credit', 'N/A'))
                    debet = structured.get('debet', structured.get('debit', 'N/A'))
                    keterangan = structured.get('keterangan', structured.get('description', 'N/A'))

                    # Determine sumber/tujuan based on transaction type
                    sumber_masuk = keterangan if kredit not in ['N/A', '', 0, '0'] else '-'
                    tujuan_keluar = keterangan if debet not in ['N/A', '', 0, '0'] else '-'

                    data_row = [
                        structured.get('tanggal', 'N/A'),
                        kredit if kredit not in ['N/A', '', 0, '0'] else '-',
                        debet if debet not in ['N/A', '', 0, '0'] else '-',
                        structured.get('saldo', 'N/A'),
                        sumber_masuk,
                        tujuan_keluar,
                        keterangan
                    ]

                    fill = data_fill_1 if transaction_row_idx % 2 == 0 else data_fill_2

                    for col_idx, value in enumerate(data_row, start=1):
                        cell = ws.cell(row=row, column=col_idx, value=value)
                        cell.fill = fill
                        # Right align for numeric columns
                        if col_idx in [2, 3, 4]:
                            cell.alignment = right_align
                        else:
                            cell.alignment = left_align
                        cell.border = border_thin
                        cell.font = Font(size=10)

                    row += 1
                    transaction_row_idx += 1

            logger.info(f"✅ Exported {transaction_row_idx} total transactions from {len(results)} documents")

            # Column widths
            ws.column_dimensions['A'].width = 12
            ws.column_dimensions['B'].width = 18
            ws.column_dimensions['C'].width = 18
            ws.column_dimensions['D'].width = 18
            ws.column_dimensions['E'].width = 30
            ws.column_dimensions['F'].width = 30
            ws.column_dimensions['G'].width = 30

            wb.save(output_path)
            logger.info(f"✅ Batch Rekening Koran Excel export created: {output_path} with {len(results)} entries")
            return True
            
        except Exception as e:
            logger.error(f"❌ Batch Rekening Koran Excel export failed: {e}", exc_info=True)
            return False
    
    def batch_export_to_pdf(self, batch_id: str, results: list, output_path: str) -> bool:
        """Export multiple Rekening Koran entries to formatted PDF (simple format, no table)"""
        try:
            if not HAS_REPORTLAB:
                logger.error("❌ reportlab not available for batch PDF export")
                return False

            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import mm
            from reportlab.platypus import Paragraph, Spacer, PageBreak
            from reportlab.lib.enums import TA_CENTER
            from datetime import datetime, timezone

            # Create PDF document
            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                rightMargin=20*mm,
                leftMargin=20*mm,
                topMargin=15*mm,
                bottomMargin=15*mm
            )

            story = []
            styles = getSampleStyleSheet()

            # Title style
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                textColor=colors.HexColor('#1F4E78'),
                spaceAfter=4*mm,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            )

            # Section header style
            section_style = ParagraphStyle(
                'SectionHeader',
                parent=styles['Heading2'],
                fontSize=11,
                textColor=colors.HexColor('#1F4E78'),
                spaceAfter=2*mm,
                spaceBefore=6*mm,
                fontName='Helvetica-Bold'
            )

            # Field style
            field_style = ParagraphStyle(
                'Field',
                parent=styles['Normal'],
                fontSize=9,
                textColor=colors.HexColor('#333333'),
                spaceAfter=2*mm,
                leading=12
            )

            # Amount style
            amount_style = ParagraphStyle(
                'Amount',
                parent=field_style,
                fontSize=10,
                fontName='Helvetica-Bold',
                textColor=colors.HexColor('#1F4E78')
            )

            # Document separator style (simple - no background)
            doc_separator_style = ParagraphStyle(
                'DocSeparator',
                parent=styles['Heading2'],
                fontSize=12,
                textColor=colors.HexColor('#1F4E78'),
                spaceAfter=4*mm,
                spaceBefore=8*mm,
                fontName='Helvetica-Bold',
                alignment=TA_CENTER,
                borderWidth=0,
                borderPadding=0
            )

            # Add batch title
            story.append(Paragraph("REKENING KORAN - MUTASI BANK", title_style))
            story.append(Paragraph(f"BATCH EXPORT - {len(results)} Dokumen",
                                 ParagraphStyle('Subtitle', parent=styles['Normal'],
                                              fontSize=10, alignment=TA_CENTER,
                                              textColor=colors.HexColor('#666666'))))
            story.append(Spacer(1, 10*mm))

            # Process each result
            for idx, result_dict in enumerate(results, start=1):
                extracted_data = result_dict.get('extracted_data', {})

                # Priority: smart_mapped > structured_data > extracted_data itself
                if 'smart_mapped' in extracted_data and extracted_data['smart_mapped']:
                    structured = self._convert_smart_mapped_to_structured(extracted_data['smart_mapped'])
                    logger.info(f"✅ Using smart_mapped data for Rekening Koran batch PDF item {idx}")
                elif 'structured_data' in extracted_data:
                    structured = extracted_data['structured_data']
                    logger.info(f"✅ Using structured_data for Rekening Koran batch PDF item {idx}")
                else:
                    structured = extracted_data
                    logger.info(f"⚠️ Using raw extracted_data for Rekening Koran batch PDF item {idx}")

                # Document separator
                story.append(Paragraph(f"REKENING {idx} dari {len(results)}", doc_separator_style))
                story.append(Spacer(1, 3*mm))

                # Compact format for batch
                story.append(Paragraph("INFORMASI REKENING", section_style))
                story.append(Paragraph(f"<b>Nomor Rekening:</b> {structured.get('nomor_rekening', 'N/A')}", field_style))
                story.append(Paragraph(f"<b>Nama Pemilik:</b> {structured.get('nama_pemilik', 'N/A')}", field_style))
                story.append(Paragraph(f"<b>Periode:</b> {structured.get('periode', 'N/A')}", field_style))

                # Ringkasan (compact)
                story.append(Paragraph("RINGKASAN", section_style))
                story.append(Paragraph(f"<b>Saldo Awal:</b> Rp {structured.get('saldo_awal', 'N/A')}", field_style))
                story.append(Paragraph(f"<b>Saldo Akhir:</b> Rp {structured.get('saldo_akhir', structured.get('saldo', 'N/A'))}", amount_style))

                # Transaksi (show limited data for batch)
                transaksi = structured.get('transaksi', [])
                if transaksi and isinstance(transaksi, list) and len(transaksi) > 0:
                    story.append(Paragraph(f"TRANSAKSI ({len(transaksi)} entries)", section_style))

                    # Show only first 5 transactions per account
                    for tidx, trans in enumerate(transaksi[:5], start=1):
                        story.append(Paragraph(f"<b>{tidx}. {trans.get('tanggal', 'N/A')}</b>", field_style))

                        kredit = trans.get('kredit', trans.get('credit', ''))
                        debet = trans.get('debet', trans.get('debit', ''))

                        if kredit and kredit not in ['', '0', 0, 'N/A']:
                            story.append(Paragraph(f"Masuk: Rp {kredit} | Saldo: Rp {trans.get('saldo', 'N/A')}", field_style))
                        elif debet and debet not in ['', '0', 0, 'N/A']:
                            story.append(Paragraph(f"Keluar: Rp {debet} | Saldo: Rp {trans.get('saldo', 'N/A')}", field_style))
                else:
                    # Single transaction
                    story.append(Paragraph("TRANSAKSI", section_style))
                    kredit = structured.get('kredit', structured.get('credit', ''))
                    debet = structured.get('debet', structured.get('debit', ''))

                    if kredit and kredit not in ['', '0', 0, 'N/A']:
                        story.append(Paragraph(f"<b>Uang Masuk:</b> Rp {kredit}", amount_style))
                    elif debet and debet not in ['', '0', 0, 'N/A']:
                        story.append(Paragraph(f"<b>Uang Keluar:</b> Rp {debet}", amount_style))

                    story.append(Paragraph(f"<b>Saldo:</b> Rp {structured.get('saldo', 'N/A')}", field_style))

                # Add page break between accounts (except last one)
                if idx < len(results):
                    story.append(PageBreak())

            # Footer on last page
            story.append(Spacer(1, 10*mm))
            footer_text = f"<i>Batch export {len(results)} rekening koran dibuat oleh Doc-Scan AI pada {datetime.now(timezone.utc).strftime('%d-%m-%Y %H:%M:%S UTC')}</i>"
            story.append(Paragraph(footer_text, ParagraphStyle('Footer', parent=styles['Normal'],
                                                              fontSize=8, alignment=TA_CENTER,
                                                              textColor=colors.HexColor('#999999'))))

            # Build PDF
            doc.build(story)
            logger.info(f"✅ Batch Rekening Koran PDF export created: {output_path} with {len(results)} entries")
            return True

        except Exception as e:
            logger.error(f"❌ Batch Rekening Koran PDF export failed: {e}", exc_info=True)
            return False
