"""
Enhanced Bank Statement Processor
Hybrid approach: Bank Adapters (pattern) + Smart Mapper (AI)
Maximizes data completeness and processing speed
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Import bank adapters
try:
    from bank_adapters import BankDetector, process_bank_statement
    HAS_BANK_ADAPTERS = True
    logger.info("✅ Bank Adapters loaded")
except ImportError as e:
    HAS_BANK_ADAPTERS = False
    logger.warning(f"⚠️ Bank Adapters not available: {e}")

# Import Smart Mapper
try:
    from smart_mapper import smart_mapper_service
    HAS_SMART_MAPPER = getattr(smart_mapper_service, "enabled", False)
    if HAS_SMART_MAPPER:
        logger.info("✅ Smart Mapper loaded")
except ImportError:
    HAS_SMART_MAPPER = False
    smart_mapper_service = None
    logger.warning("⚠️ Smart Mapper not available")


class EnhancedBankStatementProcessor:
    """
    Hybrid processor yang menggabungkan:
    1. Bank Adapters (pattern matching - cepat & reliable)
    2. Smart Mapper (AI extraction - flexible & smart)
    3. Intelligent merger (ambil yang terbaik dari keduanya)

    Strategy:
    - Jalankan kedua method secara parallel/sequential
    - Bank adapters untuk transactions (lebih akurat untuk known banks)
    - Smart Mapper untuk metadata dan fallback
    - Merge hasil untuk mendapatkan data paling lengkap
    """

    def __init__(self):
        self.has_adapters = HAS_BANK_ADAPTERS
        self.has_smart_mapper = HAS_SMART_MAPPER

        logger.info(f"🏦 Enhanced Bank Processor initialized:")
        logger.info(f"   - Bank Adapters: {'✅' if self.has_adapters else '❌'}")
        logger.info(f"   - Smart Mapper: {'✅' if self.has_smart_mapper else '❌'}")

    def process(
        self,
        ocr_result: Dict[str, Any],
        ocr_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Main processing method - Hybrid approach

        Args:
            ocr_result: OCR result dengan text dan tables
            ocr_metadata: Optional metadata dari OCR processor

        Returns:
            Structured data dengan transactions dan metadata
        """
        logger.info("🔄 Starting hybrid bank statement processing...")
        logger.info("🏦 Universal Smart Mapper Mode - Supports ALL Indonesian banks:")
        logger.info("   ✅ BCA, Mandiri, BNI, BRI, CIMB Niaga, Permata")
        logger.info("   ✅ BTN, BSI, Danamon, OCBC NISP, Panin, Maybank")
        logger.info("   ✅ UOB, MUFG, Jenius, Neo Bank, Seabank, and more...")

        # ⚠️ BYPASS BANK ADAPTER: Use Smart Mapper directly for all banks
        # Reason: Bank Adapter expects 'rows' key but Document AI returns 'bodyRows'
        # Smart Mapper handles Document AI format correctly with table extraction
        # This works for ALL banks universally - no bank-specific code needed!
        logger.info("⚠️ Skipping Bank Adapter - using Smart Mapper directly (Document AI format)")
        adapter_result = {
            'success': False,
            'source': 'bank_adapter',
            'reason': 'bypassed_for_smart_mapper',
            'note': 'Using Universal Smart Mapper instead - works for all banks'
        }

        # Strategy 1: Use Smart Mapper (universal method for ALL banks)
        smart_mapper_result = self._try_smart_mapper(ocr_result, ocr_metadata)

        # Strategy 3: Merge results intelligently
        final_result = self._merge_results(
            adapter_result,
            smart_mapper_result,
            ocr_result
        )

        # Log summary
        self._log_processing_summary(adapter_result, smart_mapper_result, final_result)

        return final_result

    def _try_bank_adapter(self, ocr_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Try to use bank adapter for extraction

        Returns:
            {
                'success': bool,
                'source': 'bank_adapter',
                'bank_name': str,
                'bank_code': str,
                'transactions': List[StandardizedTransaction],
                'account_info': Dict,
                'summary': Dict
            }
        """
        if not self.has_adapters:
            logger.warning("⚠️ Bank adapters not available")
            return {'success': False, 'source': 'bank_adapter', 'reason': 'not_available'}

        try:
            logger.info("🏦 Attempting bank adapter detection...")

            # Detect bank
            adapter = BankDetector.detect(ocr_result, verbose=True)

            if not adapter:
                logger.warning("⚠️ No matching bank adapter found")
                return {'success': False, 'source': 'bank_adapter', 'reason': 'no_match'}

            logger.info(f"✅ Detected bank: {adapter.BANK_NAME} ({adapter.BANK_CODE})")

            # Extract transactions
            transactions = adapter.parse(ocr_result)

            if not transactions:
                logger.warning(f"⚠️ {adapter.BANK_NAME} adapter returned no transactions")
                return {
                    'success': False,
                    'source': 'bank_adapter',
                    'reason': 'no_transactions',
                    'bank_name': adapter.BANK_NAME,
                    'bank_code': adapter.BANK_CODE
                }

            # Extract account info
            account_info = adapter.extract_account_info(ocr_result)

            # Get summary
            summary = adapter.get_summary()

            logger.info(f"✅ Bank adapter extracted {len(transactions)} transactions")

            return {
                'success': True,
                'source': 'bank_adapter',
                'bank_name': adapter.BANK_NAME,
                'bank_code': adapter.BANK_CODE,
                'transactions': transactions,
                'account_info': account_info,
                'summary': summary,
                'confidence': 0.90  # High confidence untuk pattern matching
            }

        except Exception as e:
            logger.error(f"❌ Bank adapter error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'success': False,
                'source': 'bank_adapter',
                'reason': 'error',
                'error': str(e)
            }

    def _try_smart_mapper(
        self,
        ocr_result: Dict[str, Any],
        ocr_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Try to use Smart Mapper for extraction

        Returns:
            {
                'success': bool,
                'source': 'smart_mapper',
                'bank_info': Dict,
                'saldo_info': Dict,
                'transactions': List[Dict]
            }
        """
        if not self.has_smart_mapper or not smart_mapper_service:
            logger.warning("⚠️ Smart Mapper not available")
            return {'success': False, 'source': 'smart_mapper', 'reason': 'not_available'}

        try:
            logger.info("🤖 Attempting Smart Mapper extraction...")

            # Load template
            template = smart_mapper_service.load_template('rekening_koran')

            if not template:
                logger.warning("⚠️ Smart Mapper template not found")
                return {'success': False, 'source': 'smart_mapper', 'reason': 'no_template'}

            # Get raw response
            if not ocr_metadata:
                logger.warning("⚠️ No OCR metadata for Smart Mapper")
                return {'success': False, 'source': 'smart_mapper', 'reason': 'no_metadata'}

            raw_response = ocr_metadata.get('raw_response')
            extracted_fields = ocr_metadata.get('extracted_fields', {})

            if not raw_response:
                logger.warning("⚠️ No raw OCR response for Smart Mapper")
                return {'success': False, 'source': 'smart_mapper', 'reason': 'no_raw_response'}

            # Map document
            mapped = smart_mapper_service.map_document(
                doc_type='rekening_koran',
                document_json=raw_response,
                template=template,
                extracted_fields=extracted_fields,
                fallback_fields={}
            )

            if not mapped:
                logger.warning("⚠️ Smart Mapper returned no data")
                return {'success': False, 'source': 'smart_mapper', 'reason': 'no_data'}

            # Extract sections
            bank_info = mapped.get('bank_info', {})
            saldo_info = mapped.get('saldo_info', {})
            transactions = mapped.get('transactions', [])

            detected_bank = bank_info.get('nama_bank', 'Unknown')
            account_number = bank_info.get('nomor_rekening', 'Unknown')
            account_holder = bank_info.get('nama_pemilik', 'Unknown')

            logger.info(f"✅ Smart Mapper SUCCESS!")
            logger.info(f"   🏦 Bank Detected: {detected_bank}")
            logger.info(f"   👤 Account Holder: {account_holder}")
            logger.info(f"   🔢 Account Number: {account_number}")
            logger.info(f"   📊 Transactions Extracted: {len(transactions)}")

            if saldo_info:
                saldo_awal = saldo_info.get('saldo_awal', 'N/A')
                saldo_akhir = saldo_info.get('saldo_akhir', 'N/A')
                logger.info(f"   💰 Saldo Awal: Rp {saldo_awal}")
                logger.info(f"   💰 Saldo Akhir: Rp {saldo_akhir}")

            return {
                'success': True,
                'source': 'smart_mapper',
                'bank_info': bank_info,
                'saldo_info': saldo_info,
                'transactions': transactions,
                'raw_mapped': mapped,
                'confidence': mapped.get('confidence', 0.70)
            }

        except Exception as e:
            logger.error(f"❌ Smart Mapper error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'success': False,
                'source': 'smart_mapper',
                'reason': 'error',
                'error': str(e)
            }

    def _merge_results(
        self,
        adapter_result: Dict[str, Any],
        smart_mapper_result: Dict[str, Any],
        ocr_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Intelligently merge results from both strategies

        Priority:
        1. Transactions: Bank adapter preferred (more reliable)
        2. Metadata: Smart Mapper preferred (more complete)
        3. Fallback: Use whatever is available

        Returns:
            Final structured data
        """
        logger.info("🔀 Merging results from both strategies...")

        merged = {
            'document_type': 'rekening_koran',
            'processing_strategy': [],
            'bank_info': {},
            'saldo_info': {},
            'transactions': [],
            'summary': {},
            'confidence': 0.0,
            'raw_text': ocr_result.get('text', ''),
            'processing_metadata': {
                'adapter_used': adapter_result.get('success', False),
                'smart_mapper_used': smart_mapper_result.get('success', False)
            }
        }

        # Strategy 1: Use Bank Adapter transactions (preferred)
        if adapter_result.get('success'):
            logger.info("✅ Using bank adapter transactions")
            merged['processing_strategy'].append('bank_adapter')

            # Convert StandardizedTransaction to dict format
            transactions = adapter_result['transactions']
            merged['transactions'] = [
                self._standardized_transaction_to_dict(t)
                for t in transactions
            ]

            # Use adapter account info
            account_info = adapter_result.get('account_info', {})
            merged['bank_info'] = {
                'nama_bank': adapter_result.get('bank_name', ''),
                'nomor_rekening': account_info.get('account_number', ''),
                'nama_pemilik': account_info.get('account_holder', ''),
                'periode': account_info.get('period', '')
            }

            # Use adapter summary
            summary = adapter_result.get('summary', {})
            merged['summary'] = summary

            merged['confidence'] += 0.50  # High confidence untuk adapter

        # Strategy 2: Use Smart Mapper metadata (supplement)
        if smart_mapper_result.get('success'):
            logger.info("✅ Using Smart Mapper metadata")
            merged['processing_strategy'].append('smart_mapper')

            sm_bank_info = smart_mapper_result.get('bank_info', {})
            sm_saldo_info = smart_mapper_result.get('saldo_info', {})
            sm_transactions = smart_mapper_result.get('transactions', [])

            # Merge bank info (fill in missing fields)
            for key, value in sm_bank_info.items():
                if value and not merged['bank_info'].get(key):
                    merged['bank_info'][key] = value

            # Use Smart Mapper saldo info
            merged['saldo_info'] = sm_saldo_info

            # Fallback: Use Smart Mapper transactions if adapter failed
            if not merged['transactions'] and sm_transactions:
                logger.info("⚠️ Fallback: Using Smart Mapper transactions")
                merged['transactions'] = sm_transactions

            merged['confidence'] += 0.30  # Additional confidence dari Smart Mapper

        # Fallback: If both failed, return error structure
        if not merged['transactions']:
            logger.warning("❌ Both strategies failed to extract transactions")
            merged['error'] = 'No transactions extracted by any strategy'
            merged['confidence'] = 0.0

            # Try to at least get bank name from text
            text = ocr_result.get('text', '').upper()
            for bank_keyword in ['BCA', 'MANDIRI', 'BNI', 'BRI', 'PERMATA', 'CIMB', 'DANAMON', 'OCBC']:
                if bank_keyword in text:
                    merged['bank_info']['nama_bank'] = f'Bank {bank_keyword}'
                    break

        # Calculate final confidence
        merged['confidence'] = min(1.0, merged['confidence'])

        logger.info(f"✅ Merge complete: {len(merged['transactions'])} transactions, confidence: {merged['confidence']:.2f}")

        return merged

    def _standardized_transaction_to_dict(self, transaction) -> Dict[str, Any]:
        """
        Convert StandardizedTransaction to dict format untuk Excel export

        New format (7 columns):
        - Tanggal
        - Nilai Uang Masuk
        - Nilai Uang Keluar
        - Saldo
        - Sumber Uang Masuk
        - Tujuan Uang Keluar
        - Keterangan
        """
        if hasattr(transaction, 'to_dict'):
            # Use StandardizedTransaction's built-in to_dict() which already has new format
            return transaction.to_dict()

        # Manual conversion if needed (fallback)
        # Extract sumber/tujuan from description
        desc = transaction.description or ''
        desc_upper = desc.upper()

        sumber_uang_masuk = ""
        tujuan_uang_keluar = ""

        debit = float(transaction.debit) if transaction.debit else 0.0
        credit = float(transaction.credit) if transaction.credit else 0.0

        if credit > 0:
            if 'TRANSFER' in desc_upper or 'TRSF' in desc_upper:
                sumber_uang_masuk = "Transfer Masuk"
            elif 'SETORAN' in desc_upper or 'DEPOSIT' in desc_upper:
                sumber_uang_masuk = "Setoran"
            elif 'BUNGA' in desc_upper or 'INTEREST' in desc_upper:
                sumber_uang_masuk = "Bunga Bank"
            else:
                sumber_uang_masuk = "Transfer Masuk"

        if debit > 0:
            if 'ATM' in desc_upper or 'WITHDRAWAL' in desc_upper:
                tujuan_uang_keluar = "Penarikan ATM"
            elif 'TRANSFER' in desc_upper or 'TRSF' in desc_upper:
                tujuan_uang_keluar = "Transfer Keluar"
            elif 'BIAYA' in desc_upper or 'ADM' in desc_upper:
                tujuan_uang_keluar = "Biaya Admin"
            else:
                tujuan_uang_keluar = "Pembayaran"

        return {
            'Tanggal': transaction.transaction_date.strftime('%d/%m/%Y') if hasattr(transaction.transaction_date, 'strftime') else str(transaction.transaction_date),
            'Nilai Uang Masuk': credit,
            'Nilai Uang Keluar': debit,
            'Saldo': float(transaction.balance) if transaction.balance else 0.0,
            'Sumber Uang Masuk': sumber_uang_masuk,
            'Tujuan Uang Keluar': tujuan_uang_keluar,
            'Keterangan': desc,
        }

    def _log_processing_summary(
        self,
        adapter_result: Dict[str, Any],
        smart_mapper_result: Dict[str, Any],
        final_result: Dict[str, Any]
    ):
        """Log processing summary untuk debugging"""
        logger.info("=" * 60)
        logger.info("HYBRID PROCESSING SUMMARY")
        logger.info("=" * 60)

        # Bank Adapter
        if adapter_result.get('success'):
            logger.info(f"✅ Bank Adapter: SUCCESS")
            logger.info(f"   Bank: {adapter_result.get('bank_name')}")
            logger.info(f"   Transactions: {len(adapter_result.get('transactions', []))}")
        else:
            logger.info(f"❌ Bank Adapter: FAILED ({adapter_result.get('reason')})")

        # Smart Mapper
        if smart_mapper_result.get('success'):
            logger.info(f"✅ Smart Mapper: SUCCESS")
            bank_name = smart_mapper_result.get('bank_info', {}).get('nama_bank', 'Unknown')
            logger.info(f"   Bank: {bank_name}")
            logger.info(f"   Transactions: {len(smart_mapper_result.get('transactions', []))}")
        else:
            logger.info(f"❌ Smart Mapper: FAILED ({smart_mapper_result.get('reason')})")

        # Final Result
        logger.info(f"")
        logger.info(f"📊 FINAL RESULT:")
        logger.info(f"   Strategy: {' + '.join(final_result.get('processing_strategy', ['none']))}")
        logger.info(f"   Transactions: {len(final_result.get('transactions', []))}")
        logger.info(f"   Bank: {final_result.get('bank_info', {}).get('nama_bank', 'Unknown')}")
        logger.info(f"   Confidence: {final_result.get('confidence', 0.0):.2%}")
        logger.info("=" * 60)


# Global instance
enhanced_processor = EnhancedBankStatementProcessor()


# Helper function untuk easy integration
def process_bank_statement_enhanced(
    ocr_result: Dict[str, Any],
    ocr_metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Quick helper function untuk process bank statement dengan hybrid approach

    Args:
        ocr_result: OCR result dengan text dan tables
        ocr_metadata: Optional OCR metadata

    Returns:
        Structured data dengan transactions
    """
    return enhanced_processor.process(ocr_result, ocr_metadata)
