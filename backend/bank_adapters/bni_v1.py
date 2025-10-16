"""
Adapter untuk Bank BNI versi 1
Format: Tgl Trans, Uraian, Debet, Kredit, Saldo
"""

from typing import Dict, Any, List
from .base import BaseBankAdapter, StandardizedTransaction
from decimal import Decimal


class BniV1Adapter(BaseBankAdapter):
    """
    Adapter untuk Rekening Koran Bank BNI Versi 1
    Format sederhana dengan 5 kolom
    """

    BANK_NAME = "Bank BNI"
    BANK_CODE = "BNI_V1"

    DETECTION_KEYWORDS = [
        "BANK NEGARA INDONESIA",
        "PT BANK BNI",
        "TGL TRANS",
        "URAIAN",
        "DEBET",
        "KREDIT",
    ]

    def parse(self, ocr_result: Dict[str, Any]) -> List[StandardizedTransaction]:
        """
        Parse OCR result dari Bank BNI V1
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
        Extract informasi rekening BNI
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

        # BNI account number format: 0123456789 (10 digits)
        acc_match = re.search(r'(?:REKENING|NO\s*REK|ACCOUNT)[:\s]*(\d{10})', text, re.IGNORECASE)
        if acc_match:
            info['account_number'] = acc_match.group(1)

        # Extract account holder
        name_match = re.search(r'(?:NAMA|NAME)[:\s]*([A-Z\s.]+?)(?:\n|REKENING|TANGGAL)', text, re.IGNORECASE)
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
                if len(cells) < 5:
                    continue

                try:
                    # BNI V1: Tgl Trans | Uraian | Debet | Kredit | Saldo
                    tgl_trans = self.parse_date(cells[0].get('text', '').strip())
                    uraian = cells[1].get('text', '').strip()
                    debet = self.clean_amount(cells[2].get('text', '').strip())
                    kredit = self.clean_amount(cells[3].get('text', '').strip())
                    saldo = self.clean_amount(cells[4].get('text', '').strip())

                    if not tgl_trans:
                        continue

                    transaction = StandardizedTransaction(
                        transaction_date=tgl_trans,
                        description=uraian,
                        debit=debet,
                        credit=kredit,
                        balance=saldo,
                        bank_name=self.BANK_NAME,
                        account_number=self.account_info.get('account_number', ''),
                        account_holder=self.account_info.get('account_holder', ''),
                        raw_data={
                            'tgl_trans': cells[0].get('text', ''),
                            'uraian': uraian,
                        }
                    )

                    self.transactions.append(transaction)

                except Exception as e:
                    print(f"Error parsing BNI V1 row: {e}")
                    continue

    def _parse_from_text(self, ocr_result: Dict[str, Any]):
        """
        Parse transaksi dari raw text (fallback)
        """
        # TODO: Implement text-based parsing jika table detection gagal
        pass
