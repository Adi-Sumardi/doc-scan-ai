"""
Adapter untuk OCBC Bank
Format: Tgl Trans/Trans Date, Tgl Valuta/Value Date, Uraian/Description, Debet/Debit, Kredit/Credit, Saldo/Balance
"""

from typing import Dict, Any, List
from .base import BaseBankAdapter, StandardizedTransaction
from decimal import Decimal


class OcbcBankAdapter(BaseBankAdapter):
    """
    Adapter untuk Rekening Koran OCBC Bank
    Format bilingual (Indonesia/English)
    """

    BANK_NAME = "OCBC Bank"
    BANK_CODE = "OCBC"

    DETECTION_KEYWORDS = [
        "OCBC BANK",
        "PT BANK OCBC",
        "OCBC NISP",
        "TGL TRANS",
        "TRANS DATE",
        "TGL VALUTA",
        "VALUE DATE",
    ]

    def parse(self, ocr_result: Dict[str, Any]) -> List[StandardizedTransaction]:
        """
        Parse OCR result dari OCBC Bank
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
        Extract informasi rekening OCBC
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

        # OCBC account number (bisa berbagai format)
        acc_patterns = [
            r'(?:ACCOUNT|REKENING|ACC\s*NO)[:\s]*(\d{10,16})',
            r'(?:NO\s*REK)[:\s]*(\d{10,16})',
        ]

        for pattern in acc_patterns:
            acc_match = re.search(pattern, text, re.IGNORECASE)
            if acc_match:
                info['account_number'] = acc_match.group(1)
                break

        # Extract account holder
        name_patterns = [
            r'(?:NAME|NAMA|PEMILIK)[:\s]*([A-Z\s.&,]+?)(?:\n|ACCOUNT|ADDRESS|ALAMAT)',
        ]

        for pattern in name_patterns:
            name_match = re.search(pattern, text, re.IGNORECASE)
            if name_match:
                info['account_holder'] = name_match.group(1).strip()
                break

        return info

    def _parse_from_tables(self, tables: List[Dict[str, Any]]):
        """
        Parse transaksi dari table structure
        OCBC: Tgl Trans/Trans Date | Tgl Valuta/Value Date | Uraian/Description | Debet/Debit | Kredit/Credit | Saldo/Balance
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
                    # OCBC format: Tgl Trans | Tgl Valuta | Uraian | Debet | Kredit | Saldo
                    tgl_trans = self.parse_date(cells[0].get('text', '').strip())
                    tgl_valuta = self.parse_date(cells[1].get('text', '').strip())
                    uraian = cells[2].get('text', '').strip()
                    debet = self.clean_amount(cells[3].get('text', '').strip())
                    kredit = self.clean_amount(cells[4].get('text', '').strip())
                    saldo = self.clean_amount(cells[5].get('text', '').strip())

                    # Use tgl_trans as main transaction date
                    transaction_date = tgl_trans or tgl_valuta
                    if not transaction_date:
                        continue

                    transaction = StandardizedTransaction(
                        transaction_date=transaction_date,
                        posting_date=tgl_trans,
                        effective_date=tgl_valuta,
                        description=uraian,
                        debit=debet,
                        credit=kredit,
                        balance=saldo,
                        bank_name=self.BANK_NAME,
                        account_number=self.account_info.get('account_number', ''),
                        account_holder=self.account_info.get('account_holder', ''),
                        raw_data={
                            'tgl_trans': cells[0].get('text', ''),
                            'tgl_valuta': cells[1].get('text', ''),
                            'uraian': uraian,
                        }
                    )

                    self.transactions.append(transaction)

                except Exception as e:
                    print(f"Error parsing OCBC row: {e}")
                    continue

    def _parse_from_text(self, ocr_result: Dict[str, Any]):
        """
        Parse transaksi dari raw text (fallback)
        Format OCBC: Date | Description | Debit | Credit | Balance
        """
        text = self.extract_text_from_ocr(ocr_result)
        if not text:
            return

        import re

        # ✅ FIX: Regex pattern untuk OCBC
        pattern = r'(\d{1,2}[/.-]\d{1,2}(?:[/.-]\d{2,4})?)\s+(.+?)\s+([\d,.-]+(?:\.\d{2})?)\s+([\d,.-]+(?:\.\d{2})?)\s+([\d,.-]+(?:\.\d{2})?)'

        matches = re.finditer(pattern, text, re.MULTILINE)

        for match in matches:
            try:
                date_str = match.group(1)
                description = match.group(2).strip()
                debit_str = match.group(3).strip()
                credit_str = match.group(4).strip()
                balance_str = match.group(5).strip()

                date = self.parse_date(date_str)
                if not date:
                    continue

                debit = self.clean_amount(debit_str)
                credit = self.clean_amount(credit_str)
                balance = self.clean_amount(balance_str)

                transaction = StandardizedTransaction(
                    transaction_date=date,
                    description=description,
                    debit=debit,
                    credit=credit,
                    balance=balance,
                    bank_name=self.BANK_NAME,
                    account_number=self.account_info.get('account_number', ''),
                    account_holder=self.account_info.get('account_holder', ''),
                    raw_data={'date': date_str, 'description': description, 'source': 'text_fallback'}
                )

                self.transactions.append(transaction)

            except Exception as e:
                continue
