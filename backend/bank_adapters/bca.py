"""
Adapter untuk BCA (Bank Central Asia)
Format: Tanggal (lengkap dengan tahun), Keterangan, CBG, Mutasi, Saldo
"""

from typing import Dict, Any, List
from .base import BaseBankAdapter, StandardizedTransaction
from decimal import Decimal


class BcaAdapter(BaseBankAdapter):
    """
    Adapter untuk Rekening Koran BCA (reguler, bukan syariah)
    Special: Tanggal harus lengkap dengan tahun, ada CBG (Cabang), Mutasi bisa (+) atau (-)
    """

    BANK_NAME = "Bank BCA"
    BANK_CODE = "BCA"

    DETECTION_KEYWORDS = [
        "BANK CENTRAL ASIA",
        "PT BANK CENTRAL ASIA",
        "BCA",
        "KETERANGAN",
        "CBG",
        "MUTASI",
        # Pastikan bukan BCA Syariah
        # BCA Syariah akan detect duluan karena ada di ADAPTERS list sebelum ini
    ]

    def parse(self, ocr_result: Dict[str, Any]) -> List[StandardizedTransaction]:
        """
        Parse OCR result dari BCA
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
        Extract informasi rekening BCA
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

        # BCA account number (10-13 digits)
        acc_match = re.search(r'(?:REKENING|NO\s*REK|ACCOUNT)[:\s]*(\d{10,13})', text, re.IGNORECASE)
        if acc_match:
            info['account_number'] = acc_match.group(1)

        # Extract account holder
        name_match = re.search(r'(?:NAMA|NAME|PEMILIK)[:\s]*([A-Z\s.&,]+?)(?:\n|REKENING|NO|ALAMAT)', text, re.IGNORECASE)
        if name_match:
            info['account_holder'] = name_match.group(1).strip()

        return info

    def _parse_mutasi(self, mutasi_str: str) -> tuple:
        """
        Parse mutasi string menjadi debit/credit
        Mutasi bisa:
        - "1,000,000.00" (positif = credit)
        - "(1,000,000.00)" atau "-1,000,000.00" (negatif = debit)
        - "1,000,000.00 CR" atau "1,000,000.00 DB"

        Returns:
            tuple: (debit, credit)
        """
        mutasi_str = mutasi_str.strip()

        # Check for explicit CR/DB markers
        if 'CR' in mutasi_str.upper() or '+' in mutasi_str:
            # Credit
            amount = self.clean_amount(mutasi_str.replace('CR', '').replace('+', ''))
            return (Decimal('0.00'), amount)

        elif 'DB' in mutasi_str.upper() or 'DR' in mutasi_str.upper():
            # Debit
            amount = self.clean_amount(mutasi_str.replace('DB', '').replace('DR', ''))
            return (amount, Decimal('0.00'))

        # Check for parentheses (negative = debit)
        elif mutasi_str.startswith('(') and mutasi_str.endswith(')'):
            # Debit
            amount = self.clean_amount(mutasi_str.strip('()'))
            return (amount, Decimal('0.00'))

        # Check for negative sign
        elif mutasi_str.startswith('-'):
            # Debit
            amount = self.clean_amount(mutasi_str.lstrip('-'))
            return (amount, Decimal('0.00'))

        else:
            # Default: positive = credit (pemasukan)
            amount = self.clean_amount(mutasi_str)
            return (Decimal('0.00'), amount)

    def _parse_from_tables(self, tables: List[Dict[str, Any]]):
        """
        Parse transaksi dari table structure
        BCA: Tanggal | Keterangan | CBG | Mutasi | Saldo
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
                    # BCA: Tanggal | Keterangan | CBG | Mutasi | Saldo
                    tanggal_str = cells[0].get('text', '').strip()
                    keterangan = cells[1].get('text', '').strip()
                    cbg = cells[2].get('text', '').strip()
                    mutasi_str = cells[3].get('text', '').strip()
                    saldo = self.clean_amount(cells[4].get('text', '').strip())

                    # Parse tanggal (harus lengkap dengan tahun)
                    tanggal = self.parse_date(tanggal_str, formats=[
                        '%d/%m/%Y',
                        '%d-%m-%Y',
                        '%d.%m.%Y',
                        '%d %b %Y',
                        '%d %B %Y',
                    ])

                    if not tanggal:
                        continue

                    # Parse mutasi ke debit/credit
                    debit, credit = self._parse_mutasi(mutasi_str)

                    transaction = StandardizedTransaction(
                        transaction_date=tanggal,
                        description=keterangan,
                        branch_code=cbg,
                        debit=debit,
                        credit=credit,
                        balance=saldo,
                        bank_name=self.BANK_NAME,
                        account_number=self.account_info.get('account_number', ''),
                        account_holder=self.account_info.get('account_holder', ''),
                        raw_data={
                            'tanggal': tanggal_str,
                            'keterangan': keterangan,
                            'cbg': cbg,
                            'mutasi': mutasi_str,
                        }
                    )

                    self.transactions.append(transaction)

                except Exception as e:
                    print(f"Error parsing BCA row: {e}")
                    continue

    def _parse_from_text(self, ocr_result: Dict[str, Any]):
        """
        Parse transaksi dari raw text (fallback)
        Format BCA: Tanggal | Keterangan | CBG | Mutasi | Saldo
        """
        text = self.extract_text_from_ocr(ocr_result)
        if not text:
            return

        import re
        from datetime import datetime

        # ✅ FIX: Regex pattern untuk transaksi BCA
        # Pattern: DD/MM/YYYY ... KETERANGAN ... CBG ... MUTASI ... SALDO
        # Example: "01/01/2025 TRANSFER 001 1,000,000.00 10,000,000.00"
        pattern = r'(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})\s+(.+?)\s+(\d{3})\s+([\d,.-]+(?:\.\d{2})?)\s+([\d,.-]+(?:\.\d{2})?)'

        matches = re.finditer(pattern, text, re.MULTILINE)

        for match in matches:
            try:
                tanggal_str = match.group(1)
                keterangan = match.group(2).strip()
                cbg = match.group(3)
                mutasi_str = match.group(4).strip()
                saldo_str = match.group(5).strip()

                # Parse tanggal
                tanggal = self.parse_date(tanggal_str, formats=[
                    '%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y',
                    '%d %b %Y', '%d %B %Y',
                ])

                if not tanggal:
                    continue

                # Parse mutasi ke debit/credit
                debit, credit = self._parse_mutasi(mutasi_str)

                # Parse saldo
                saldo = self.clean_amount(saldo_str)

                transaction = StandardizedTransaction(
                    transaction_date=tanggal,
                    description=keterangan,
                    branch_code=cbg,
                    debit=debit,
                    credit=credit,
                    balance=saldo,
                    bank_name=self.BANK_NAME,
                    account_number=self.account_info.get('account_number', ''),
                    account_holder=self.account_info.get('account_holder', ''),
                    raw_data={
                        'tanggal': tanggal_str,
                        'keterangan': keterangan,
                        'cbg': cbg,
                        'mutasi': mutasi_str,
                        'source': 'text_fallback'  # Mark as text-based parsing
                    }
                )

                self.transactions.append(transaction)

            except Exception as e:
                # Silent fail - regex might match non-transaction text
                continue
