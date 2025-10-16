"""
Adapter untuk MUFG Bank
Format: Booking Date (Value Date), Debit, Credit, Balance, Transaction Type, References, Detail
"""

from typing import Dict, Any, List
from .base import BaseBankAdapter, StandardizedTransaction
from decimal import Decimal


class MufgBankAdapter(BaseBankAdapter):
    """
    Adapter untuk Rekening Koran MUFG Bank
    Special: Ada 2 tanggal (Booking Date & Value Date)
    """

    BANK_NAME = "MUFG Bank"
    BANK_CODE = "MUFG"

    DETECTION_KEYWORDS = [
        "MUFG BANK",
        "MITSUBISHI UFJ",
        "BOOKING DATE",
        "VALUE DATE",
        "CUSTOMER REFERENCE",
        "BANK REFERENCE",
    ]

    def parse(self, ocr_result: Dict[str, Any]) -> List[StandardizedTransaction]:
        """
        Parse OCR result dari MUFG Bank
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
        Extract informasi rekening MUFG
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

        # MUFG account number
        acc_match = re.search(r'(?:ACCOUNT|ACC\s*NO)[:\s]*(\d+[-]?\d*)', text, re.IGNORECASE)
        if acc_match:
            info['account_number'] = acc_match.group(1)

        # Extract account holder
        name_match = re.search(r'(?:NAME|ACCOUNT\s*NAME)[:\s]*([A-Z\s.&,]+?)(?:\n|ACCOUNT|ADDRESS)', text, re.IGNORECASE)
        if name_match:
            info['account_holder'] = name_match.group(1).strip()

        return info

    def _parse_from_tables(self, tables: List[Dict[str, Any]]):
        """
        Parse transaksi dari table structure
        MUFG format bisa bervariasi, common format:
        Booking Date | Value Date | Debit | Credit | Balance | Transaction Type | Customer Ref | Bank Ref | Detail
        """
        for table in tables:
            if 'rows' not in table:
                continue

            # Skip header row
            for row_idx, row in enumerate(table['rows']):
                if row_idx == 0:  # Skip header
                    continue

                cells = row.get('cells', [])
                if len(cells) < 5:  # Minimal: date, debit, credit, balance, detail
                    continue

                try:
                    # Flexible parsing - MUFG bisa punya banyak variasi kolom
                    booking_date = None
                    value_date = None
                    debit = Decimal('0.00')
                    credit = Decimal('0.00')
                    balance = Decimal('0.00')
                    transaction_type = ""
                    customer_ref = ""
                    bank_ref = ""
                    detail = ""

                    # Parse based on column count
                    if len(cells) >= 8:
                        # Full format: Booking | Value | Debit | Credit | Balance | Type | CustRef | BankRef | Detail
                        booking_date = self.parse_date(cells[0].get('text', '').strip())
                        value_date = self.parse_date(cells[1].get('text', '').strip())
                        debit = self.clean_amount(cells[2].get('text', '').strip())
                        credit = self.clean_amount(cells[3].get('text', '').strip())
                        balance = self.clean_amount(cells[4].get('text', '').strip())
                        transaction_type = cells[5].get('text', '').strip()
                        customer_ref = cells[6].get('text', '').strip()

                        if len(cells) >= 9:
                            bank_ref = cells[7].get('text', '').strip()
                            detail = cells[8].get('text', '').strip()
                        else:
                            detail = cells[7].get('text', '').strip()

                    elif len(cells) >= 5:
                        # Simplified format: Date | Debit | Credit | Balance | Detail
                        booking_date = self.parse_date(cells[0].get('text', '').strip())
                        debit = self.clean_amount(cells[1].get('text', '').strip())
                        credit = self.clean_amount(cells[2].get('text', '').strip())
                        balance = self.clean_amount(cells[3].get('text', '').strip())
                        detail = cells[4].get('text', '').strip()

                    # Use booking date as main transaction date, value date as effective date
                    transaction_date = booking_date or value_date
                    if not transaction_date:
                        continue

                    transaction = StandardizedTransaction(
                        transaction_date=transaction_date,
                        effective_date=value_date,
                        posting_date=booking_date,
                        description=detail,
                        transaction_type=transaction_type,
                        reference_number=customer_ref,
                        debit=debit,
                        credit=credit,
                        balance=balance,
                        additional_info=f"Bank Ref: {bank_ref}" if bank_ref else "",
                        bank_name=self.BANK_NAME,
                        account_number=self.account_info.get('account_number', ''),
                        account_holder=self.account_info.get('account_holder', ''),
                        raw_data={
                            'booking_date': cells[0].get('text', '') if len(cells) >= 8 else '',
                            'value_date': cells[1].get('text', '') if len(cells) >= 8 else '',
                            'transaction_type': transaction_type,
                            'customer_reference': customer_ref,
                            'bank_reference': bank_ref,
                        }
                    )

                    self.transactions.append(transaction)

                except Exception as e:
                    print(f"Error parsing MUFG row: {e}")
                    continue

    def _parse_from_text(self, ocr_result: Dict[str, Any]):
        """
        Parse transaksi dari raw text (fallback)
        """
        # TODO: Implement text-based parsing
        pass
