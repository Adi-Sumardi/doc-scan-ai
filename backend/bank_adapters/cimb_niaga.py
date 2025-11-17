"""
Adapter untuk Bank CIMB Niaga
Mendukung 2 format rekening koran:
- Format 1 (Feb 2024): 9 kolom dengan header bahasa Inggris
- Format 2 (June 2022): 6-7 kolom dengan header bilingual
"""

from typing import Dict, Any, List, Tuple, Optional
from .base import BaseBankAdapter, StandardizedTransaction
from decimal import Decimal
import re


class CimbNiagaAdapter(BaseBankAdapter):
    """
    Adapter untuk Rekening Koran Bank CIMB Niaga
    Auto-detect format dan parse sesuai struktur yang sesuai
    """

    BANK_NAME = "CIMB Niaga"
    BANK_CODE = "CIMB_NIAGA"

    DETECTION_KEYWORDS = [
        "CIMB NIAGA",
        "PT BANK CIMB NIAGA",
        "POST DATE",
        "EFF DATE",
        "TRANSACTION REF NO",
        "TGL. TXN",
        "TXN. DATE",
        "TGL. VALUTA",
    ]

    # Format detection keywords
    FORMAT_1_KEYWORDS = ["POST DATE", "EFF DATE", "TRANSACTION REF NO"]
    FORMAT_2_KEYWORDS = ["TGL. TXN", "TXN. DATE", "TGL. VALUTA"]

    def __init__(self):
        super().__init__()
        self.detected_format = None  # Will be 'format_1' or 'format_2'

    def parse(self, ocr_result: Dict[str, Any]) -> List[StandardizedTransaction]:
        """
        Parse OCR result dari Bank CIMB Niaga
        Auto-detect format dan proses sesuai struktur
        """
        self.raw_ocr_data = ocr_result
        self.transactions = []

        # Detect format
        self.detected_format = self._detect_format(ocr_result)
        if not self.detected_format:
            self.logger.warning("⚠️ Could not detect CIMB Niaga format")
            return self.transactions

        self.logger.info(f"🏦 Detected CIMB Niaga {self.detected_format}")

        # Extract account info
        self.account_info = self.extract_account_info(ocr_result)

        # Parse transactions based on detected format
        if 'tables' in ocr_result:
            self._parse_from_tables(ocr_result['tables'])
        else:
            self._parse_from_text(ocr_result)

        return self.transactions

    def _detect_format(self, ocr_result: Dict[str, Any]) -> Optional[str]:
        """
        Detect which CIMB format based on table headers

        Returns:
            'format_1', 'format_2', or None
        """
        text = self.extract_text_from_ocr(ocr_result).upper()

        # Check for format 1 keywords
        format_1_score = sum(1 for kw in self.FORMAT_1_KEYWORDS if kw in text)
        format_2_score = sum(1 for kw in self.FORMAT_2_KEYWORDS if kw in text)

        if format_1_score >= 2:
            return 'format_1'
        elif format_2_score >= 2:
            return 'format_2'

        # Fallback: check table structure
        if 'tables' in ocr_result:
            for table in ocr_result['tables']:
                rows = table.get('rows', [])
                if rows:
                    header = ' '.join([cell.get('text', '') for cell in rows[0].get('cells', [])]).upper()
                    if any(kw in header for kw in self.FORMAT_1_KEYWORDS):
                        return 'format_1'
                    if any(kw in header for kw in self.FORMAT_2_KEYWORDS):
                        return 'format_2'

        return None

    def extract_account_info(self, ocr_result: Dict[str, Any]) -> Dict[str, str]:
        """
        Extract informasi rekening CIMB Niaga
        """
        text = self.extract_text_from_ocr(ocr_result)
        info = {
            'bank_name': self.BANK_NAME,
            'account_number': '',
            'account_holder': '',
            'period_start': '',
            'period_end': '',
            'currency': 'IDR',
        }

        # Account number patterns
        acc_patterns = [
            r'ACCOUNT\s+(?:NO|NUMBER)[:\s]*(\d{10,16})',
            r'NO\.\s+REKENING[:\s]*(\d{10,16})',
            r'ACCOUNT[:\s]*(\d{10,16})',
        ]
        for pattern in acc_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                info['account_number'] = match.group(1)
                break

        # Account holder
        name_patterns = [
            r'ACCOUNT\s+NAME[:\s]*([^\n]+)',
            r'NAMA\s+(?:REKENING|PEMILIK)[:\s]*([^\n]+)',
        ]
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                info['account_holder'] = match.group(1).strip()
                break

        # Period (both formats use similar pattern)
        period_match = re.search(r'PERIOD[:\s]*(\d{2}/\d{2}/\d{2,4})\s*-\s*(\d{2}/\d{2}/\d{2,4})', text, re.IGNORECASE)
        if not period_match:
            period_match = re.search(r'PERIODE[:\s]*(\d{2}/\d{2}/\d{2,4})\s*-\s*(\d{2}/\d{2}/\d{2,4})', text, re.IGNORECASE)
        if period_match:
            info['period_start'] = period_match.group(1)
            info['period_end'] = period_match.group(2)

        return info

    def _parse_from_tables(self, tables: List[Dict[str, Any]]):
        """
        Parse transaksi dari table structure
        Route to appropriate parser based on detected format
        """
        if self.detected_format == 'format_1':
            self._parse_format_1(tables)
        elif self.detected_format == 'format_2':
            self._parse_format_2(tables)

    def _parse_format_1(self, tables: List[Dict[str, Any]]):
        """
        Parse Format 1 (Feb 2024): 9 kolom
        [No, Post Date, Eff Date, Cheque No, Description, Debit, Credit, Balance, Ref No]
        """
        for table in tables:
            if 'rows' not in table:
                continue

            for row_idx, row in enumerate(table['rows']):
                if row_idx == 0:  # Skip header
                    continue

                cells = row.get('cells', [])
                if len(cells) < 7:  # Minimal untuk extract data
                    continue

                try:
                    # Column mapping untuk Format 1
                    post_date_text = cells[1].get('text', '').strip() if len(cells) > 1 else ''
                    eff_date_text = cells[2].get('text', '').strip() if len(cells) > 2 else ''
                    cheque_no = cells[3].get('text', '').strip() if len(cells) > 3 else ''
                    description = cells[4].get('text', '').strip() if len(cells) > 4 else ''
                    debit_text = cells[5].get('text', '').strip() if len(cells) > 5 else ''
                    credit_text = cells[6].get('text', '').strip() if len(cells) > 6 else ''
                    balance_text = cells[7].get('text', '').strip() if len(cells) > 7 else ''
                    ref_no = cells[8].get('text', '').strip() if len(cells) > 8 else ''

                    # Parse dates (Format 1 uses MM/DD/YY HH:MM)
                    post_date = self._parse_format_1_date(post_date_text)
                    eff_date = self._parse_format_1_date(eff_date_text)
                    transaction_date = eff_date or post_date

                    if not transaction_date:
                        continue

                    # Parse amounts
                    debit = self.clean_amount(debit_text)
                    credit = self.clean_amount(credit_text)
                    balance = self.clean_amount(balance_text)

                    # Create transaction
                    txn = StandardizedTransaction(
                        transaction_date=transaction_date,
                        posting_date=post_date,
                        effective_date=eff_date,
                        description=description,
                        reference_number=ref_no or cheque_no,
                        debit=debit,
                        credit=credit,
                        balance=balance,
                        bank_name=self.BANK_NAME,
                        account_number=self.account_info.get('account_number', ''),
                        account_holder=self.account_info.get('account_holder', ''),
                        raw_data={
                            'format': 'format_1',
                            'cheque_no': cheque_no,
                            'ref_no': ref_no,
                        }
                    )
                    self.transactions.append(txn)

                except Exception as e:
                    self.logger.warning(f"⚠️ Error parsing Format 1 row: {e}")
                    continue

    def _parse_format_2(self, tables: List[Dict[str, Any]]):
        """
        Parse Format 2 (June 2022): 6-7 kolom
        [Tgl. Txn, Tgl. Valuta, Description, Cheque No, Debit, Credit, Balance]
        """
        for table in tables:
            if 'rows' not in table:
                continue

            for row_idx, row in enumerate(table['rows']):
                if row_idx == 0:  # Skip header
                    continue

                cells = row.get('cells', [])
                if len(cells) < 5:  # Minimal untuk extract data
                    continue

                try:
                    # Column mapping untuk Format 2
                    txn_date_text = cells[0].get('text', '').strip() if len(cells) > 0 else ''
                    val_date_text = cells[1].get('text', '').strip() if len(cells) > 1 else ''
                    description = cells[2].get('text', '').strip() if len(cells) > 2 else ''
                    cheque_no = cells[3].get('text', '').strip() if len(cells) > 3 else ''
                    debit_text = cells[4].get('text', '').strip() if len(cells) > 4 else ''
                    credit_text = cells[5].get('text', '').strip() if len(cells) > 5 else ''
                    balance_text = cells[6].get('text', '').strip() if len(cells) > 6 else ''

                    # Parse dates (Format 2 uses DD/MM, need to infer year)
                    txn_date = self._parse_format_2_date(txn_date_text)
                    val_date = self._parse_format_2_date(val_date_text)
                    transaction_date = txn_date or val_date

                    if not transaction_date:
                        continue

                    # Parse amounts
                    debit = self.clean_amount(debit_text)
                    credit = self.clean_amount(credit_text)
                    balance = self.clean_amount(balance_text)

                    # Create transaction
                    txn = StandardizedTransaction(
                        transaction_date=transaction_date,
                        posting_date=txn_date,
                        effective_date=val_date,
                        description=description,
                        reference_number=cheque_no,
                        debit=debit,
                        credit=credit,
                        balance=balance,
                        bank_name=self.BANK_NAME,
                        account_number=self.account_info.get('account_number', ''),
                        account_holder=self.account_info.get('account_holder', ''),
                        raw_data={
                            'format': 'format_2',
                            'cheque_no': cheque_no,
                        }
                    )
                    self.transactions.append(txn)

                except Exception as e:
                    self.logger.warning(f"⚠️ Error parsing Format 2 row: {e}")
                    continue

    def _parse_format_1_date(self, date_text: str) -> Optional[datetime]:
        """
        Parse Format 1 date: MM/DD/YY HH:MM
        Example: "02/01/24 09:30"
        """
        if not date_text:
            return None

        match = re.search(r'(\d{2})/(\d{2})/(\d{2})\s+(\d{2}):(\d{2})', date_text)
        if match:
            mm, dd, yy, hh, mi = match.groups()
            year = 2000 + int(yy)  # Assume 2000s
            try:
                from datetime import datetime
                return datetime(year, int(mm), int(dd), int(hh), int(mi))
            except ValueError:
                pass

        # Fallback to generic date parser
        return self.parse_date(date_text)

    def _parse_format_2_date(self, date_text: str) -> Optional[datetime]:
        """
        Parse Format 2 date: DD/MM
        Example: "15/06"
        Need to infer year from statement period
        """
        if not date_text:
            return None

        match = re.search(r'(\d{2})/(\d{2})(?:/(\d{2,4}))?', date_text)
        if match:
            dd, mm, yy = match.groups()

            # Infer year
            if yy:
                year = int(yy)
                if year < 100:
                    year = 2000 + year
            else:
                # Use year from period_start if available
                period_start = self.account_info.get('period_start', '')
                year_match = re.search(r'/(\d{2,4})$', period_start)
                if year_match:
                    year = int(year_match.group(1))
                    if year < 100:
                        year = 2000 + year
                else:
                    # Default to current year
                    from datetime import datetime
                    year = datetime.now().year

            try:
                from datetime import datetime
                return datetime(year, int(mm), int(dd))
            except ValueError:
                pass

        # Fallback to generic date parser
        return self.parse_date(date_text)

    def _parse_from_text(self, ocr_result: Dict[str, Any]):
        """
        Fallback: Parse dari raw text jika tidak ada table structure
        """
        self.logger.warning("⚠️ No table structure found, parsing from text")
        # Implement text-based parsing if needed
        pass
