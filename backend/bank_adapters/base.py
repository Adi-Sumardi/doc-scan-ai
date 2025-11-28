"""
Base Adapter untuk semua bank
Ini adalah interface yang harus diimplementasi oleh setiap bank adapter
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any, Optional
import re
import logging


@dataclass
class StandardizedTransaction:
    """
    Format standar untuk semua transaksi bank
    Semua bank adapter harus convert ke format ini
    """
    # Tanggal
    transaction_date: datetime
    posting_date: Optional[datetime] = None
    effective_date: Optional[datetime] = None

    # Detail Transaksi
    description: str = ""
    transaction_type: str = ""  # Tipe transaksi (transfer, tarik tunai, etc)
    reference_number: str = ""

    # Jumlah
    debit: Decimal = Decimal('0.00')
    credit: Decimal = Decimal('0.00')
    balance: Decimal = Decimal('0.00')

    # Metadata
    branch_code: str = ""
    teller: str = ""
    additional_info: str = ""

    # Info Bank
    bank_name: str = ""
    account_number: str = ""
    account_holder: str = ""

    # Raw data untuk debugging
    raw_data: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert ke dictionary untuk Excel export

        Format baru (7 kolom):
        - Tanggal
        - Nilai Uang Masuk (Credit)
        - Nilai Uang Keluar (Debit)
        - Saldo
        - Sumber Uang Masuk
        - Tujuan Uang Keluar
        - Keterangan
        """
        # Extract sumber/tujuan dari description
        sumber_uang_masuk = ""
        tujuan_uang_keluar = ""

        desc_upper = self.description.upper()

        # Identify sumber uang masuk (for credit transactions)
        if float(self.credit) > 0:
            # Keywords untuk sumber uang masuk
            if 'TRANSFER' in desc_upper or 'TRSF' in desc_upper or 'TRF' in desc_upper:
                sumber_uang_masuk = "Transfer Masuk"
            elif 'SETORAN' in desc_upper or 'SETOR' in desc_upper or 'DEPOSIT' in desc_upper:
                sumber_uang_masuk = "Setoran"
            elif 'BUNGA' in desc_upper or 'INTEREST' in desc_upper:
                sumber_uang_masuk = "Bunga Bank"
            elif 'GAJI' in desc_upper or 'SALARY' in desc_upper:
                sumber_uang_masuk = "Gaji"
            elif 'KLIRING' in desc_upper or 'CLEARING' in desc_upper:
                sumber_uang_masuk = "Kliring"
            else:
                # Try to extract name/source from description
                sumber_uang_masuk = "Transfer Masuk"

        # Identify tujuan uang keluar (for debit transactions)
        if float(self.debit) > 0:
            # Keywords untuk tujuan uang keluar
            if 'ATM' in desc_upper or 'WITHDRAWAL' in desc_upper or 'TARIK TUNAI' in desc_upper:
                tujuan_uang_keluar = "Penarikan ATM"
            elif 'TRANSFER' in desc_upper or 'TRSF' in desc_upper or 'TRF' in desc_upper:
                tujuan_uang_keluar = "Transfer Keluar"
            elif 'BIAYA ADM' in desc_upper or 'ADM' in desc_upper or 'ADMIN' in desc_upper:
                tujuan_uang_keluar = "Biaya Admin"
            elif 'PAJAK' in desc_upper or 'TAX' in desc_upper:
                tujuan_uang_keluar = "Pajak"
            elif 'PULSA' in desc_upper or 'LISTRIK' in desc_upper or 'PDAM' in desc_upper or 'BPJS' in desc_upper:
                tujuan_uang_keluar = "Pembayaran Tagihan"
            elif 'DEBET' in desc_upper or 'DEBIT' in desc_upper:
                tujuan_uang_keluar = "Pembayaran"
            else:
                tujuan_uang_keluar = "Pembayaran"

        return {
            'Tanggal': self.transaction_date.strftime('%d/%m/%Y') if self.transaction_date else '',
            'Nilai Uang Masuk': float(self.credit) if float(self.credit) > 0 else 0.0,
            'Nilai Uang Keluar': float(self.debit) if float(self.debit) > 0 else 0.0,
            'Saldo': float(self.balance),
            'Sumber Uang Masuk': sumber_uang_masuk,
            'Tujuan Uang Keluar': tujuan_uang_keluar,
            'Keterangan': self.description,
        }


