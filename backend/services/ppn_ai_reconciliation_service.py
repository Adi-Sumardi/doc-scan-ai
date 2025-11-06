"""
PPN AI-Enhanced Reconciliation Service
Hybrid approach: GPT-4o primary + rule-based fallback
- Uses GPT-4o for intelligent matching with fuzzy logic
- Falls back to traditional rule-based matching if GPT-4o fails or quota exceeded
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional
import logging
import os
import json
from openai import OpenAI
from services.ppn_reconciliation_service import (
    load_excel_to_dataframe,
    split_faktur_pajak,
    match_point_a_vs_c as rule_based_match_a_c,
    match_point_b_vs_e as rule_based_match_b_e
)

logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class AIReconciliationService:
    """
    Hybrid AI + Rule-based reconciliation service
    """

    def __init__(self):
        self.use_ai = bool(os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o"
        self.max_retries = 2
        logger.info(f"🤖 AI Reconciliation Service initialized (AI enabled: {self.use_ai})")

    def match_point_a_vs_c_ai(
        self,
        point_a: pd.DataFrame,
        point_c: pd.DataFrame,
        use_fallback: bool = True
    ) -> Dict[str, List]:
        """
        Match Point A vs C using GPT-4o with fallback to rule-based

        Args:
            point_a: Faktur Keluaran dataframe
            point_c: Bukti Potong dataframe
            use_fallback: Whether to fallback to rule-based if AI fails

        Returns:
            Dictionary with matches and unmatched items
        """
        if not self.use_ai:
            logger.info("⚙️ AI disabled, using rule-based matching for Point A vs C")
            return rule_based_match_a_c(point_a, point_c)

        try:
            logger.info("🤖 Attempting AI-enhanced matching for Point A vs C with GPT-4o")
            return self._ai_match_a_vs_c(point_a, point_c)

        except Exception as e:
            error_msg = str(e).lower()

            # Check for quota/rate limit errors
            if "quota" in error_msg or "rate_limit" in error_msg or "insufficient" in error_msg:
                logger.warning(f"⚠️ GPT-4o quota exceeded or rate limited: {str(e)}")
            else:
                logger.error(f"❌ GPT-4o matching failed: {str(e)}")

            if use_fallback:
                logger.info("♻️ Falling back to rule-based matching for Point A vs C")
                return rule_based_match_a_c(point_a, point_c)
            else:
                raise

    def match_point_b_vs_e_ai(
        self,
        point_b: pd.DataFrame,
        point_e: pd.DataFrame,
        use_fallback: bool = True
    ) -> Dict[str, List]:
        """
        Match Point B vs E using GPT-4o with fallback to rule-based

        Args:
            point_b: Faktur Masukan dataframe
            point_e: Rekening Koran dataframe
            use_fallback: Whether to fallback to rule-based if AI fails

        Returns:
            Dictionary with matches and unmatched items
        """
        if not self.use_ai:
            logger.info("⚙️ AI disabled, using rule-based matching for Point B vs E")
            return rule_based_match_b_e(point_b, point_e)

        try:
            logger.info("🤖 Attempting AI-enhanced matching for Point B vs E with GPT-4o")
            return self._ai_match_b_vs_e(point_b, point_e)

        except Exception as e:
            error_msg = str(e).lower()

            # Check for quota/rate limit errors
            if "quota" in error_msg or "rate_limit" in error_msg or "insufficient" in error_msg:
                logger.warning(f"⚠️ GPT-4o quota exceeded or rate limited: {str(e)}")
            else:
                logger.error(f"❌ GPT-4o matching failed: {str(e)}")

            if use_fallback:
                logger.info("♻️ Falling back to rule-based matching for Point B vs E")
                return rule_based_match_b_e(point_b, point_e)
            else:
                raise

    def _ai_match_a_vs_c(self, point_a: pd.DataFrame, point_c: pd.DataFrame) -> Dict[str, List]:
        """
        AI-enhanced matching for Point A vs C using GPT-4o
        """
        matches = []
        point_a_matched_idx = set()
        point_c_matched_idx = set()

        # Limit batch size for API efficiency
        batch_size = 20

        for batch_start in range(0, len(point_a), batch_size):
            batch_end = min(batch_start + batch_size, len(point_a))
            batch_a = point_a.iloc[batch_start:batch_end]

            # Prepare data for AI
            a_data = batch_a.to_dict('records')
            c_data = point_c.to_dict('records')

            prompt = self._build_matching_prompt_a_vs_c(a_data, c_data)

            try:
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert accountant specializing in Indonesian tax document reconciliation. Analyze and match Faktur Pajak Keluaran (Point A) with Bukti Potong (Point C) based on NPWP, vendor names, amounts, and dates. Return matches in JSON format."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                    max_tokens=4000
                )

                result = json.loads(response.choices[0].message.content)
                batch_matches = result.get('matches', [])

                # Process matches
                for match in batch_matches:
                    a_idx = match.get('point_a_index')
                    c_idx = match.get('point_c_index')
                    confidence = match.get('confidence', 1.0)

                    if a_idx is not None and c_idx is not None:
                        # Get actual dataframe rows
                        actual_a_idx = point_a.index[batch_start + a_idx]
                        actual_c_idx = point_c.index[c_idx]

                        if actual_c_idx not in point_c_matched_idx:
                            a_row = point_a.loc[actual_a_idx]

                            match_entry = {
                                "id": f"match_a_c_{len(matches)+1}",
                                "point_a_id": str(actual_a_idx),
                                "point_c_id": str(actual_c_idx),
                                "match_type": "ai_enhanced",
                                "match_confidence": confidence,
                                "details": {
                                    "nomor_faktur": str(a_row.get('Nomor Faktur', '')),
                                    "tanggal": str(a_row.get('Tanggal Faktur', '')),
                                    "vendor_name": str(a_row.get('Nama Pembeli', '')),
                                    "amount": float(a_row.get('Total (Rp)', 0)),
                                    "npwp": str(a_row.get('NPWP Pembeli', '')),
                                    "dpp": float(a_row.get('DPP (Rp)', 0)),
                                    "ppn": float(a_row.get('PPN (Rp)', 0)),
                                    "nama_barang": str(a_row.get('Nama Barang/Jasa', a_row.get('Nama Barang', '-'))),
                                    "quantity": str(a_row.get('Quantity', a_row.get('Jumlah', '-'))),
                                    "keterangan": f"AI Match ({confidence*100:.0f}% confidence)"
                                }
                            }

                            matches.append(match_entry)
                            point_a_matched_idx.add(actual_a_idx)
                            point_c_matched_idx.add(actual_c_idx)

                logger.info(f"✅ AI matched {len(batch_matches)} items in batch {batch_start//batch_size + 1}")

            except Exception as e:
                logger.error(f"Error in AI matching batch: {str(e)}")
                # Continue with next batch or raise to trigger fallback
                if "quota" in str(e).lower() or "rate" in str(e).lower():
                    raise  # Trigger fallback

        # Collect unmatched items
        point_a_unmatched = []
        for a_idx, a_row in point_a.iterrows():
            if a_idx not in point_a_matched_idx:
                point_a_unmatched.append({
                    "Nomor Faktur": str(a_row.get('Nomor Faktur', '')),
                    "Tanggal Faktur": str(a_row.get('Tanggal Faktur', '')),
                    "Nama Pembeli": str(a_row.get('Nama Pembeli', '')),
                    "NPWP Pembeli": str(a_row.get('NPWP Pembeli', '')),
                    "Nama Barang": str(a_row.get('Nama Barang/Jasa', a_row.get('Nama Barang', '-'))),
                    "Quantity": str(a_row.get('Quantity', a_row.get('Jumlah', '-'))),
                    "DPP": float(a_row.get('DPP (Rp)', 0)),
                    "PPN": float(a_row.get('PPN (Rp)', 0)),
                    "Total": float(a_row.get('Total (Rp)', 0))
                })

        point_c_unmatched = []
        for c_idx, c_row in point_c.iterrows():
            if c_idx not in point_c_matched_idx:
                point_c_unmatched.append({
                    "Nomor Bukti Potong": str(c_row.get('Nomor Bukti Potong', '')),
                    "Tanggal": str(c_row.get('Tanggal Bukti Potong', '')),
                    "Nama Pemotong": str(c_row.get('Nama Pemotong', '')),
                    "NPWP Pemotong": str(c_row.get('NPWP Pemotong', '')),
                    "Jenis Penghasilan": str(c_row.get('Jenis Penghasilan', '')),
                    "Jumlah Bruto": float(c_row.get('Jumlah Penghasilan Bruto (Rp)', 0)),
                    "PPh Dipotong": float(c_row.get('PPh Dipotong (Rp)', 0))
                })

        logger.info(f"🎯 AI matching complete: {len(matches)} matches, {len(point_a_unmatched)} A unmatched, {len(point_c_unmatched)} C unmatched")

        return {
            "matches": matches,
            "point_a_unmatched": point_a_unmatched,
            "point_c_unmatched": point_c_unmatched
        }

    def _ai_match_b_vs_e(self, point_b: pd.DataFrame, point_e: pd.DataFrame) -> Dict[str, List]:
        """
        AI-enhanced matching for Point B vs E using GPT-4o
        """
        matches = []
        point_b_matched_idx = set()
        point_e_matched_idx = set()

        # Limit batch size
        batch_size = 15

        for batch_start in range(0, len(point_b), batch_size):
            batch_end = min(batch_start + batch_size, len(point_b))
            batch_b = point_b.iloc[batch_start:batch_end]

            # Prepare data for AI
            b_data = batch_b.to_dict('records')
            e_data = point_e.to_dict('records')

            prompt = self._build_matching_prompt_b_vs_e(b_data, e_data)

            try:
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert accountant specializing in payment reconciliation. Match Faktur Pajak Masukan (Point B) with Rekening Koran (Point E) based on amounts, dates (±3 days tolerance), and vendor information. Return matches in JSON format with confidence scores."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                    max_tokens=4000
                )

                result = json.loads(response.choices[0].message.content)
                batch_matches = result.get('matches', [])

                # Process matches
                for match in batch_matches:
                    b_idx = match.get('point_b_index')
                    e_idx = match.get('point_e_index')
                    confidence = match.get('confidence', 1.0)

                    if b_idx is not None and e_idx is not None:
                        actual_b_idx = point_b.index[batch_start + b_idx]
                        actual_e_idx = point_e.index[e_idx]

                        if actual_e_idx not in point_e_matched_idx:
                            b_row = point_b.loc[actual_b_idx]
                            e_row = point_e.loc[actual_e_idx]

                            b_amount = float(b_row.get('Total (Rp)', 0))
                            e_debet = float(e_row.get('Debet (Rp)', 0))

                            match_entry = {
                                "id": f"match_b_e_{len(matches)+1}",
                                "point_b_id": str(actual_b_idx),
                                "point_e_id": str(actual_e_idx),
                                "match_type": "ai_enhanced",
                                "match_confidence": confidence,
                                "details": {
                                    "nomor_faktur": str(b_row.get('Nomor Faktur', '')),
                                    "tanggal": str(b_row.get('Tanggal Faktur', '')),
                                    "vendor_name": str(b_row.get('Nama Penjual', '')),
                                    "npwp": str(b_row.get('NPWP Penjual', '')),
                                    "nama_barang": str(b_row.get('Nama Barang/Jasa', b_row.get('Nama Barang', '-'))),
                                    "quantity": str(b_row.get('Quantity', b_row.get('Jumlah', '-'))),
                                    "dpp": float(b_row.get('DPP (Rp)', 0)),
                                    "ppn": float(b_row.get('PPN (Rp)', 0)),
                                    "amount": b_amount,
                                    "bank_date": str(e_row.get('Tanggal', '')),
                                    "bank_amount": e_debet,
                                    "date_confidence": 1.0,
                                    "amount_confidence": 1.0,
                                    "keterangan": f"AI Match ({confidence*100:.0f}% confidence) - {str(e_row.get('Keterangan', ''))}"
                                }
                            }

                            matches.append(match_entry)
                            point_b_matched_idx.add(actual_b_idx)
                            point_e_matched_idx.add(actual_e_idx)

                logger.info(f"✅ AI matched {len(batch_matches)} items in batch {batch_start//batch_size + 1}")

            except Exception as e:
                logger.error(f"Error in AI matching batch: {str(e)}")
                if "quota" in str(e).lower() or "rate" in str(e).lower():
                    raise

        # Collect unmatched items
        point_b_unmatched = []
        for b_idx, b_row in point_b.iterrows():
            if b_idx not in point_b_matched_idx:
                point_b_unmatched.append({
                    "Nomor Faktur": str(b_row.get('Nomor Faktur', '')),
                    "Tanggal Faktur": str(b_row.get('Tanggal Faktur', '')),
                    "Nama Penjual": str(b_row.get('Nama Penjual', '')),
                    "NPWP Penjual": str(b_row.get('NPWP Penjual', '')),
                    "Nama Barang": str(b_row.get('Nama Barang/Jasa', b_row.get('Nama Barang', '-'))),
                    "Quantity": str(b_row.get('Quantity', b_row.get('Jumlah', '-'))),
                    "DPP": float(b_row.get('DPP (Rp)', 0)),
                    "PPN": float(b_row.get('PPN (Rp)', 0)),
                    "Total": float(b_row.get('Total (Rp)', 0))
                })

        point_e_unmatched = []
        for e_idx, e_row in point_e.iterrows():
            if e_idx not in point_e_matched_idx:
                point_e_unmatched.append({
                    "Tanggal": str(e_row.get('Tanggal', '')),
                    "Keterangan": str(e_row.get('Keterangan', '')),
                    "Cabang": str(e_row.get('Cabang', '')),
                    "Debet": float(e_row.get('Debet (Rp)', 0)),
                    "Kredit": float(e_row.get('Kredit (Rp)', 0)),
                    "Saldo": float(e_row.get('Saldo (Rp)', 0))
                })

        logger.info(f"🎯 AI matching complete: {len(matches)} matches, {len(point_b_unmatched)} B unmatched, {len(point_e_unmatched)} E unmatched")

        return {
            "matches": matches,
            "point_b_unmatched": point_b_unmatched,
            "point_e_unmatched": point_e_unmatched
        }

    def _build_matching_prompt_a_vs_c(self, a_data: List[Dict], c_data: List[Dict]) -> str:
        """Build prompt for Point A vs C matching"""
        return f"""
