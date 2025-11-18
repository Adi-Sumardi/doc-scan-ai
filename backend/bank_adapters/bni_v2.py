"""
Adapter untuk Bank BNI versi 2
Format: Posting Date, Effective Date, Branch, Journal, Transaction Description, Amount, DB/CR, Balance
"""

from typing import Dict, Any, List, Tuple
from .base import BaseBankAdapter, StandardizedTransaction
from decimal import Decimal


class BniV2Adapter(BaseBankAdapter):
    """
    Adapter untuk Rekening Koran Bank BNI Versi 2
    Special: Ada DB/CR flag untuk distinguish debit/credit
    """

    BANK_NAME = "Bank BNI"
    BANK_CODE = "BNI_V2"

    DETECTION_KEYWORDS = [
        "BANK NEGARA INDONESIA",
        "PT BANK BNI",
        "POSTING DATE",
        "EFFECTIVE DATE",
        "DB/CR",
        "JOURNAL",
    ]

    def parse(self, ocr_result: Dict[str, Any]) -> List[StandardizedTransaction]:
        """
        Parse OCR result dari Bank BNI V2
        """
        self.raw_ocr_data = ocr_result
        self.transactions = []

        # Extract account info
        self.account_info = self.extract_account_info(ocr_result)

        # Parse transactions
        if 'tables' in ocr_result:
            self._parse_from_tables(ocr_result['tables'])
        else:
            self._parse_from_text(ocr_result)

        return self.transactions

    def extract_account_info(self, ocr_result: Dict[str, Any]) -> Dict[str, str]:
        """
        Extract informasi rekening BNI V2
        """
        text = self.extract_text_from_ocr(ocr_result)
        info = {
            'bank_name': self.BANK_NAME,
            'account_number': '',
            'account_holder': '',
            'period_start': '',
            'period_end': '',
        }

        import re

        # BNI account number
        acc_match = re.search(r'(?:ACCOUNT|REKENING)[:\s]*(\d{10,16})', text, re.IGNORECASE)
        if acc_match:
            info['account_number'] = acc_match.group(1)

        # Extract account holder
        name_match = re.search(r'(?:NAME|NAMA)[:\s]*([A-Z\s.]+?)(?:\n|ACCOUNT|ADDRESS)', text, re.IGNORECASE)
        if name_match:
            info['account_holder'] = name_match.group(1).strip()

        return info

    def _parse_db_cr(self, db_cr_flag: str, amount: Decimal) -> Tuple[Decimal, Decimal]:
        """
        Parse DB/CR flag untuk determine debit atau credit

        Args:
            db_cr_flag: "DB", "CR", "DEBIT", "CREDIT", "D", "C"
            amount: Jumlah transaksi

        Returns:
            Tuple[debit, credit]
        """
        flag_upper = db_cr_flag.upper().strip()

        # Check debit indicators
        if flag_upper in ['DB', 'DEBIT', 'D', 'DR']:
            return (amount, Decimal('0.00'))  # (debit, credit)

        # Check credit indicators
        elif flag_upper in ['CR', 'CREDIT', 'C', 'K', 'KREDIT']:
            return (Decimal('0.00'), amount)  # (debit, credit)

        # Default: assume credit if unclear
        return (Decimal('0.00'), amount)

    def _parse_from_tables(self, tables: List[Dict[str, Any]]):
        """
        Parse transaksi dari table structure
        BNI V2: Posting Date | Effective Date | Branch | Journal | Trans Desc | Amount | DB/CR | Balance
        """
        for table in tables:
            if 'rows' not in table:
                continue

            # Skip header row
            for row_idx, row in enumerate(table['rows']):
                if row_idx == 0:  # Skip header
                    continue

                cells = row.get('cells', [])
                # ✅ FIX: Be lenient for synthetic tables (1 cell per line)
                if len(cells) < 1:  # Reduced from 6 to 1
                    continue

                try:
                    posting_date = None
                    effective_date = None
                    branch = ""
                    journal = ""
                    description = ""
                    amount = Decimal('0.00')
                    db_cr = ""
                    balance = Decimal('0.00')

                    if len(cells) >= 8:
                        # Full format: Post Date | Eff Date | Branch | Journal | Desc | Amount | DB/CR | Balance
                        posting_date = self.parse_date(cells[0].get('text', '').strip())
                        effective_date = self.parse_date(cells[1].get('text', '').strip())
                        branch = cells[2].get('text', '').strip()
                        journal = cells[3].get('text', '').strip()
                        description = cells[4].get('text', '').strip()
                        amount = self.clean_amount(cells[5].get('text', '').strip())
                        db_cr = cells[6].get('text', '').strip()
                        balance = self.clean_amount(cells[7].get('text', '').strip())

                    elif len(cells) >= 6:
                        # Simplified: Date | Desc | Amount | DB/CR | Balance | Journal
                        effective_date = self.parse_date(cells[0].get('text', '').strip())
                        description = cells[1].get('text', '').strip()
                        amount = self.clean_amount(cells[2].get('text', '').strip())
                        db_cr = cells[3].get('text', '').strip()
                        balance = self.clean_amount(cells[4].get('text', '').strip())
                        journal = cells[5].get('text', '').strip() if len(cells) > 5 else ""

                    # Use effective date as main transaction date
                    transaction_date = effective_date or posting_date
                    if not transaction_date:
                        continue

                    # Parse DB/CR
                    debit, credit = self._parse_db_cr(db_cr, amount)

                    transaction = StandardizedTransaction(
                        transaction_date=transaction_date,
                        posting_date=posting_date,
                        effective_date=effective_date,
                        description=description,
                        reference_number=journal,
                        debit=debit,
                        credit=credit,
                        balance=balance,
                        branch_code=branch,
                        bank_name=self.BANK_NAME,
                        account_number=self.account_info.get('account_number', ''),
                        account_holder=self.account_info.get('account_holder', ''),
                        raw_data={
                            'posting_date': cells[0].get('text', '') if len(cells) >= 8 else '',
                            'effective_date': cells[1].get('text', '') if len(cells) >= 8 else cells[0].get('text', ''),
                            'branch': branch,
                            'journal': journal,
                            'db_cr': db_cr,
                        }
                    )

                    self.transactions.append(transaction)

                except Exception as e:
                    print(f"Error parsing BNI V2 row: {e}")
                    continue

    def _parse_from_text(self, ocr_result: Dict[str, Any]):
        """
        Parse transaksi dari raw text (fallback)
        Format BNI V2: Tanggal | Keterangan | Debet | Kredit | Saldo
        """
        text = self.extract_text_from_ocr(ocr_result)
        if not text:
            return

        import re

        # ✅ FIX: Regex pattern untuk BNI V2
        pattern = r'(\d{1,2}[/.-]\d{1,2}(?:[/.-]\d{2,4})?)\s+(.+?)\s+([\d,.-]+(?:\.\d{2})?)\s+([\d,.-]+(?:\.\d{2})?)\s+([\d,.-]+(?:\.\d{2})?)'

        matches = re.finditer(pattern, text, re.MULTILINE)

        for match in matches:
            try:
                tgl_str = match.group(1)
                keterangan = match.group(2).strip()
                debet_str = match.group(3).strip()
                kredit_str = match.group(4).strip()
                saldo_str = match.group(5).strip()

                tgl = self.parse_date(tgl_str)
                if not tgl:
                    continue

                debet = self.clean_amount(debet_str)
                kredit = self.clean_amount(kredit_str)
                saldo = self.clean_amount(saldo_str)

                transaction = StandardizedTransaction(
                    transaction_date=tgl,
                    description=keterangan,
                    debit=debet,
                    credit=kredit,
                    balance=saldo,
                    bank_name=self.BANK_NAME,
                    account_number=self.account_info.get('account_number', ''),
                    account_holder=self.account_info.get('account_holder', ''),
                    raw_data={'tanggal': tgl_str, 'keterangan': keterangan, 'source': 'text_fallback'}
                )

                self.transactions.append(transaction)

            except Exception as e:
                continue
