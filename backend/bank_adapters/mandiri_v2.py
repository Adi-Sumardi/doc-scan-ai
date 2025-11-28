"""
Adapter untuk Bank Mandiri versi 2
Format: Nama, Nomer Rekening, Tanggal Transaksi, Ket. Kode Transaksi, Jenis Trans, Remark, Amount, Saldo
"""

from typing import Dict, Any, List, Tuple
from .base import BaseBankAdapter, StandardizedTransaction
from decimal import Decimal


class MandiriV2Adapter(BaseBankAdapter):
    """
    Adapter untuk Rekening Koran Bank Mandiri Versi 2
    Special: Amount perlu di-parse dari context (debit/credit detection)
    """

    BANK_NAME = "Bank Mandiri"
    BANK_CODE = "MANDIRI_V2"

    DETECTION_KEYWORDS = [
        "PT BANK MANDIRI",
        "BANK MANDIRI (PERSERO)",
        "KET. KODE TRANSAKSI",
        "JENIS TRANS",
        "NOMER REKENING",  # Typo di format asli bank
    ]

    def parse(self, ocr_result: Dict[str, Any]) -> List[StandardizedTransaction]:
        """
        Parse OCR result dari Bank Mandiri V2
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
        Extract informasi rekening Mandiri V2
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

        # Mandiri account format: 123-45-67890123-4
        acc_match = re.search(r'(\d{3}-\d{2}-\d{8,11}-\d)', text)
        if acc_match:
            info['account_number'] = acc_match.group(1)

        # Extract account holder
        name_match = re.search(r'(?:NAMA|NAME)[:\s]*([A-Z\s.]+?)(?:\n|REKENING|NOMOR)', text, re.IGNORECASE)
        if name_match:
            info['account_holder'] = name_match.group(1).strip()

        return info

    def _parse_amount(self, ket_kode: str, jenis_trans: str, amount: Decimal) -> Tuple[Decimal, Decimal]:
        """
        Parse amount menjadi debit atau credit berdasarkan context

        Returns:
            Tuple[debit, credit]
        """
        # Keywords untuk debit (pengeluaran)
        debit_keywords = [
            'TARIK', 'BAYAR', 'TRANSFER KE', 'POTONGAN', 'BIAYA', 'ADMIN',
            'PURCHASE', 'BELANJA', 'SETOR KE', 'PEMBELIAN', 'PEMBAYARAN',
            'ATM WITHDRAWAL', 'DEBIT'
        ]

        # Keywords untuk credit (pemasukan)
        credit_keywords = [
            'SETOR', 'TERIMA', 'TRANSFER DARI', 'BUNGA', 'CREDIT',
            'DEPOSIT', 'PENERIMAAN', 'MASUK', 'INCOME', 'REVERSAL'
        ]

        combined = f"{ket_kode} {jenis_trans}".upper()

        # Check debit keywords first
        for keyword in debit_keywords:
            if keyword in combined:
                return (amount, Decimal('0.00'))  # (debit, credit)

        # Check credit keywords
        for keyword in credit_keywords:
            if keyword in combined:
                return (Decimal('0.00'), amount)  # (debit, credit)

        # Default: jika tidak detect, assume credit (safe default)
        return (Decimal('0.00'), amount)

    def _parse_from_tables(self, tables: List[Dict[str, Any]]):
        """
        Parse transaksi dari table structure
        Mandiri V2: Nama | Nomer Rekening | Tgl Trans | Ket Kode | Jenis Trans | Remark | Amount | Saldo
        """
        for table in tables:
            if 'rows' not in table:
                continue

            # Skip header row
            for row_idx, row in enumerate(table['rows']):
                if row_idx == 0:  # Skip header
                    continue

                cells = row.get('cells', [])
                # ✅ FIXED: Check minimum required cells for Mandiri V2
                if len(cells) < 5:  # Mandiri V2 needs at least 5 columns
                    continue

                try:
                    nama = ""
                    nomer_rekening = ""
                    tgl_trans = None
                    ket_kode = ""
                    jenis_trans = ""
                    remark = ""
                    amount = Decimal('0.00')
                    saldo = Decimal('0.00')

                    # ✅ SAFE ACCESSOR: Parse based on exact column count
                    if len(cells) == 8:
                        # Full format: Nama | Nomer Rek | Tgl | Ket Kode | Jenis | Remark | Amount | Saldo
                        nama = self.safe_get_cell(cells, 0)
                        nomer_rekening = self.safe_get_cell(cells, 1)
                        tgl_trans_str = self.safe_get_cell(cells, 2)
                        ket_kode = self.safe_get_cell(cells, 3)
                        jenis_trans = self.safe_get_cell(cells, 4)
                        remark = self.safe_get_cell(cells, 5)
                        amount_str = self.safe_get_cell(cells, 6)
                        saldo_str = self.safe_get_cell(cells, 7)
                        
                        tgl_trans = self.parse_date(tgl_trans_str)
                        amount = self.clean_amount(amount_str)
                        saldo = self.clean_amount(saldo_str)

                    elif len(cells) == 5:
                        # Simplified: Tgl | Ket Kode | Remark | Amount | Saldo
                        tgl_trans_str = self.safe_get_cell(cells, 0)
                        ket_kode = self.safe_get_cell(cells, 1)
                        remark = self.safe_get_cell(cells, 2)
                        amount_str = self.safe_get_cell(cells, 3)
                        saldo_str = self.safe_get_cell(cells, 4)
                        
                        tgl_trans = self.parse_date(tgl_trans_str)
                        amount = self.clean_amount(amount_str)
                        saldo = self.clean_amount(saldo_str)
                    else:
                        # Unexpected column count, log and skip
                        self.logger.warning(f"⚠️ Mandiri V2: Unexpected column count: {len(cells)}, expected 5 or 8")
                        continue

                    if not tgl_trans:
                        continue

                    # Parse amount ke debit/credit
                    debit, credit = self._parse_amount(ket_kode, jenis_trans, amount)

                    # Use account info from table row if available, else from extracted info
                    account_number = nomer_rekening if nomer_rekening else self.account_info.get('account_number', '')
                    account_holder = nama if nama else self.account_info.get('account_holder', '')

                    transaction = StandardizedTransaction(
                        transaction_date=tgl_trans,
                        description=remark,
                        transaction_type=f"{ket_kode} - {jenis_trans}".strip(' -'),
                        debit=debit,
                        credit=credit,
                        balance=saldo,
                        bank_name=self.BANK_NAME,
                        account_number=account_number,
                        account_holder=account_holder,
                        raw_data={
                            'nama': nama,
                            'nomer_rekening': nomer_rekening,
                            'ket_kode_transaksi': ket_kode,
                            'jenis_trans': jenis_trans,
                            'remark': remark,
                            'amount': str(amount),
                        }
                    )

                    self.transactions.append(transaction)

                except Exception as e:
                    print(f"Error parsing Mandiri V2 row: {e}")
                    continue

    def _parse_from_text(self, ocr_result: Dict[str, Any]):
        """
        Parse transaksi dari raw text (fallback)
        Format Mandiri V2: Tanggal | Keterangan | Debet | Kredit | Saldo
        """
        self.logger.info("📝 No table structure - using text-based extraction")

        text = self.extract_text_from_ocr(ocr_result)
        if not text:
            self.logger.warning("⚠️ No text found in OCR result")
            return

        import re

        # ✅ FIX: Regex pattern untuk Mandiri V2
        pattern = r'(\d{1,2}[/.-]\d{1,2}(?:[/.-]\d{2,4})?)\s+(.+?)\s+([\d,.-]+(?:\.\d{2})?)\s+([\d,.-]+(?:\.\d{2})?)\s+([\d,.-]+(?:\.\d{2})?)'

        matches = re.finditer(pattern, text, re.MULTILINE)
        transactions_found = 0

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
                transactions_found += 1

            except Exception as e:
                continue

        self.logger.info(f"📝 Text extraction: {transactions_found} transactions found")
        if transactions_found == 0:
            self.logger.warning("⚠️ Text extraction failed - falling back to Smart Mapper")
