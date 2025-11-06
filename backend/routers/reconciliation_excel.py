"""
Excel-Based Reconciliation API Router
NEW approach: Link existing Excel exports instead of re-uploading PDFs
"""

from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from excel_reader_service import excel_reader_service
from matching_engine import MatchingEngine
import logging
from functools import lru_cache
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Initialize matching engine
matching_engine = MatchingEngine(
    date_tolerance_days=3,
    amount_tolerance_percent=1.0,
    vendor_similarity_threshold=0.80,
    min_confidence_score=0.70
)

router = APIRouter(
    prefix="/api/reconciliation-excel",
    tags=["reconciliation-excel"]
)

# Cache for Excel files list (expires every 60 seconds)
_excel_files_cache = {
    'data': None,
    'timestamp': None,
    'ttl': 60  # seconds
}

def get_cached_excel_files(document_type: Optional[str] = None):
    """Get cached Excel files list or fetch fresh data if cache expired"""
    cache_key = f"excel_files_{document_type or 'all'}"
    now = datetime.now()

    # Check if cache exists and is still valid
    if (_excel_files_cache.get('data') is not None and
        _excel_files_cache.get('timestamp') is not None):
        age = (now - _excel_files_cache['timestamp']).total_seconds()
        if age < _excel_files_cache['ttl']:
            logger.info(f"⚡ Using cached Excel files list (age: {age:.1f}s)")
            return _excel_files_cache['data']

    # Cache miss or expired - fetch fresh data
    logger.info("💾 Fetching fresh Excel files list")
    excel_files = excel_reader_service.list_available_exports(document_type)

    # Update cache
    _excel_files_cache['data'] = excel_files
    _excel_files_cache['timestamp'] = now

    return excel_files


# ==================== List Excel Exports ====================

@router.get("/files")
async def list_excel_files(
    document_type: Optional[str] = Query(
        None,
        description="Filter by document type: faktur_pajak, rekening_koran, pph21, pph23, batch"
    )
):
    """
    List all available Excel export files from OCR scans (CACHED for 60s)

    Returns:
        List of Excel files with metadata (filename, row_count, file_size, etc.)

    Example:
        GET /api/reconciliation-excel/excel-files?document_type=faktur_pajak
    """
    try:
        excel_files = get_cached_excel_files(document_type)

        return {
            "success": True,
            "count": len(excel_files),
            "document_type": document_type or "all",
            "files": [file.to_dict() for file in excel_files]
        }

    except Exception as e:
        logger.error(f"Error listing Excel files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/excel-files/{filename}/preview")
async def preview_excel_file(
    filename: str,
    max_rows: int = Query(10, description="Maximum number of rows to preview")
):
    """
    Preview Excel file content (first N rows)

    Args:
        filename: Excel filename
        max_rows: Maximum rows to return (default: 10)

    Returns:
        Preview data based on document type
    """
    try:
        # Detect document type from filename
        doc_type = excel_reader_service._detect_document_type(filename)

        preview_data = {
            "filename": filename,
            "document_type": doc_type,
            "preview": []
        }

        if doc_type == 'faktur_pajak' or doc_type == 'batch':
            # Parse Faktur Pajak
            fakturs = excel_reader_service.read_faktur_pajak(filename)
            preview_data["total_rows"] = len(fakturs)
            preview_data["preview"] = [f.to_dict() for f in fakturs[:max_rows]]

        elif doc_type == 'rekening_koran':
            # Parse Rekening Koran
            transactions = excel_reader_service.read_rekening_koran(filename)
            preview_data["total_rows"] = len(transactions)
            preview_data["preview"] = [t.to_dict() for t in transactions[:max_rows]]

        elif doc_type in ['pph21', 'pph23']:
            # Parse PPh
            pph_records = excel_reader_service.read_pph(filename, doc_type)
            preview_data["total_rows"] = len(pph_records)
            preview_data["preview"] = [p.to_dict() for p in pph_records[:max_rows]]

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported document type: {doc_type}"
            )

        return {
            "success": True,
            **preview_data
        }

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")
    except Exception as e:
        logger.error(f"Error previewing Excel file {filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/excel-files/{filename}/full-data")
