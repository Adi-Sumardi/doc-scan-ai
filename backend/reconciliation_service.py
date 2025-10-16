"""
Tax Reconciliation Service
Auto-matching algorithm untuk mencocokan Faktur Pajak dengan Transaksi Bank
"""

from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import uuid
from difflib import SequenceMatcher
from sqlalchemy.orm import Session

from database import (
    ReconciliationProject,
    TaxInvoice,
    BankTransaction,
    ReconciliationMatch
)


class ReconciliationService:
    """
    Service untuk auto-matching Faktur Pajak dengan Rekening Koran

    Matching Algorithm:
    1. Amount Match (50%): Invoice amount vs Transaction amount
    2. Date Match (25%): Invoice date vs Transaction date (tolerance ±7 hari)
    3. Vendor Match (15%): Vendor name similarity dengan transaction description
    4. Reference Match (10%): Invoice number in transaction reference/description

    Total Score = 100%
    - High Confidence: ≥ 90%
    - Medium Confidence: 70-89%
    - Low Confidence: 50-69%
    - No Match: < 50%
    """

    # Matching thresholds
    HIGH_CONFIDENCE = 0.90
    MEDIUM_CONFIDENCE = 0.70
    LOW_CONFIDENCE = 0.50

    # Scoring weights
    WEIGHT_AMOUNT = 0.50
    WEIGHT_DATE = 0.25
    WEIGHT_VENDOR = 0.15
    WEIGHT_REFERENCE = 0.10

    # Date tolerance (days)
    DATE_TOLERANCE = 7

    def __init__(self, db: Session):
        self.db = db

    def auto_match_project(
        self,
        project_id: str,
        min_confidence: float = 0.70
    ) -> Dict[str, Any]:
        """
        Auto-match semua invoices dengan transactions dalam project

        Args:
            project_id: ID proyek rekonsiliasi
            min_confidence: Minimum confidence untuk create match

        Returns:
            Dict dengan hasil matching
        """
        start_time = datetime.now()

        # Get project
        project = self.db.query(ReconciliationProject).filter(
            ReconciliationProject.id == project_id
        ).first()

        if not project:
            raise ValueError(f"Project not found: {project_id}")

        # Get unmatched invoices
        invoices = self.db.query(TaxInvoice).filter(
            TaxInvoice.project_id == project_id,
            TaxInvoice.match_status == "unmatched"
        ).all()

        # Get unmatched transactions
        transactions = self.db.query(BankTransaction).filter(
            BankTransaction.project_id == project_id,
            BankTransaction.match_status == "unmatched"
        ).all()

        if not invoices or not transactions:
            return {
                'project_id': project_id,
                'total_invoices': len(invoices),
                'total_transactions': len(transactions),
                'matches_found': 0,
                'high_confidence_matches': 0,
                'medium_confidence_matches': 0,
                'low_confidence_matches': 0,
                'processing_time_seconds': 0.0
            }

        # Perform matching
        matches = []
        high_confidence = 0
        medium_confidence = 0
        low_confidence = 0

        for invoice in invoices:
            best_match = None
            best_score = 0.0

            for transaction in transactions:
                # Skip if transaction already matched
                if transaction.match_status != "unmatched":
                    continue

                # Calculate match score
                score_details = self._calculate_match_score(invoice, transaction)
                total_score = score_details['total_score']

                # Keep best match
                if total_score > best_score and total_score >= min_confidence:
                    best_score = total_score
                    best_match = (transaction, score_details)

            # Create match if found
            if best_match:
                transaction, score_details = best_match

                # Create match record
                match = self._create_match(
                    project_id=project_id,
                    invoice=invoice,
                    transaction=transaction,
                    score_details=score_details,
                    match_type="auto"
                )

                # Update invoice and transaction status
                invoice.match_status = "auto_matched"
                invoice.match_confidence = best_score
                invoice.matched_transaction_id = transaction.id
                invoice.matched_at = datetime.now()

                transaction.match_status = "auto_matched"
                transaction.match_confidence = best_score
                transaction.matched_invoice_id = invoice.id
                transaction.matched_at = datetime.now()

                matches.append(match)

                # Count by confidence level
                if best_score >= self.HIGH_CONFIDENCE:
                    high_confidence += 1
                elif best_score >= self.MEDIUM_CONFIDENCE:
                    medium_confidence += 1
                else:
                    low_confidence += 1

        # Commit all changes
        self.db.commit()

        # Update project statistics
        self._update_project_statistics(project_id)

        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()

        return {
            'project_id': project_id,
            'total_invoices': len(invoices),
            'total_transactions': len(transactions),
            'matches_found': len(matches),
            'high_confidence_matches': high_confidence,
            'medium_confidence_matches': medium_confidence,
            'low_confidence_matches': low_confidence,
            'processing_time_seconds': round(processing_time, 2)
        }

    def suggest_matches(
        self,
        project_id: str,
        invoice_id: str,
        limit: int = 5
    ) -> List[Tuple[BankTransaction, Dict[str, Any]]]:
        """
        Suggest top N matching transactions untuk specific invoice

        Args:
            project_id: ID proyek
            invoice_id: ID invoice
            limit: Jumlah suggestions

        Returns:
            List of (transaction, score_details) tuples
        """
        # Get invoice
        invoice = self.db.query(TaxInvoice).filter(
            TaxInvoice.id == invoice_id,
            TaxInvoice.project_id == project_id
        ).first()

        if not invoice:
            raise ValueError(f"Invoice not found: {invoice_id}")

        # Get unmatched transactions
        transactions = self.db.query(BankTransaction).filter(
            BankTransaction.project_id == project_id,
            BankTransaction.match_status == "unmatched"
        ).all()

        # Calculate scores for all transactions
        suggestions = []
        for transaction in transactions:
            score_details = self._calculate_match_score(invoice, transaction)
            suggestions.append((transaction, score_details))

        # Sort by score (descending)
        suggestions.sort(key=lambda x: x[1]['total_score'], reverse=True)

        # Return top N
        return suggestions[:limit]

    def manual_match(
        self,
        project_id: str,
        invoice_id: str,
        transaction_id: str,
        user_id: str = None,
        notes: str = None
    ) -> ReconciliationMatch:
        """
        Manual match antara invoice dan transaction

        Args:
            project_id: ID proyek
            invoice_id: ID invoice
            transaction_id: ID transaction
            user_id: ID user yang melakukan match
            notes: Catatan

        Returns:
            ReconciliationMatch object
        """
        # Get invoice and transaction
        invoice = self.db.query(TaxInvoice).filter(
            TaxInvoice.id == invoice_id,
            TaxInvoice.project_id == project_id
        ).first()

        transaction = self.db.query(BankTransaction).filter(
            BankTransaction.id == transaction_id,
            BankTransaction.project_id == project_id
        ).first()

        if not invoice or not transaction:
            raise ValueError("Invoice or transaction not found")

        # Calculate score (for reference)
        score_details = self._calculate_match_score(invoice, transaction)

        # Create match
        match = self._create_match(
            project_id=project_id,
            invoice=invoice,
            transaction=transaction,
            score_details=score_details,
            match_type="manual"
        )
        match.notes = notes
        match.matched_by = user_id

        # Update invoice and transaction
        invoice.match_status = "manual_matched"
        invoice.match_confidence = score_details['total_score']
        invoice.matched_transaction_id = transaction_id
        invoice.matched_by = user_id
        invoice.matched_at = datetime.now()

        transaction.match_status = "manual_matched"
        transaction.match_confidence = score_details['total_score']
        transaction.matched_invoice_id = invoice_id
        transaction.matched_by = user_id
        transaction.matched_at = datetime.now()

        self.db.commit()

        # Update project statistics
        self._update_project_statistics(project_id)

        return match

    def unmatch(
        self,
        project_id: str,
        match_id: str,
        reason: str = None
    ) -> bool:
        """
        Unmatch/reject a match

        Args:
            project_id: ID proyek
            match_id: ID match
            reason: Rejection reason

        Returns:
            True if successful
        """
        # Get match
        match = self.db.query(ReconciliationMatch).filter(
            ReconciliationMatch.id == match_id,
            ReconciliationMatch.project_id == project_id
        ).first()

        if not match:
            raise ValueError(f"Match not found: {match_id}")

        # Get invoice and transaction
        invoice = self.db.query(TaxInvoice).filter(
            TaxInvoice.id == match.invoice_id
        ).first()

        transaction = self.db.query(BankTransaction).filter(
            BankTransaction.id == match.transaction_id
        ).first()

        # Update match status
        match.status = "rejected"
        match.rejection_reason = reason

        # Reset invoice and transaction
        if invoice:
            invoice.match_status = "unmatched"
            invoice.match_confidence = 0.0
            invoice.matched_transaction_id = None
            invoice.matched_by = None
            invoice.matched_at = None

        if transaction:
            transaction.match_status = "unmatched"
            transaction.match_confidence = 0.0
            transaction.matched_invoice_id = None
            transaction.matched_by = None
            transaction.matched_at = None

        self.db.commit()

        # Update project statistics
        self._update_project_statistics(project_id)

        return True

    def _calculate_match_score(
        self,
        invoice: TaxInvoice,
        transaction: BankTransaction
    ) -> Dict[str, Any]:
        """
        Calculate match score antara invoice dan transaction

        Returns:
            Dict dengan detailed scores
        """
        # 1. Amount Score (50%)
        score_amount = self._calculate_amount_score(
            invoice.total_amount,
            transaction.credit if transaction.credit > 0 else transaction.debit
        )

        # 2. Date Score (25%)
        score_date = self._calculate_date_score(
            invoice.invoice_date,
            transaction.transaction_date
        )

        # 3. Vendor Score (15%)
        score_vendor = self._calculate_vendor_score(
            invoice.vendor_name or "",
            transaction.description or ""
        )

        # 4. Reference Score (10%)
        score_reference = self._calculate_reference_score(
            invoice.invoice_number,
            transaction.reference_number or "",
            transaction.description or ""
        )

        # Calculate weighted total
        total_score = (
            score_amount * self.WEIGHT_AMOUNT +
            score_date * self.WEIGHT_DATE +
            score_vendor * self.WEIGHT_VENDOR +
            score_reference * self.WEIGHT_REFERENCE
        )

        # Calculate variance
        amount_variance = abs(
            invoice.total_amount -
            (transaction.credit if transaction.credit > 0 else transaction.debit)
        )

        date_variance_days = abs(
            (invoice.invoice_date - transaction.transaction_date).days
        )

        return {
            'score_amount': round(score_amount, 4),
            'score_date': round(score_date, 4),
            'score_vendor': round(score_vendor, 4),
            'score_reference': round(score_reference, 4),
            'total_score': round(total_score, 4),
            'amount_variance': round(amount_variance, 2),
            'date_variance_days': date_variance_days
        }

    def _calculate_amount_score(
        self,
        invoice_amount: float,
        transaction_amount: float
    ) -> float:
        """
        Calculate amount similarity score (0-1)

        Algorithm:
        - Exact match: 1.0
        - Within 1%: 0.95
        - Within 5%: 0.85
        - Within 10%: 0.70
        - Beyond 10%: decreasing score
        """
        if invoice_amount == 0 or transaction_amount == 0:
            return 0.0

        # Calculate percentage difference
        diff_percentage = abs(invoice_amount - transaction_amount) / invoice_amount

        if diff_percentage == 0:
            return 1.0
        elif diff_percentage <= 0.01:  # 1%
            return 0.95
        elif diff_percentage <= 0.05:  # 5%
            return 0.85
        elif diff_percentage <= 0.10:  # 10%
            return 0.70
        else:
            # Decreasing score beyond 10%
            score = max(0.0, 0.70 - (diff_percentage - 0.10) * 2)
            return score

    def _calculate_date_score(
        self,
        invoice_date: datetime,
        transaction_date: datetime
    ) -> float:
        """
        Calculate date proximity score (0-1)

        Algorithm:
        - Same date: 1.0
        - Within 1 day: 0.95
        - Within 3 days: 0.85
        - Within 7 days: 0.70
        - Beyond 7 days: decreasing score
        """
        days_diff = abs((invoice_date - transaction_date).days)

        if days_diff == 0:
            return 1.0
        elif days_diff <= 1:
            return 0.95
        elif days_diff <= 3:
            return 0.85
        elif days_diff <= self.DATE_TOLERANCE:
            return 0.70
        else:
            # Decreasing score beyond tolerance
            score = max(0.0, 0.70 - (days_diff - self.DATE_TOLERANCE) * 0.05)
            return score

    def _calculate_vendor_score(
        self,
        vendor_name: str,
        transaction_description: str
    ) -> float:
        """
        Calculate vendor name similarity score (0-1)

        Using SequenceMatcher for fuzzy string matching
        """
        if not vendor_name or not transaction_description:
            return 0.0

        # Normalize strings
        vendor_clean = vendor_name.upper().strip()
        desc_clean = transaction_description.upper().strip()

        # Check if vendor name is in description
        if vendor_clean in desc_clean:
            return 1.0

        # Calculate similarity ratio
        similarity = SequenceMatcher(None, vendor_clean, desc_clean).ratio()

        return similarity

    def _calculate_reference_score(
        self,
        invoice_number: str,
        transaction_reference: str,
        transaction_description: str
    ) -> float:
        """
        Calculate reference matching score (0-1)

        Check if invoice number appears in transaction reference or description
        """
        if not invoice_number:
            return 0.0

        invoice_clean = invoice_number.upper().strip()
        ref_clean = (transaction_reference or "").upper().strip()
        desc_clean = (transaction_description or "").upper().strip()

        # Exact match in reference
        if invoice_clean in ref_clean:
            return 1.0

        # Exact match in description
        if invoice_clean in desc_clean:
            return 0.8

        # Partial match
        # Split invoice number and check parts
        invoice_parts = [p for p in invoice_clean.split('-') if len(p) >= 3]

        for part in invoice_parts:
            if part in ref_clean or part in desc_clean:
                return 0.5

        return 0.0

    def _create_match(
        self,
        project_id: str,
        invoice: TaxInvoice,
        transaction: BankTransaction,
        score_details: Dict[str, Any],
        match_type: str
    ) -> ReconciliationMatch:
        """
        Create a match record
        """
        match = ReconciliationMatch(
            id=str(uuid.uuid4()),
            project_id=project_id,
            invoice_id=invoice.id,
            transaction_id=transaction.id,
            match_type=match_type,
            match_confidence=score_details['total_score'],
            match_score=score_details['total_score'],
            amount_variance=score_details['amount_variance'],
            date_variance_days=score_details['date_variance_days'],
            score_amount=score_details['score_amount'],
            score_date=score_details['score_date'],
            score_vendor=score_details['score_vendor'],
            score_reference=score_details['score_reference'],
            status="active",
            confirmed=False
        )

        self.db.add(match)
        return match

    def _update_project_statistics(self, project_id: str):
        """
        Update project statistics setelah matching
        """
        project = self.db.query(ReconciliationProject).filter(
            ReconciliationProject.id == project_id
        ).first()

        if not project:
            return

        # Count invoices
        total_invoices = self.db.query(TaxInvoice).filter(
            TaxInvoice.project_id == project_id
        ).count()

        matched_invoices = self.db.query(TaxInvoice).filter(
            TaxInvoice.project_id == project_id,
            TaxInvoice.match_status.in_(['auto_matched', 'manual_matched'])
        ).count()

        # Count transactions
        total_transactions = self.db.query(BankTransaction).filter(
            BankTransaction.project_id == project_id
        ).count()

        matched_transactions = self.db.query(BankTransaction).filter(
            BankTransaction.project_id == project_id,
            BankTransaction.match_status.in_(['auto_matched', 'manual_matched'])
        ).count()

        # Count matches
        matched_count = self.db.query(ReconciliationMatch).filter(
            ReconciliationMatch.project_id == project_id,
            ReconciliationMatch.status == 'active'
        ).count()

        # Calculate totals
        from sqlalchemy import func

        invoice_sum = self.db.query(func.sum(TaxInvoice.total_amount)).filter(
            TaxInvoice.project_id == project_id
        ).scalar() or 0.0

        transaction_sum = self.db.query(
            func.sum(BankTransaction.credit) + func.sum(BankTransaction.debit)
        ).filter(
            BankTransaction.project_id == project_id
        ).scalar() or 0.0

        # Update project
        project.total_invoices = total_invoices
        project.total_transactions = total_transactions
        project.matched_count = matched_count
        project.unmatched_invoices = total_invoices - matched_invoices
        project.unmatched_transactions = total_transactions - matched_transactions
        project.total_invoice_amount = float(invoice_sum)
        project.total_transaction_amount = float(transaction_sum)
        project.variance_amount = abs(float(invoice_sum) - float(transaction_sum))
        project.updated_at = datetime.now()

        self.db.commit()