Match Faktur Pajak Keluaran (Point A) with Bukti Potong (Point C).

Point A data ({len(a_data)} items):
{json.dumps(a_data[:10], indent=2, default=str)}

Point C data ({len(c_data)} items):
{json.dumps(c_data[:20], indent=2, default=str)}

Matching criteria:
1. PRIMARY: NPWP Pembeli (Point A) should match NPWP Pemotong (Point C)
2. SECONDARY: Vendor name similarity
3. Consider date proximity if NPWP matches

Return JSON with format:
{{
  "matches": [
    {{
      "point_a_index": 0,
      "point_c_index": 5,
      "confidence": 0.95,
      "reason": "NPWP exact match + vendor name similarity"
    }}
  ]
}}

Only include high-confidence matches (>0.7). One-to-one matching only.
"""

    def _build_matching_prompt_b_vs_e(self, b_data: List[Dict], e_data: List[Dict]) -> str:
        """Build prompt for Point B vs E matching"""
        return f"""
Match Faktur Pajak Masukan (Point B) with Rekening Koran (Point E).

Point B data ({len(b_data)} items):
{json.dumps(b_data[:10], indent=2, default=str)}

Point E data ({len(e_data)} items):
{json.dumps(e_data[:20], indent=2, default=str)}

Matching criteria:
1. Amount matching: Total (Point B) ≈ Debet (Point E) within 1% tolerance
2. Date matching: Tanggal Faktur ± 3 days from Tanggal (bank)
3. Vendor name similarity in Keterangan