async def get_full_excel_data(filename: str):
    """
    Get complete parsed data from Excel file

    Args:
        filename: Excel filename

    Returns:
        All parsed records from the Excel file
    """
    try:
        doc_type = excel_reader_service._detect_document_type(filename)

        result = {
            "filename": filename,
            "document_type": doc_type,
            "data": []
        }

        if doc_type == 'faktur_pajak' or doc_type == 'batch':
            fakturs = excel_reader_service.read_faktur_pajak(filename)
            result["total_count"] = len(fakturs)
            result["data"] = [f.to_dict() for f in fakturs]

        elif doc_type == 'rekening_koran':
            transactions = excel_reader_service.read_rekening_koran(filename)
            result["total_count"] = len(transactions)
            result["data"] = [t.to_dict() for t in transactions]

        elif doc_type in ['pph21', 'pph23']:
            pph_records = excel_reader_service.read_pph(filename, doc_type)
            result["total_count"] = len(pph_records)
            result["data"] = [p.to_dict() for p in pph_records]

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported document type: {doc_type}"
            )

        return {
            "success": True,
            **result
        }

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")
    except Exception as e:
        logger.error(f"Error reading Excel file {filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Statistics ====================

@router.get("/excel-files/stats/summary")
async def get_excel_stats():
    """
    Get summary statistics of all Excel exports

    Returns:
        Summary by document type
    """
    try:
        stats = {
            "faktur_pajak": [],
            "rekening_koran": [],
            "pph21": [],
            "pph23": [],
            "batch": []
        }

        # Get counts for each type
        for doc_type in stats.keys():
            files = excel_reader_service.list_available_exports(doc_type)
            stats[doc_type] = {
                "count": len(files),
                "total_rows": sum(f.row_count for f in files),
                "total_size_mb": sum(f.file_size for f in files) / (1024 * 1024)
            }

        return {
            "success": True,
            "statistics": stats,
            "total_files": sum(s["count"] for s in stats.values())
        }

    except Exception as e:
        logger.error(f"Error getting Excel stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Pydantic Models ====================

class MatchRequest(BaseModel):
    """Request model for matching operation"""
    faktur_file: str
    rekening_file: str
    pph_file: Optional[str] = None
    date_tolerance_days: Optional[int] = 3
    amount_tolerance_percent: Optional[float] = 1.0
    vendor_similarity_threshold: Optional[float] = 0.80
    min_confidence_score: Optional[float] = 0.70

    class Config:
        json_schema_extra = {
            "example": {
                "faktur_file": "103 FAKTUR PAJAK 103pdf_scan_result.xlsx",
                "rekening_file": "BNI IDR 01_31122021pdf_scan_result.xlsx",
                "pph_file": "Bukti Potong PPh 21pdf_scan_result.xlsx",
                "date_tolerance_days": 3,
                "amount_tolerance_percent": 1.0,
                "vendor_similarity_threshold": 0.80,
                "min_confidence_score": 0.70
            }
        }


# ==================== Matching Endpoints ====================

@router.post("/match")
async def match_documents(request: MatchRequest):
    """
    Match Faktur Pajak with Rekening Koran and optionally PPh documents

    This endpoint performs automatic reconciliation by matching:
    - Date (within tolerance)
    - Amount (within tolerance)
    - Vendor name (fuzzy matching)

    Args:
        request: MatchRequest containing file names and matching parameters

    Returns:
        Match results with confidence scores, matched items, and unmatched items
    """
    try:
        logger.info("🔍 Starting document matching...")
        logger.info(f"   Faktur file: {request.faktur_file}")
        logger.info(f"   Rekening file: {request.rekening_file}")
        logger.info(f"   PPh file: {request.pph_file}")

        # Parse Excel files
        logger.info("📖 Reading Faktur Pajak Excel...")
        faktur_data = excel_reader_service.read_faktur_pajak(request.faktur_file)

        logger.info("📖 Reading Rekening Koran Excel...")
        rekening_data = excel_reader_service.read_rekening_koran(request.rekening_file)

        pph_data = None
        if request.pph_file:
            logger.info("📖 Reading PPh Excel...")
            doc_type = excel_reader_service._detect_document_type(request.pph_file)
            pph_data = excel_reader_service.read_pph(request.pph_file, doc_type)

        # Convert to MatchCandidates
        logger.info("🔄 Converting data to MatchCandidates...")
        faktur_candidates = excel_reader_service.convert_faktur_to_candidates(
            faktur_data,
            request.faktur_file
        )

        rekening_candidates = excel_reader_service.convert_rekening_to_candidates(
            rekening_data,
            request.rekening_file
        )

        pph_candidates = None
        if pph_data:
            doc_type = excel_reader_service._detect_document_type(request.pph_file)
            pph_candidates = excel_reader_service.convert_pph_to_candidates(
                pph_data,
                request.pph_file,
                doc_type
            )

        # Create matching engine with custom parameters if provided
        if (request.date_tolerance_days or
            request.amount_tolerance_percent or
            request.vendor_similarity_threshold or
            request.min_confidence_score):

            custom_engine = MatchingEngine(
                date_tolerance_days=request.date_tolerance_days or 3,
                amount_tolerance_percent=request.amount_tolerance_percent or 1.0,
                vendor_similarity_threshold=request.vendor_similarity_threshold or 0.80,
                min_confidence_score=request.min_confidence_score or 0.70
            )
            engine = custom_engine
        else:
            engine = matching_engine

        # Perform matching
        logger.info("🎯 Performing matching...")
        match_result = engine.find_matches(
            faktur_candidates,
            rekening_candidates,
            pph_candidates
        )

        # Generate summary
        summary = engine.generate_summary(match_result)

        logger.info(f"✅ Matching complete! Match ID: {match_result.match_id}")

        return {
            "success": True,
            "match_id": match_result.match_id,
            "confidence_score": match_result.confidence_score,
            "match_type": match_result.match_type,
            "matched_items": match_result.matched_items,
            "unmatched_items": match_result.unmatched_items,
            "details": match_result.details,
            "summary": {
                "total_faktur": summary.total_faktur,
                "total_rekening": summary.total_rekening,
                "total_pph": summary.total_pph,
                "matched_count": summary.matched_count,
                "unmatched_faktur": summary.unmatched_faktur,
                "unmatched_rekening": summary.unmatched_rekening,
                "unmatched_pph": summary.unmatched_pph,
                "belum_dilaporkan": summary.belum_dilaporkan,
                "match_rate": summary.match_rate,
                "total_matched_amount": float(summary.total_matched_amount),
                "total_unmatched_amount": float(summary.total_unmatched_amount)
            }
        }

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        raise HTTPException(status_code=404, detail=f"File not found: {str(e)}")
    except Exception as e:
        logger.error(f"Error during matching: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/match/{match_id}")
async def get_match_result(match_id: str):
    """
    Get previously executed match results by match_id

    Note: This is a placeholder - in production, match results should be stored
    in database or cache for retrieval
    """
    # TODO: Implement match result storage and retrieval
    raise HTTPException(
        status_code=501,
        detail="Match result retrieval not yet implemented. Results are currently ephemeral."
    )
