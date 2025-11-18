"""
Adapter untuk Bank Mandiri versi 1
Format: Posting Date, Remark, Reference No, Debit, Credit, Balance
"""

from typing import Dict, Any, List
from .base import BaseBankAdapter, StandardizedTransaction
from decimal import Decimal


class MandiriV1Adapter(BaseBankAdapter):
    """
    Adapter untuk Rekening Koran Bank Mandiri Versi 1
    """

    BANK_NAME = "Bank Mandiri"
    BANK_CODE = "MANDIRI_V1"

    DETECTION_KEYWORDS = [
        "PT BANK MANDIRI",
        "BANK MANDIRI (PERSERO)",
        "POSTING DATE",
        "REMARK",
    ]

    def parse(self, ocr_result: Dict[str, Any]) -> List[StandardizedTransaction]:
        """
        Parse OCR result dari Bank Mandiri V1
        """
        self.raw_ocr_data = ocr_result
        self.transactions = []

        # Extract account info
        self.account_info = self.extract_account_info(ocr_result)

        # Parse transactions dari table atau text
        if 'tables' in ocr_result:
            self._parse_from_tables(ocr_result['tables'])
        else:
            self._parse_from_text(ocr_result)

        return self.transactions

    def extract_account_info(self, ocr_result: Dict[str, Any]) -> Dict[str, str]:
        """
        Extract informasi rekening
        """
        text = self.extract_text_from_ocr(ocr_result)
        info = {
            'bank_name': self.BANK_NAME,
            'account_number': '',
            'account_holder': '',
            'period_start': '',
            'period_end': '',
        }

        # Extract account number (format: 123-45-67890123-4)
        import re
        acc_match = re.search(r'(\d{3}-\d{2}-\d{8,11}-\d)', text)
        if acc_match:
            info['account_number'] = acc_match.group(1)

        # Extract account holder name (biasanya setelah "NAMA" atau sebelum account number)
        name_match = re.search(r'NAMA[:\s]+([A-Z\s.]+?)(?:\n|ACCOUNT|NOMOR)', text, re.IGNORECASE)
        if name_match:
            info['account_holder'] = name_match.group(1).strip()

        return info

    def _parse_from_tables(self, tables: List[Dict[str, Any]]):
        """
        Parse transaksi dari table structure
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
                    # Mandiri V1: Posting Date | Remark | Reference No | Debit | Credit | Balance
                    posting_date = self.parse_date(cells[0].get('text', '').strip())
                    remark = cells[1].get('text', '').strip()
                    ref_no = cells[2].get('text', '').strip()
                    debit = self.clean_amount(cells[3].get('text', '').strip())
                    credit = self.clean_amount(cells[4].get('text', '').strip())
                    balance = self.clean_amount(cells[5].get('text', '').strip())

                    if not posting_date:
                        continue

                    transaction = StandardizedTransaction(
                        transaction_date=posting_date,
                        posting_date=posting_date,
                        description=remark,
                        transaction_type="",
                        reference_number=ref_no,
                        debit=debit,
                        credit=credit,
                        balance=balance,
                        bank_name=self.BANK_NAME,
                        account_number=self.account_info.get('account_number', ''),
                        account_holder=self.account_info.get('account_holder', ''),
                        raw_data={
                            'posting_date': cells[0].get('text', ''),
                            'remark': remark,
                            'reference_no': ref_no,
                        }
                    )

                    self.transactions.append(transaction)

                except Exception as e:
                    # Skip rows with parsing errors
                    print(f"Error parsing Mandiri V1 row: {e}")
                    continue

    def _parse_from_text(self, ocr_result: Dict[str, Any]):
        """
        Parse transaksi dari raw text (fallback)
        Format Mandiri V1: Tanggal | Keterangan | Debet | Kredit | Saldo
        """
        text = self.extract_text_from_ocr(ocr_result)
        if not text:
            return

        import re

        # ✅ FIX: Regex pattern untuk Mandiri V1
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
