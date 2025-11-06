"""
PPN Reconciliation Service
Handles auto-splitting of Faktur Pajak and reconciliation logic
"""

import pandas as pd
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@dataclass
class FakturPajakData:
    """Faktur Pajak data structure"""
    nomor_faktur: str
    tanggal_faktur: datetime
    npwp_seller: str
    nama_seller: str
    npwp_buyer: str
    nama_buyer: str
    dpp: float
    ppn: float
    total: float
    raw_data: Dict[str, Any]


@dataclass
class BuktiPotongData:
    """Bukti Potong data structure"""
    nomor_bukti_potong: str
    tanggal_bukti_potong: datetime
    npwp_pemotong: str
    nama_pemotong: str
    npwp_dipotong: str
    nama_dipotong: str
    jumlah_penghasilan_bruto: float
    tarif_pph: float
    pph_dipotong: float
    raw_data: Dict[str, Any]


@dataclass
class RekeningKoranData:
    """Rekening Koran data structure"""
    tanggal_transaksi: datetime
    keterangan: str
    nominal: float
    jenis_transaksi: str  # 'debit' or 'credit'
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None


@dataclass
class MatchResult:
    """Match result structure"""
    point_a_id: Optional[str]
    point_b_id: Optional[str]
    point_c_id: Optional[str]
    point_e_id: Optional[str]
    match_type: str  # 'exact', 'fuzzy', 'partial'
    match_confidence: float
    details: Dict[str, Any]


