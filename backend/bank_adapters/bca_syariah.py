"""
Adapter untuk BCA Syariah
Format LANDSCAPE dengan banyak kolom:
Tanggal Efektif, Tanggal Transaksi, Jam Input, Kode Transaksi, Keterangan, Keterangan Tambahan,
D/C, Nominal, Saldo, Nomor Referensi, Status Otorisasi, User Input, User Otorisasi, Kode Cabang
"""

from typing import Dict, Any, List, Tuple
from .base import BaseBankAdapter, StandardizedTransaction
from decimal import Decimal


class BcaSyariahAdapter(BaseBankAdapter):
    """
    Adapter untuk Rekening Koran BCA Syariah
    Special: Format LANDSCAPE dengan banyak kolom, D/C flag
    """

    BANK_NAME = "BCA Syariah"
    BANK_CODE = "BCA_SYARIAH"

    DETECTION_KEYWORDS = [
        "BCA SYARIAH",
        "PT BANK BCA SYARIAH",
        "TANGGAL EFEKTIF",
        "TANGGAL TRANSAKSI",
        "KODE TRANSAKSI",
        "KETERANGAN TAMBAHAN",
        "KODE CABANG",
    ]

    def parse(self, ocr_result: Dict[str, Any]) -> List[StandardizedTransaction]:
        """
        Parse OCR result dari BCA Syariah
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
        Extract informasi rekening BCA Syariah
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

        # BCA Syariah account number
        acc_match = re.search(r'(?:REKENING|ACCOUNT|NO\s*REK)[:\s]*(\d{10,16})', text, re.IGNORECASE)
        if acc_match:
            info['account_number'] = acc_match.group(1)

        # Extract account holder
        name_match = re.search(r'(?:NAMA|NAME|PEMILIK)[:\s]*([A-Z\s.]+?)(?:\n|REKENING|NO)', text, re.IGNORECASE)
        if name_match:
            info['account_holder'] = name_match.group(1).strip()

        return info

    def _parse_dc(self, dc_flag: str, nominal: Decimal) -> Tuple[Decimal, Decimal]:
        """
        Parse D/C flag untuk determine debit atau credit

        Args:
            dc_flag: "D" atau "C"
            nominal: Jumlah transaksi

        Returns:
            Tuple[debit, credit]
        """
        flag_upper = dc_flag.upper().strip()

        # D = Debit (pengeluaran)
        if flag_upper in ['D', 'DEBIT', 'DB']:
            return (nominal, Decimal('0.00'))  # (debit, credit)

        # C = Credit (pemasukan)
        elif flag_upper in ['C', 'CREDIT', 'CR', 'K', 'KREDIT']:
            return (Decimal('0.00'), nominal)  # (debit, credit)

        # Default: assume credit if unclear
        return (Decimal('0.00'), nominal)

    def _parse_from_tables(self, tables: List[Dict[str, Any]]):
        """
        Parse transaksi dari table structure (LANDSCAPE format!)
        BCA Syariah: Tgl Efektif | Tgl Trans | Jam | Kode Trans | Keterangan | Ket Tambahan |
                     D/C | Nominal | Saldo | No Ref | Status | User Input | User Otorisasi | Kode Cabang
        """
        for table in tables:
            if 'rows' not in table:
                continue

            # Skip header row
            for row_idx, row in enumerate(table['rows']):
                if row_idx == 0:  # Skip header
                    continue

                cells = row.get('cells', [])
                # ✅ FIXED: Check minimum required cells for BCA Syariah
                if len(cells) < 9:  # BCA Syariah needs at least 9 columns
                    continue

                try:
                    # Initialize variables
                    tgl_efektif = None
                    tgl_transaksi = None
                    jam_input = ""
                    kode_transaksi = ""
                    keterangan = ""
                    keterangan_tambahan = ""
                    dc_flag = ""
                    nominal = Decimal('0.00')
                    saldo = Decimal('0.00')
                    nomor_referensi = ""
                    status_otorisasi = ""
                    user_input = ""
                    user_otorisasi = ""
                    kode_cabang = ""

                    # ✅ SAFE ACCESSOR: Parse based on exact column count (BCA Syariah bisa 9-14 kolom)
                    if len(cells) == 14:
                        # Full format (14 kolom)
                        tgl_efektif_str = self.safe_get_cell(cells, 0)
                        tgl_transaksi_str = self.safe_get_cell(cells, 1)
                        jam_input = self.safe_get_cell(cells, 2)
                        kode_transaksi = self.safe_get_cell(cells, 3)
                        keterangan = self.safe_get_cell(cells, 4)
                        keterangan_tambahan = self.safe_get_cell(cells, 5)
                        dc_flag = self.safe_get_cell(cells, 6)
                        nominal_str = self.safe_get_cell(cells, 7)
                        saldo_str = self.safe_get_cell(cells, 8)
                        nomor_referensi = self.safe_get_cell(cells, 9)
                        status_otorisasi = self.safe_get_cell(cells, 10)
                        user_input = self.safe_get_cell(cells, 11)
                        user_otorisasi = self.safe_get_cell(cells, 12)
                        kode_cabang = self.safe_get_cell(cells, 13)
                        
                        tgl_efektif = self.parse_date(tgl_efektif_str)
                        tgl_transaksi = self.parse_date(tgl_transaksi_str)
                        nominal = self.clean_amount(nominal_str)
                        saldo = self.clean_amount(saldo_str)

                    elif len(cells) in [10, 11, 12, 13]:
                        # Medium format (10-13 kolom)
                        tgl_efektif_str = self.safe_get_cell(cells, 0)
                        tgl_transaksi_str = self.safe_get_cell(cells, 1)
                        jam_input = self.safe_get_cell(cells, 2)
                        kode_transaksi = self.safe_get_cell(cells, 3)
                        keterangan = self.safe_get_cell(cells, 4)
                        keterangan_tambahan = self.safe_get_cell(cells, 5)
                        dc_flag = self.safe_get_cell(cells, 6)
                        nominal_str = self.safe_get_cell(cells, 7)
                        saldo_str = self.safe_get_cell(cells, 8)
                        nomor_referensi = self.safe_get_cell(cells, 9)
                        kode_cabang = self.safe_get_cell(cells, 10)
                        
                        tgl_efektif = self.parse_date(tgl_efektif_str)
                        tgl_transaksi = self.parse_date(tgl_transaksi_str)
                        nominal = self.clean_amount(nominal_str)
                        saldo = self.clean_amount(saldo_str)

                    elif len(cells) == 9:
                        # Minimal format (9 kolom): Tgl Trans | Kode | Ket | DC | Nominal | Saldo | Ref | Cabang | Jam
                        tgl_transaksi_str = self.safe_get_cell(cells, 0)
                        kode_transaksi = self.safe_get_cell(cells, 1)
                        keterangan = self.safe_get_cell(cells, 2)
                        dc_flag = self.safe_get_cell(cells, 3)
                        nominal_str = self.safe_get_cell(cells, 4)
                        saldo_str = self.safe_get_cell(cells, 5)
                        nomor_referensi = self.safe_get_cell(cells, 6)
                        kode_cabang = self.safe_get_cell(cells, 7)
                        jam_input = self.safe_get_cell(cells, 8)
                        
                        tgl_transaksi = self.parse_date(tgl_transaksi_str)
                        nominal = self.clean_amount(nominal_str)
                        saldo = self.clean_amount(saldo_str)
                    else:
                        # Unexpected column count, log and skip
                        self.logger.warning(f"⚠️ BCA Syariah: Unexpected column count: {len(cells)}, expected 9-14")
                        continue

                    # Use tgl_transaksi as main date, tgl_efektif as effective date
                    transaction_date = tgl_transaksi or tgl_efektif
                    if not transaction_date:
                        continue

                    # Parse D/C untuk debit/credit
                    debit, credit = self._parse_dc(dc_flag, nominal)

                    # Combine keterangan
                    full_description = f"{keterangan} {keterangan_tambahan}".strip()

                    # Additional info
                    additional_info_parts = []
                    if jam_input:
                        additional_info_parts.append(f"Jam: {jam_input}")
                    if user_input:
                        additional_info_parts.append(f"User: {user_input}")
                    if status_otorisasi:
                        additional_info_parts.append(f"Status: {status_otorisasi}")

                    transaction = StandardizedTransaction(
                        transaction_date=transaction_date,
                        effective_date=tgl_efektif,
                        description=full_description,
                        transaction_type=kode_transaksi,
                        reference_number=nomor_referensi,
                        debit=debit,
                        credit=credit,
                        balance=saldo,
                        branch_code=kode_cabang,
                        additional_info=", ".join(additional_info_parts) if additional_info_parts else "",
                        bank_name=self.BANK_NAME,
                        account_number=self.account_info.get('account_number', ''),
                        account_holder=self.account_info.get('account_holder', ''),
                        raw_data={
                            'tanggal_efektif': tgl_efektif_str if len(cells) >= 10 else '',
                            'tanggal_transaksi': tgl_transaksi_str if 'tgl_transaksi_str' in locals() else '',
                            'jam_input': jam_input,
                            'kode_transaksi': kode_transaksi,
                            'keterangan': keterangan,
                            'keterangan_tambahan': keterangan_tambahan,
                            'dc': dc_flag,
                            'nomor_referensi': nomor_referensi,
                            'kode_cabang': kode_cabang,
                        }
                    )

                    self.transactions.append(transaction)

                except Exception as e:
                    print(f"Error parsing BCA Syariah row: {e}")
                    continue

    def _parse_from_text(self, ocr_result: Dict[str, Any]):
        """
        Parse transaksi dari raw text (fallback)
        Format BCA Syariah (minimal): Tgl | Kode | Ket | D/C | Nominal | Saldo | Ref | Cabang
        """
        self.logger.info("📝 No table structure - using text-based extraction")

        text = self.extract_text_from_ocr(ocr_result)
        if not text:
            self.logger.warning("⚠️ No text found in OCR result")
            return

        import re

        # ✅ FIX: Simplified regex pattern untuk BCA Syariah
        # Pattern: DD/MM/YYYY (or DD/MM) ... CODE ... DESCRIPTION ... D/C ... AMOUNT ... BALANCE
        pattern = r'(\d{1,2}[/.-]\d{1,2}(?:[/.-]\d{2,4})?)\s+(\w+)\s+(.+?)\s+([DC])\s+([\d,.-]+(?:\.\d{2})?)\s+([\d,.-]+(?:\.\d{2})?)'

        matches = re.finditer(pattern, text, re.MULTILINE)
        transactions_found = 0

        for match in matches:
            try:
                tanggal_str = match.group(1)
                kode = match.group(2).strip()
                keterangan = match.group(3).strip()
                dc_flag = match.group(4)
                nominal_str = match.group(5).strip()
                saldo_str = match.group(6).strip()

                # Parse tanggal (might be incomplete without year)
                tanggal = self.parse_date(tanggal_str)

                if not tanggal:
                    continue

                # Parse D/C
                nominal = self.clean_amount(nominal_str)
                debit, credit = self._parse_dc(dc_flag, nominal)

                # Parse saldo
                saldo = self.clean_amount(saldo_str)

                transaction = StandardizedTransaction(
                    transaction_date=tanggal,
                    description=keterangan,
                    transaction_code=kode,
                    debit=debit,
                    credit=credit,
                    balance=saldo,
                    bank_name=self.BANK_NAME,
                    account_number=self.account_info.get('account_number', ''),
                    account_holder=self.account_info.get('account_holder', ''),
                    raw_data={
                        'tanggal': tanggal_str,
                        'kode': kode,
                        'keterangan': keterangan,
                        'dc': dc_flag,
                        'nominal': nominal_str,
                        'source': 'text_fallback'
                    }
                )

                self.transactions.append(transaction)
                transactions_found += 1

            except Exception as e:
                # Silent fail - regex might match non-transaction text
                continue

        self.logger.info(f"📝 Text extraction: {transactions_found} transactions found")
        if transactions_found == 0:
            self.logger.warning("⚠️ Text extraction failed - falling back to Smart Mapper")
