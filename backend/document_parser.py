"""
Document Parser Module
Handles parsing of Indonesian tax documents and invoices
Supports: Faktur Pajak, PPh21, PPh23, Rekening Koran, Invoice
"""

import re
import logging
from datetime import datetime
from typing import Dict, Any, Optional

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
    
    def parse_faktur_pajak(self, text: str) -> Dict[str, Any]:
        """Parse Faktur Pajak with raw OCR text AND structured fields"""
        try:
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            
            # Extract structured fields for table export
            structured_fields = self.extract_structured_fields(text, "faktur_pajak")
            
            # Combined structure with both raw text and structured data
            result = {
                "document_type": "Faktur Pajak",
                "raw_text": text,
                "text_lines": lines,
                "structured_data": structured_fields,  # NEW: for table exports
                "extracted_content": {
                    "full_text": text,
                    "line_count": len(lines),
                    "character_count": len(text),
                    "scan_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                },
                "processing_info": {
                    "parsing_method": "hybrid_ocr_structured",
                    "status": "Raw OCR text + Structured field extraction",
                    "fields_extracted": len([v for v in structured_fields.values() if v])
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
                    "scan_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                },
                "processing_info": {
                    "parsing_method": "raw_ocr_output",
                    "status": "Structured parsing disabled. Displaying full OCR text."
                }
            }
        except Exception as e:
            logger.error(f"❌ Raw text response creation failed for {doc_type_name}: {e}")
            return {"raw_text": text, "error": str(e)}

    def _clean_company_name_advanced(self, raw_name: str) -> str:
        """Advanced AI-powered company name cleaning"""
        # Remove common prefixes and suffixes
        cleaned = raw_name.strip()
        
        # Remove prefixes
        prefixes_to_remove = [
            r'^(?:Nama\s*:?\s*)',
            r'^(?:PT\.?\s*)',
            r'^(?:CV\.?\s*)',
            r'^(?:UD\.?\s*)'
        ]
        
        for prefix in prefixes_to_remove:
            cleaned = re.sub(prefix, '', cleaned, flags=re.IGNORECASE).strip()
        
        # Remove trailing noise
        suffixes_to_remove = [
            r'\s*(?:NPWP|Alamat|Email).*$',
            r'\s*\d+.*$',  # Remove trailing numbers
            r'\s*[,.].*$'  # Remove trailing punctuation and text
        ]
        
        for suffix in suffixes_to_remove:
            cleaned = re.sub(suffix, '', cleaned, flags=re.IGNORECASE).strip()
        
        # Clean up multiple spaces
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned
    
    def _is_valid_company_name_advanced(self, name: str) -> bool:
        """Advanced validation for company names using AI patterns"""
        if len(name) < 3:
            return False
            
        # Reject generic terms
        generic_terms = [
            'barang kena pajak', 'jasa kena pajak', 'harga jual', 'penggantian',
            'termin', 'uang muka', 'dpp', 'ppn', 'total', 'pajak pertambahan nilai',
            'faktur pajak', 'nomor seri', 'tanggal faktur'
        ]
        
        name_lower = name.lower()
        for term in generic_terms:
            if term in name_lower:
                return False
        
        # Accept names with business indicators
        business_indicators = [
            'pt', 'cv', 'ud', 'tbk', 'persero', 'indonesia', 'nusantara', 
            'abadi', 'mandiri', 'jaya', 'sukses', 'group', 'corp', 'ltd',
            'telekomunikasi', 'telkom', 'mitratel'
        ]
        
        if any(indicator in name_lower for indicator in business_indicators):
            return True
            
        # Accept names that are mostly uppercase (likely company names)
        if len([c for c in name if c.isupper()]) > len(name) * 0.5:
            return True
            
        return len(name) > 5  # At least reasonable length
    
    def _is_seller_context_advanced(self, current_line: str, all_lines: list) -> bool:
        """Advanced contextual analysis to determine if this is seller information"""
        line_lower = current_line.lower()
        
        # Strong seller indicators
        seller_indicators = [
            'gedung', 'tower', 'landmark', 'plaza', 'building', 'kantor',
            'head office', 'pusat', 'jl ', 'jalan', 'alamat penjual'
        ]
        
        if any(indicator in line_lower for indicator in seller_indicators):
            return True
            
        # Analyze surrounding context (2 lines before and after)
        current_idx = -1
        for i, line in enumerate(all_lines):
            if current_line in line:
                current_idx = i
                break
                
        if current_idx >= 0:
            context_start = max(0, current_idx - 2)
            context_end = min(len(all_lines), current_idx + 3)
            context = ' '.join(all_lines[context_start:context_end]).lower()
            
            # Count seller vs buyer indicators in context
            seller_count = sum(1 for indicator in seller_indicators if indicator in context)
            buyer_indicators = ['email', '@', '.co.id', 'pembeli', 'penerima', 'contact']
            buyer_count = sum(1 for indicator in buyer_indicators if indicator in context)
            
            return seller_count > buyer_count
            
        return False  # Default to buyer if uncertain

    def parse_pph21(self, text: str) -> Dict[str, Any]:
        """Return raw OCR text for PPh21 without complex parsing."""
        try:
            return self._create_raw_text_response(text, "PPh 21")
        except Exception as e:
            logger.error(f"❌ Error parsing PPh 21: {e}")
            return self._get_empty_pph21_result()
    
    def _extract_pph21_data_ai(self, full_text: str, lines: list, result: dict):
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
        """Return raw OCR text for PPh23 without complex parsing"""
        try:
            return self._create_raw_text_response(text, "PPh 23")
        except Exception as e:
            logger.error(f"❌ Error parsing PPh 23: {e}")
            return self._get_empty_pph23_result()

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

    def parse_rekening_koran(self, text: str) -> Dict[str, Any]:
        """Return raw OCR text for Rekening Koran without complex parsing."""
        try:
            return self._create_raw_text_response(text, "Rekening Koran")
        except Exception as e:
            logger.error(f"❌ Error parsing Rekening Koran: {e}")
            return self._get_empty_rekening_result()
    
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
    
    def extract_structured_fields(self, text: str, doc_type: str = "faktur_pajak") -> Dict[str, str]:
        """
        Extract structured fields from OCR text for table format export
        Returns: Dict with keys: nama, tanggal, npwp, nomor_faktur, alamat, dpp, ppn, total, invoice, nama_barang_jasa
        """
        result = {
            "nama": "",
            "tanggal": "",
            "npwp": "",
            "nomor_faktur": "",
            "alamat": "",
            "dpp": "",
            "ppn": "",
            "total": "",
            "invoice": "",
            "nama_barang_jasa": ""
        }
        
        try:
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            full_text = ' '.join(lines)
            
            # Extract Nama (Nama Penjual / Nama Perusahaan)
            nama_patterns = [
                r'(?:Nama\s*[Pp]enjual|Nama|NAMA)\s*:?\s*([A-Z][A-Za-z\s\.]+(?:PT|CV|UD|Tbk)?[A-Za-z\s\.]*)',
                r'(PT\s+[A-Z][A-Za-z\s]+)',
                r'(CV\s+[A-Z][A-Za-z\s]+)',
                r'([A-Z][A-Z\s]+(?:INDONESIA|NUSANTARA|TELEKOMUNIKASI|GRUP|GROUP))',
            ]
            for pattern in nama_patterns:
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if match:
                    nama = match.group(1).strip()
                    if len(nama) > 3 and not any(x in nama.lower() for x in ['barang', 'jasa', 'faktur', 'npwp']):
                        result["nama"] = nama
                        break
            
            # Extract Tanggal
            tanggal_patterns = [
                r'(?:Tanggal\s*[Ff]aktur|Tanggal|Tgl\.?)\s*:?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
                r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})',
                r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|Mei|Jun|Jul|Agt|Sep|Okt|Nov|Des)[a-z]*\s+\d{4})',
            ]
            for pattern in tanggal_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    result["tanggal"] = match.group(1).strip()
                    break
            
            # Extract NPWP
            npwp_patterns = [
                r'NPWP\s*:?\s*([\d\.\-]{15,20})',
                r'(?:Nomor\s*Pokok\s*Wajib\s*Pajak|NPWP)[:\s]*([\d\.\-]{15,20})',
                r'(\d{2}\.\d{3}\.\d{3}\.\d\-\d{3}\.\d{3})',
            ]
            for pattern in npwp_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    result["npwp"] = match.group(1).strip()
                    break
            
            # Extract Nomor Faktur
            nomor_patterns = [
                r'(?:Nomor\s*[Ff]aktur|No\.\s*[Ff]aktur|Nomor\s*Seri\s*Faktur\s*Pajak)\s*:?\s*([\d\.\-]+)',
                r'(?:Kode\s*dan\s*Nomor\s*Seri|Nomor)\s*:?\s*(\d{3}\.\d{3}\-\d{2}\.\d{8})',
                r'(\d{3}\.\d{3}\-\d{2}\.\d{8})',
            ]
            for pattern in nomor_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    result["nomor_faktur"] = match.group(1).strip()
                    break
            
            # Extract Alamat
            alamat_patterns = [
                r'(?:Alamat|Address)\s*:?\s*([A-Za-z0-9\s,\.]+(?:Gedung|Tower|Jl|Jalan|Jakarta|Indonesia)[A-Za-z0-9\s,\.]*)',
                r'(Jl\.?\s+[A-Za-z0-9\s,\.]+\d+)',
                r'(Gedung\s+[A-Za-z0-9\s,\.]+)',
            ]
            for pattern in alamat_patterns:
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if match:
                    alamat = match.group(1).strip()
                    if len(alamat) > 10:
                        result["alamat"] = alamat[:100]  # Limit length
                        break
            
            # Extract DPP (Dasar Pengenaan Pajak)
            dpp_patterns = [
                r'(?:DPP|Dasar\s*Pengenaan\s*Pajak|Harga\s*Jual)\s*:?\s*Rp\.?\s*([\d\.,]+)',
                r'(?:DPP|Dasar\s*Pengenaan)\s*:?\s*([\d\.,]+)',
            ]
            for pattern in dpp_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    amount_str = match.group(1).replace('.', '').replace(',', '')
                    result["dpp"] = f"Rp {int(amount_str):,}" if amount_str.isdigit() else match.group(1)
                    break
            
            # Extract PPN (Pajak Pertambahan Nilai)
            ppn_patterns = [
                r'(?:PPN|Pajak\s*Pertambahan\s*Nilai)\s*:?\s*Rp\.?\s*([\d\.,]+)',
                r'(?:PPN|Pajak)\s*:?\s*([\d\.,]+)',
            ]
            for pattern in ppn_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    amount_str = match.group(1).replace('.', '').replace(',', '')
                    result["ppn"] = f"Rp {int(amount_str):,}" if amount_str.isdigit() else match.group(1)
                    break
            
            # Extract Total / Jumlah
            total_patterns = [
                r'(?:Total|Jumlah|Grand\s*Total)\s*:?\s*Rp\.?\s*([\d\.,]+)',
                r'(?:Total\s*Harga|Nilai\s*Total)\s*:?\s*([\d\.,]+)',
            ]
            for pattern in total_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    amount_str = match.group(1).replace('.', '').replace(',', '')
                    result["total"] = f"Rp {int(amount_str):,}" if amount_str.isdigit() else match.group(1)
                    break
            
            # Extract Invoice Number (alternative to Nomor Faktur)
            invoice_patterns = [
                r'(?:Invoice|INV|No\.?\s*Invoice)\s*:?\s*#?\s*([A-Z0-9\-\/]+)',
                r'(?:Invoice\s*Number|INV\s*No)\s*:?\s*([A-Z0-9\-\/]+)',
            ]
            for pattern in invoice_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    result["invoice"] = match.group(1).strip()
                    break
            
            # Extract Nama Barang/Jasa Kena Pajak
            barang_patterns = [
                r'(?:Nama\s*Barang\s*Kena\s*Pajak|Barang\s*Kena\s*Pajak|BKP)\s*:?\s*([A-Za-z0-9\s,\.]+)',
                r'(?:Jasa\s*Kena\s*Pajak|JKP)\s*:?\s*([A-Za-z0-9\s,\.]+)',
                r'(?:Deskripsi|Description|Item|Produk)\s*:?\s*([A-Za-z0-9\s,\.]+)',
            ]
            for pattern in barang_patterns:
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if match:
                    barang = match.group(1).strip()
                    if len(barang) > 3:
                        result["nama_barang_jasa"] = barang[:150]  # Limit length
                        break
            
            logger.info(f"✅ Structured fields extracted: {len([v for v in result.values() if v])} fields populated")
            
        except Exception as e:
            logger.error(f"❌ Structured field extraction failed: {e}")
        
        return result


# Global parser instance
parser = IndonesianTaxDocumentParser()
