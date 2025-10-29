"""
Adapter untuk BSI (Bank Syariah Indonesia)
Format: TrxId, Tanggal, Trx Time, D/K, Mutasi, Saldo, Keterangan
"""

from typing import Dict, Any, List, Tuple
from .base import BaseBankAdapter, StandardizedTransaction
from decimal import Decimal


class BsiSyariahAdapter(BaseBankAdapter):
    """
    Adapter untuk Rekening Koran BSI (Bank Syariah Indonesia)
    Special: Ada D/K flag dan Trx Time
    """

    BANK_NAME = "Bank Syariah Indonesia"
    BANK_CODE = "BSI_SYARIAH"

    DETECTION_KEYWORDS = [
        "BANK SYARIAH INDONESIA",
        "BSI SYARIAH",
        "PT BSI",
        "PT. BSI",
        "TRX TIME",
        "TRXID",
        "TRX ID",
        "D/K",
    ]

    def parse(self, ocr_result: Dict[str, Any]) -> List[StandardizedTransaction]:
        """
        Parse OCR result dari BSI Syariah
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
        Extract informasi rekening BSI
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

        # BSI account number
        acc_match = re.search(r'(?:REKENING|NO\s*REK|ACCOUNT)[:\s]*(\d{10,16})', text, re.IGNORECASE)
        if acc_match:
            info['account_number'] = acc_match.group(1)

        # Extract account holder
        name_match = re.search(r'(?:NAMA|NAME|PEMILIK)[:\s]*([A-Z\s.]+?)(?:\n|REKENING|NO)', text, re.IGNORECASE)
        if name_match:
            info['account_holder'] = name_match.group(1).strip()

        return info

    def _parse_dk(self, dk_flag: str, mutasi: Decimal) -> Tuple[Decimal, Decimal]:
        """
        Parse D/K flag untuk determine debit atau kredit

        Args:
            dk_flag: "D" atau "K"
            mutasi: Jumlah mutasi

        Returns:
            Tuple[debit, credit]
        """
        flag_upper = dk_flag.upper().strip()

        # D = Debit (pengeluaran)
        if flag_upper in ['D', 'DEBIT', 'DB', 'DR']:
            return (mutasi, Decimal('0.00'))  # (debit, credit)

        # K = Kredit (pemasukan)
        elif flag_upper in ['K', 'KREDIT', 'CREDIT', 'CR', 'C']:
            return (Decimal('0.00'), mutasi)  # (debit, credit)

        # Default: assume credit if unclear
        return (Decimal('0.00'), mutasi)

    def _parse_from_tables(self, tables: List[Dict[str, Any]]):
        """
        Parse transaksi dari table structure
        BSI: TrxId | Tanggal | Trx Time | D/K | Mutasi | Saldo | Keterangan
        """
        for table in tables:
            if 'rows' not in table:
                continue

            # Skip header row
            for row_idx, row in enumerate(table['rows']):
                if row_idx == 0:  # Skip header
                    continue

                cells = row.get('cells', [])
                if len(cells) < 6:  # Minimal columns
                    continue

                try:
                    trx_id = ""
                    tanggal = None
                    trx_time = ""
                    dk_flag = ""
                    mutasi = Decimal('0.00')
                    saldo = Decimal('0.00')
                    keterangan = ""

                    if len(cells) >= 7:
                        # Full format: TrxId | Tanggal | Trx Time | D/K | Mutasi | Saldo | Keterangan
                        trx_id = cells[0].get('text', '').strip()
                        tanggal = self.parse_date(cells[1].get('text', '').strip())
                        trx_time = cells[2].get('text', '').strip()
                        dk_flag = cells[3].get('text', '').strip()
                        mutasi = self.clean_amount(cells[4].get('text', '').strip())
                        saldo = self.clean_amount(cells[5].get('text', '').strip())
                        keterangan = cells[6].get('text', '').strip()

                    elif len(cells) >= 6:
                        # Simplified: Tanggal | Trx Time | D/K | Mutasi | Saldo | Keterangan
                        tanggal = self.parse_date(cells[0].get('text', '').strip())
                        trx_time = cells[1].get('text', '').strip()
                        dk_flag = cells[2].get('text', '').strip()
                        mutasi = self.clean_amount(cells[3].get('text', '').strip())
                        saldo = self.clean_amount(cells[4].get('text', '').strip())
                        keterangan = cells[5].get('text', '').strip()

                    if not tanggal:
                        continue

                    # Parse D/K untuk debit/credit
                    debit, credit = self._parse_dk(dk_flag, mutasi)

                    transaction = StandardizedTransaction(
                        transaction_date=tanggal,
                        description=keterangan,
                        reference_number=trx_id,
                        debit=debit,
                        credit=credit,
                        balance=saldo,
                        additional_info=f"Time: {trx_time}" if trx_time else "",
                        bank_name=self.BANK_NAME,
                        account_number=self.account_info.get('account_number', ''),
                        account_holder=self.account_info.get('account_holder', ''),
                        raw_data={
                            'trx_id': trx_id,
                            'tanggal': cells[1].get('text', '') if len(cells) >= 7 else cells[0].get('text', ''),
                            'trx_time': trx_time,
                            'dk': dk_flag,
                            'mutasi': str(mutasi),
                        }
                    )

                    self.transactions.append(transaction)

                except Exception as e:
                    print(f"Error parsing BSI Syariah row: {e}")
                    continue

    def _parse_from_text(self, ocr_result: Dict[str, Any]):
        """
        Parse transaksi dari raw text (fallback)
        Format BSI Syariah: Tanggal | Uraian | Debet | Kredit | Saldo
        """
        text = self.extract_text_from_ocr(ocr_result)
        if not text:
            return

        import re

        # ✅ FIX: Regex pattern untuk BSI Syariah
        pattern = r'(\d{1,2}[/.-]\d{1,2}(?:[/.-]\d{2,4})?)\s+(.+?)\s+([\d,.-]+(?:\.\d{2})?)\s+([\d,.-]+(?:\.\d{2})?)\s+([\d,.-]+(?:\.\d{2})?)'

        matches = re.finditer(pattern, text, re.MULTILINE)

        for match in matches:
            try:
                tgl_str = match.group(1)
                uraian = match.group(2).strip()
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
                    description=uraian,
                    debit=debet,
                    credit=kredit,
                    balance=saldo,
                    bank_name=self.BANK_NAME,
                    account_number=self.account_info.get('account_number', ''),
                    account_holder=self.account_info.get('account_holder', ''),
                    raw_data={'tanggal': tgl_str, 'uraian': uraian, 'source': 'text_fallback'}
                )

                self.transactions.append(transaction)

            except Exception as e:
                continue
