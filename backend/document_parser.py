"""
Document Parser Module
Handles parsing of Indonesian tax documents and invoices
Supports: Faktur Pajak, PPh21, PPh23, Rekening Koran, Invoice
"""

import re
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

import pandas as pd

try:  # Optional heavy dependencies for table extraction
    import pdfplumber  # type: ignore
except ImportError:  # pragma: no cover - optional
    pdfplumber = None  # type: ignore

try:  # Tabula requires Java; wrap in optional block
    import tabula  # type: ignore
except ImportError:  # pragma: no cover - optional
    tabula = None  # type: ignore

logger = logging.getLogger(__name__)


class IndonesianTaxDocumentParser:
    """Parser for Indonesian tax documents"""
    
    def __init__(self):
        # Import OCR processor for initialization if needed
        try:
            from ocr_processor import RealOCRProcessor
            self.ocr_processor = RealOCRProcessor()
        except ImportError:
            logger.warning("⚠️ OCR Processor not available for document parser")
            self.ocr_processor = None
    
    def parse_faktur_pajak(self, text: str, file_path: Optional[str] = None) -> Dict[str, Any]:
        """Parse Faktur Pajak - minimal structure for Smart Mapper"""
        try:
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            
            # Simple structure - Smart Mapper will handle the heavy lifting
            result = {
                "document_type": "Faktur Pajak",
                "raw_text": text,
                "text_lines": lines,
                "extracted_content": {
                    "full_text": text,
                    "line_count": len(lines),
                    "character_count": len(text),
                    "scan_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                },
                "processing_info": {
                    "parsing_method": "smart_mapper_ready",
                    "status": "Ready for Smart Mapper AI processing"
                }
            }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Faktur Pajak processing failed: {e}")
            return {
                "document_type": "Faktur Pajak",
                "raw_text": text,
                "processing_info": {
                    "parsing_method": "raw_ocr_output",
                    "error": str(e)
                }
            }

    def _create_raw_text_response(self, text: str, doc_type_name: str) -> Dict[str, Any]:
        """Helper function to create a standardized raw text response."""
        try:
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            return {
                "document_type": doc_type_name,
                "raw_text": text,
                "text_lines": lines,
                "extracted_content": {
                    "full_text": text,
                    "line_count": len(lines),
                    "character_count": len(text),
                    "scan_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                },
                "processing_info": {
                    "parsing_method": "raw_ocr_output",
                    "status": "Structured parsing disabled. Displaying full OCR text."
                }
            }
        except Exception as e:
            logger.error(f"❌ Raw text response creation failed for {doc_type_name}: {e}")
            return {"raw_text": text, "error": str(e)}

    # Legacy parsing methods removed - Smart Mapper AI handles all extraction

    def parse_pph21(self, text: str) -> Dict[str, Any]:
        """Return raw OCR text for PPh21 - Smart Mapper will handle extraction."""
        return self._create_raw_text_response(text, "PPh 21")
    
    # All legacy extraction methods removed - Smart Mapper handles everything
    
    def _OLD_extract_pph21_data_ai(self, full_text: str, lines: list, result: dict):
        """AI-powered PPh 21 data extraction with contextual analysis"""
        
        # 🔍 ADVANCED NOMOR DETECTION
        nomor_patterns = [
            r'(?:Nomor\s*:?\s*)([A-Z0-9./-]+)',
            r'(?:No\.?\s*Bukti\s*:?\s*)([A-Z0-9./-]+)',
            r'(\d{1,3}[./]\w+[./]\w+[./]\d{2,4})' # Pattern like 1.3-08.23/0001
        ]
        
        for pattern in nomor_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match and not result['nomor']:
                result['nomor'] = self._clean_document_number(match.group(1))
                break
        
        # 🔍 ADVANCED MASA PAJAK DETECTION
        masa_patterns = [
            r'(?:Masa\s+Pajak\s*:?\s*)([A-Za-z0-9\s/-]+)',
            r'(?:Periode\s*:?\s*)([A-Za-z0-9\s/-]+)',
            r'(\d{2}\s*-\s*\d{4})' # Pattern like 08 - 2023
        ]
        
        for pattern in masa_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match and not result['masa_pajak']:
                result['masa_pajak'] = self._clean_period_text(match.group(1))
                break
        
        # 🔍 INTELLIGENT NAMA DETECTION for PPh 21
        nama_patterns = [
            r'(?:Nama\s+Penerima\s*:?\s*)([A-Z\s.,]+?)(?:\s*(?:NPWP|NIK|Alamat)|\n|$)',
            r'(?:Nama\s+Wajib\s+Pajak\s*:?\s*)([A-Z\s.,]+?)(?:\s*(?:NPWP|NIK)|\n|$)',
        ]
        
        for pattern in nama_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match and not result['identitas_penerima_penghasilan']['nama']:
                nama = self._clean_person_name(match.group(1))
                if self._is_valid_person_name(nama):
                    result['identitas_penerima_penghasilan']['nama'] = nama
                    break
        
        # 🔍 ADVANCED NPWP/NIK DETECTION
        npwp_nik_patterns = [
            r'(?:NPWP\s*:?\s*)(\d{2}\.?\d{3}\.?\d{3}\.?\d-\d{3}\.\d{3})',
            r'(?:NIK\s*:?\s*)(\d{16})',
        ]
        
        for pattern in npwp_nik_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match and not result['identitas_penerima_penghasilan']['npwp_nik']:
                result['identitas_penerima_penghasilan']['npwp_nik'] = self._clean_id_number(match.group(1))
                break
        
        # 🔍 FINANCIAL DATA EXTRACTION
        self._extract_pph21_financial_data(full_text, result)

    def _extract_pph21_financial_data(self, full_text: str, result: dict):
        """Extract financial data for PPh 21 with AI patterns"""
        
        # Penghasilan Bruto
        bruto_patterns = [
            r'(?:Penghasilan\s+Bruto\s*\(Rp\)\s*:?\s*)(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)',
            r'Bruto\s*\(Rp\)\s*([\d,.-]+)'
        ]
        for pattern in bruto_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match and not result['penghasilan_bruto']:
                result['penghasilan_bruto'] = self._clean_amount(match.group(1))
                break
        
        # PPh amount
        pph_patterns = [
            r'(?:PPh\s*DIPOTONG\s*\(Rp\)\s*:?\s*)(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)',
            r'DIPOTONG\s*\(Rp\)\s*([\d,.-]+)'
        ]
        for pattern in pph_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match and not result['pph']:
                result['pph'] = self._clean_amount(match.group(1))
                break

    def _get_empty_pph21_result(self):
        """Return empty PPh 21 result structure"""
        return {
            "nomor": "",
            "masa_pajak": "",
            "identitas_penerima_penghasilan": {"nama": "", "npwp_nik": ""},
            "penghasilan_bruto": 0,
            "pph": 0,
            "parsing_error": "Failed to parse PPh 21 document"
        }

    def parse_pph23(self, text: str) -> Dict[str, Any]:
        """Return raw OCR text for PPh23 - Smart Mapper will handle extraction."""
        return self._create_raw_text_response(text, "PPh 23")

    def _get_empty_pph23_result(self):
        """Return empty PPh 23 result structure"""
        return {
            "nomor": "",
            "masa_pajak": "",
            "identitas_penerima_penghasilan": {"nama": "", "npwp_nik": ""},
            "penghasilan_bruto": 0,
            "pph": 0,
            "parsing_error": "Failed to parse PPh 23 document"
        }

    async def parse_rekening_koran(self, text: str, ocr_result: Dict[str, Any] = None, ocr_metadata: Dict[str, Any] = None, page_offset: int = 0) -> Dict[str, Any]:
        """
        Parse Rekening Koran - SIMPLIFIED FLOW

        ✅ NEW ARCHITECTURE (Simple & Reliable):
        Google Document AI (OCR) → Claude AI (Smart Mapper) → Excel Export

        ❌ OLD ARCHITECTURE (Complex & Error-prone):
        OCR → Bank Detector → Bank Adapter → Rule Parser → Smart Mapper Fallback

        Why simplified:
        1. Bank detection often fails (BSI detected as BCA due to transfer descriptions)
        2. Bank adapters need constant maintenance (12 adapters for different formats)
        3. Rule-based parsing is brittle - format changes break it
        4. Claude AI is smart enough to handle ALL bank formats universally

        Args:
            text: Raw OCR text from Google Document AI
            ocr_result: Full OCR result with tables
            ocr_metadata: OCR metadata with raw_response

        Returns:
            Raw text response ready for Smart Mapper (Claude AI)
        """
        try:
            logger.info("=" * 60)
            logger.info("🏦 REKENING KORAN - SIMPLIFIED PROCESSING")
            logger.info("=" * 60)
            logger.info("📋 Flow: Google Document AI → Claude AI → Excel")
            logger.info("   ✅ Skip bank detection (error-prone)")
            logger.info("   ✅ Skip bank adapters (high maintenance)")
            logger.info("   ✅ Let Claude AI handle all formats universally")

            # Return raw text for Smart Mapper to process
            # Smart Mapper (Claude AI) will be called by ai_processor.py
            logger.info(f"📝 Returning {len(text)} chars for Claude AI processing")
            return self._create_raw_text_response(text, "Rekening Koran")

        except Exception as e:
            logger.error(f"❌ Error in parse_rekening_koran: {e}")
            return self._create_raw_text_response(text, "Rekening Koran")

    def _extract_rekening_data_ai(self, full_text: str, lines: list, result: dict):
        """AI-powered Rekening Koran data extraction with transaction analysis"""
        
        # 🔍 ADVANCED DATE DETECTION
        date_patterns = [
            r'(?:Tanggal\s*:?\s*)(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(?:Tgl\s*:?\s*)(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match and not result['tanggal']:
                result['tanggal'] = self._clean_date(match.group(1))
                break
        
        # 🔍 ADVANCED SALDO DETECTION
        saldo_patterns = [
            r'(?:Saldo\s*(?:Akhir)?\s*:?\s*)(?:Rp\.?\s*)?(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)',
            r'(?:Balance\s*:?\s*)(?:Rp\.?\s*)?(\d{1,3}(?:[.,]\d{3})*)'
        ]
        
        for pattern in saldo_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match and not result['saldo']:
                result['saldo'] = self._clean_amount(match.group(1))
                break
        
        # 🔍 INTELLIGENT TRANSACTION ANALYSIS
        self._extract_transactions_ai(full_text, lines, result)
        
        # 🔍 CALCULATE TOTALS from transactions
        self._calculate_totals_from_transactions(result)

    def _extract_transactions_ai(self, full_text: str, lines: list, result: dict):
        """Extract individual transactions with AI pattern recognition"""
        
        transactions = []
        
        # Advanced transaction patterns
        transaction_patterns = [
            # Credit transactions (money in)
            r'(?:CR|CREDIT|KREDIT|MASUK)\s*(?:Rp\.?\s*)?(\d{1,3}(?:[.,]\d{3})*)',
            r'(?:\+)\s*(?:Rp\.?\s*)?(\d{1,3}(?:[.,]\d{3})*)',
            # Debit transactions (money out) 
            r'(?:DR|DEBIT|KELUAR)\s*(?:Rp\.?\s*)?(\d{1,3}(?:[.,]\d{3})*)',
            r'(?:\-)\s*(?:Rp\.?\s*)?(\d{1,3}(?:[.,]\d{3})*)'
        ]
        
        for line in lines:
            line_clean = line.strip()
            if len(line_clean) < 10:  # Skip short lines
                continue
                
            # Try to detect transaction type and amount
            for pattern in transaction_patterns:
                match = re.search(pattern, line_clean, re.IGNORECASE)
                if match:
                    amount = self._clean_amount(match.group(1))
                    
                    # Determine transaction type
                    if any(indicator in pattern.upper() for indicator in ['CR', 'CREDIT', 'MASUK', '+']):
                        trans_type = 'credit'
                        if amount > result['nilai_uang_masuk']:
                            result['nilai_uang_masuk'] = amount
                    else:
                        trans_type = 'debit'
                        if amount > result['nilai_uang_keluar']:
                            result['nilai_uang_keluar'] = amount
                    
                    # Extract description/keterangan
                    description = self._extract_transaction_description(line_clean)
                    
                    transactions.append({
                        'type': trans_type,
                        'amount': amount,
                        'description': description
                    })
                    break
        
        result['transactions'] = transactions

    def _extract_transaction_description(self, line: str) -> str:
        """Extract meaningful description from transaction line"""
        # Remove common banking terms and amounts
        cleaned = line
        
        # Remove amounts and currency symbols
        cleaned = re.sub(r'(?:Rp\.?\s*)?\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?', '', cleaned)
        cleaned = re.sub(r'(?:CR|DR|CREDIT|DEBIT|KREDIT|MASUK|KELUAR|\+|\-)', '', cleaned, flags=re.IGNORECASE)
        
        # Clean up spaces
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned[:100]  # Limit length

    def _calculate_totals_from_transactions(self, result: dict):
        """Calculate total values from transaction analysis"""
        if not result['transactions']:
            return
            
        total_masuk = sum(t['amount'] for t in result['transactions'] if t['type'] == 'credit')
        total_keluar = sum(t['amount'] for t in result['transactions'] if t['type'] == 'debit')
        
        if total_masuk > result['nilai_uang_masuk']:
            result['nilai_uang_masuk'] = total_masuk
        if total_keluar > result['nilai_uang_keluar']:
            result['nilai_uang_keluar'] = total_keluar

    def _get_empty_rekening_result(self):
        """Return empty Rekening Koran result structure"""
        return {
            "raw_text": "",  # Empty raw text for failed parsing
            "tanggal": "",
            "nilai_uang_masuk": 0,
            "nilai_uang_keluar": 0,
            "saldo": 0,
            "transactions": [],
            "parsing_error": "Failed to parse Rekening Koran document"
        }

    def parse_invoice(self, text: str) -> Dict[str, Any]:
        """Return raw OCR text for Invoice without complex parsing."""
        try:
            return self._create_raw_text_response(text, "Invoice")
        except Exception as e:
            logger.error(f"❌ Error parsing Invoice: {e}")
            return self._get_empty_invoice_result()
    
    def _extract_invoice_data_ai(self, full_text: str, lines: list, result: dict):
        """AI-powered Invoice data extraction with business logic"""
        
        # 🔍 ADVANCED PO NUMBER DETECTION
        po_patterns = [
            r'(?:PO\s*(?:Number|No)?\s*:?\s*)([A-Z0-9/-]+)',
            r'(?:Purchase\s+Order\s*:?\s*)([A-Z0-9/-]+)',
            r'(?:P\.O\.\s*:?\s*)([A-Z0-9/-]+)'
        ]
        
        for pattern in po_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match and not result['po']:
                result['po'] = self._clean_document_number(match.group(1))
                break
        
        # 🔍 ADVANCED DATE DETECTION
        date_patterns = [
            r'(?:Invoice\s+Date\s*:?\s*)(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(?:Tanggal\s+Invoice\s*:?\s*)(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(?:Date\s*:?\s*)(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match and not result['tanggal_invoice']:
                result['tanggal_invoice'] = self._clean_date(match.group(1))
                break
        
        # 🔍 INTELLIGENT VENDOR/CUSTOMER DETECTION
        vendor_patterns = [
            r'(?:Vendor\s*:?\s*)([A-Z\s.,]+?)(?:\s*(?:Address|NPWP)|\n|$)',
            r'(?:From\s*:?\s*)([A-Z\s.,]+?)(?:\s*(?:Address|NPWP)|\n|$)',
            r'(?:Bill\s+From\s*:?\s*)([A-Z\s.,]+?)(?:\s*(?:Address|NPWP)|\n|$)'
        ]
        
        for pattern in vendor_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match and not result['vendor']:
                vendor = self._clean_company_name_advanced(match.group(1))
                if self._is_valid_company_name_advanced(vendor):
                    result['vendor'] = vendor
                    break
        
        # 🔍 FINANCIAL DATA EXTRACTION
        self._extract_invoice_financial_data(full_text, result)
        
        # 🔍 ITEM EXTRACTION
        self._extract_invoice_items(lines, result)

    def _extract_invoice_financial_data(self, full_text: str, result: dict):
        """Extract financial data for Invoice with AI patterns"""
        
        # Total/Grand Total
        total_patterns = [
            r'(?:Total\s*(?:Amount)?\s*:?\s*)(?:Rp\.?\s*)?(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)',
            r'(?:Grand\s+Total\s*:?\s*)(?:Rp\.?\s*)?(\d{1,3}(?:[.,]\d{3})*)',
            r'(?:Amount\s+Due\s*:?\s*)(?:Rp\.?\s*)?(\d{1,3}(?:[.,]\d{3})*)'
        ]
        
        for pattern in total_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match and not result['nilai']:
                result['nilai'] = self._clean_amount(match.group(1))
                break

    def _extract_invoice_items(self, lines: list, result: dict):
        """Extract individual items from invoice"""
        
        items = []
        
        for line in lines:
            # Simple item detection - lines with quantity and amount
            item_pattern = r'(\d+)\s+([A-Za-z\s]+?)\s+(?:Rp\.?\s*)?(\d{1,3}(?:[.,]\d{3})*)'
            match = re.search(item_pattern, line)
            
            if match:
                items.append({
                    'quantity': int(match.group(1)),
                    'description': match.group(2).strip(),
                    'amount': self._clean_amount(match.group(3))
                })
        
        result['items'] = items[:10]  # Limit to 10 items

    def _get_empty_invoice_result(self):
        """Return empty Invoice result structure"""
        return {
            "raw_text": "",  # Empty raw text for failed parsing
            "po": "",
            "tanggal_invoice": "",
            "vendor": "",
            "nilai": 0,
            "items": [],
            "parsing_error": "Failed to parse Invoice document"
        }

    # ------------------------------------------------------------------
    # Legacy parsing helpers - kept for minimal fallback support
    # Smart Mapper AI now handles primary extraction
    # ------------------------------------------------------------------
    def _build_key_value_dataframe(self, lines: List[str]) -> Optional[pd.DataFrame]:
        """Convert colon-based lines into a pandas dataframe for flexible mapping."""
        kv_rows = []
        for line in lines:
            if ':' not in line:
                continue
            key, value = line.split(':', 1)
            key_clean = key.strip()
            value_clean = value.strip()
            if not key_clean or not value_clean:
                continue
            kv_rows.append({
                'key': key_clean,
                'value': value_clean
            })

        if not kv_rows:
            return None

        df = pd.DataFrame(kv_rows)
        df['key_norm'] = df['key'].str.lower().str.strip()
        df['value_norm'] = df['value'].str.strip()
        return df

    def _populate_from_dataframe(self, df: pd.DataFrame, result: Dict[str, str]) -> None:
        """Populate structured fields using a dataframe mapping with regex fallbacks."""
        field_map = {
            'nama': ['nama penjual', 'pengusaha kena pajak', 'nama wajib pajak', 'nama'],
            'alamat': ['alamat penjual', 'alamat wajib pajak', 'alamat'],
            'npwp': ['npwp', 'nomor pokok wajib pajak'],
            'nomor_faktur': ['nomor faktur', 'kode dan nomor seri faktur pajak', 'nomor seri'],
            'tanggal': ['tanggal faktur', 'tanggal'],
            'dpp': ['dpp', 'dasar pengenaan pajak', 'harga jual'],
            'ppn': ['ppn', 'pajak pertambahan nilai'],
            'total': ['total', 'jumlah', 'grand total', 'nilai total'],
            'invoice': ['invoice', 'no invoice', 'referensi'],
            'nama_barang_jasa': ['nama barang kena pajak', 'nama barang', 'nama jasa', 'deskripsi']
        }

        amount_fields = {'dpp', 'ppn', 'total'}

        for field, keywords in field_map.items():
            if result.get(field):
                continue
            mask = df['key_norm'].apply(lambda key: any(keyword in key for keyword in keywords))
            if not mask.any():
                continue
            value = df.loc[mask, 'value_norm'].iloc[0]
            if field in amount_fields:
                formatted = self._format_amount_string(value)
                if formatted:
                    result[field] = formatted
            elif field == 'npwp':
                normalized = self._format_npwp(value)
                result[field] = normalized if normalized else value
            else:
                result[field] = value

    def _table_to_text(self, table: pd.DataFrame) -> str:
        """Flatten a table dataframe into a searchable string."""
        if table is None or table.empty:
            return ""
        table = table.fillna('')
        rows = table.astype(str).apply(lambda row: ' '.join(cell.strip() for cell in row if cell), axis=1)
        return ' '.join(row for row in rows if row).strip()

    def _format_amount_string(self, raw_value: str) -> str:
        cleaned = re.sub(r"[^0-9]", "", str(raw_value))
        if not cleaned:
            return ""
        try:
            return f"Rp {int(cleaned):,}"
        except ValueError:
            return str(raw_value).strip()

    def _extract_from_pdf_tables(self, file_path: Optional[str]) -> Dict[str, str]:
        """Use pdfplumber/tabula to enrich structured fields from table data."""
        if not file_path:
            return {}

        aggregated_texts: List[str] = []

        if pdfplumber is not None:
            try:
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        tables = page.extract_tables() or []
                        for table in tables:
                            df = pd.DataFrame(table)
                            text_block = self._table_to_text(df)
                            if text_block:
                                aggregated_texts.append(text_block)
            except Exception as exc:  # pragma: no cover - best effort
                logger.debug(f"⚠️ pdfplumber table extraction failed: {exc}")

        if not aggregated_texts and tabula is not None:
            try:
                dfs = tabula.read_pdf(file_path, pages='all', lattice=True, multiple_tables=True)  # type: ignore[arg-type]
                for df in dfs:
                    if isinstance(df, pd.DataFrame):
                        text_block = self._table_to_text(df)
                        if text_block:
                            aggregated_texts.append(text_block)
            except Exception as exc:  # pragma: no cover
                logger.debug(f"⚠️ tabula table extraction failed: {exc}")

        enriched: Dict[str, str] = {}
        if not aggregated_texts:
            return enriched

        search_text = ' \n '.join(aggregated_texts)
        amount_labels = {
            'dpp': ('dpp', 'dasar pengenaan pajak', 'harga jual'),
            'ppn': ('ppn', 'pajak pertambahan nilai'),
            'total': ('total', 'jumlah', 'grand total'),
        }

        for field, labels in amount_labels.items():
            if enriched.get(field):
                continue
            label_pattern = r'(?:' + '|'.join(labels) + r')\s*[:\-–]?\s*(?:Rp\.?\s*)?([0-9.,]+)'
            match = re.search(label_pattern, search_text, re.IGNORECASE)
            if match:
                enriched[field] = self._format_amount_string(match.group(1))

        if not enriched.get('nama_barang_jasa'):
            desc_match = re.search(
                r'(?:Nama\s+Barang\s+Kena\s+Pajak(?:\s*/\s*Jasa\s+Kena\s+Pajak)?)[\s:]+(.+?)(?:Harga|Total|Rp|\n|$)',
                search_text,
                re.IGNORECASE,
            )
            if desc_match:
                enriched['nama_barang_jasa'] = desc_match.group(1).strip(' ,;')

        return enriched

    # 🛠️ HELPER METHODS for AI-powered parsing
    def _clean_document_number(self, text: str) -> str:
        """Clean document numbers with AI patterns"""
        return re.sub(r'[^\w/-]', '', text.strip()).upper()

    def _clean_period_text(self, text: str) -> str:
        """Clean period/date text"""
        return re.sub(r'\s+', ' ', text.strip())

    def _clean_person_name(self, text: str) -> str:
        """Clean person/company names"""
        cleaned = text.strip()
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned

    def _is_valid_person_name(self, name: str) -> bool:
        """Validate if text is a valid person/company name"""
        if len(name) < 3:
            return False
        # Reject if mostly numbers or special characters
        if len([c for c in name if c.isalnum()]) < len(name) * 0.7:
            return False
        return True

    def _clean_id_number(self, text: str) -> str:
        """Clean ID numbers (NPWP/NIK)"""
        return re.sub(r'[^\d]', '', text.strip())

    def _format_npwp(self, value: str) -> str:
        digits = re.sub(r'[^0-9]', '', str(value))
        if len(digits) != 15:
            return str(value).strip()
        return f"{digits[0:2]}.{digits[2:5]}.{digits[5:8]}.{digits[8]}-{digits[9:12]}.{digits[12:15]}"

    def _clean_amount(self, text: str) -> int:
        """Clean monetary amounts"""
        if isinstance(text, (int, float)):
            return int(text)
        # Remove currency symbols and extract numbers
        cleaned = re.sub(r'[^\d,.]', '', str(text))
        cleaned = re.sub(r'[,.]', '', cleaned)
        try:
            return int(cleaned) if cleaned else 0
        except ValueError:
            return 0

    def _clean_date(self, text: str) -> str:
        """Clean date text"""
        return text.strip()

    def extract_amount(self, text: str) -> int:
        """Extract monetary amount from text"""
        try:
            # Remove common currency symbols and separators
            cleaned = text.replace('Rp', '').replace('IDR', '').replace('.', '').replace(',', '').replace(' ', '')
            
            # Extract numbers
            import re
            numbers = re.findall(r'\d+', cleaned)
            
            if numbers:
                return int(''.join(numbers))
            
            return 0
            
        except:
            return 0
    
    # Removed extract_structured_fields - Smart Mapper AI now handles all field extraction intelligently


# Global parser instance
parser = IndonesianTaxDocumentParser()
