"""
Hybrid Bank Processor
Combines Strategy 2 (Structured First) + Strategy 5 (Progressive Validation)

Pipeline:
1. Document AI → Extract structured tables
2. Rule-Based Parser → Parse 90% of transactions (NO GPT!)
3. Progressive Validator → Check saldo continuity
4. GPT Fallback → Only for failed validation chunks (~10%)
5. Merge Results → Combine all transactions

Expected Savings: 90-96% token reduction!
"""

import logging
import time
from typing import Dict, List, Optional, Tuple
import asyncio

logger = logging.getLogger(__name__)


class HybridBankProcessor:
    """
    Orchestrates hybrid processing pipeline

    Components:
    - RuleBasedParser: Parse transactions without GPT
    - ProgressiveValidator: Validate and determine GPT need
    - SmartMapper (GPT): Fallback for edge cases
    """

    def __init__(
        self,
        rule_parser=None,
        validator=None,
        smart_mapper=None,
        bank_detector=None,
        ai_detector=None,
        confidence_threshold: float = 0.90,
        enable_gpt_fallback: bool = True
    ):
        """
        Args:
            rule_parser: RuleBasedTransactionParser instance
            validator: ProgressiveValidator instance
            smart_mapper: SmartMapper instance (for GPT fallback)
            bank_detector: BankDetector instance (for bank-specific adapters)
            ai_detector: AIBankDetector instance (for AI-based bank detection)
            confidence_threshold: Minimum confidence to skip GPT
            enable_gpt_fallback: Whether to use GPT for edge cases
        """
        self.rule_parser = rule_parser
        self.validator = validator
        self.smart_mapper = smart_mapper
        self.bank_detector = bank_detector
        self.ai_detector = ai_detector
        self.confidence_threshold = confidence_threshold
        self.enable_gpt_fallback = enable_gpt_fallback

        logger.info("🚀 HybridBankProcessor initialized")
        logger.info(f"   ✅ Rule-based parser: {'Loaded' if rule_parser else 'Not loaded'}")
        logger.info(f"   ✅ Progressive validator: {'Loaded' if validator else 'Not loaded'}")
        logger.info(f"   ✅ Smart Mapper (GPT): {'Loaded' if smart_mapper else 'Not loaded'}")
        logger.info(f"   ✅ Bank Detector: {'Loaded' if bank_detector else 'Not loaded'}")
        logger.info(f"   ✅ AI Bank Detector: {'Loaded' if ai_detector else 'Not loaded'}")
        logger.info(f"   ⚙️ Confidence threshold: {confidence_threshold}")
        logger.info(f"   ⚙️ GPT fallback: {'Enabled' if enable_gpt_fallback else 'Disabled'}")

    async def process_bank_statement(
        self,
        ocr_result: Dict,
        raw_text: str,
        metadata: Optional[Dict] = None,
        page_offset: int = 0
    ) -> Dict:
        """
        Process bank statement using hybrid pipeline

        Args:
            ocr_result: Document AI OCR result with structured tables
            raw_text: Raw OCR text (fallback)
            metadata: Optional metadata (bank name, account, etc.)
            page_offset: Starting page number offset for chunks (default: 0)

        Returns:
            Processed result with transactions and metrics
        """
        start_time = time.time()

        logger.info("=" * 60)
        logger.info("🏦 HYBRID BANK STATEMENT PROCESSING")
        logger.info("=" * 60)

        # Initialize metrics
        metrics = {
            'rule_based_parsed': 0,
            'gpt_processed': 0,
            'validation_passed': 0,
            'validation_failed': 0,
            'total_transactions': 0,
            'token_savings_percentage': 0,
            'processing_time': 0,
        }

        # Step 1: Extract metadata from first page
        logger.info("📋 Step 1: Extracting metadata...")
        extracted_metadata = self._extract_metadata(ocr_result, raw_text)

        if metadata:
            extracted_metadata.update(metadata)

        bank_name = extracted_metadata.get('nama_bank', '').lower()
        saldo_awal = float(extracted_metadata.get('saldo_awal', 0))

        logger.info(f"   Bank: {bank_name}")
        logger.info(f"   Saldo Awal: {saldo_awal:,.2f}")

        # Step 1.5: Try bank-specific adapter first (NEW!)
        logger.info("🏦 Step 1.5: Trying bank-specific adapter...")
        adapter_result = self._try_bank_adapter(ocr_result)

        if adapter_result and adapter_result.get('success'):
            logger.info(f"   ✅ Bank adapter succeeded: {adapter_result.get('bank_name', 'N/A')}")
            logger.info(f"   ✅ Found {len(adapter_result.get('transactions', []))} transactions")

            # Convert adapter transactions to standard format
            adapter_transactions = adapter_result.get('transactions', [])
            transactions = [self._convert_adapter_transaction(t) for t in adapter_transactions]

            # Update metadata from adapter
            if adapter_result.get('account_info'):
                extracted_metadata.update(adapter_result['account_info'])

            metrics['rule_based_parsed'] = len(transactions)
            logger.info("   🎯 Using bank adapter results (skipping rule-based parser)")
        else:
            logger.info("   ⚠️ Bank adapter failed or not available - falling back to rule-based parser")

            # Step 2: Rule-based parsing (NO GPT!) - FALLBACK
            logger.info("🔧 Step 2: Rule-based parsing...")

            tables = self._extract_tables(ocr_result, page_offset)
            logger.info(f"   Found {len(tables)} tables")

            # Track page information
            pages_info = self._extract_pages_info(ocr_result, page_offset)
            logger.info(f"   Processing {len(pages_info)} pages")

            parsed_transactions = self.rule_parser.parse_transactions(tables, bank_name)
            logger.info(f"   Parsed {len(parsed_transactions)} transactions")

            # Get parsing statistics
            parse_stats = self.rule_parser.get_statistics(parsed_transactions)
            logger.info(f"   High confidence: {parse_stats['high_confidence']} "
                       f"({parse_stats['high_conf_percentage']:.1f}%)")
            logger.info(f"   Low confidence: {parse_stats['low_confidence']} "
                       f"({parse_stats['low_conf_percentage']:.1f}%)")

            metrics['rule_based_parsed'] = len(parsed_transactions)

            # Convert to standard format
            transactions = [self._to_standard_format(t) for t in parsed_transactions]

        # Step 3: Chunk transactions by saldo context
        logger.info("📦 Step 3: Chunking by saldo context...")
        chunks = self._chunk_by_saldo_context(transactions, saldo_awal)
        logger.info(f"   Created {len(chunks)} chunks")

        # Step 4: Progressive validation
        logger.info("🔍 Step 4: Validating chunks...")
        validations = self.validator.validate_all_chunks(chunks, saldo_awal)

        validation_stats = self.validator.get_validation_stats(validations)
        logger.info(f"   Passed: {validation_stats['passed']} chunks")
        logger.info(f"   Failed: {validation_stats['failed']} chunks")
        logger.info(f"   Need GPT: {validation_stats['needs_gpt']} chunks "
                   f"({validation_stats['gpt_usage_rate']:.1f}%)")

        metrics['validation_passed'] = validation_stats['passed']
        metrics['validation_failed'] = validation_stats['failed']

        # Step 5: GPT fallback for failed chunks
        final_chunks = []

        if self.enable_gpt_fallback and self.smart_mapper:
            logger.info("🤖 Step 5: Processing failed chunks with GPT...")

            for validation in validations:
                if validation.validation.needs_gpt:
                    logger.info(f"   Processing chunk {validation.chunk_id} with GPT...")

                    # Get raw text for this chunk
                    chunk_text = self._get_chunk_text(
                        validation.transactions,
                        raw_text
                    )

                    # Process with GPT
                    try:
                        gpt_result = await self._process_chunk_with_gpt(
                            chunk_text,
                            validation.saldo_start,
                            bank_name
                        )

                        # Update chunk with GPT results
                        validation.transactions = gpt_result['transactions']
                        validation.processed_with_gpt = True
                        metrics['gpt_processed'] += 1

                        logger.info(f"   ✅ Chunk {validation.chunk_id} processed with GPT "
                                   f"({len(gpt_result['transactions'])} txns)")

                    except Exception as e:
                        logger.error(f"   ❌ GPT processing failed for chunk {validation.chunk_id}: {e}")
                        # Keep original rule-based result
                        validation.processed_with_gpt = False

                final_chunks.append(validation)
        else:
            logger.info("⚠️ Step 5: GPT fallback disabled - using rule-based results only")
            final_chunks = validations

        # Step 6: Merge all chunks
        logger.info("🔀 Step 6: Merging results...")
        all_transactions = []

        for chunk in final_chunks:
            all_transactions.extend(chunk.transactions)

        logger.info(f"   Total transactions: {len(all_transactions)}")

        # Calculate saldo_akhir
        if all_transactions:
            saldo_akhir = all_transactions[-1].get('saldo', saldo_awal)
        else:
            saldo_akhir = saldo_awal

        # Calculate metrics
        metrics['total_transactions'] = len(all_transactions)
        metrics['processing_time'] = time.time() - start_time

        # Token savings calculation
        # Assume: Without optimization, would use GPT for all chunks
        total_chunks = len(chunks)
        gpt_chunks = metrics['gpt_processed']
        chunks_saved = total_chunks - gpt_chunks

        metrics['token_savings_percentage'] = (
            (chunks_saved / total_chunks * 100) if total_chunks > 0 else 0
        )

        # Calculate page statistics
        page_stats = self._calculate_page_statistics(all_transactions, pages_info)

        # Final result
        result = {
            'document_type': 'rekening_koran',
            'processing_strategy': ['hybrid', 'rule_based', 'progressive_validation'],
            'bank_info': {
                'nama_bank': extracted_metadata.get('nama_bank', 'N/A'),
                'nomor_rekening': extracted_metadata.get('nomor_rekening', 'N/A'),
                'nama_pemilik': extracted_metadata.get('nama_pemilik', 'N/A'),
                'periode': extracted_metadata.get('periode', 'N/A'),
                'alamat': extracted_metadata.get('alamat', ''),
                'jenis_rekening': extracted_metadata.get('jenis_rekening', ''),
            },
            'saldo_info': {
                'saldo_awal': str(int(saldo_awal)),
                'saldo_akhir': str(int(saldo_akhir)),
                'mata_uang': extracted_metadata.get('mata_uang', 'IDR'),
            },
            'transactions': all_transactions,
            'summary': self._generate_summary(all_transactions),
            'confidence': self._calculate_overall_confidence(all_transactions, validations),
            'pages_info': page_stats,  # NEW: Page tracking information
            'processing_metadata': {
                'hybrid_processing': True,
                'rule_based_percentage': (metrics['rule_based_parsed'] / metrics['total_transactions'] * 100)
                    if metrics['total_transactions'] > 0 else 0,
                'gpt_usage_percentage': (metrics['gpt_processed'] / len(chunks) * 100)
                    if len(chunks) > 0 else 0,
                'token_savings_percentage': metrics['token_savings_percentage'],
                'chunks_processed': len(chunks),
                'chunks_with_gpt': metrics['gpt_processed'],
                'validation_pass_rate': validation_stats['pass_rate'],
                'processing_time_seconds': metrics['processing_time'],
            }
        }

        # Log summary
        logger.info("=" * 60)
        logger.info("📊 PROCESSING SUMMARY")
        logger.info("=" * 60)
        logger.info(f"✅ Total Transactions: {metrics['total_transactions']}")

        if metrics['total_transactions'] > 0:
            logger.info(f"✅ Rule-based Parsed: {metrics['rule_based_parsed']} "
                       f"({metrics['rule_based_parsed'] / metrics['total_transactions'] * 100:.1f}%)")
        else:
            logger.info(f"✅ Rule-based Parsed: {metrics['rule_based_parsed']} (0.0%)")

        if len(chunks) > 0:
            logger.info(f"🤖 GPT Processed Chunks: {metrics['gpt_processed']}/{len(chunks)} "
                       f"({metrics['gpt_processed'] / len(chunks) * 100:.1f}%)")
        else:
            logger.info(f"🤖 GPT Processed Chunks: {metrics['gpt_processed']}/0 (0.0%)")

        logger.info(f"💰 Token Savings: {metrics['token_savings_percentage']:.1f}%")
        logger.info(f"⏱️ Processing Time: {metrics['processing_time']:.2f}s")
        logger.info("=" * 60)

        return result

    def _extract_metadata(self, ocr_result: Dict, raw_text: str) -> Dict:
        """Extract metadata from first page"""
        metadata = {}

        # Try to extract from structured data first
        if 'pages' in ocr_result and len(ocr_result['pages']) > 0:
            first_page = ocr_result['pages'][0]

            # Look for text blocks with metadata keywords
            text_blocks = first_page.get('text_blocks', [])

            for block in text_blocks:
                text = block.get('text', '').lower()

                # Bank name
                if 'bank' in text:
                    metadata['nama_bank'] = self._extract_bank_name(block.get('text', ''))

                # Account number
                if 'rekening' in text or 'account' in text:
                    metadata['nomor_rekening'] = self._extract_account_number(block.get('text', ''))

                # Saldo awal
                if 'saldo awal' in text or 'balance' in text:
                    metadata['saldo_awal'] = self._extract_saldo(block.get('text', ''))

        # Fallback to regex on raw text
        if not metadata.get('nama_bank'):
            metadata['nama_bank'] = self._extract_bank_name(raw_text)

        if not metadata.get('nomor_rekening'):
            metadata['nomor_rekening'] = self._extract_account_number(raw_text)

        if not metadata.get('saldo_awal'):
            metadata['saldo_awal'] = self._extract_saldo(raw_text)

        return metadata

    def _extract_bank_name(self, text: str) -> str:
        """Extract bank name from text"""
        import re

        # Common bank patterns
        banks = ['BCA', 'Mandiri', 'BNI', 'BRI', 'CIMB', 'Permata', 'BTN', 'BSI', 'Danamon']

        for bank in banks:
            if re.search(rf'\b{bank}\b', text, re.IGNORECASE):
                return f"Bank {bank}"

        return 'N/A'

    def _extract_account_number(self, text: str) -> str:
        """Extract account number from text"""
        import re

        # Pattern: 10-16 digit account number
        match = re.search(r'\b\d{10,16}\b', text)

        if match:
            return match.group()

        return 'N/A'

    def _extract_saldo(self, text: str) -> float:
        """Extract saldo from text"""
        import re

        # Look for numbers after "saldo" keyword
        match = re.search(r'saldo[:\s]+([0-9\.,]+)', text, re.IGNORECASE)

        if match:
            amount_text = match.group(1)
            # Use rule parser to parse amount
            amount = self.rule_parser.extract_amount(amount_text)
            return amount if amount is not None else 0

        return 0

    def _extract_tables(self, ocr_result: Dict, page_offset: int = 0) -> List[Dict]:
        """Extract tables from OCR result with page offset support"""
        tables = []

        if 'pages' in ocr_result:
            for page_idx, page in enumerate(ocr_result['pages']):
                page_number = page.get('page_number', page_idx + 1)
                # Apply page offset for chunked processing
                actual_page_number = page_number + page_offset
                page_tables = page.get('tables', [])

                # Tag each table with actual page number
                for table in page_tables:
                    table['page_number'] = actual_page_number

                tables.extend(page_tables)

        return tables

    def _extract_pages_info(self, ocr_result: Dict, page_offset: int = 0) -> List[Dict]:
        """Extract page information for tracking with page offset support"""
        pages_info = []

        if 'pages' in ocr_result:
            for page_idx, page in enumerate(ocr_result['pages']):
                page_number = page.get('page_number', page_idx + 1)
                # Apply page offset for chunked processing
                actual_page_number = page_number + page_offset
                page_tables = page.get('tables', [])

                pages_info.append({
                    'page_number': actual_page_number,
                    'has_tables': len(page_tables) > 0,
                    'table_count': len(page_tables),
                })

        return pages_info

    def _to_standard_format(self, parsed_txn) -> Dict:
        """Convert ParsedTransaction to standard dict format"""
        return {
            'tanggal': parsed_txn.tanggal or '',
            'keterangan': parsed_txn.keterangan or '',
            'debet': parsed_txn.debet or 0,
            'kredit': parsed_txn.kredit or 0,
            'saldo': parsed_txn.saldo or 0,
            'referensi': parsed_txn.referensi or '',
            'confidence': parsed_txn.confidence,
            'page': parsed_txn.page_number or 1,  # Include page number
        }

    def _chunk_by_saldo_context(
        self,
        transactions: List[Dict],
        saldo_awal: float,
        chunk_size: int = 50
    ) -> List[Dict]:
        """
        Chunk transactions by saldo context

        Args:
            transactions: All transactions
            saldo_awal: Starting saldo
            chunk_size: Target transactions per chunk

        Returns:
            List of chunk dicts with saldo context
        """
        chunks = []
        current_chunk = []
        current_saldo = saldo_awal

        for txn in transactions:
            current_chunk.append(txn)

            if len(current_chunk) >= chunk_size:
                # Save chunk
                saldo_end = current_chunk[-1].get('saldo', current_saldo)

                chunks.append({
                    'saldo_start': current_saldo,
                    'transactions': current_chunk,
                    'saldo_end': saldo_end,
                })

                # Next chunk
                current_saldo = saldo_end
                current_chunk = []

        # Add remaining transactions
        if current_chunk:
            saldo_end = current_chunk[-1].get('saldo', current_saldo)

            chunks.append({
                'saldo_start': current_saldo,
                'transactions': current_chunk,
                'saldo_end': saldo_end,
            })

        return chunks

    def _get_chunk_text(self, transactions: List[Dict], raw_text: str) -> str:
        """Get relevant text for a chunk (simplified)"""
        # For now, return formatted transaction text
        # In production, should extract relevant portion from raw_text

        chunk_text = ""
        for txn in transactions:
            chunk_text += f"{txn.get('tanggal', '')} {txn.get('keterangan', '')} "
            chunk_text += f"{txn.get('debet', 0)} {txn.get('kredit', 0)} {txn.get('saldo', 0)}\n"

        return chunk_text

    async def _process_chunk_with_gpt(
        self,
        chunk_text: str,
        saldo_start: float,
        bank_name: str
    ) -> Dict:
        """Process chunk with GPT (via SmartMapper)"""
        # Call SmartMapper with chunk context
        result = await self.smart_mapper.extract_from_text(
            text=chunk_text,
            document_type='rekening_koran',
            metadata={
                'bank_name': bank_name,
                'saldo_start': saldo_start,
            }
        )

        return result

    def _generate_summary(self, transactions: List[Dict]) -> Dict:
        """Generate transaction summary"""
        if not transactions:
            return {}

        total_debet = sum(float(t.get('debet', 0)) for t in transactions)
        total_kredit = sum(float(t.get('kredit', 0)) for t in transactions)

        return {
            'total_transaksi': len(transactions),
            'total_debet': str(int(total_debet)),
            'total_kredit': str(int(total_kredit)),
            'net_change': str(int(total_kredit - total_debet)),
        }

    def _calculate_overall_confidence(
        self,
        transactions: List[Dict],
        validations: List
    ) -> float:
        """Calculate overall confidence score"""
        if not transactions:
            return 0.0

        # Average transaction confidence
        txn_confidences = [t.get('confidence', 0.7) for t in transactions]
        avg_txn_confidence = (sum(txn_confidences) / len(txn_confidences)) if len(txn_confidences) > 0 else 0.7

        # Validation pass rate
        total_chunks = len(validations)
        passed_chunks = sum(1 for v in validations if v.validation.is_valid)
        validation_rate = passed_chunks / total_chunks if total_chunks > 0 else 0

        # Weighted average
        overall_confidence = (avg_txn_confidence * 0.6) + (validation_rate * 0.4)

        return overall_confidence

    def _calculate_page_statistics(
        self,
        transactions: List[Dict],
        pages_info: List[Dict]
    ) -> Dict:
        """
        Calculate statistics per page

        Returns detailed page information including:
        - Total pages
        - Transactions per page
        - Page details (which pages have data, which don't)
        """
        # Count transactions per page
        transactions_per_page = {}
        for txn in transactions:
            page = txn.get('page', 1)
            transactions_per_page[page] = transactions_per_page.get(page, 0) + 1

        # Build detailed page info
        pages_detail = []
        total_pages = len(pages_info) if pages_info else 1

        for page_info in pages_info:
            page_num = page_info['page_number']
            txn_count = transactions_per_page.get(page_num, 0)

            pages_detail.append({
                'page_number': page_num,
                'transaction_count': txn_count,
                'has_tables': page_info.get('has_tables', False),
                'table_count': page_info.get('table_count', 0),
                'has_data': txn_count > 0,
            })

        # Summary
        pages_with_data = sum(1 for p in pages_detail if p['has_data'])
        pages_without_data = total_pages - pages_with_data

        return {
            'total_pages': total_pages,
            'pages_with_transactions': pages_with_data,
            'pages_without_transactions': pages_without_data,
            'transactions_per_page': transactions_per_page,
            'pages_detail': pages_detail,
        }

    def _try_bank_adapter(self, ocr_result: Dict) -> Optional[Dict]:
        """
        Try to detect and use bank-specific adapter

        Returns:
            Dict with success flag, transactions, and account_info
            or None if detection/parsing failed
        """
        if not self.bank_detector:
            logger.info("   ⚠️ BankDetector not available")
            return None

        try:
            # Try AI detection first if available
            bank_code = None
            adapter = None

            if self.ai_detector:
                try:
                    logger.info("   🤖 Trying AI-based bank detection...")
                    bank_code = self.ai_detector.detect(ocr_result, verbose=True)
                    if bank_code:
                        logger.info(f"   ✅ AI detected bank code: {bank_code}")
                        adapter = self.bank_detector.get_adapter_by_code(bank_code)
                except Exception as e:
                    logger.warning(f"   ⚠️ AI detection failed: {e}")
                    bank_code = None

            # Fallback to keyword-based detection
            if not adapter:
                logger.info("   🔍 Trying keyword-based bank detection...")
                adapter = self.bank_detector.detect(ocr_result, verbose=True)

            if not adapter:
                logger.warning("   ⚠️ No bank adapter detected")
                return {'success': False, 'reason': 'no_adapter_detected'}

            logger.info(f"   ✅ Detected bank: {adapter.BANK_NAME} ({adapter.BANK_CODE})")

            # Parse transactions using bank adapter
            logger.info("   📝 Parsing with bank adapter...")
            transactions = adapter.parse(ocr_result)

            if not transactions:
                logger.warning("   ⚠️ Bank adapter returned no transactions")
                return {'success': False, 'reason': 'no_transactions'}

            logger.info(f"   ✅ Bank adapter parsed {len(transactions)} transactions")

            # Extract account info
            account_info = adapter.extract_account_info(ocr_result)

            return {
                'success': True,
                'source': 'bank_adapter',
                'bank_name': adapter.BANK_NAME,
                'bank_code': adapter.BANK_CODE,
                'transactions': transactions,
                'account_info': account_info,
                'confidence': 0.90  # Bank adapters have high confidence
            }

        except Exception as e:
            logger.error(f"   ❌ Bank adapter error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {'success': False, 'reason': str(e)}

    def _convert_adapter_transaction(self, adapter_txn) -> Dict:
        """
        Convert bank adapter's StandardizedTransaction to our format

        Args:
            adapter_txn: StandardizedTransaction object from bank adapter

        Returns:
            Dict in our standard format
        """
        # Extract values from adapter transaction
        # Handle both object attributes and dict access
        if hasattr(adapter_txn, 'transaction_date'):
            # It's a StandardizedTransaction object
            tanggal = adapter_txn.transaction_date or ''
            keterangan = adapter_txn.description or ''
            debet = float(adapter_txn.debit or 0)
            kredit = float(adapter_txn.credit or 0)
            saldo = float(adapter_txn.balance or 0)
            referensi = adapter_txn.reference_number or ''
            page = getattr(adapter_txn, 'page_number', 1)
        else:
            # It's already a dict
            tanggal = adapter_txn.get('transaction_date', '')
            keterangan = adapter_txn.get('description', '')
            debet = float(adapter_txn.get('debit', 0))
            kredit = float(adapter_txn.get('credit', 0))
            saldo = float(adapter_txn.get('balance', 0))
            referensi = adapter_txn.get('reference_number', '')
            page = adapter_txn.get('page_number', 1)

        return {
            'tanggal': tanggal,
            'keterangan': keterangan,
            'debet': debet,
            'kredit': kredit,
            'saldo': saldo,
            'referensi': referensi,
            'confidence': 0.90,  # Bank adapters have high confidence
            'page': page,
        }
