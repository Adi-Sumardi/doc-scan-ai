"""
Progressive Validator
Validates rule-based parsing and only uses GPT when needed

Strategy:
1. Parse with rules first (cheap)
2. Validate saldo continuity
3. IF validation fails → Use GPT for that chunk only
4. Track which chunks needed GPT (for metrics)
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of validation check"""
    is_valid: bool
    saldo_match: bool
    expected_saldo: Optional[float]
    actual_saldo: Optional[float]
    error_message: Optional[str]
    needs_gpt: bool


@dataclass
class ChunkValidation:
    """Validation result for a chunk"""
    chunk_id: int
    validation: ValidationResult
    transactions: List[Dict]
    saldo_start: float
    saldo_end: float
    processed_with_gpt: bool


class ProgressiveValidator:
    """
    Validates transactions and determines if GPT is needed

    Validation checks:
    1. Saldo continuity (each transaction's saldo matches calculation)
    2. Running balance (saldo_end = saldo_start + kredit - debet)
    3. Data completeness (no missing critical fields)
    """

    def __init__(self, tolerance: float = 0.01):
        """
        Args:
            tolerance: Tolerance for saldo comparison (default 1 cent)
        """
        self.tolerance = tolerance
        logger.info(f"🔍 ProgressiveValidator initialized (tolerance={tolerance})")

    def validate_transaction_saldo(
        self,
        transaction: Dict,
        previous_saldo: float
    ) -> Tuple[bool, float]:
        """
        Validate a single transaction's saldo

        Args:
            transaction: Transaction dict with debet, kredit, saldo
            previous_saldo: Expected saldo before this transaction

        Returns:
            (is_valid, calculated_saldo)
        """
        debet = float(transaction.get('debet', 0))
        kredit = float(transaction.get('kredit', 0))
        reported_saldo = float(transaction.get('saldo', 0))

        # Calculate expected saldo
        calculated_saldo = previous_saldo + kredit - debet

        # Compare with reported saldo
        difference = abs(calculated_saldo - reported_saldo)
        is_valid = difference <= self.tolerance

        return is_valid, calculated_saldo

    def validate_chunk_saldo_continuity(
        self,
        transactions: List[Dict],
        saldo_start: float
    ) -> ValidationResult:
        """
        Validate saldo continuity for all transactions in a chunk

        Args:
            transactions: List of transaction dicts
            saldo_start: Starting saldo for this chunk

        Returns:
            ValidationResult with validation status
        """
        if not transactions:
            return ValidationResult(
                is_valid=False,
                saldo_match=False,
                expected_saldo=saldo_start,
                actual_saldo=None,
                error_message="No transactions in chunk",
                needs_gpt=True
            )

        current_saldo = saldo_start
        all_valid = True
        error_messages = []

        for i, txn in enumerate(transactions):
            is_valid, calculated_saldo = self.validate_transaction_saldo(txn, current_saldo)

            if not is_valid:
                all_valid = False
                reported = txn.get('saldo', 0)
                error_messages.append(
                    f"Txn {i}: Expected saldo {calculated_saldo:.2f}, got {reported:.2f}"
                )

            current_saldo = calculated_saldo

        # Final saldo
        final_transaction = transactions[-1]
        final_saldo_reported = float(final_transaction.get('saldo', 0))
        final_saldo_calculated = current_saldo

        saldo_match = abs(final_saldo_reported - final_saldo_calculated) <= self.tolerance

        return ValidationResult(
            is_valid=all_valid and saldo_match,
            saldo_match=saldo_match,
            expected_saldo=final_saldo_calculated,
            actual_saldo=final_saldo_reported,
            error_message='; '.join(error_messages) if error_messages else None,
            needs_gpt=not (all_valid and saldo_match)
        )

    def validate_data_completeness(self, transactions: List[Dict]) -> Tuple[bool, List[str]]:
        """
        Check if all transactions have required fields

        Args:
            transactions: List of transaction dicts

        Returns:
            (is_complete, missing_fields)
        """
        required_fields = ['tanggal', 'keterangan', 'saldo']
        missing_fields = []

        for i, txn in enumerate(transactions):
            for field in required_fields:
                if not txn.get(field):
                    missing_fields.append(f"Txn {i}: missing '{field}'")

        is_complete = len(missing_fields) == 0

        return is_complete, missing_fields

    def validate_chunk(
        self,
        chunk_id: int,
        transactions: List[Dict],
        saldo_start: float,
        previous_chunk_saldo: Optional[float] = None
    ) -> ChunkValidation:
        """
        Validate a chunk and determine if GPT is needed

        Args:
            chunk_id: Chunk identifier
            transactions: List of transactions in this chunk
            saldo_start: Starting saldo for this chunk
            previous_chunk_saldo: Ending saldo from previous chunk (for continuity check)

        Returns:
            ChunkValidation with validation result and recommendation
        """
        # Check 1: Saldo continuity within chunk
        saldo_validation = self.validate_chunk_saldo_continuity(transactions, saldo_start)

        # Check 2: Data completeness
        is_complete, missing_fields = self.validate_data_completeness(transactions)

        # Check 3: Inter-chunk continuity
        inter_chunk_valid = True
        if previous_chunk_saldo is not None:
            difference = abs(saldo_start - previous_chunk_saldo)
            inter_chunk_valid = difference <= self.tolerance

            if not inter_chunk_valid:
                logger.warning(
                    f"⚠️ Chunk {chunk_id} saldo mismatch with previous chunk: "
                    f"Expected {previous_chunk_saldo:.2f}, got {saldo_start:.2f}"
                )

        # Determine if GPT is needed
        needs_gpt = (
            saldo_validation.needs_gpt or
            not is_complete or
            not inter_chunk_valid
        )

        # Calculate saldo_end
        if transactions:
            saldo_end = float(transactions[-1].get('saldo', saldo_start))
        else:
            saldo_end = saldo_start

        # Build validation result
        validation = ValidationResult(
            is_valid=saldo_validation.is_valid and is_complete and inter_chunk_valid,
            saldo_match=saldo_validation.saldo_match,
            expected_saldo=saldo_validation.expected_saldo,
            actual_saldo=saldo_validation.actual_saldo,
            error_message=saldo_validation.error_message,
            needs_gpt=needs_gpt
        )

        result = ChunkValidation(
            chunk_id=chunk_id,
            validation=validation,
            transactions=transactions,
            saldo_start=saldo_start,
            saldo_end=saldo_end,
            processed_with_gpt=False  # Will be set to True if GPT is used
        )

        # Log validation result
        if validation.is_valid:
            logger.info(f"✅ Chunk {chunk_id} validation PASSED (no GPT needed)")
        else:
            logger.warning(
                f"⚠️ Chunk {chunk_id} validation FAILED - GPT required\n"
                f"   Reason: {validation.error_message or 'Saldo mismatch'}"
            )

        return result

    def validate_all_chunks(
        self,
        chunks: List[Dict],
        saldo_awal: float
    ) -> List[ChunkValidation]:
        """
        Validate all chunks sequentially

        Args:
            chunks: List of chunk dicts with transactions
            saldo_awal: Starting saldo for the first chunk

        Returns:
            List of ChunkValidation results
        """
        validations = []
        previous_saldo = None

        for i, chunk in enumerate(chunks):
            transactions = chunk.get('transactions', [])
            chunk_saldo_start = chunk.get('saldo_start', saldo_awal if i == 0 else previous_saldo)

            validation = self.validate_chunk(
                chunk_id=i,
                transactions=transactions,
                saldo_start=chunk_saldo_start,
                previous_chunk_saldo=previous_saldo
            )

            validations.append(validation)
            previous_saldo = validation.saldo_end

        return validations

    def get_validation_stats(self, validations: List[ChunkValidation]) -> Dict:
        """
        Get statistics about validation results

        Args:
            validations: List of ChunkValidation results

        Returns:
            Statistics dict
        """
        total = len(validations)
        passed = sum(1 for v in validations if v.validation.is_valid)
        failed = total - passed
        needs_gpt = sum(1 for v in validations if v.validation.needs_gpt)
        processed_with_gpt = sum(1 for v in validations if v.processed_with_gpt)

        return {
            'total_chunks': total,
            'passed': passed,
            'failed': failed,
            'needs_gpt': needs_gpt,
            'processed_with_gpt': processed_with_gpt,
            'pass_rate': (passed / total * 100) if total > 0 else 0,
            'gpt_usage_rate': (needs_gpt / total * 100) if total > 0 else 0,
        }

    def should_use_gpt(self, validation: ChunkValidation, confidence_threshold: float = 0.90) -> bool:
        """
        Determine if GPT should be used based on validation and confidence

        Args:
            validation: ChunkValidation result
            confidence_threshold: Minimum confidence to skip GPT

        Returns:
            True if GPT should be used
        """
        # Always use GPT if validation failed
        if validation.validation.needs_gpt:
            return True

        # Check transaction confidence scores (if available)
        avg_confidence = 0.0
        txn_count = len(validation.transactions)

        if txn_count > 0:
            confidences = [
                txn.get('confidence', 1.0)
                for txn in validation.transactions
            ]
            avg_confidence = sum(confidences) / len(confidences)

        # Use GPT if average confidence is low
        if avg_confidence < confidence_threshold:
            logger.info(
                f"⚠️ Chunk {validation.chunk_id} has low confidence "
                f"({avg_confidence:.2f} < {confidence_threshold}) - using GPT"
            )
            return True

        return False

    def calculate_expected_saldo_chain(
        self,
        all_transactions: List[Dict],
        saldo_awal: float
    ) -> List[float]:
        """
        Calculate expected saldo for each transaction

        Args:
            all_transactions: All transactions
            saldo_awal: Starting balance

        Returns:
            List of calculated saldo values
        """
        saldo_chain = [saldo_awal]
        current_saldo = saldo_awal

        for txn in all_transactions:
            debet = float(txn.get('debet', 0))
            kredit = float(txn.get('kredit', 0))
            current_saldo = current_saldo + kredit - debet
            saldo_chain.append(current_saldo)

        return saldo_chain

    def reconcile_saldo_mismatch(
        self,
        transactions: List[Dict],
        expected_saldo_start: float,
        actual_saldo_end: float
    ) -> Optional[Dict]:
        """
        Attempt to reconcile saldo mismatch by finding the error point

        Args:
            transactions: List of transactions
            expected_saldo_start: Starting saldo
            actual_saldo_end: Reported ending saldo

        Returns:
            Dict with reconciliation info or None if can't reconcile
        """
        saldo_chain = self.calculate_expected_saldo_chain(transactions, expected_saldo_start)
        calculated_end = saldo_chain[-1]

        difference = actual_saldo_end - calculated_end

        # Check if the difference is consistent (might be a starting saldo error)
        if abs(difference) > self.tolerance:
            return {
                'type': 'saldo_offset',
                'difference': difference,
                'calculated_end': calculated_end,
                'actual_end': actual_saldo_end,
                'suggestion': 'Adjust starting saldo or review transactions'
            }

        return None
