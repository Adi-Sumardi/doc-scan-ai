"""
PPN Reconciliation Service
Handles the matching logic between:
- Point A (Faktur Keluaran) vs Point C (Bukti Potong)
- Point B (Faktur Masukan) vs Point E (Rekening Koran)
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional
import logging

logger = logging.getLogger(__name__)


def load_excel_to_dataframe(file_path: str) -> pd.DataFrame:
    """Load Excel file to pandas DataFrame"""
    try:
        logger.info(f"Loading Excel file: {file_path}")
        df = pd.read_excel(file_path)
        logger.info(f"Loaded DataFrame with {len(df)} rows and {len(df.columns)} columns")
        logger.info(f"Column names: {list(df.columns)}")
        return df
    except Exception as e:
        logger.error(f"Failed to load Excel file {file_path}: {str(e)}")
        raise


def split_faktur_pajak(df: pd.DataFrame, company_npwp: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Split Faktur Pajak into Point A and Point B
    Point A: Company is seller (NPWP Penjual = company_npwp)
    Point B: Company is buyer (NPWP Pembeli = company_npwp)
    """
    logger.info(f"Starting split_faktur_pajak with company_npwp: {company_npwp}")
    logger.info(f"DataFrame has {len(df)} rows")

    # Normalize NPWP for comparison (remove dots and dashes)
    def normalize_npwp(npwp: str) -> str:
        if pd.isna(npwp):
            return ""
        return str(npwp).replace(".", "").replace("-", "").strip()

    company_npwp_normalized = normalize_npwp(company_npwp)
    logger.info(f"Normalized company NPWP: {company_npwp_normalized}")

    # Log first few NPWP values from the DataFrame
    if 'NPWP Penjual' in df.columns:
        logger.info(f"Sample NPWP Penjual values: {df['NPWP Penjual'].head(3).tolist()}")
    else:
        logger.error(f"Column 'NPWP Penjual' not found! Available columns: {list(df.columns)}")

    if 'NPWP Pembeli' in df.columns:
        logger.info(f"Sample NPWP Pembeli values: {df['NPWP Pembeli'].head(3).tolist()}")
    else:
        logger.error(f"Column 'NPWP Pembeli' not found! Available columns: {list(df.columns)}")

    # Split based on NPWP
    point_a = df[df['NPWP Penjual'].apply(normalize_npwp) == company_npwp_normalized].copy()
    point_b = df[df['NPWP Pembeli'].apply(normalize_npwp) == company_npwp_normalized].copy()

    logger.info(f"Split Faktur Pajak: Point A={len(point_a)}, Point B={len(point_b)}")

    return point_a, point_b


def match_point_a_vs_c(point_a: pd.DataFrame, point_c: pd.DataFrame) -> Dict[str, List]:
    """
    Match Point A (Faktur Keluaran) with Point C (Bukti Potong)
    Matching criteria: NPWP Pembeli (Point A) == NPWP Pemotong (Point C)
    """
    matches = []
    point_a_matched_idx = set()
    point_c_matched_idx = set()

    # Normalize NPWP function
    def normalize_npwp(npwp: str) -> str:
        if pd.isna(npwp):
            return ""
        return str(npwp).replace(".", "").replace("-", "").strip()

    # Create index for Point A by normalized NPWP Pembeli
    for a_idx, a_row in point_a.iterrows():
        npwp_pembeli = normalize_npwp(a_row.get('NPWP Pembeli', ''))

        if not npwp_pembeli:
            continue

        # Find matches in Point C
        for c_idx, c_row in point_c.iterrows():
            if c_idx in point_c_matched_idx:
                continue

            npwp_pemotong = normalize_npwp(c_row.get('NPWP Pemotong', ''))

            if npwp_pembeli == npwp_pemotong:
                # Match found!
                match = {
                    "id": f"match_a_c_{len(matches)+1}",
                    "point_a_id": str(a_idx),
                    "point_c_id": str(c_idx),
                    "match_type": "exact",
                    "match_confidence": 1.0,
                    "details": {
                        "nomor_faktur": str(a_row.get('Nomor Faktur', '')),
                        "tanggal": str(a_row.get('Tanggal Faktur', '')),
                        "vendor_name": str(a_row.get('Nama Pembeli', '')),
                        "amount": float(a_row.get('Total (Rp)', 0)),
                        "npwp": npwp_pembeli,
                        "dpp": float(a_row.get('DPP (Rp)', 0)),
                        "ppn": float(a_row.get('PPN (Rp)', 0)),
                        "nama_barang": str(a_row.get('Nama Barang/Jasa', a_row.get('Nama Barang', '-'))),
                        "quantity": str(a_row.get('Quantity', a_row.get('Jumlah', '-'))),
                        "keterangan": "Matched by NPWP"
                    }
                }
                matches.append(match)
                point_a_matched_idx.add(a_idx)
                point_c_matched_idx.add(c_idx)
                break  # One-to-one matching

    # Collect unmatched items - use actual Excel column names for frontend display
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

    logger.info(f"Point A vs C: {len(matches)} matches, {len(point_a_unmatched)} A unmatched, {len(point_c_unmatched)} C unmatched")

    return {
        "matches": matches,
        "point_a_unmatched": point_a_unmatched,
        "point_c_unmatched": point_c_unmatched
    }


