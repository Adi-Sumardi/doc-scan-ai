"""
Tax Reconciliation Service V2.0
Auto-matching algorithm untuk mencocokan Faktur Pajak dengan Transaksi Bank
Enhanced with dual AI import from existing scan results
"""

from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import uuid
from difflib import SequenceMatcher
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
import logging

from database import (
    ReconciliationProject,
    TaxInvoice,
    BankTransaction,
    ReconciliationMatch,
    ScanResult,
    Batch
)

logger = logging.getLogger(__name__)

# Import AI services for intelligent matching
try:
    from smart_mapper import SmartMapper
    SMART_MAPPER_AVAILABLE = True
except ImportError:
    SMART_MAPPER_AVAILABLE = False
    logger.warning("⚠️ SmartMapper not available - AI vendor matching disabled")


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

        # Initialize AI services
        self.smart_mapper = None
        if SMART_MAPPER_AVAILABLE:
            try:
                self.smart_mapper = SmartMapper()
                logger.info("🤖 SmartMapper initialized for AI vendor matching")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize SmartMapper: {e}")

    # ========================================
    # Project Management (V2.0)
    # ========================================

    def create_project(
        self,
        name: str,
        period_start: datetime,
        period_end: datetime,
        description: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> ReconciliationProject:
        """Create a new reconciliation project"""

        project = ReconciliationProject(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            period_start=period_start,
            period_end=period_end,
            status="active",
            user_id=user_id
        )

        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)

        logger.info(f"✅ Created reconciliation project: {project.name} ({project.id})")
        return project

    def get_project(self, project_id: str) -> Optional[ReconciliationProject]:
        """Get project by ID"""
        return self.db.query(ReconciliationProject).filter(
            ReconciliationProject.id == project_id
        ).first()

    # ========================================
    # Import from Existing Scans (V2.0 - 70% Reuse!)
    # ========================================

    def import_invoices_from_batch(
        self,
        project_id: str,
        batch_id: str
    ) -> Dict[str, Any]:
        """
        Import tax invoices from existing scan batch
        Reuses OCR results from processing pipeline (GPT-4o)
        """

        project = self.get_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        # Get all scan results from batch that are tax invoices
        scan_results = self.db.query(ScanResult).filter(
            and_(
                ScanResult.batch_id == batch_id,
                ScanResult.document_type == "faktur_pajak"
            )
        ).all()

        imported_count = 0
        skipped_count = 0

        for scan_result in scan_results:
            # Check if already imported
            existing = self.db.query(TaxInvoice).filter(
                TaxInvoice.scan_result_id == scan_result.id
            ).first()

            if existing:
                logger.info(f"⏭️  Skipping already imported invoice: {scan_result.original_filename}")
                skipped_count += 1
                continue

            # Extract invoice data from scan result
            extracted_data = scan_result.extracted_data or {}

            # Determine AI model used
            ai_model = extracted_data.get("ai_model_used", "gpt-4o")

            # Parse date
            invoice_date = self._parse_date(extracted_data.get("tanggal_faktur"))
            if not invoice_date:
                logger.warning(f"⚠️  Skipping invoice with invalid date: {scan_result.original_filename}")
                skipped_count += 1
                continue

            # Create tax invoice from scan result
            invoice = TaxInvoice(
                id=str(uuid.uuid4()),
                project_id=project_id,
                scan_result_id=scan_result.id,
                invoice_number=extracted_data.get("nomor_faktur", ""),
                invoice_date=invoice_date,
                invoice_type=extracted_data.get("jenis_faktur", "keluaran"),
                vendor_name=extracted_data.get("nama_penjual", ""),
                vendor_npwp=extracted_data.get("npwp_penjual", ""),
                dpp=float(extracted_data.get("dpp", 0)),
                ppn=float(extracted_data.get("ppn", 0)),
                total_amount=float(extracted_data.get("total", 0)),
                ai_model_used=ai_model,
                extraction_confidence=scan_result.confidence,
                match_status="unmatched"
            )

            self.db.add(invoice)
            imported_count += 1

        self.db.commit()

        # Update project statistics
        self._update_project_statistics(project_id)

        logger.info(f"✅ Imported {imported_count} invoices, skipped {skipped_count}")

        return {
            "imported": imported_count,
            "skipped": skipped_count,
            "total": imported_count + skipped_count
        }

    def import_transactions_from_batch(
        self,
        project_id: str,
        batch_id: str
    ) -> Dict[str, Any]:
        """
        Import bank transactions from existing scan batch
        Reuses OCR results from processing pipeline (Claude Sonnet 4)
        """

        project = self.get_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        # Get all scan results from batch that are bank statements
        scan_results = self.db.query(ScanResult).filter(
            and_(
                ScanResult.batch_id == batch_id,
                ScanResult.document_type == "rekening_koran"
            )
        ).all()

        imported_count = 0
        skipped_count = 0

        for scan_result in scan_results:
            # Extract transaction data from scan result
            extracted_data = scan_result.extracted_data or {}
            transactions = extracted_data.get("transactions", [])

            # Determine AI model used
            ai_model = extracted_data.get("ai_model_used", "claude-sonnet-4")

            for transaction_data in transactions:
                # Parse date
                transaction_date = self._parse_date(transaction_data.get("tanggal"))
                if not transaction_date:
                    skipped_count += 1
                    continue

                # Check if already imported (by unique combination)
                ref_number = transaction_data.get("keterangan", "")

                existing = self.db.query(BankTransaction).filter(
                    and_(
                        BankTransaction.scan_result_id == scan_result.id,
                        BankTransaction.transaction_date == transaction_date,
                        BankTransaction.description == ref_number
                    )
                ).first()

                if existing:
                    skipped_count += 1
                    continue

                # Create bank transaction
                transaction = BankTransaction(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    scan_result_id=scan_result.id,
                    bank_name=extracted_data.get("bank_name", ""),
                    account_number=extracted_data.get("nomor_rekening", ""),
                    account_holder=extracted_data.get("nama_pemilik", ""),
                    transaction_date=transaction_date,
                    description=ref_number,
                    transaction_type=transaction_data.get("jenis", ""),
                    reference_number=transaction_data.get("nomor_referensi", ""),
                    debit=float(transaction_data.get("debit", 0)),
                    credit=float(transaction_data.get("kredit", 0)),
                    balance=float(transaction_data.get("saldo", 0)),
                    ai_model_used=ai_model,
                    extraction_confidence=scan_result.confidence,
                    match_status="unmatched"
                )

                self.db.add(transaction)
                imported_count += 1

        self.db.commit()

        # Update project statistics
        self._update_project_statistics(project_id)

        logger.info(f"✅ Imported {imported_count} transactions, skipped {skipped_count}")

        return {
            "imported": imported_count,
            "skipped": skipped_count,
            "total": imported_count + skipped_count
        }

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string to datetime"""
        if not date_str:
            return None

        # Try multiple date formats
        formats = [
            "%d/%m/%Y",
            "%Y-%m-%d",
            "%d-%m-%Y",
            "%d %B %Y",
            "%d %b %Y",
            "%d.%m.%Y"
        ]

        for fmt in formats:
            try:
                return datetime.strptime(str(date_str), fmt)
            except ValueError:
                continue

        logger.warning(f"⚠️  Could not parse date: {date_str}")
        return None

    # ========================================
    # AI-Powered Vendor & Invoice Extraction (V2.0)
    # ========================================

    def ai_extract_vendor_from_transactions(
        self,
        project_id: str,
        batch_size: int = 50
    ) -> Dict[str, Any]:
        """
        Use GPT-4o to extract clean vendor names from messy bank transaction descriptions

        Example:
        Input: "TRANSFER KE PT MAJU JAYA SEJAHTERA/REF123"
        Output: extracted_vendor_name = "PT MAJU JAYA SEJAHTERA"
        """

        if not self.smart_mapper or not self.smart_mapper._client:
            logger.warning("⚠️ SmartMapper not available - skipping AI vendor extraction")
            return {"processed": 0, "extracted": 0, "failed": 0}

        # Get unprocessed transactions (no extracted_vendor_name yet)
        transactions = self.db.query(BankTransaction).filter(
            and_(
                BankTransaction.project_id == project_id,
                BankTransaction.extracted_vendor_name == None
            )
        ).limit(batch_size).all()

        if not transactions:
            logger.info("✅ All transactions already have vendor names extracted")
            return {"processed": 0, "extracted": 0, "failed": 0}

        processed = 0
        extracted = 0
        failed = 0

        for transaction in transactions:
            try:
                # Build prompt for GPT-4o
                prompt = f"""Extract the vendor/company name from this bank transaction description:

Description: "{transaction.description}"
Reference: "{transaction.reference_number or ''}"

Rules:
1. Extract ONLY the company/vendor name (e.g., "PT MAJU JAYA", "CV BERKAH", "TOKO SINAR")
2. Remove prefixes like "TRANSFER KE", "BAYAR", "SETORAN"
3. Remove suffixes like reference numbers, dates, invoice numbers
4. Return just the clean company name
5. If no clear vendor name found, return "UNKNOWN"

Return ONLY the vendor name, nothing else."""

                # Call GPT-4o
                response = self.smart_mapper._client.chat.completions.create(
                    model=self.smart_mapper.model,
                    messages=[
                        {"role": "system", "content": "You are a financial data extraction expert."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    max_tokens=100
                )

                vendor_name = response.choices[0].message.content.strip()

                # Update transaction
                if vendor_name and vendor_name != "UNKNOWN":
                    transaction.extracted_vendor_name = vendor_name
                    transaction.ai_model_used = self.smart_mapper.model
                    transaction.extraction_confidence = 0.85  # GPT-4o confidence
                    extracted += 1
                    logger.info(f"✅ Extracted vendor: '{vendor_name}' from '{transaction.description[:50]}'")
                else:
                    transaction.extracted_vendor_name = None
                    failed += 1

                processed += 1

            except Exception as e:
                logger.error(f"❌ Failed to extract vendor from transaction {transaction.id}: {e}")
                failed += 1

        self.db.commit()
        logger.info(f"🎯 AI Vendor Extraction: {extracted} extracted, {failed} failed out of {processed} processed")

        return {
            "processed": processed,
            "extracted": extracted,
            "failed": failed
        }

    def ai_extract_invoice_from_transactions(
        self,
        project_id: str,
        batch_size: int = 50
    ) -> Dict[str, Any]:
        """
        Use Claude to extract invoice numbers from bank transaction descriptions/references

        Example:
        Input: "TRANSFER/INV-2024-001/PT MAJU"
        Output: extracted_invoice_number = "INV-2024-001"
        """

        if not self.smart_mapper or not self.smart_mapper._claude_client:
            logger.warning("⚠️ Claude not available - skipping AI invoice extraction")
            return {"processed": 0, "extracted": 0, "failed": 0}

        # Get unprocessed transactions (no extracted_invoice_number yet)
        transactions = self.db.query(BankTransaction).filter(
            and_(
                BankTransaction.project_id == project_id,
                BankTransaction.extracted_invoice_number == None
            )
        ).limit(batch_size).all()

        if not transactions:
            logger.info("✅ All transactions already have invoice numbers extracted")
            return {"processed": 0, "extracted": 0, "failed": 0}

        processed = 0
        extracted = 0
        failed = 0

        for transaction in transactions:
            try:
                # Build prompt for Claude
                prompt = f"""Extract the invoice/faktur number from this bank transaction:

Description: "{transaction.description}"
Reference: "{transaction.reference_number or ''}"

Rules:
1. Look for invoice numbers (formats: INV-XXX, FP-XXX, FAKTUR-XXX, etc.)
2. Return ONLY the invoice number
3. If no invoice number found, return "NONE"

Return ONLY the invoice number or "NONE"."""

                # Call Claude
                response = self.smart_mapper._claude_client.messages.create(
                    model=self.smart_mapper.claude_model,
                    max_tokens=100,
                    temperature=0.1,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )

                invoice_number = response.content[0].text.strip()

                # Update transaction
                if invoice_number and invoice_number != "NONE":
                    transaction.extracted_invoice_number = invoice_number
                    transaction.ai_model_used = self.smart_mapper.claude_model
                    transaction.extraction_confidence = 0.90  # Claude confidence
                    extracted += 1
                    logger.info(f"✅ Extracted invoice: '{invoice_number}' from '{transaction.description[:50]}'")
                else:
                    transaction.extracted_invoice_number = None
                    failed += 1

                processed += 1

            except Exception as e:
                logger.error(f"❌ Failed to extract invoice from transaction {transaction.id}: {e}")
                failed += 1

        self.db.commit()
        logger.info(f"🎯 AI Invoice Extraction: {extracted} extracted, {failed} failed out of {processed} processed")

        return {
            "processed": processed,
            "extracted": extracted,
            "failed": failed
        }

    # ========================================
    # Auto-Matching Algorithm
    # ========================================

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