class BaseBankAdapter(ABC):
    """
    Base class untuk semua bank adapter
    Setiap bank harus implement class ini
    """

    # Identifikasi bank
    BANK_NAME = "Unknown Bank"
    BANK_CODE = "UNKNOWN"

    # Keywords untuk deteksi otomatis
    DETECTION_KEYWORDS = []

    # Field mapping dari OCR result ke StandardizedTransaction
    FIELD_MAPPING = {}

    def __init__(self):
        self.transactions: List[StandardizedTransaction] = []
        self.account_info = {}
        self.raw_ocr_data = None
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def parse(self, ocr_result: Dict[str, Any]) -> List[StandardizedTransaction]:
        """
        Parse hasil OCR dari Google Document AI
        Convert ke format StandardizedTransaction

        Args:
            ocr_result: Raw hasil dari Google Document AI

        Returns:
            List of StandardizedTransaction
        """
        pass

    @abstractmethod
    def extract_account_info(self, ocr_result: Dict[str, Any]) -> Dict[str, str]:
        """
        Extract informasi rekening (nomor, nama, periode)

        Args:
            ocr_result: Raw hasil dari Google Document AI

        Returns:
            Dict dengan info rekening
        """
        pass

    def detect(self, ocr_text: str) -> bool:
        """
        Detect apakah ini rekening koran dari bank ini

        Args:
            ocr_text: Text hasil OCR

        Returns:
            True jika match dengan bank ini
        """
        ocr_text_upper = ocr_text.upper()

        # Check keywords
        for keyword in self.DETECTION_KEYWORDS:
            if keyword.upper() in ocr_text_upper:
                return True

        return False

    def clean_amount(self, amount_str: str) -> Decimal:
        """
        Clean dan convert string amount ke Decimal
        Handle berbagai format: 1.000,00 atau 1,000.00
        """
        if not amount_str or amount_str.strip() == '':
            return Decimal('0.00')

        # Remove currency symbols
        amount_str = re.sub(r'[Rp$€£¥]', '', amount_str)
        amount_str = amount_str.strip()

        # Remove whitespace
        amount_str = amount_str.replace(' ', '')

        # Detect format
        if ',' in amount_str and '.' in amount_str:
            # Check which comes last
            if amount_str.rindex(',') > amount_str.rindex('.'):
                # Format: 1.000.000,00 (Indonesia)
                amount_str = amount_str.replace('.', '').replace(',', '.')
            else:
                # Format: 1,000,000.00 (International)
                amount_str = amount_str.replace(',', '')
        elif ',' in amount_str:
            # Could be decimal separator (Indonesia) or thousands (International)
            # Count commas
            comma_count = amount_str.count(',')
            if comma_count == 1 and amount_str.rindex(',') > len(amount_str) - 4:
                # Likely decimal: 1000,00
                amount_str = amount_str.replace(',', '.')
            else:
                # Likely thousands: 1,000 or 1,000,000
                amount_str = amount_str.replace(',', '')
        elif '.' in amount_str:
            # Check if it's thousands or decimal
            dot_count = amount_str.count('.')
            if dot_count == 1 and amount_str.rindex('.') > len(amount_str) - 4:
                # Likely decimal: 1000.00
                pass  # Keep as is
            else:
                # Likely thousands: 1.000 or 1.000.000
                amount_str = amount_str.replace('.', '')

        try:
            return Decimal(amount_str)
        except:
            return Decimal('0.00')

    def parse_date(self, date_str: str, formats: List[str] = None) -> Optional[datetime]:
        """
        Parse tanggal dari berbagai format

        Args:
            date_str: String tanggal
            formats: List format yang mau dicoba (default: common Indonesian formats)

        Returns:
            datetime object atau None
        """
        if not date_str or date_str.strip() == '':
            return None

        if formats is None:
            formats = [
                '%d/%m/%Y',
                '%d-%m-%Y',
                '%d.%m.%Y',
                '%Y-%m-%d',
                '%d %b %Y',
                '%d %B %Y',
                '%d/%m/%y',
                '%d-%m-%y',
            ]

        date_str = date_str.strip()

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        return None

    def extract_text_from_ocr(self, ocr_result: Dict[str, Any]) -> str:
        """
        Extract full text dari OCR result untuk detection
        """
        if 'text' in ocr_result:
            return ocr_result['text']

        # Try to extract from pages
        text_parts = []
        if 'pages' in ocr_result:
            for page in ocr_result['pages']:
                if 'blocks' in page:
                    for block in page['blocks']:
                        if 'text' in block:
                            text_parts.append(block['text'])

        return '\n'.join(text_parts)

    def get_standardized_transactions(self) -> List[StandardizedTransaction]:
        """
        Get hasil parsing dalam format standar
        """
        return self.transactions

    def to_excel_format(self) -> List[Dict[str, Any]]:
        """
        Convert semua transaksi ke format Excel
        """
        return [trans.to_dict() for trans in self.transactions]

    def safe_get_cell(self, cells: List, index: int, default: str = '') -> str:
        """
        Safely get cell value by index
        Returns default if index out of bounds
        
        This is critical for handling:
        - Synthetic tables (1 cell per row)
        - Partially parsed tables
        - OCR errors that result in missing cells
        
        Args:
            cells: List of cell dictionaries
            index: Index to access
            default: Default value if index out of bounds
            
        Returns:
            Cell text or default value
        """
        try:
            if index < len(cells) and cells[index]:
                return cells[index].get('text', '').strip()
        except (IndexError, TypeError, AttributeError):
            pass
        return default

    def get_summary(self) -> Dict[str, Any]:
        """
        Get ringkasan transaksi
        """
        total_debit = sum(t.debit for t in self.transactions)
        total_credit = sum(t.credit for t in self.transactions)

        return {
            'bank_name': self.BANK_NAME,
            'bank_code': self.BANK_CODE,
            'account_number': self.account_info.get('account_number', ''),
            'account_holder': self.account_info.get('account_holder', ''),
            'transaction_count': len(self.transactions),
            'total_debit': float(total_debit),
            'total_credit': float(total_credit),
            'opening_balance': float(self.transactions[0].balance) if self.transactions else 0,
            'closing_balance': float(self.transactions[-1].balance) if self.transactions else 0,
        }
