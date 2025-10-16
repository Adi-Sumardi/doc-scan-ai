"""
Adapter untuk Bank BRI
Format: Tanggal Transaksi, Uraian Transaksi, Teller, Debet, Kredit, Saldo
"""

from typing import Dict, Any, List
from .base import BaseBankAdapter, StandardizedTransaction
from decimal import Decimal


class BriAdapter(BaseBankAdapter):
    """
    Adapter untuk Rekening Koran Bank BRI
    Unique: Ada kolom Teller
    """

    BANK_NAME = "Bank BRI"
    BANK_CODE = "BRI"

    DETECTION_KEYWORDS = [
        "BANK RAKYAT INDONESIA",
        "PT BANK BRI",
        "PT. BANK BRI",
        "TANGGAL TRANSAKSI",
        "URAIAN TRANSAKSI",
        "TELLER",
    ]

    def parse(self, ocr_result: Dict[str, Any]) -> List[StandardizedTransaction]:
        """
        Parse OCR result dari Bank BRI
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
        Extract informasi rekening BRI
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

        # BRI account number format bisa berbeda, coba pattern umum
        acc_match = re.search(r'(?:REKENING|NO\s*REK|ACCOUNT)[:\s]*(\d{10,16})', text, re.IGNORECASE)
        if acc_match:
            info['account_number'] = acc_match.group(1)

        # Extract account holder
        name_match = re.search(r'(?:NAMA|NAME|PEMILIK)[:\s]*([A-Z\s.]+?)(?:\n|REKENING|NO)', text, re.IGNORECASE)
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
                if len(cells) < 6:
                    continue

                try:
                    # BRI: Tanggal Transaksi | Uraian Transaksi | Teller | Debet | Kredit | Saldo
                    tanggal = self.parse_date(cells[0].get('text', '').strip())
                    uraian = cells[1].get('text', '').strip()
                    teller = cells[2].get('text', '').strip()
                    debet = self.clean_amount(cells[3].get('text', '').strip())
                    kredit = self.clean_amount(cells[4].get('text', '').strip())
                    saldo = self.clean_amount(cells[5].get('text', '').strip())

                    if not tanggal:
                        continue

                    transaction = StandardizedTransaction(
                        transaction_date=tanggal,
                        description=uraian,
                        teller=teller,  # Unique untuk BRI!
                        debit=debet,
                        credit=kredit,
                        balance=saldo,
                        bank_name=self.BANK_NAME,
                        account_number=self.account_info.get('account_number', ''),
                        account_holder=self.account_info.get('account_holder', ''),
                        raw_data={
                            'tanggal': cells[0].get('text', ''),
                            'uraian': uraian,
                            'teller': teller,
                        }
                    )

                    self.transactions.append(transaction)

                except Exception as e:
                    print(f"Error parsing BRI row: {e}")
                    continue

    def _parse_from_text(self, ocr_result: Dict[str, Any]):
        """
        Parse transaksi dari raw text (fallback)
        """
        # TODO: Implement text-based parsing
        pass
