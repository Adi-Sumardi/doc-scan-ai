"""
Adapter untuk Bank CIMB Niaga
Mendukung 2 format rekening koran:
- Format 1 (Feb 2024): 9 kolom dengan header bahasa Inggris
- Format 2 (June 2022): 6-7 kolom dengan header bilingual
"""

from typing import Dict, Any, List, Tuple, Optional
from .base import BaseBankAdapter, StandardizedTransaction
from decimal import Decimal
from datetime import datetime
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

        # Detect format (might be None if text-only, will be inferred later)
        self.detected_format = self._detect_format(ocr_result)

        if self.detected_format:
            self.logger.info(f"🏦 Detected CIMB Niaga {self.detected_format}")
        else:
            self.logger.info("🏦 CIMB Niaga format not detected yet - will try to infer from text patterns")

        # Extract account info
        self.account_info = self.extract_account_info(ocr_result)

        # Parse transactions based on detected format
        if 'tables' in ocr_result and ocr_result['tables']:
            # If format not detected but we have tables, skip (shouldn't happen)
            if not self.detected_format:
                self.logger.warning("⚠️ Tables found but format not detected - falling back to text extraction")
                self._parse_from_text(ocr_result)
            else:
                self._parse_from_tables(ocr_result['tables'])
        else:
            # No tables - use text extraction (will auto-infer format)
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
        # ✅ DEBUG: Log table structure
        self.logger.info(f"📊 Parsing {len(tables)} tables with format: {self.detected_format}")
        if tables:
            self.logger.info(f"   First table has {len(tables[0].get('rows', []))} rows")
            if tables[0].get('rows'):
                first_row = tables[0]['rows'][0]
                cells = first_row.get('cells', [])
                self.logger.info(f"   First row has {len(cells)} cells")
                if cells:
                    self.logger.info(f"   Cell structure: {list(cells[0].keys())}")

        if self.detected_format == 'format_1':
            self._parse_format_1(tables)
        elif self.detected_format == 'format_2':
            self._parse_format_2(tables)

    def _parse_format_1(self, tables: List[Dict[str, Any]]):
        """
        Parse Format 1 (Feb 2024): 9 kolom
        [No, Post Date, Eff Date, Cheque No, Description, Debit, Credit, Balance, Ref No]
        """
        transactions_found = 0
        rows_skipped = 0

        for table in tables:
            if 'rows' not in table:
                continue

            for row_idx, row in enumerate(table['rows']):
                if row_idx == 0:  # Skip header
                    continue

                cells = row.get('cells', [])

                # ✅ FIXED: Check minimum required cells for Format 1
                if len(cells) < 7:  # Format 1 needs at least 7 columns
                    rows_skipped += 1
                    continue

                try:
                    # ✅ SAFE ACCESSOR: Column mapping untuk Format 1
                    post_date_text = self.safe_get_cell(cells, 1)
                    eff_date_text = self.safe_get_cell(cells, 2)
                    cheque_no = self.safe_get_cell(cells, 3)
                    description = self.safe_get_cell(cells, 4)
                    debit_text = self.safe_get_cell(cells, 5)
                    credit_text = self.safe_get_cell(cells, 6)
                    balance_text = self.safe_get_cell(cells, 7)
                    ref_no = self.safe_get_cell(cells, 8)

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
                    transactions_found += 1

                except Exception as e:
                    self.logger.warning(f"⚠️ Error parsing Format 1 row {row_idx}: {e}")
                    rows_skipped += 1
                    continue

        # ✅ LOG SUMMARY
        self.logger.info(f"📊 Format 1 Parsing Summary:")
        self.logger.info(f"   ✅ Transactions found: {transactions_found}")
        self.logger.info(f"   ⚠️ Rows skipped: {rows_skipped}")

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
                # ✅ FIXED: Check minimum required cells for Format 2
                if len(cells) < 6:  # Format 2 needs at least 6 columns (without cheque_no)
                    continue

                try:
                    # ✅ SAFE ACCESSOR: Column mapping untuk Format 2
                    txn_date_text = self.safe_get_cell(cells, 0)
                    val_date_text = self.safe_get_cell(cells, 1)
                    description = self.safe_get_cell(cells, 2)
                    cheque_no = self.safe_get_cell(cells, 3)
                    debit_text = self.safe_get_cell(cells, 4)
                    credit_text = self.safe_get_cell(cells, 5)
                    balance_text = self.safe_get_cell(cells, 6)

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
        Uses regex patterns to extract transactions directly from text
        """
        self.logger.info("📝 No table structure - using text-based extraction")

        # Extract raw text
        text = self.extract_text_from_ocr(ocr_result)
        if not text:
            self.logger.warning("⚠️ No text found in OCR result")
            return

        # Split into lines
        lines = text.split('\n')

        # Transaction pattern for Format 1: MM/DD/YY HH:MM ... Debit/Credit ... Balance
        # Example: "02/01/24 09:30  02/01/24 09:30  Transfer  1,500,000.00  -  15,000,000.00"
        format_1_pattern = r'(\d{2}/\d{2}/\d{2}\s+\d{2}:\d{2}).*?(?:(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s+)?(?:(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s+)?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'

        # Transaction pattern for Format 2: DD/MM ... Description ... Debit/Credit ... Balance
        # Example: "15/06  Transfer  1,500,000  -  15,000,000"
        format_2_pattern = r'(\d{2}/\d{2})(?:/\d{2,4})?\s+(.*?)\s+(?:(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s+)?(?:(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s+)?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'

        # ✅ FIX: If format not detected yet, try to auto-detect from transaction patterns
        if not self.detected_format:
            self.logger.info("🔍 Format not detected - trying to infer from transaction patterns...")
            # Count which pattern matches more lines
            format_1_matches = sum(1 for line in lines if re.search(format_1_pattern, line))
            format_2_matches = sum(1 for line in lines if re.search(format_2_pattern, line))

            if format_1_matches > format_2_matches and format_1_matches >= 2:
                self.detected_format = 'format_1'
                self.logger.info(f"✅ Inferred format_1 from {format_1_matches} transaction lines")
            elif format_2_matches >= 2:
                self.detected_format = 'format_2'
                self.logger.info(f"✅ Inferred format_2 from {format_2_matches} transaction lines")
            else:
                self.logger.warning("⚠️ Could not infer format from transaction patterns")
                return

        transactions_found = 0

        for line in lines:
            line = line.strip()
            if not line or len(line) < 20:  # Skip short lines
                continue

            # Try Format 1 first
            match = re.search(format_1_pattern, line)
            if match and self.detected_format == 'format_1':
                try:
                    post_date_text = match.group(1)
                    debit_text = match.group(2) or ''
                    credit_text = match.group(3) or ''
                    balance_text = match.group(4) or ''

                    # Parse date
                    transaction_date = self._parse_format_1_date(post_date_text)
                    if not transaction_date:
                        continue

                    # Parse amounts
                    debit = self.clean_amount(debit_text)
                    credit = self.clean_amount(credit_text)
                    balance = self.clean_amount(balance_text)

                    # Extract description (everything between date and amounts)
                    desc_match = re.search(r'\d{2}:\d{2}\s+(.*?)\s+\d{1,3}(?:,\d{3})*', line)
                    description = desc_match.group(1).strip() if desc_match else ''

                    txn = StandardizedTransaction(
                        transaction_date=transaction_date,
                        posting_date=transaction_date,
                        effective_date=transaction_date,
                        description=description,
                        reference_number='',
                        debit=debit,
                        credit=credit,
                        balance=balance,
                        bank_name=self.BANK_NAME,
                        account_number=self.account_info.get('account_number', ''),
                        account_holder=self.account_info.get('account_holder', ''),
                        raw_data={'format': 'format_1_text', 'source': 'text_extraction'}
                    )
                    self.transactions.append(txn)
                    transactions_found += 1
                except Exception as e:
                    self.logger.warning(f"⚠️ Error parsing Format 1 text line: {e}")
                    continue

            # Try Format 2
            elif self.detected_format == 'format_2':
                match = re.search(format_2_pattern, line)
                if match:
                    try:
                        date_text = match.group(1)
                        description = match.group(2).strip()
                        debit_text = match.group(3) or ''
                        credit_text = match.group(4) or ''
                        balance_text = match.group(5) or ''

                        # Parse date
                        transaction_date = self._parse_format_2_date(date_text)
                        if not transaction_date:
                            continue

                        # Parse amounts
                        debit = self.clean_amount(debit_text)
                        credit = self.clean_amount(credit_text)
                        balance = self.clean_amount(balance_text)

                        txn = StandardizedTransaction(
                            transaction_date=transaction_date,
                            posting_date=transaction_date,
                            effective_date=transaction_date,
                            description=description,
                            reference_number='',
                            debit=debit,
                            credit=credit,
                            balance=balance,
                            bank_name=self.BANK_NAME,
                            account_number=self.account_info.get('account_number', ''),
                            account_holder=self.account_info.get('account_holder', ''),
                            raw_data={'format': 'format_2_text', 'source': 'text_extraction'}
                        )
                        self.transactions.append(txn)
                        transactions_found += 1
                    except Exception as e:
                        self.logger.warning(f"⚠️ Error parsing Format 2 text line: {e}")
                        continue

        self.logger.info(f"📝 Text extraction: {transactions_found} transactions found")
        if transactions_found == 0:
            self.logger.warning("⚠️ Text extraction failed - falling back to Smart Mapper")