def match_point_b_vs_e(point_b: pd.DataFrame, point_e: pd.DataFrame) -> Dict[str, List]:
    """
    Match Point B (Faktur Masukan) with Point E (Rekening Koran)
    Matching criteria:
    1. Date match (within 3 days tolerance)
    2. Amount match (Total from Point B == Debet from Point E, within 1% tolerance)
    """
    matches = []
    point_b_matched_idx = set()
    point_e_matched_idx = set()

    # Parse dates
    def parse_date(date_str):
        if pd.isna(date_str):
            return None
        try:
            # Try DD/MM/YYYY format
            return pd.to_datetime(str(date_str), format='%d/%m/%Y', errors='coerce')
        except:
            try:
                return pd.to_datetime(date_str, errors='coerce')
            except:
                return None

    # Match with tolerance
    for b_idx, b_row in point_b.iterrows():
        b_date = parse_date(b_row.get('Tanggal Faktur', ''))
        b_amount = float(b_row.get('Total (Rp)', 0))

        if b_date is None or b_amount == 0:
            continue

        # Find matches in Point E
        for e_idx, e_row in point_e.iterrows():
            if e_idx in point_e_matched_idx:
                continue

            e_date = parse_date(e_row.get('Tanggal', ''))
            e_debet = float(e_row.get('Debet (Rp)', 0))

            if e_date is None or e_debet == 0:
                continue

            # Check date match (within 3 days)
            date_diff = abs((b_date - e_date).days)
            if date_diff > 3:
                continue

            # Check amount match (within 1% tolerance)
            amount_diff_pct = abs(b_amount - e_debet) / b_amount * 100
            if amount_diff_pct > 1:
                continue

            # Match found!
            date_confidence = 1.0 - (date_diff / 3.0 * 0.3)  # Max 30% penalty for 3 days
            amount_confidence = 1.0 - (amount_diff_pct / 100.0)

            match = {
                "id": f"match_b_e_{len(matches)+1}",
                "point_b_id": str(b_idx),
                "point_e_id": str(e_idx),
                "match_type": "fuzzy" if date_diff > 0 or amount_diff_pct > 0 else "exact",
                "match_confidence": (date_confidence + amount_confidence) / 2,
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
                    "date_confidence": date_confidence,
                    "amount_confidence": amount_confidence,
                    "keterangan": str(e_row.get('Keterangan', ''))
                }
            }
            matches.append(match)
            point_b_matched_idx.add(b_idx)
            point_e_matched_idx.add(e_idx)
            break  # One-to-one matching

    # Collect unmatched items - use actual Excel column names for frontend display
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

    logger.info(f"Point B vs E: {len(matches)} matches, {len(point_b_unmatched)} B unmatched, {len(point_e_unmatched)} E unmatched")

    return {
        "matches": matches,
        "point_b_unmatched": point_b_unmatched,
        "point_e_unmatched": point_e_unmatched
    }


def run_ppn_reconciliation(
    faktur_pajak_path: str,
    bukti_potong_path: Optional[str],
    rekening_koran_path: Optional[str],
    company_npwp: str
) -> Dict[str, Any]:
    """
    Main reconciliation function

    Args:
        faktur_pajak_path: Path to Faktur Pajak Excel file (required)
        bukti_potong_path: Path to Bukti Potong Excel file (optional)
        rekening_koran_path: Path to Rekening Koran Excel file (optional)
        company_npwp: Company NPWP for splitting Point A/B

    Returns:
        Dictionary with reconciliation results
    """
    logger.info("=" * 80)
    logger.info("Starting PPN reconciliation...")
    logger.info(f"Faktur Pajak path: {faktur_pajak_path}")
    logger.info(f"Bukti Potong path: {bukti_potong_path}")
    logger.info(f"Rekening Koran path: {rekening_koran_path}")
    logger.info(f"Company NPWP: {company_npwp}")
    logger.info("=" * 80)

    # Load Faktur Pajak (required)
    df_faktur = load_excel_to_dataframe(faktur_pajak_path)

    # Split Faktur Pajak
    point_a, point_b = split_faktur_pajak(df_faktur, company_npwp)

    # Initialize counts
    point_c_count = 0
    point_e_count = 0

    # Match Point A vs C (only if Bukti Potong provided)
    if bukti_potong_path:
        df_bukti_potong = load_excel_to_dataframe(bukti_potong_path)
        point_c_count = len(df_bukti_potong)
        result_a_vs_c = match_point_a_vs_c(point_a, df_bukti_potong)
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

    # Match Point B vs E (only if Rekening Koran provided)
    if rekening_koran_path:
        df_rekening_koran = load_excel_to_dataframe(rekening_koran_path)
        point_e_count = len(df_rekening_koran)
        result_b_vs_e = match_point_b_vs_e(point_b, df_rekening_koran)
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
            "match_rate": match_rate
        }
    }

    logger.info(f"Reconciliation completed: {total_matched} matched, {total_unmatched} unmatched, {match_rate:.1f}% match rate")

    return result
