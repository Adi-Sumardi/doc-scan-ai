"""
Rule-Based Transaction Parser
Extracts 90% of transactions WITHOUT using GPT
Saves tokens and costs!

Strategy: Use regex patterns + Document AI structured tables
Only fallback to GPT for edge cases
"""

import re
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ParsedTransaction:
    """Parsed transaction with confidence score"""
    tanggal: Optional[str]
    keterangan: Optional[str]
    debet: Optional[float]
    kredit: Optional[float]
    saldo: Optional[float]
    referensi: Optional[str]
    confidence: float
    page_number: Optional[int]  # Track which page this transaction is from
    raw_data: Dict


class RuleBasedTransactionParser:
    """
    Parse bank transactions using regex patterns (NO GPT!)

    Supports:
    - BCA, Mandiri, BNI, BRI, CIMB, Permata
    - Multiple date formats
    - Multiple amount formats
    - Debit/Credit notations
    """

    def __init__(self):
        logger.info("🔧 RuleBasedTransactionParser initialized")

        # Date patterns
        self.date_patterns = [
            r'\b(\d{2})[/-](\d{2})[/-](\d{4})\b',  # DD/MM/YYYY or DD-MM-YYYY
            r'\b(\d{2})[/-](\d{2})[/-](\d{2})\b',  # DD/MM/YY
            r'\b(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})\b',  # 01 Jan 2024
            r'\b(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\b',  # 1 Januari 2024
            r'\b(\d{4})[/-](\d{2})[/-](\d{2})\b',  # YYYY-MM-DD
        ]

        # Month name mapping
        self.month_mapping = {
            'jan': '01', 'januari': '01', 'january': '01',
            'feb': '02', 'februari': '02', 'february': '02',
            'mar': '03', 'maret': '03', 'march': '03',
            'apr': '04', 'april': '04',
            'mei': '05', 'may': '05',
            'jun': '06', 'juni': '06', 'june': '06',
            'jul': '07', 'juli': '07', 'july': '07',
            'agu': '08', 'agustus': '08', 'august': '08',
            'sep': '09', 'september': '09',
            'okt': '10', 'oktober': '10', 'october': '10',
            'nov': '11', 'november': '11',
            'des': '12', 'desember': '12', 'december': '12',
        }

        # Amount patterns
        self.amount_patterns = [
            r'([\d\.,]+)',  # Any number with dots/commas
        ]

        # Bank-specific patterns
        self.bank_patterns = {
            'bca': {
                'debit_indicators': ['db', 'debit', 'debet', 'keluar'],
                'credit_indicators': ['cr', 'credit', 'kredit', 'masuk'],
            },
            'mandiri': {
                'debit_indicators': ['db', 'debit', 'debet', 'keluar'],
                'credit_indicators': ['cr', 'credit', 'kredit', 'masuk'],
            },
            'bni': {
                'debit_indicators': ['db', 'debit', 'debet', 'keluar'],
                'credit_indicators': ['cr', 'credit', 'kredit', 'masuk'],
            },
            'cimb': {
                'debit_indicators': ['debit', 'debet', 'db'],
                'credit_indicators': ['credit', 'kredit', 'cr'],
                'format_1_headers': ['Post Date', 'Eff Date', 'Transaction Ref No'],  # Feb 2024 format
                'format_2_headers': ['Tgl. Txn', 'Txn. Date', 'Tgl. Valuta'],  # June 2022 format
            },
        }

        # CIMB-specific date patterns
        self.cimb_date_patterns = {
            'format_1': r'(\d{2})/(\d{2})/(\d{2})\s+(\d{2}):(\d{2})',  # MM/DD/YY HH:MM
            'format_2': r'(\d{2})/(\d{2})',  # DD/MM
        }

    def detect_cimb_format(self, header_row: List[str]) -> Optional[str]:
        """
        Detect CIMB format type based on header row

        Args:
            header_row: List of header cell texts

        Returns:
            'format_1', 'format_2', or None
        """
        header_text = ' '.join(header_row).lower()

        # Format 1: Feb 2024 format with English headers
        format_1_indicators = ['post date', 'eff date', 'transaction ref no']
        if any(indicator in header_text for indicator in format_1_indicators):
            logger.info("🏦 Detected CIMB Format 1 (Feb 2024 - 9 columns)")
            return 'format_1'

        # Format 2: June 2022 format with bilingual headers
        format_2_indicators = ['tgl. txn', 'txn. date', 'tgl. valuta']
        if any(indicator in header_text for indicator in format_2_indicators):
            logger.info("🏦 Detected CIMB Format 2 (June 2022 - 6 columns)")
            return 'format_2'

        return None

    def extract_cimb_date(self, text: str, format_type: str) -> Optional[str]:
        """
        Extract date from CIMB bank statement

        Args:
            text: Date text
            format_type: 'format_1' or 'format_2'

        Returns:
            Date in YYYY-MM-DD format or None
        """
        if not text:
            return None

        text = text.strip()

        if format_type == 'format_1':
            # Format: MM/DD/YY HH:MM (e.g., "02/01/24 09:30")
            match = re.search(self.cimb_date_patterns['format_1'], text)
            if match:
                mm, dd, yy, hh, mi = match.groups()
                year = f"20{yy}"  # Assume 2000s
                return f"{year}-{mm.zfill(2)}-{dd.zfill(2)}"

        elif format_type == 'format_2':
            # Format: DD/MM (e.g., "15/06")
            # Need to infer year from context or use current year
            match = re.search(self.cimb_date_patterns['format_2'], text)
            if match:
                dd, mm = match.groups()
                # Use current year as fallback (should be extracted from document header)
                year = datetime.now().year
                return f"{year}-{mm.zfill(2)}-{dd.zfill(2)}"

        # Fallback to generic date extraction
        return self.extract_date(text)

    def parse_cimb_transaction(self, row_cells: List[str], format_type: str, page_number: int = None) -> ParsedTransaction:
        """
        Parse CIMB transaction based on detected format

        Args:
            row_cells: List of cell texts
            format_type: 'format_1' or 'format_2'
            page_number: Page number where this transaction is from

        Returns:
            ParsedTransaction with confidence score
        """
        try:
            if format_type == 'format_1':
                # Format 1: [No, Post Date, Eff Date, Cheque No, Description, Debit, Credit, Balance, Ref No]
                # 9 columns total
                if len(row_cells) < 7:
                    return self._low_confidence_result(row_cells, page_number)

                # Extract date from "Post Date" column (index 1)
                tanggal = self.extract_cimb_date(row_cells[1], 'format_1')

                # Description (index 4)
                keterangan = self.clean_text(row_cells[4]) if len(row_cells) > 4 else None

                # Debit (index 5), Credit (index 6), Balance (index 7)
                debet = self.extract_amount(row_cells[5]) if len(row_cells) > 5 else None
                kredit = self.extract_amount(row_cells[6]) if len(row_cells) > 6 else None
                saldo = self.extract_amount(row_cells[7]) if len(row_cells) > 7 else None

                # Ref No (index 8)
                referensi = self.clean_text(row_cells[8]) if len(row_cells) > 8 else None

            elif format_type == 'format_2':
                # Format 2: [Tgl. Txn, Tgl. Valuta, Description, Cheque No, Debit, Credit, Balance]
                # 7 columns total (but often 6 if cheque no is empty)
                if len(row_cells) < 5:
                    return self._low_confidence_result(row_cells, page_number)

                # Extract date from "Tgl. Txn" column (index 0)
                tanggal = self.extract_cimb_date(row_cells[0], 'format_2')

                # Description (index 2)
                keterangan = self.clean_text(row_cells[2]) if len(row_cells) > 2 else None

                # Debit (index 4), Credit (index 5), Balance (index 6)
                debet = self.extract_amount(row_cells[4]) if len(row_cells) > 4 else None
                kredit = self.extract_amount(row_cells[5]) if len(row_cells) > 5 else None
                saldo = self.extract_amount(row_cells[6]) if len(row_cells) > 6 else None

                # Cheque No (index 3) - can be used as reference
                referensi = self.clean_text(row_cells[3]) if len(row_cells) > 3 else None

            else:
                return self._low_confidence_result(row_cells, page_number)

            # Calculate confidence score
            confidence = self._calculate_confidence({
                'tanggal': tanggal,
                'keterangan': keterangan,
                'debet': debet,
                'kredit': kredit,
                'saldo': saldo,
            })

            return ParsedTransaction(
                tanggal=tanggal,
                keterangan=keterangan,
                debet=debet or 0,
                kredit=kredit or 0,
                saldo=saldo,
                referensi=referensi or '',
                confidence=confidence,
                page_number=page_number,
                raw_data={
                    'row_cells': row_cells,
                    'cell_count': len(row_cells),
                    'cimb_format': format_type
                }
            )

        except Exception as e:
            logger.warning(f"⚠️ CIMB parse error: {e}")
            return self._low_confidence_result(row_cells, page_number)

    def parse_table_row(self, row_cells: List[str], bank_name: str = None, page_number: int = None) -> ParsedTransaction:
        """
        Parse a table row from Document AI

        Args:
            row_cells: List of cell texts [date, desc, debit, credit, saldo]
            bank_name: Bank name for bank-specific parsing
            page_number: Page number where this transaction is from

        Returns:
            ParsedTransaction with confidence score
        """
        try:
            # Assume standard format: [Tanggal, Keterangan, Debet, Kredit, Saldo]
            # Adjust based on actual column count

            if len(row_cells) < 3:
                return self._low_confidence_result(row_cells)

            # Extract fields
            tanggal = self.extract_date(row_cells[0]) if len(row_cells) > 0 else None
            keterangan = self.clean_text(row_cells[1]) if len(row_cells) > 1 else None

            # Handle different column layouts
            if len(row_cells) == 5:
                # Format: [Date, Desc, Debit, Credit, Saldo]
                debet = self.extract_amount(row_cells[2])
                kredit = self.extract_amount(row_cells[3])
                saldo = self.extract_amount(row_cells[4])
                referensi = None
            elif len(row_cells) == 6:
                # Format: [Date, Desc, Debit, Credit, Saldo, Ref]
                debet = self.extract_amount(row_cells[2])
                kredit = self.extract_amount(row_cells[3])
                saldo = self.extract_amount(row_cells[4])
                referensi = self.clean_text(row_cells[5])
            elif len(row_cells) == 4:
                # Format: [Date, Desc, Amount, Saldo] - need to infer debit/credit
                amount = self.extract_amount(row_cells[2])
                saldo = self.extract_amount(row_cells[3])

                # Infer debit/credit from description or amount sign
                if amount and amount < 0:
                    debet = abs(amount)
                    kredit = 0
                else:
                    debet = 0
                    kredit = amount
                referensi = None
            else:
                # Unknown format - try best effort
                debet = None
                kredit = None
                saldo = None
                referensi = None

            # Calculate confidence score
            confidence = self._calculate_confidence({
                'tanggal': tanggal,
                'keterangan': keterangan,
                'debet': debet,
                'kredit': kredit,
                'saldo': saldo,
            })

            return ParsedTransaction(
                tanggal=tanggal,
                keterangan=keterangan,
                debet=debet or 0,
                kredit=kredit or 0,
                saldo=saldo,
                referensi=referensi or '',
                confidence=confidence,
                page_number=page_number,
                raw_data={
                    'row_cells': row_cells,
                    'cell_count': len(row_cells)
                }
            )

        except Exception as e:
            logger.warning(f"⚠️ Parse error: {e}")
            return self._low_confidence_result(row_cells)

    def extract_date(self, text: str) -> Optional[str]:
        """
        Extract date from text using multiple patterns

        Returns:
            Date in YYYY-MM-DD format or None
        """
        if not text:
            return None

        text = text.strip()

        # Try each pattern
        for pattern in self.date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return self._normalize_date(match.groups())
                except:
                    continue

        return None

    def _normalize_date(self, date_parts: Tuple) -> Optional[str]:
        """
        Normalize date parts to YYYY-MM-DD format
        """
        if len(date_parts) == 3:
            part1, part2, part3 = date_parts

            # Check if month is text
            if part2.isalpha():
                # Format: DD Month YYYY
                day = part1.zfill(2)
                month = self.month_mapping.get(part2.lower())
                year = part3

                if month:
                    return f"{year}-{month}-{day}"

            # Numeric date
            if len(part3) == 4:
                # DD/MM/YYYY
                day = part1.zfill(2)
                month = part2.zfill(2)
                year = part3
                return f"{year}-{month}-{day}"
            elif len(part1) == 4:
                # YYYY-MM-DD
                return f"{part1}-{part2.zfill(2)}-{part3.zfill(2)}"
            else:
                # DD/MM/YY
                day = part1.zfill(2)
                month = part2.zfill(2)
                year = f"20{part3}"  # Assume 2000s
                return f"{year}-{month}-{day}"

        return None

    def extract_amount(self, text: str) -> Optional[float]:
        """
        Extract monetary amount from text

        Handles:
        - Rp 1.000.000,00
        - 1,000,000.00
        - 1.000.000
        - (1.000.000) = negative
        """
        if not text:
            return None

        text = text.strip()

        # Handle empty or dash
        if text in ['-', '', 'N/A', 'n/a']:
            return None

        # Remove currency symbols
        text = re.sub(r'[Rp\s$€£¥]', '', text)

        # Handle negative notation: (1.000)
        is_negative = False
        if '(' in text and ')' in text:
            is_negative = True
            text = text.replace('(', '').replace(')', '')

        # Detect format
        # Indonesian: 1.000.000,00 (dots for thousands, comma for decimal)
        # US: 1,000,000.00 (commas for thousands, dot for decimal)

        if ',' in text and '.' in text:
            # Both present - need to determine which is decimal
            last_comma = text.rfind(',')
            last_dot = text.rfind('.')

            if last_comma > last_dot:
                # Indonesian format: 1.000,00
                text = text.replace('.', '').replace(',', '.')
            else:
                # US format: 1,000.00
                text = text.replace(',', '')
        elif ',' in text:
            # Only comma - could be thousands or decimal
            comma_count = text.count(',')
            parts = text.split(',')

            if comma_count == 1 and len(parts[1]) == 2:
                # Decimal: 1000,00
                text = text.replace(',', '.')
            else:
                # Thousands: 1,000,000
                text = text.replace(',', '')
        elif '.' in text:
            # Only dot - could be thousands or decimal
            dot_count = text.count('.')
            parts = text.split('.')

            if dot_count == 1 and len(parts[1]) == 2:
                # Could be decimal: 1000.00
                # Keep as is
                pass
            elif dot_count > 1 or (dot_count == 1 and len(parts[1]) == 3):
                # Thousands: 1.000.000
                text = text.replace('.', '')

        # Clean and convert
        try:
            amount = float(text)
            return -amount if is_negative else amount
        except ValueError:
            logger.warning(f"⚠️ Could not parse amount: {text}")
            return None

    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text
        """
        if not text:
            return ''

        # Remove extra spaces
        text = ' '.join(text.split())

        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s\-./,]', '', text)

        return text.strip()

    def _calculate_confidence(self, data: Dict) -> float:
        """
        Calculate confidence score based on data completeness and validity

        Score breakdown:
        - Date present: 0.25
        - Description present: 0.15
        - Amount (debit or credit) present: 0.30
        - Saldo present: 0.30
        """
        score = 0.0

        # Date
        if data.get('tanggal'):
            score += 0.25

        # Description
        if data.get('keterangan') and len(data['keterangan']) > 0:
            score += 0.15

        # Amount (debit or credit)
        if data.get('debet') is not None or data.get('kredit') is not None:
            score += 0.30

        # Saldo
        if data.get('saldo') is not None:
            score += 0.30

        return score

    def _low_confidence_result(self, row_cells: List[str], page_number: int = None) -> ParsedTransaction:
        """
        Return low-confidence result for failed parsing
        """
        return ParsedTransaction(
            tanggal=None,
            keterangan=' '.join(row_cells) if row_cells else '',
            debet=0,
            kredit=0,
            saldo=None,
            referensi='',
            confidence=0.0,
            page_number=page_number,
            raw_data={'row_cells': row_cells, 'parse_failed': True}
        )

    def parse_transactions(self, tables: List[Dict], bank_name: str = None, page_number: int = None) -> List[ParsedTransaction]:
        """
        Parse all transactions from Document AI tables

        Args:
            tables: List of table dictionaries from Document AI
            bank_name: Bank name for bank-specific parsing
            page_number: Page number for these tables

        Returns:
            List of ParsedTransaction objects
        """
        all_transactions = []

        for table in tables:
            # Get page number from table if available, otherwise use parameter
            table_page = table.get('page_number', page_number)

            rows = table.get('rows', [])
            if not rows:
                continue

            # Get header row for CIMB format detection
            header_cells = [cell.get('text', '') for cell in rows[0].get('cells', [])]
            cimb_format = None

            # Detect CIMB format if bank is CIMB
            if bank_name and bank_name.lower() == 'cimb':
                cimb_format = self.detect_cimb_format(header_cells)

            # Process transaction rows (skip header)
            transaction_rows = rows[1:]

            for row in transaction_rows:
                cells = [cell.get('text', '') for cell in row.get('cells', [])]

                # Skip empty rows
                if all(not cell.strip() for cell in cells):
                    continue

                # Route to CIMB parser if format detected
                if cimb_format:
                    txn = self.parse_cimb_transaction(cells, cimb_format, page_number=table_page)
                else:
                    txn = self.parse_table_row(cells, bank_name, page_number=table_page)

                all_transactions.append(txn)

        logger.info(f"✅ Parsed {len(all_transactions)} transactions with rule-based parser")

        return all_transactions

    def get_statistics(self, transactions: List[ParsedTransaction]) -> Dict:
        """
        Get parsing statistics
        """
        total = len(transactions)
        high_conf = sum(1 for t in transactions if t.confidence > 0.90)
        medium_conf = sum(1 for t in transactions if 0.70 <= t.confidence <= 0.90)
        low_conf = sum(1 for t in transactions if t.confidence < 0.70)

        return {
            'total': total,
            'high_confidence': high_conf,
            'medium_confidence': medium_conf,
            'low_confidence': low_conf,
            'high_conf_percentage': (high_conf / total * 100) if total > 0 else 0,
            'low_conf_percentage': (low_conf / total * 100) if total > 0 else 0,
        }