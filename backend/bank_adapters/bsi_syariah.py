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
        # Primary keywords - paling unik untuk BSI
        "BANK SYARIAH INDONESIA",
        "BSI BANK SYARIAH",
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
        Parse transaksi dari tables
        BSI bisa ada multiple format:
        - 6 kolom: Tanggal | Trx Time | D/K | Mutasi | Saldo | Keterangan
        - 7 kolom: TrxId | Tanggal | Trx Time | D/K | Mutasi | Saldo | Keterangan
        """
        self.logger.info(f"📊 BSI: Parsing {len(tables)} tables...")
        
        total_rows_processed = 0
        total_rows_skipped = 0
        
        # Iterate semua tables
        for table_idx, table in enumerate(tables):
            rows = table.get('rows', [])
            self.logger.info(f"  Table {table_idx + 1}: {len(rows)} rows")

            for row_idx, row in enumerate(rows):
                total_rows_processed += 1
                cells = row.get('cells', [])
                
                # Log column count for first few rows
                if row_idx < 3:
                    self.logger.info(f"    Row {row_idx + 1}: {len(cells)} cells")
                    if len(cells) > 0:
                        first_cell = self.safe_get_cell(cells, 0)
                        self.logger.info(f"      First cell: '{first_cell[:50]}...'")
                
                # ✅ FIXED: Check minimum required cells for BSI
                if len(cells) < 6:  # BSI needs at least 6 columns
                    total_rows_skipped += 1
                    continue

                try:
                    trx_id = ""
                    tanggal = None
                    trx_time = ""
                    dk_flag = ""
                    mutasi = Decimal('0.00')
                    saldo = Decimal('0.00')
                    keterangan = ""

                    # ✅ SAFE ACCESSOR: Use exact column count check
                    if len(cells) == 7:
                        # Full format: TrxId | Tanggal | Trx Time | D/K | Mutasi | Saldo | Keterangan
                        trx_id = self.safe_get_cell(cells, 0)
                        tanggal_str = self.safe_get_cell(cells, 1)
                        trx_time = self.safe_get_cell(cells, 2)
                        dk_flag = self.safe_get_cell(cells, 3)
                        mutasi_str = self.safe_get_cell(cells, 4)
                        saldo_str = self.safe_get_cell(cells, 5)
                        keterangan = self.safe_get_cell(cells, 6)
                        
                        tanggal = self.parse_date(tanggal_str)
                        mutasi = self.clean_amount(mutasi_str)
                        saldo = self.clean_amount(saldo_str)

                    elif len(cells) == 6:
                        # Simplified: Tanggal | Trx Time | D/K | Mutasi | Saldo | Keterangan
                        tanggal_str = self.safe_get_cell(cells, 0)
                        trx_time = self.safe_get_cell(cells, 1)
                        dk_flag = self.safe_get_cell(cells, 2)
                        mutasi_str = self.safe_get_cell(cells, 3)
                        saldo_str = self.safe_get_cell(cells, 4)
                        keterangan = self.safe_get_cell(cells, 5)
                        
                        tanggal = self.parse_date(tanggal_str)
                        mutasi = self.clean_amount(mutasi_str)
                        saldo = self.clean_amount(saldo_str)
                    else:
                        # Unexpected column count, log and skip
                        self.logger.warning(f"⚠️ BSI: Unexpected column count: {len(cells)}, expected 6 or 7")
                        continue

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
                            'tanggal': tanggal_str if tanggal else '',
                            'trx_time': trx_time,
                            'dk': dk_flag,
                            'mutasi': str(mutasi),
                        }
                    )

                    self.transactions.append(transaction)

                except Exception as e:
                    self.logger.warning(f"⚠️ BSI: Error parsing row {row_idx + 1}: {e}")
                    total_rows_skipped += 1
                    continue
        
        # Log parsing summary
        self.logger.info(f"📊 BSI Parsing Summary:")
        self.logger.info(f"   Total rows processed: {total_rows_processed}")
        self.logger.info(f"   Rows skipped: {total_rows_skipped}")
        self.logger.info(f"   Transactions extracted: {len(self.transactions)}")
        
        # Log parsing summary
        self.logger.info(f"📊 BSI: Processed {total_rows_processed} rows, skipped {total_rows_skipped} rows")
        self.logger.info(f"📊 BSI: Found {len(self.transactions)} transactions")

    def _parse_from_text(self, ocr_result: Dict[str, Any]):
        """
        Parse transaksi dari raw text (fallback)
        Format BSI Syariah: Tanggal | Uraian | Debet | Kredit | Saldo
        """
        self.logger.info("📝 No table structure - using text-based extraction")

        text = self.extract_text_from_ocr(ocr_result)
        if not text:
            self.logger.warning("⚠️ No text found in OCR result")
            return

        import re

        # ✅ FIX: Regex pattern untuk BSI Syariah
        pattern = r'(\d{1,2}[/.-]\d{1,2}(?:[/.-]\d{2,4})?)\s+(.+?)\s+([\d,.-]+(?:\.\d{2})?)\s+([\d,.-]+(?:\.\d{2})?)\s+([\d,.-]+(?:\.\d{2})?)'

        matches = re.finditer(pattern, text, re.MULTILINE)
        transactions_found = 0

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
                transactions_found += 1

            except Exception:
                continue

        self.logger.info(f"📝 Text extraction: {transactions_found} transactions found")
        if transactions_found == 0:
            self.logger.warning("⚠️ Text extraction failed - falling back to Smart Mapper")
