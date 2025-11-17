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

# Required column definitions
REQUIRED_COLUMNS_FAKTUR_PAJAK = [
    'Nomor Faktur',
    'Tanggal Faktur',
    'NPWP Penjual',
    'Nama Penjual',
    'NPWP Pembeli',
    'Nama Pembeli',
    'DPP (Rp)',
    'PPN (Rp)',
    'Total (Rp)'
]

REQUIRED_COLUMNS_BUKTI_POTONG = [
    'Nomor Bukti Potong',
    'Tanggal Bukti Potong',
    'NPWP Pemotong',
    'Nama Pemotong',
    'Jumlah Penghasilan Bruto (Rp)',
    'PPh Dipotong (Rp)'
]

REQUIRED_COLUMNS_REKENING_KORAN = [
    'Tanggal',
    'Keterangan',
    'Debet (Rp)',
    'Kredit (Rp)'
]


def validate_excel_columns(df: pd.DataFrame, required_columns: List[str], file_type: str) -> None:
    """
    Validate that Excel has all required columns

    Args:
        df: DataFrame to validate
        required_columns: List of required column names
        file_type: Type of file for error message (e.g., 'Faktur Pajak', 'Bukti Potong')

    Raises:
        ValueError: If required columns are missing
    """
    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        error_msg = (
            f"❌ {file_type} Excel file is missing required columns:\n"
            f"Missing: {', '.join(missing_columns)}\n\n"
            f"Available columns: {', '.join(df.columns)}\n\n"
            f"Please use the correct template with all required columns."
        )
        logger.error(error_msg)
        raise ValueError(error_msg)

    logger.info(f"✅ {file_type} Excel columns validated successfully")


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


def detect_and_remove_duplicates(df: pd.DataFrame, key_column: str, file_type: str) -> pd.DataFrame:
    """
    Detect and remove duplicate rows based on key column (e.g., Nomor Faktur)

    Args:
        df: DataFrame to check
        key_column: Column name to use for duplicate detection
        file_type: Type of file for logging (e.g., 'Faktur Pajak')

    Returns:
        DataFrame with duplicates removed
    """
    original_count = len(df)

    # Find duplicates
    duplicates = df[df.duplicated(subset=[key_column], keep='first')]

    if len(duplicates) > 0:
        duplicate_values = duplicates[key_column].tolist()
        logger.warning(
            f"⚠️ Found {len(duplicates)} duplicate {file_type} records:\n"
            f"Duplicate values: {', '.join(map(str, duplicate_values[:10]))}"
            f"{' ...' if len(duplicate_values) > 10 else ''}"
        )

        # Remove duplicates, keep first occurrence
        df_clean = df.drop_duplicates(subset=[key_column], keep='first')
        logger.info(f"✅ Removed {original_count - len(df_clean)} duplicates, {len(df_clean)} records remaining")
        return df_clean
    else:
        logger.info(f"✅ No duplicates found in {file_type}")
        return df


