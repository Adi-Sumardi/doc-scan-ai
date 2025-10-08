"""
Exports Router
Handles export endpoints for Excel and PDF
"""

from fastapi import APIRouter, Depends, HTTPException, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path
import logging

from database import get_db, Batch, DocumentFile, User
from database import ScanResult as DBScanResult
from auth import get_current_active_user
from config import get_exports_dir
from excel_template import create_batch_excel_export
from pdf_template import create_batch_pdf_export

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api", tags=["exports"])

# Storage directory
EXPORTS_DIR = Path(get_exports_dir())


# ==================== Basic Export Endpoints ====================

@router.get("/results/{result_id}/export/{format}")
async def export_result(
    result_id: str,
    format: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Export single scan result to Excel or PDF"""
    try:
        # Validate format
        if format not in ['excel', 'pdf']:
            raise HTTPException(status_code=400, detail="Format must be 'excel' or 'pdf'")
        
        # Get scan result from database
        result = db.query(DBScanResult).filter(DBScanResult.id == result_id).first()
        if not result:
            raise HTTPException(status_code=404, detail="Scan result not found")
        
        # Verify ownership
        batch = db.query(Batch).filter(Batch.id == result.batch_id).first()
        if not batch:
            raise HTTPException(status_code=404, detail="Associated batch not found")
        
        if batch.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Not authorized to export this result")
        
        # Get associated file info
        file_info = db.query(DocumentFile).filter(DocumentFile.id == result.document_file_id).first()
        
        # Prepare result data for export
        result_data = {
            'id': result.id,
            'filename': file_info.name if file_info else 'Unknown',
            'original_filename': file_info.name if file_info else 'Unknown',
            'document_type': result.document_type or 'Unknown',
            'confidence': result.confidence or 0,
            'extracted_data': result.extracted_data or {},
            'extracted_text': result.extracted_text or '',
            'created_at': result.created_at.isoformat() if result.created_at else None,
            'processing_time': result.total_processing_time or 0.0,
            'ocr_engine': result.ocr_engine_used or 'Unknown'
        }
        
        # Create filename
        safe_filename = "".join(c for c in (file_info.name if file_info else 'document') 
                               if c.isalnum() or c in (' ', '-', '_')).rstrip()
        export_filename = f"{safe_filename}_scan_result.{format if format == 'pdf' else 'xlsx'}"
        export_path = EXPORTS_DIR / export_filename
        
        # Create export
        if format == 'excel':
            success = create_batch_excel_export(
                batch_results=[result_data],
                output_path=str(export_path),
                document_type=result.document_type
            )
        else:  # PDF
            success = create_batch_pdf_export(
                batch_results=[result_data],
                output_path=str(export_path),
                document_type=result.document_type
            )
        
        if not success:
            raise HTTPException(status_code=500, detail=f"Failed to create {format.upper()} export")
        
        logger.info(f"✅ Created {format} export for result {result_id}")
        
        # Return file
        return FileResponse(
            path=str(export_path),
            filename=export_filename,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' if format == 'excel' else 'application/pdf'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export error: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/batches/{batch_id}/export/{format}")
async def export_batch(
    batch_id: str,
    format: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Export all scan results in a batch to Excel or PDF"""
    try:
        # Validate format
        if format not in ['excel', 'pdf']:
            raise HTTPException(status_code=400, detail="Format must be 'excel' or 'pdf'")
        
        # Get batch info
        batch = db.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            raise HTTPException(status_code=404, detail="Batch not found")
        
        # Verify ownership
        if batch.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Not authorized to export this batch")
        
        # Get all scan results for this batch
        results = db.query(DBScanResult).filter(DBScanResult.batch_id == batch_id).all()
        if not results:
            raise HTTPException(status_code=404, detail="No scan results found for this batch")
        
        # Optimization: Fetch all file info in one query to avoid N+1 problem
        file_ids = [r.document_file_id for r in results]
        file_infos = db.query(DocumentFile).filter(DocumentFile.id.in_(file_ids)).all()
        file_info_map = {f.id: f for f in file_infos}

        # Prepare results data for export
        results_data = []
        for r in results:
            file_info = file_info_map.get(r.document_file_id)
            result_dict = {
                'id': r.id,
                'batch_id': r.batch_id,
                'filename': file_info.name if file_info else 'Unknown',
                'original_filename': file_info.name if file_info else 'Unknown',
                'document_type': r.document_type or 'Unknown',
                'confidence': r.confidence or 0,
                'extracted_data': r.extracted_data or {},
                'extracted_text': r.extracted_text or '',
                'created_at': r.created_at.isoformat() if r.created_at else None,
                'processing_time': r.total_processing_time or 0.0,
                'ocr_engine': r.ocr_engine_used or 'Unknown'
            }
            results_data.append(result_dict)
        
        # Create filename for batch export
        export_filename = f"batch_{batch_id[:8]}_results.{format if format == 'pdf' else 'xlsx'}"
        export_path = EXPORTS_DIR / export_filename
        
        # Create export
        if format == 'excel':
            success = create_batch_excel_export(
                batch_results=results_data,
                output_path=str(export_path)
            )
        else:  # PDF
            success = create_batch_pdf_export(
                batch_results=results_data,
                output_path=str(export_path)
            )

        if not success:
            raise HTTPException(status_code=500, detail=f"Failed to create batch {format.upper()} export")
        
        logger.info(f"✅ Created batch {format} export for {len(results_data)} results")
        
        # Return file
        return FileResponse(
            path=str(export_path),
            filename=export_filename,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' if format == 'excel' else 'application/pdf'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch export error: {e}")
        raise HTTPException(status_code=500, detail=f"Batch export failed: {str(e)}")


# ==================== Enhanced Export Endpoints ====================

@router.post("/export/enhanced/excel")
async def export_enhanced_excel(
    result_id: str = Form(...),
    template_style: str = Form("professional"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Export scan result using enhanced Excel template with professional styling
    
    Args:
        result_id: Scan result ID to export
        template_style: Template style (professional, basic, detailed)
    
    Returns:
        Excel file with professional formatting
    """
    try:
        # Get scan result from database
        result = db.query(DBScanResult).filter(DBScanResult.id == result_id).first()
        if not result:
            raise HTTPException(status_code=404, detail="Scan result not found")
        
        # Verify ownership
        batch = db.query(Batch).filter(Batch.id == result.batch_id).first()
        if not batch:
            raise HTTPException(status_code=404, detail="Associated batch not found")
        
        if batch.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Not authorized to export this result")
        
        # Get associated file info
        file_info = db.query(DocumentFile).filter(DocumentFile.id == result.document_file_id).first()
        
        # Prepare result data for export
        result_data = {
            'id': result.id,
            'filename': file_info.name if file_info else 'Unknown',
            'original_filename': file_info.name if file_info else 'Unknown',
            'document_type': result.document_type or 'Unknown',
            'confidence': result.confidence or 0,
            'extracted_data': result.extracted_data or {},
            'extracted_text': result.extracted_text or '',
            'created_at': result.created_at.isoformat() if result.created_at else None,
            'processing_time': result.total_processing_time or 0.0,
            'ocr_engine': result.ocr_engine_used or 'Unknown'
        }
        
        # Create filename
        safe_filename = "".join(c for c in (file_info.name if file_info else 'document') 
                               if c.isalnum() or c in (' ', '-', '_')).rstrip()
        export_filename = f"{safe_filename}_enhanced.xlsx"
        export_path = EXPORTS_DIR / export_filename
        
        # Generate enhanced Excel using batch export function with single result
        success = create_batch_excel_export(
            batch_results=[result_data],
            output_path=str(export_path),
            document_type=result.document_type
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to create enhanced Excel export")
        
        logger.info(f"✅ Created enhanced Excel export for result {result_id}")
        
        # Return file
        return FileResponse(
            path=str(export_path),
            filename=export_filename,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Enhanced Excel export error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Enhanced Excel export failed: {str(e)}")


@router.post("/export/enhanced/pdf")
async def export_enhanced_pdf(
    result_id: str = Form(...),
    template_style: str = Form("professional"),
    include_watermark: bool = Form(False),
    watermark_text: str = Form("CONFIDENTIAL"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Export scan result using enhanced PDF template with professional layout
    
    Args:
        result_id: Scan result ID to export
        template_style: Template style (professional, official, simple)
        include_watermark: Whether to add watermark
        watermark_text: Text for watermark
    
    Returns:
        PDF file with professional formatting
    """
    try:
        # Get scan result from database
        result = db.query(DBScanResult).filter(DBScanResult.id == result_id).first()
        if not result:
            raise HTTPException(status_code=404, detail="Scan result not found")
        
        # Verify ownership
        batch = db.query(Batch).filter(Batch.id == result.batch_id).first()
        if not batch:
            raise HTTPException(status_code=404, detail="Associated batch not found")
        
        if batch.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Not authorized to export this result")
        
        # Get associated file info
        file_info = db.query(DocumentFile).filter(DocumentFile.id == result.document_file_id).first()
        
        # Prepare result data for export
        result_data = {
            'id': result.id,
            'filename': file_info.name if file_info else 'Unknown',
            'original_filename': file_info.name if file_info else 'Unknown',
            'document_type': result.document_type or 'Unknown',
            'confidence': result.confidence or 0,
            'extracted_data': result.extracted_data or {},
            'extracted_text': result.extracted_text or '',
            'created_at': result.created_at.isoformat() if result.created_at else None,
            'processing_time': result.total_processing_time or 0.0,
            'ocr_engine': result.ocr_engine_used or 'Unknown',
            'include_watermark': include_watermark,
            'watermark_text': watermark_text
        }
        
        # Create filename
        safe_filename = "".join(c for c in (file_info.name if file_info else 'document') 
                               if c.isalnum() or c in (' ', '-', '_')).rstrip()
        export_filename = f"{safe_filename}_enhanced.pdf"
        export_path = EXPORTS_DIR / export_filename
        
        # Generate enhanced PDF using batch export function with single result
        success = create_batch_pdf_export(
            batch_results=[result_data],
            output_path=str(export_path),
            document_type=result.document_type
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to create enhanced PDF export")
        
        logger.info(f"✅ Created enhanced PDF export for result {result_id}")
        
        # Return file
        return FileResponse(
            path=str(export_path),
            filename=export_filename,
            media_type='application/pdf'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Enhanced PDF export error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Enhanced PDF export failed: {str(e)}")