class PPNReconciliationService:
    """Service for PPN reconciliation processing"""

    def __init__(
        self,
        date_tolerance_days: int = 7,
        amount_tolerance_percent: float = 2.0,
        min_confidence_score: float = 0.70
    ):
        """
        Initialize PPN Reconciliation Service

        Args:
            date_tolerance_days: Maximum days difference for date matching
            amount_tolerance_percent: Maximum percentage difference for amount matching
            min_confidence_score: Minimum confidence score for a match to be considered valid
        """
        self.date_tolerance_days = date_tolerance_days
        self.amount_tolerance_percent = amount_tolerance_percent
        self.min_confidence_score = min_confidence_score

    def normalize_npwp(self, npwp: str) -> str:
        """
        Normalize NPWP by removing dots and dashes

        Args:
            npwp: NPWP string with possible dots and dashes

        Returns:
            Normalized NPWP (15 digits)
        """
        if not npwp:
            return ""
        return npwp.replace(".", "").replace("-", "").strip()

    def split_faktur_pajak(
        self,
        faktur_data: List[FakturPajakData],
        company_npwp: str
    ) -> Tuple[List[FakturPajakData], List[FakturPajakData]]:
        """
        Split Faktur Pajak into Point A (Keluaran) and Point B (Masukan)
        based on company NPWP

        Args:
            faktur_data: List of Faktur Pajak data
            company_npwp: Company NPWP for matching

        Returns:
            Tuple of (point_a_data, point_b_data)
        """
        company_npwp_clean = self.normalize_npwp(company_npwp)
        point_a_data = []  # Faktur Keluaran (company is seller)
        point_b_data = []  # Faktur Masukan (company is buyer)

        logger.info(f"Splitting Faktur Pajak for company NPWP: {company_npwp_clean}")

        for faktur in faktur_data:
            seller_npwp_clean = self.normalize_npwp(faktur.npwp_seller)
            buyer_npwp_clean = self.normalize_npwp(faktur.npwp_buyer)

            if seller_npwp_clean == company_npwp_clean:
                # Company is the seller → Point A (Faktur Keluaran)
                point_a_data.append(faktur)
            elif buyer_npwp_clean == company_npwp_clean:
                # Company is the buyer → Point B (Faktur Masukan)
                point_b_data.append(faktur)
            else:
                # Neither matches - log warning
                logger.warning(
                    f"Faktur {faktur.nomor_faktur} does not match company NPWP. "
                    f"Seller: {seller_npwp_clean}, Buyer: {buyer_npwp_clean}, Company: {company_npwp_clean}"
                )

        logger.info(f"Split result: Point A = {len(point_a_data)}, Point B = {len(point_b_data)}")
        return point_a_data, point_b_data

    def match_dates(self, date1: datetime, date2: datetime) -> Tuple[bool, float]:
        """
        Check if two dates match within tolerance

        Args:
            date1: First date
            date2: Second date

        Returns:
            Tuple of (is_match, confidence_score)
        """
        if not date1 or not date2:
            return False, 0.0

        diff_days = abs((date1 - date2).days)

        if diff_days == 0:
            return True, 1.0
        elif diff_days <= self.date_tolerance_days:
            # Linear decay from 1.0 to 0.7 based on days difference
            confidence = 1.0 - (diff_days / self.date_tolerance_days) * 0.3
            return True, confidence
        else:
            return False, 0.0

    def match_amounts(self, amount1: float, amount2: float) -> Tuple[bool, float]:
        """
        Check if two amounts match within tolerance

        Args:
            amount1: First amount
            amount2: Second amount

        Returns:
            Tuple of (is_match, confidence_score)
        """
        if amount1 == 0 or amount2 == 0:
            return False, 0.0

        # Calculate percentage difference
        diff_percent = abs((amount1 - amount2) / max(amount1, amount2)) * 100

        if diff_percent == 0:
            return True, 1.0
        elif diff_percent <= self.amount_tolerance_percent:
            # Linear decay from 1.0 to 0.7 based on percentage difference
            confidence = 1.0 - (diff_percent / self.amount_tolerance_percent) * 0.3
            return True, confidence
        else:
            return False, 0.0

    def reconcile_point_a_vs_c(
        self,
        point_a_data: List[FakturPajakData],
        point_c_data: List[BuktiPotongData]
    ) -> List[MatchResult]:
        """
        Reconcile Point A (Faktur Keluaran) vs Point C (Bukti Potong)

        Logic:
        - Match by NPWP: Point A buyer NPWP should match Point C pemotong NPWP
        - Match by date (within tolerance)
        - Match by amount (DPP should match jumlah_penghasilan_bruto)

        Args:
            point_a_data: List of Point A (Faktur Keluaran)
            point_c_data: List of Point C (Bukti Potong)

        Returns:
            List of match results
        """
        matches = []
        logger.info(f"Reconciling Point A ({len(point_a_data)}) vs Point C ({len(point_c_data)})")

        for faktur in point_a_data:
            faktur_npwp_buyer = self.normalize_npwp(faktur.npwp_buyer)

            for bukti in point_c_data:
                bukti_npwp_pemotong = self.normalize_npwp(bukti.npwp_pemotong)

                # Step 1: NPWP must match
                if faktur_npwp_buyer != bukti_npwp_pemotong:
                    continue

                # Step 2: Date matching
                date_match, date_confidence = self.match_dates(
                    faktur.tanggal_faktur,
                    bukti.tanggal_bukti_potong
                )

                # Step 3: Amount matching (compare DPP with jumlah_penghasilan_bruto)
                amount_match, amount_confidence = self.match_amounts(
                    faktur.dpp,
                    bukti.jumlah_penghasilan_bruto
                )

                # Calculate overall confidence
                if date_match and amount_match:
                    overall_confidence = (date_confidence + amount_confidence) / 2

                    if overall_confidence >= self.min_confidence_score:
                        match_type = "exact" if overall_confidence >= 0.95 else "fuzzy"

                        matches.append(MatchResult(
                            point_a_id=faktur.nomor_faktur,
                            point_b_id=None,
                            point_c_id=bukti.nomor_bukti_potong,
                            point_e_id=None,
                            match_type=match_type,
                            match_confidence=overall_confidence,
                            details={
                                "npwp_matched": faktur_npwp_buyer,
                                "date_confidence": date_confidence,
                                "amount_confidence": amount_confidence,
                                "faktur_date": faktur.tanggal_faktur.isoformat(),
                                "bukti_date": bukti.tanggal_bukti_potong.isoformat(),
                                "faktur_dpp": faktur.dpp,
                                "bukti_amount": bukti.jumlah_penghasilan_bruto
                            }
                        ))

        logger.info(f"Found {len(matches)} matches for Point A vs C")
        return matches

    def reconcile_point_b_vs_e(
        self,
        point_b_data: List[FakturPajakData],
        point_e_data: List[RekeningKoranData]
    ) -> List[MatchResult]:
        """
        Reconcile Point B (Faktur Masukan) vs Point E (Rekening Koran)

        Logic:
        - Match by date (within tolerance)
        - Match by amount (Faktur total should match Rekening Koran debit)
        - Optionally match by vendor name in keterangan

        Args:
            point_b_data: List of Point B (Faktur Masukan)
            point_e_data: List of Point E (Rekening Koran)

        Returns:
            List of match results
        """
        matches = []
        logger.info(f"Reconciling Point B ({len(point_b_data)}) vs Point E ({len(point_e_data)})")

        # Filter only debit transactions (payments out)
        point_e_debits = [t for t in point_e_data if t.jenis_transaksi == 'debit']

        for faktur in point_b_data:
            for transaksi in point_e_debits:
                # Step 1: Date matching
                date_match, date_confidence = self.match_dates(
                    faktur.tanggal_faktur,
                    transaksi.tanggal_transaksi
                )

                if not date_match:
                    continue

                # Step 2: Amount matching (compare Faktur total with transaction nominal)
                amount_match, amount_confidence = self.match_amounts(
                    faktur.total,
                    transaksi.nominal
                )

                if not amount_match:
                    continue

                # Calculate overall confidence
                overall_confidence = (date_confidence + amount_confidence) / 2

                if overall_confidence >= self.min_confidence_score:
                    match_type = "exact" if overall_confidence >= 0.95 else "fuzzy"

                    matches.append(MatchResult(
                        point_a_id=None,
                        point_b_id=faktur.nomor_faktur,
                        point_c_id=None,
                        point_e_id=str(transaksi.tanggal_transaksi),  # Use date as ID for now
                        match_type=match_type,
                        match_confidence=overall_confidence,
                        details={
                            "date_confidence": date_confidence,
                            "amount_confidence": amount_confidence,
                            "faktur_date": faktur.tanggal_faktur.isoformat(),
                            "transaksi_date": transaksi.tanggal_transaksi.isoformat(),
                            "faktur_total": faktur.total,
                            "transaksi_nominal": transaksi.nominal,
                            "keterangan": transaksi.keterangan
                        }
                    ))

        logger.info(f"Found {len(matches)} matches for Point B vs E")
        return matches

    def run_full_reconciliation(
        self,
        faktur_pajak_data: List[FakturPajakData],
        bukti_potong_data: List[BuktiPotongData],
        rekening_koran_data: List[RekeningKoranData],
        company_npwp: str
    ) -> Dict[str, Any]:
        """
        Run full PPN reconciliation workflow

        Steps:
        1. Auto-split Faktur Pajak into Point A and Point B
        2. Reconcile Point A vs Point C
        3. Reconcile Point B vs Point E
        4. Generate summary report

        Args:
            faktur_pajak_data: All Faktur Pajak data
            bukti_potong_data: Bukti Potong data
            rekening_koran_data: Rekening Koran data
            company_npwp: Company NPWP for auto-split

        Returns:
            Reconciliation results dictionary
        """
        logger.info("Starting full PPN reconciliation workflow")

        # Step 1: Auto-split Faktur Pajak
        point_a_data, point_b_data = self.split_faktur_pajak(faktur_pajak_data, company_npwp)

        # Step 2: Reconcile Point A vs Point C
        matches_a_c = self.reconcile_point_a_vs_c(point_a_data, bukti_potong_data)

        # Step 3: Reconcile Point B vs Point E
        matches_b_e = self.reconcile_point_b_vs_e(point_b_data, rekening_koran_data)

        # Step 4: Generate summary
        total_matches = len(matches_a_c) + len(matches_b_e)
        total_items = len(point_a_data) + len(point_b_data) + len(bukti_potong_data) + len(rekening_koran_data)

        summary = {
            "point_a_count": len(point_a_data),
            "point_b_count": len(point_b_data),
            "point_c_count": len(bukti_potong_data),
            "point_e_count": len(rekening_koran_data),
            "matches_a_vs_c": len(matches_a_c),
            "matches_b_vs_e": len(matches_b_e),
            "total_matches": total_matches,
            "match_rate": (total_matches / total_items * 100) if total_items > 0 else 0,
            "unmatched_point_a": len(point_a_data) - len(matches_a_c),
            "unmatched_point_b": len(point_b_data) - len(matches_b_e),
            "unmatched_point_c": len(bukti_potong_data) - len(matches_a_c),
            "unmatched_point_e": len(rekening_koran_data) - len(matches_b_e),
        }

        logger.info(f"Reconciliation complete: {summary}")

        return {
            "status": "completed",
            "point_a_data": point_a_data,
            "point_b_data": point_b_data,
            "matches_a_c": matches_a_c,
            "matches_b_e": matches_b_e,
            "summary": summary
        }


# Global service instance
ppn_reconciliation_service = PPNReconciliationService(
    date_tolerance_days=7,
    amount_tolerance_percent=2.0,
    min_confidence_score=0.70
)