def split_faktur_pajak(df: pd.DataFrame, company_npwp: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Split Faktur Pajak into Point A and Point B
    Point A: Company is seller (NPWP Penjual = company_npwp)
    Point B: Company is buyer (NPWP Pembeli = company_npwp)
    """
    logger.info(f"Starting split_faktur_pajak with company_npwp: {company_npwp}")
    logger.info(f"DataFrame has {len(df)} rows")

    # Remove duplicates before splitting
    df = detect_and_remove_duplicates(df, 'Nomor Faktur', 'Faktur Pajak')

    # Normalize NPWP for comparison (remove dots and dashes)
    def normalize_npwp(npwp: str) -> str:
        if pd.isna(npwp):
            return ""
        return str(npwp).replace(".", "").replace("-", "").strip()

    company_npwp_normalized = normalize_npwp(company_npwp)
    logger.info(f"Normalized company NPWP: {company_npwp_normalized}")

    # Log first few NPWP values from the DataFrame
    if 'NPWP Penjual' in df.columns:
        sample_penjual = df['NPWP Penjual'].head(3).tolist()
        logger.info(f"Sample NPWP Penjual values (raw): {sample_penjual}")
        logger.info(f"Sample NPWP Penjual values (normalized): {[normalize_npwp(x) for x in sample_penjual]}")
    else:
        logger.error(f"Column 'NPWP Penjual' not found! Available columns: {list(df.columns)}")

    if 'NPWP Pembeli' in df.columns:
        sample_pembeli = df['NPWP Pembeli'].head(3).tolist()
        logger.info(f"Sample NPWP Pembeli values (raw): {sample_pembeli}")
        logger.info(f"Sample NPWP Pembeli values (normalized): {[normalize_npwp(x) for x in sample_pembeli]}")
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

    Enhanced matching with graduated confidence scoring:
    - Date tolerance: up to 7 days (graduated penalty)
    - Amount tolerance: up to 5% (graduated penalty)
    - Auto-match: confidence >= 70%
    - Suggest: confidence 50-69%
    """
    matches = []
    suggested_matches = []
    point_b_matched_idx = set()
    point_e_matched_idx = set()

    # Parse dates with multiple format support
    def parse_date(date_str):
        if pd.isna(date_str):
            return None

        # Try multiple date formats
        formats = [
            '%d/%m/%Y',    # 01/12/2024
            '%Y-%m-%d',    # 2024-12-01
            '%d-%m-%Y',    # 01-12-2024
            '%d.%m.%Y',    # 01.12.2024
        ]

        for fmt in formats:
            try:
                return pd.to_datetime(str(date_str), format=fmt, errors='raise')
            except:
                continue

        # Fallback to pandas auto-parse
        try:
            return pd.to_datetime(date_str, errors='coerce')
        except:
            return None

    # Match with graduated tolerance
    for b_idx, b_row in point_b.iterrows():
        b_date = parse_date(b_row.get('Tanggal Faktur', ''))
        b_amount = float(b_row.get('Total (Rp)', 0))

        if b_date is None or b_amount == 0:
            continue

        # Track best match for this invoice
        best_match = None
        best_confidence = 0.0

        # Find matches in Point E
        for e_idx, e_row in point_e.iterrows():
            if e_idx in point_e_matched_idx:
                continue

            e_date = parse_date(e_row.get('Tanggal', ''))
            e_debet = float(e_row.get('Debet (Rp)', 0))

            if e_date is None or e_debet == 0:
                continue

            # Calculate date score (up to 7 days tolerance)
            date_diff = abs((b_date - e_date).days)
            if date_diff <= 7:
                date_score = max(0.0, 1.0 - (date_diff / 7.0))
            else:
                date_score = 0.0  # Beyond 7 days = no match

            # Calculate amount score (up to 5% tolerance)
            amount_diff_pct = abs(b_amount - e_debet) / b_amount * 100
            if amount_diff_pct <= 5:
                amount_score = max(0.0, 1.0 - (amount_diff_pct / 5.0))
            else:
                amount_score = 0.0  # Beyond 5% = no match

            # Overall confidence (weighted: 60% date, 40% amount)
            overall_confidence = (date_score * 0.6) + (amount_score * 0.4)

            # Track best match
            if overall_confidence >= 0.50 and overall_confidence > best_confidence:
                best_confidence = overall_confidence
                best_match = {
                    'e_idx': e_idx,
                    'e_row': e_row,
                    'date_diff': date_diff,
                    'amount_diff_pct': amount_diff_pct,
                    'date_score': date_score,
                    'amount_score': amount_score,
                    'overall_confidence': overall_confidence
                }

        # Process best match if found
        if best_match:
            e_idx = best_match['e_idx']
            e_row = best_match['e_row']

            match_type = 'auto' if best_confidence >= 0.70 else 'suggested'

            match = {
                "id": f"match_b_e_{len(matches) + len(suggested_matches) + 1}",
                "point_b_id": str(b_idx),
                "point_e_id": str(e_idx),
                "match_type": match_type,
                "match_confidence": round(best_confidence, 2),
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
                    "bank_amount": float(e_row.get('Debet (Rp)', 0)),
                    "date_diff_days": best_match['date_diff'],
                    "amount_diff_pct": round(best_match['amount_diff_pct'], 2),
                    "date_score": round(best_match['date_score'], 2),
                    "amount_score": round(best_match['amount_score'], 2),
                    "keterangan": str(e_row.get('Keterangan', ''))
                }
            }

            if match_type == 'auto':
                matches.append(match)
            else:
                suggested_matches.append(match)

            point_b_matched_idx.add(b_idx)
            point_e_matched_idx.add(e_idx)

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

    logger.info(
        f"Point B vs E: {len(matches)} auto-matches, {len(suggested_matches)} suggested, "
        f"{len(point_b_unmatched)} B unmatched, {len(point_e_unmatched)} E unmatched"
    )

    return {
        "matches": matches,
        "suggested_matches": suggested_matches,
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

    # Validate Faktur Pajak columns
    validate_excel_columns(df_faktur, REQUIRED_COLUMNS_FAKTUR_PAJAK, "Faktur Pajak")

    # Split Faktur Pajak
    point_a, point_b = split_faktur_pajak(df_faktur, company_npwp)

    # Initialize counts
    point_c_count = 0
    point_e_count = 0

    # Match Point A vs C (only if Bukti Potong provided)
    if bukti_potong_path:
        df_bukti_potong = load_excel_to_dataframe(bukti_potong_path)
        validate_excel_columns(df_bukti_potong, REQUIRED_COLUMNS_BUKTI_POTONG, "Bukti Potong")
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
        validate_excel_columns(df_rekening_koran, REQUIRED_COLUMNS_REKENING_KORAN, "Rekening Koran")
        point_e_count = len(df_rekening_koran)
        result_b_vs_e = match_point_b_vs_e(point_b, df_rekening_koran)
    else:
        logger.info("Rekening Koran not provided, skipping Point B vs E matching")
        result_b_vs_e = {
            "matches": [],
            "suggested_matches": [],
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

    # Calculate summary with enhanced statistics
    auto_matched = len(result_a_vs_c['matches']) + len(result_b_vs_e['matches'])
    suggested = len(result_b_vs_e.get('suggested_matches', []))
    total_unmatched = (len(result_a_vs_c['point_a_unmatched']) +
                       len(result_a_vs_c['point_c_unmatched']) +
                       len(result_b_vs_e['point_b_unmatched']) +
                       len(result_b_vs_e['point_e_unmatched']))

    total_items = auto_matched + suggested + total_unmatched
    match_rate = (auto_matched / total_items * 100) if total_items > 0 else 0

    # Calculate total amounts
    total_amount_matched = sum(
        m['details'].get('amount', 0) for m in result_a_vs_c['matches']
    ) + sum(
        m['details'].get('amount', 0) for m in result_b_vs_e['matches']
    )

    total_amount_unmatched = sum(
        item.get('Total', 0) for item in result_a_vs_c['point_a_unmatched']
    ) + sum(
        item.get('Total', 0) for item in result_b_vs_e['point_b_unmatched']
    )

    # Calculate average confidence
    all_auto_matches = result_a_vs_c['matches'] + result_b_vs_e['matches']
    avg_confidence = (
        sum(m.get('match_confidence', 0) for m in all_auto_matches) / len(all_auto_matches)
        if all_auto_matches else 0
    )

    # Calculate margin: Penjualan (Point A) - Pembelian (Point B)
    # Point A = Faktur Keluaran (company as seller = revenue/penjualan)
    # Point B = Faktur Masukan (company as buyer = cost/pembelian)

    # Total penjualan (Point A - all invoices where company is seller)
    total_penjualan = sum(
        float(row.get('Total (Rp)', 0)) for idx, row in point_a.iterrows()
    )
    total_penjualan_dpp = sum(
        float(row.get('DPP (Rp)', 0)) for idx, row in point_a.iterrows()
    )

    # Total pembelian (Point B - all invoices where company is buyer)
    total_pembelian = sum(
        float(row.get('Total (Rp)', 0)) for idx, row in point_b.iterrows()
    )
    total_pembelian_dpp = sum(
        float(row.get('DPP (Rp)', 0)) for idx, row in point_b.iterrows()
    )

    # Calculate margin (Gross Profit)
    # Margin = Penjualan - Pembelian (using DPP, excluding PPN for accurate margin)
    margin_idr = total_penjualan_dpp - total_pembelian_dpp

    # Margin percentage = (Margin / Penjualan) * 100
    margin_pct = (margin_idr / total_penjualan_dpp * 100) if total_penjualan_dpp > 0 else 0

    result = {
        "point_a_count": len(point_a),
        "point_b_count": len(point_b),
        "point_c_count": point_c_count,
        "point_e_count": point_e_count,
        "matches": {
            "point_a_vs_c": result_a_vs_c['matches'],
            "point_b_vs_e": result_b_vs_e['matches']
        },
        "suggested_matches": {
            "point_b_vs_e": result_b_vs_e.get('suggested_matches', [])
        },
        "mismatches": {
            "point_a_unmatched": result_a_vs_c['point_a_unmatched'],
            "point_c_unmatched": result_a_vs_c['point_c_unmatched'],
            "point_b_unmatched": result_b_vs_e['point_b_unmatched'],
            "point_e_unmatched": result_b_vs_e['point_e_unmatched']
        },
        "summary": {
            "total_auto_matched": auto_matched,
            "total_suggested": suggested,
            "total_unmatched": total_unmatched,
            "match_rate": round(match_rate, 2),
            "match_rate_a_vs_c": round(
                len(result_a_vs_c['matches']) / max(len(point_a), 1) * 100, 2
            ) if point_c_count > 0 else 0,
            "match_rate_b_vs_e": round(
                len(result_b_vs_e['matches']) / max(len(point_b), 1) * 100, 2
            ) if point_e_count > 0 else 0,
            "total_amount_matched": round(total_amount_matched, 2),
            "total_amount_unmatched": round(total_amount_unmatched, 2),
            "avg_confidence": round(avg_confidence, 2),
            # Margin analysis (Penjualan vs Pembelian)
            "total_penjualan": round(total_penjualan, 2),
            "total_penjualan_dpp": round(total_penjualan_dpp, 2),
            "total_pembelian": round(total_pembelian, 2),
            "total_pembelian_dpp": round(total_pembelian_dpp, 2),
            "margin_idr": round(margin_idr, 2),
            "margin_pct": round(margin_pct, 2)
        }
    }

    logger.info(
        f"Reconciliation completed: {auto_matched} auto-matched, {suggested} suggested, "
        f"{total_unmatched} unmatched, {match_rate:.1f}% match rate"
    )
    logger.info(
        f"💰 Margin Analysis: Penjualan Rp {total_penjualan_dpp:,.0f} - Pembelian Rp {total_pembelian_dpp:,.0f} "
        f"= Margin Rp {margin_idr:,.0f} ({margin_pct:.2f}%)"
    )

    return result