Return JSON with format:
{{
  "matches": [
    {{
      "point_b_index": 0,
      "point_e_index": 5,
      "confidence": 0.92,
      "reason": "Amount match within 0.5%, date within 1 day"
    }}
  ]
}}

Only include high-confidence matches (>0.7). One-to-one matching only.
"""


# Singleton instance
ai_reconciliation_service = AIReconciliationService()


def run_ppn_ai_reconciliation(
    faktur_pajak_path: str,
    bukti_potong_path: Optional[str],
    rekening_koran_path: Optional[str],
    company_npwp: str,
    use_ai: bool = True
) -> Dict[str, Any]:
    """
    Main AI-enhanced reconciliation function with fallback

    Args:
        faktur_pajak_path: Path to Faktur Pajak Excel file
        bukti_potong_path: Path to Bukti Potong Excel file (optional)
        rekening_koran_path: Path to Rekening Koran Excel file (optional)
        company_npwp: Company NPWP for splitting
        use_ai: Whether to use AI matching (True) or rule-based only (False)

    Returns:
        Dictionary with reconciliation results
    """
    logger.info("=" * 80)
    logger.info(f"🚀 Starting {'AI-Enhanced' if use_ai else 'Rule-Based'} PPN Reconciliation")
    logger.info(f"Faktur Pajak: {faktur_pajak_path}")
    logger.info(f"Bukti Potong: {bukti_potong_path}")
    logger.info(f"Rekening Koran: {rekening_koran_path}")
    logger.info(f"Company NPWP: {company_npwp}")
    logger.info("=" * 80)

    # Load and split Faktur Pajak
    df_faktur = load_excel_to_dataframe(faktur_pajak_path)
    point_a, point_b = split_faktur_pajak(df_faktur, company_npwp)

    point_c_count = 0
    point_e_count = 0

    # Match Point A vs C
    if bukti_potong_path:
        df_bukti_potong = load_excel_to_dataframe(bukti_potong_path)
        point_c_count = len(df_bukti_potong)

        if use_ai and ai_reconciliation_service.use_ai:
            result_a_vs_c = ai_reconciliation_service.match_point_a_vs_c_ai(
                point_a, df_bukti_potong, use_fallback=True
            )
        else:
            result_a_vs_c = rule_based_match_a_c(point_a, df_bukti_potong)
    else:
        logger.info("Bukti Potong not provided, skipping Point A vs C matching")
        result_a_vs_c = {
            "matches": [],
            "point_a_unmatched": [{
                "Nomor Faktur": str(row.get('Nomor Faktur', '')),
                "Tanggal Faktur": str(row.get('Tanggal Faktur', '')),
                "Nama Pembeli": str(row.get('Nama Pembeli', '')),
                "NPWP Pembeli": str(row.get('NPWP Pembeli', '')),
                "Nama Barang": str(row.get('Nama Barang/Jasa', row.get('Nama Barang', '-'))),
                "Quantity": str(row.get('Quantity', row.get('Jumlah', '-'))),
                "DPP": float(row.get('DPP (Rp)', 0)),
                "PPN": float(row.get('PPN (Rp)', 0)),
                "Total": float(row.get('Total (Rp)', 0))
            } for idx, row in point_a.iterrows()],
            "point_c_unmatched": []
        }

    # Match Point B vs E
    if rekening_koran_path:
        df_rekening_koran = load_excel_to_dataframe(rekening_koran_path)
        point_e_count = len(df_rekening_koran)

        if use_ai and ai_reconciliation_service.use_ai:
            result_b_vs_e = ai_reconciliation_service.match_point_b_vs_e_ai(
                point_b, df_rekening_koran, use_fallback=True
            )
        else:
            result_b_vs_e = rule_based_match_b_e(point_b, df_rekening_koran)
    else:
        logger.info("Rekening Koran not provided, skipping Point B vs E matching")
        result_b_vs_e = {
            "matches": [],
            "point_b_unmatched": [{
                "Nomor Faktur": str(row.get('Nomor Faktur', '')),
                "Tanggal Faktur": str(row.get('Tanggal Faktur', '')),
                "Nama Penjual": str(row.get('Nama Penjual', '')),
                "NPWP Penjual": str(row.get('NPWP Penjual', '')),
                "Nama Barang": str(row.get('Nama Barang/Jasa', row.get('Nama Barang', '-'))),
                "Quantity": str(row.get('Quantity', row.get('Jumlah', '-'))),
                "DPP": float(row.get('DPP (Rp)', 0)),
                "PPN": float(row.get('PPN (Rp)', 0)),
                "Total": float(row.get('Total (Rp)', 0))
            } for idx, row in point_b.iterrows()],
            "point_e_unmatched": []
        }

    # Calculate summary
    total_matched = len(result_a_vs_c['matches']) + len(result_b_vs_e['matches'])
    total_unmatched = (len(result_a_vs_c['point_a_unmatched']) +
                       len(result_a_vs_c['point_c_unmatched']) +
                       len(result_b_vs_e['point_b_unmatched']) +
                       len(result_b_vs_e['point_e_unmatched']))

    total_items = total_matched + total_unmatched
    match_rate = (total_matched / total_items * 100) if total_items > 0 else 0

    result = {
        "point_a_count": len(point_a),
        "point_b_count": len(point_b),
        "point_c_count": point_c_count,
        "point_e_count": point_e_count,
        "matches": {
            "point_a_vs_c": result_a_vs_c['matches'],
            "point_b_vs_e": result_b_vs_e['matches']
        },
        "mismatches": {
            "point_a_unmatched": result_a_vs_c['point_a_unmatched'],
            "point_c_unmatched": result_a_vs_c['point_c_unmatched'],
            "point_b_unmatched": result_b_vs_e['point_b_unmatched'],
            "point_e_unmatched": result_b_vs_e['point_e_unmatched']
        },
        "summary": {
            "total_matched": total_matched,
            "total_unmatched": total_unmatched,
            "match_rate": match_rate,
            "ai_used": use_ai and ai_reconciliation_service.use_ai
        }
    }

    logger.info(f"✅ Reconciliation completed: {total_matched} matched, {total_unmatched} unmatched, {match_rate:.1f}% match rate")
    logger.info(f"🤖 AI Usage: {'Enabled with fallback' if (use_ai and ai_reconciliation_service.use_ai) else 'Disabled'}")

    return result
