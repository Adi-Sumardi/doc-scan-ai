"""
Adapter untuk Permata Bank
Format: Post Date, Eff Date, Transaction Code, Cheque Number, Ref No, Customer No, Description, Debit, Credit, Total
"""

from typing import Dict, Any, List
from .base import BaseBankAdapter, StandardizedTransaction
from decimal import Decimal


class PermataBankAdapter(BaseBankAdapter):
    """
    Adapter untuk Rekening Koran Permata Bank
    Special: Ada Post Date dan Eff Date terpisah
    """

    BANK_NAME = "Permata Bank"
    BANK_CODE = "PERMATA"

    DETECTION_KEYWORDS = [
        "BANK PERMATA",
        "PERMATA BANK",
        "PT BANK PERMATA",
        "POST DATE",
        "EFF DATE",
        "TRANSACTION CODE",
    ]

    def parse(self, ocr_result: Dict[str, Any]) -> List[StandardizedTransaction]:
        """
        Parse OCR result dari Permata Bank
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
        Extract informasi rekening Permata
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

        # Permata account number
        acc_match = re.search(r'(?:ACCOUNT|NO\s*REK)[:\s]*(\d{10,16})', text, re.IGNORECASE)
        if acc_match:
            info['account_number'] = acc_match.group(1)

        # Extract account holder
        name_match = re.search(r'(?:NAME|NAMA)[:\s]*([A-Z\s.]+?)(?:\n|ACCOUNT|ADDRESS)', text, re.IGNORECASE)
        if name_match:
            info['account_holder'] = name_match.group(1).strip()

        return info

    def _parse_from_tables(self, tables: List[Dict[str, Any]]):
        """
        Parse transaksi dari table structure
        Permata: Post Date | Eff Date | Transaction Code | Cheque | Ref No | Customer No | Description | Debit | Credit | Total
        """
        for table in tables:
            if 'rows' not in table:
                continue

            # Skip header row
            for row_idx, row in enumerate(table['rows']):
                if row_idx == 0:  # Skip header
                    continue

                cells = row.get('cells', [])
                # ✅ FIXED: Check minimum required cells for Permata
                if len(cells) < 7:  # Permata needs at least 7 columns
                    continue

                try:
                    post_date = None
                    eff_date = None
                    transaction_code = ""
                    cheque_number = ""
                    ref_no = ""
                    customer_no = ""
                    description = ""
                    debit = Decimal('0.00')
                    credit = Decimal('0.00')
                    total = Decimal('0.00')

                    # ✅ SAFE ACCESSOR: Parse based on exact column count
                    if len(cells) == 10:
                        # Full format: Post Date | Eff Date | Trans Code | Cheque | Ref | Cust No | Desc | Debit | Credit | Total
                        post_date_str = self.safe_get_cell(cells, 0)
                        eff_date_str = self.safe_get_cell(cells, 1)
                        transaction_code = self.safe_get_cell(cells, 2)
                        cheque_number = self.safe_get_cell(cells, 3)
                        ref_no = self.safe_get_cell(cells, 4)
                        customer_no = self.safe_get_cell(cells, 5)
                        description = self.safe_get_cell(cells, 6)
                        debit_str = self.safe_get_cell(cells, 7)
                        credit_str = self.safe_get_cell(cells, 8)
                        total_str = self.safe_get_cell(cells, 9)
                        
                        post_date = self.parse_date(post_date_str)
                        eff_date = self.parse_date(eff_date_str)
                        debit = self.clean_amount(debit_str)
                        credit = self.clean_amount(credit_str)
                        total = self.clean_amount(total_str)

                    elif len(cells) == 7:
                        # Simplified: Eff Date | Trans Code | Desc | Debit | Credit | Total | Ref
                        eff_date_str = self.safe_get_cell(cells, 0)
                        transaction_code = self.safe_get_cell(cells, 1)
                        description = self.safe_get_cell(cells, 2)
                        debit_str = self.safe_get_cell(cells, 3)
                        credit_str = self.safe_get_cell(cells, 4)
                        total_str = self.safe_get_cell(cells, 5)
                        ref_no = self.safe_get_cell(cells, 6)
                        
                        eff_date = self.parse_date(eff_date_str)
                        debit = self.clean_amount(debit_str)
                        credit = self.clean_amount(credit_str)
                        total = self.clean_amount(total_str)
                    else:
                        # Unexpected column count, log and skip
                        self.logger.warning(f"⚠️ Permata: Unexpected column count: {len(cells)}, expected 7 or 10")
                        continue

                    # Use eff_date as main transaction date
                    transaction_date = eff_date or post_date
                    if not transaction_date:
                        continue

                    # Reference number: prioritize cheque number if exists, else use ref_no
                    reference = cheque_number if cheque_number else ref_no

                    transaction = StandardizedTransaction(
                        transaction_date=transaction_date,
                        posting_date=post_date,
                        effective_date=eff_date,
                        description=description,
                        transaction_type=transaction_code,
                        reference_number=reference,
                        debit=debit,
                        credit=credit,
                        balance=total,
                        additional_info=f"Customer No: {customer_no}" if customer_no else "",
                        bank_name=self.BANK_NAME,
                        account_number=self.account_info.get('account_number', ''),
                        account_holder=self.account_info.get('account_holder', ''),
                        raw_data={
                            'post_date': post_date_str if len(cells) == 10 else '',
                            'eff_date': eff_date_str,
                            'transaction_code': transaction_code,
                            'cheque_number': cheque_number,
                            'ref_no': ref_no,
                            'customer_no': customer_no,
                        }
                    )

                    self.transactions.append(transaction)

                except Exception as e:
                    print(f"Error parsing Permata row: {e}")
                    continue

    def _parse_from_text(self, ocr_result: Dict[str, Any]):
        """
        Parse transaksi dari raw text (fallback)
        Format Permata: Date | Description | Debit | Credit | Balance
        """
        self.logger.info("📝 No table structure - using text-based extraction")

        text = self.extract_text_from_ocr(ocr_result)
        if not text:
            self.logger.warning("⚠️ No text found in OCR result")
            return

        import re

        # ✅ FIX: Regex pattern untuk Permata
        pattern = r'(\d{1,2}[/.-]\d{1,2}(?:[/.-]\d{2,4})?)\s+(.+?)\s+([\d,.-]+(?:\.\d{2})?)\s+([\d,.-]+(?:\.\d{2})?)\s+([\d,.-]+(?:\.\d{2})?)'

        matches = re.finditer(pattern, text, re.MULTILINE)
        transactions_found = 0

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
                transactions_found += 1

            except Exception as e:
                continue

        self.logger.info(f"📝 Text extraction: {transactions_found} transactions found")
        if transactions_found == 0:
            self.logger.warning("⚠️ Text extraction failed - falling back to Smart Mapper")
