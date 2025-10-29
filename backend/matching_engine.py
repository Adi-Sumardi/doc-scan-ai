"""
Matching Engine Service
Matches data from Faktur Pajak, Rekening Koran, and PPh documents
Based on date, amount, and vendor name similarity
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
from difflib import SequenceMatcher
import logging
import re

logger = logging.getLogger(__name__)


@dataclass
class MatchCandidate:
    """Represents a potential match candidate"""
    source_type: str  # 'faktur_pajak', 'rekening_koran', 'pph21', 'pph23'
    source_file: str
    source_row: int
    date: str
    amount: Decimal
    vendor_name: str
    reference: str
    raw_data: Dict[str, Any]


@dataclass
class MatchResult:
    """Result of a matching operation"""
    match_id: str
    confidence_score: float
    match_type: str  # 'exact', 'partial', 'fuzzy'
    matched_items: List[Dict[str, Any]]
    unmatched_items: List[Dict[str, Any]]
    details: Dict[str, Any]


@dataclass
class ReconciliationSummary:
    """Summary of reconciliation results"""
    total_faktur: int
    total_rekening: int
    total_pph: int
    matched_count: int
    unmatched_faktur: int
    unmatched_rekening: int
    unmatched_pph: int
    belum_dilaporkan: int  # Transactions not yet reported in tax documents
    match_rate: float
    total_matched_amount: Decimal
    total_unmatched_amount: Decimal


class MatchingEngine:
    """
    Core matching engine for tax document reconciliation

    Matching Strategy:
    1. Date matching: ±3 days tolerance
    2. Amount matching: Exact match or within 1% tolerance
    3. Vendor name matching: Fuzzy string matching with 80% threshold
    4. Confidence scoring: Weighted average of all criteria
    """

    def __init__(
        self,
        date_tolerance_days: int = 3,
        amount_tolerance_percent: float = 1.0,
        vendor_similarity_threshold: float = 0.80,
        min_confidence_score: float = 0.70
    ):
        """
        Initialize matching engine with configurable thresholds

        Args:
            date_tolerance_days: Number of days tolerance for date matching
            amount_tolerance_percent: Percentage tolerance for amount matching
            vendor_similarity_threshold: Minimum similarity score for vendor names (0-1)
            min_confidence_score: Minimum confidence score to consider a match (0-1)
        """
        self.date_tolerance_days = date_tolerance_days
        self.amount_tolerance_percent = amount_tolerance_percent / 100.0
        self.vendor_similarity_threshold = vendor_similarity_threshold
        self.min_confidence_score = min_confidence_score

        logger.info(f"🔧 Matching Engine initialized:")
        logger.info(f"   Date tolerance: ±{date_tolerance_days} days")
        logger.info(f"   Amount tolerance: {amount_tolerance_percent}%")
        logger.info(f"   Vendor similarity threshold: {vendor_similarity_threshold}")
        logger.info(f"   Min confidence score: {min_confidence_score}")

    def normalize_vendor_name(self, name: str) -> str:
        """
        Normalize vendor name for comparison
        - Convert to uppercase
        - Remove extra spaces
        - Remove special characters
        - Remove common business entity suffixes
        """
        if not name:
            return ""

        # Convert to uppercase
        normalized = name.upper()

        # Remove common business suffixes
        suffixes = [
            r'\bPT\b', r'\bCV\b', r'\bUD\b', r'\bTBK\b',
            r'\bLTD\b', r'\bINC\b', r'\bCORP\b', r'\bLLC\b',
            r'\bPERSERO\b', r'\bTBK\b'
        ]
        for suffix in suffixes:
            normalized = re.sub(suffix, '', normalized)

        # Remove special characters except spaces
        normalized = re.sub(r'[^A-Z0-9\s]', '', normalized)

        # Remove extra spaces
        normalized = ' '.join(normalized.split())

        return normalized.strip()

    def calculate_vendor_similarity(self, name1: str, name2: str) -> float:
        """
        Calculate similarity between two vendor names using SequenceMatcher

        Returns:
            float: Similarity score between 0 and 1
        """
        norm1 = self.normalize_vendor_name(name1)
        norm2 = self.normalize_vendor_name(name2)

        if not norm1 or not norm2:
            return 0.0

        # Use SequenceMatcher for fuzzy string matching
        similarity = SequenceMatcher(None, norm1, norm2).ratio()

        return similarity

    def parse_date(self, date_str: str) -> Optional[datetime]:
        """
        Parse date string to datetime object
        Supports multiple Indonesian date formats
        """
        if not date_str:
            return None

        # Remove extra spaces
        date_str = date_str.strip()

        # Try multiple date formats
        formats = [
            '%d/%m/%Y',      # 31/12/2021
            '%d-%m-%Y',      # 31-12-2021
            '%Y-%m-%d',      # 2021-12-31
            '%d %m %Y',      # 31 12 2021
            '%d/%m/%y',      # 31/12/21
            '%d-%m-%y',      # 31-12-21
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        # If all formats fail, log warning and return None
        logger.warning(f"⚠️ Could not parse date: {date_str}")
        return None

    def is_date_match(self, date1: str, date2: str) -> Tuple[bool, float]:
        """
        Check if two dates match within tolerance

        Returns:
            Tuple[bool, float]: (is_match, confidence_score)
        """
        dt1 = self.parse_date(date1)
        dt2 = self.parse_date(date2)

        if not dt1 or not dt2:
            return False, 0.0

        # Calculate day difference
        day_diff = abs((dt1 - dt2).days)

        # Exact match gets 1.0
        if day_diff == 0:
            return True, 1.0

        # Within tolerance gets scaled score
        if day_diff <= self.date_tolerance_days:
            # Linear decay: 1.0 at day 0, decreasing to 0.5 at max tolerance
            confidence = 1.0 - (day_diff / (self.date_tolerance_days * 2))
            confidence = max(confidence, 0.5)  # Minimum 0.5 for matches within tolerance
            return True, confidence

        return False, 0.0

    def is_amount_match(self, amount1: Decimal, amount2: Decimal) -> Tuple[bool, float]:
        """
        Check if two amounts match within tolerance

        Returns:
            Tuple[bool, float]: (is_match, confidence_score)
        """
        if not amount1 or not amount2:
            return False, 0.0

        # Convert to Decimal if needed
        amt1 = Decimal(str(amount1))
        amt2 = Decimal(str(amount2))

        # Exact match gets 1.0
        if amt1 == amt2:
            return True, 1.0

        # Calculate percentage difference
        avg_amount = (amt1 + amt2) / 2
        diff = abs(amt1 - amt2)
        pct_diff = float(diff / avg_amount) if avg_amount > 0 else 1.0

        # Within tolerance gets scaled score
        if pct_diff <= self.amount_tolerance_percent:
            # Linear decay: 1.0 at 0%, decreasing to 0.7 at max tolerance
            confidence = 1.0 - (pct_diff / self.amount_tolerance_percent * 0.3)
            confidence = max(confidence, 0.7)
            return True, confidence

        return False, 0.0

    def calculate_match_confidence(
        self,
        date_match: bool,
        date_confidence: float,
        amount_match: bool,
        amount_confidence: float,
        vendor_similarity: float
    ) -> Tuple[float, str]:
        """
        Calculate overall match confidence score

        Weighting:
        - Date: 30%
        - Amount: 50%
        - Vendor: 20%

        Returns:
            Tuple[float, str]: (confidence_score, match_type)
        """
        # If date or amount don't match at all, return 0
        if not date_match or not amount_match:
            return 0.0, 'no_match'

        # Calculate weighted confidence
        confidence = (
            date_confidence * 0.30 +
            amount_confidence * 0.50 +
            vendor_similarity * 0.20
        )

        # Determine match type
        if confidence >= 0.95:
            match_type = 'exact'
        elif confidence >= 0.85:
            match_type = 'high'
        elif confidence >= self.min_confidence_score:
            match_type = 'partial'
        else:
            match_type = 'low'

        return confidence, match_type

    def find_matches(
        self,
        faktur_data: List[MatchCandidate],
        rekening_data: List[MatchCandidate],
        pph_data: Optional[List[MatchCandidate]] = None
    ) -> MatchResult:
        """
        Find matches between Faktur Pajak, Rekening Koran, and PPh data

        Args:
            faktur_data: List of Faktur Pajak candidates
            rekening_data: List of Rekening Koran candidates
            pph_data: Optional list of PPh candidates

        Returns:
            MatchResult: Matching results with confidence scores
        """
        logger.info("🔍 Starting matching process...")
        logger.info(f"   Faktur Pajak records: {len(faktur_data)}")
        logger.info(f"   Rekening Koran records: {len(rekening_data)}")
        logger.info(f"   PPh records: {len(pph_data) if pph_data else 0}")

        matched_items = []
        unmatched_faktur = list(faktur_data)
        unmatched_rekening = list(rekening_data)
        unmatched_pph = list(pph_data) if pph_data else []

        # Match Faktur Pajak with Rekening Koran
        for faktur in faktur_data:
            best_match = None
            best_confidence = 0.0
            best_rekening_idx = -1

            for rek_idx, rekening in enumerate(unmatched_rekening):
                # Check date match
                date_match, date_conf = self.is_date_match(faktur.date, rekening.date)

                # Check amount match (compare faktur total with rekening debit/kredit)
                amount_match, amount_conf = self.is_amount_match(
                    faktur.amount,
                    rekening.amount
                )

                # Check vendor similarity
                vendor_sim = self.calculate_vendor_similarity(
                    faktur.vendor_name,
                    rekening.vendor_name
                )

                # Calculate overall confidence
                confidence, match_type = self.calculate_match_confidence(
                    date_match, date_conf,
                    amount_match, amount_conf,
                    vendor_sim
                )

                # Keep track of best match
                if confidence >= self.min_confidence_score and confidence > best_confidence:
                    best_confidence = confidence
                    best_match = {
                        'faktur': faktur,
                        'rekening': rekening,
                        'confidence': confidence,
                        'match_type': match_type,
                        'date_confidence': date_conf,
                        'amount_confidence': amount_conf,
                        'vendor_similarity': vendor_sim
                    }
                    best_rekening_idx = rek_idx

            # If match found, add to matched items and remove from unmatched
            if best_match:
                matched_items.append(best_match)
                if best_rekening_idx >= 0:
                    unmatched_rekening.pop(best_rekening_idx)
                if faktur in unmatched_faktur:
                    unmatched_faktur.remove(faktur)

        # Convert to serializable format
        matched_serialized = []
        for match in matched_items:
            matched_serialized.append({
                'faktur': self._candidate_to_dict(match['faktur']),
                'rekening': self._candidate_to_dict(match['rekening']),
                'confidence': float(match['confidence']),
                'match_type': match['match_type'],
                'date_confidence': float(match['date_confidence']),
                'amount_confidence': float(match['amount_confidence']),
                'vendor_similarity': float(match['vendor_similarity'])
            })

        unmatched_serialized = [
            self._candidate_to_dict(c) for c in unmatched_faktur + unmatched_rekening + unmatched_pph
        ]

        # Generate match ID
        match_id = f"match_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Calculate average confidence
        avg_confidence = sum(m['confidence'] for m in matched_serialized) / len(matched_serialized) if matched_serialized else 0.0

        logger.info(f"✅ Matching complete!")
        logger.info(f"   Matched: {len(matched_serialized)} pairs")
        logger.info(f"   Unmatched: {len(unmatched_serialized)} items")
        logger.info(f"   Average confidence: {avg_confidence:.2%}")

        return MatchResult(
            match_id=match_id,
            confidence_score=avg_confidence,
            match_type='batch',
            matched_items=matched_serialized,
            unmatched_items=unmatched_serialized,
            details={
                'total_faktur': len(faktur_data),
                'total_rekening': len(rekening_data),
                'total_pph': len(pph_data) if pph_data else 0,
                'matched_count': len(matched_serialized),
                'unmatched_faktur': len([c for c in unmatched_serialized if c['source_type'] == 'faktur_pajak']),
                'unmatched_rekening': len([c for c in unmatched_serialized if c['source_type'] == 'rekening_koran']),
                'unmatched_pph': len([c for c in unmatched_serialized if c['source_type'] in ['pph21', 'pph23']]),
                'match_rate': len(matched_serialized) / len(faktur_data) if faktur_data else 0.0
            }
        )

    def _candidate_to_dict(self, candidate: MatchCandidate) -> Dict[str, Any]:
        """Convert MatchCandidate to serializable dictionary"""
        return {
            'source_type': candidate.source_type,
            'source_file': candidate.source_file,
            'source_row': candidate.source_row,
            'date': candidate.date,
            'amount': float(candidate.amount),
            'vendor_name': candidate.vendor_name,
            'reference': candidate.reference,
            'raw_data': candidate.raw_data
        }

    def generate_summary(self, match_result: MatchResult) -> ReconciliationSummary:
        """
        Generate reconciliation summary from match results

        Args:
            match_result: MatchResult from find_matches

        Returns:
            ReconciliationSummary: Summary statistics
        """
        details = match_result.details

        # Calculate total matched amount
        total_matched = sum(
            Decimal(str(m['faktur']['amount']))
            for m in match_result.matched_items
        )

        # Calculate total unmatched amount
        total_unmatched = sum(
            Decimal(str(item['amount']))
            for item in match_result.unmatched_items
        )

        return ReconciliationSummary(
            total_faktur=details['total_faktur'],
            total_rekening=details['total_rekening'],
            total_pph=details['total_pph'],
            matched_count=details['matched_count'],
            unmatched_faktur=details['unmatched_faktur'],
            unmatched_rekening=details['unmatched_rekening'],
            unmatched_pph=details['unmatched_pph'],
            belum_dilaporkan=details['unmatched_rekening'],  # Rekening items without matching faktur
            match_rate=details['match_rate'],
            total_matched_amount=total_matched,
            total_unmatched_amount=total_unmatched
        )
