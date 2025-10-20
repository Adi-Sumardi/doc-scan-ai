"""
Batches Router
Handles batch and result management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Form, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime
from pathlib import Path
import logging
import os
import json

from database import get_db, Batch, DocumentFile, User
from database import ScanResult as DBScanResult
from auth import get_current_active_user
from batch_processor import batch_processor
from websocket_manager import manager
from config import get_upload_dir, get_results_dir
from redis_cache import RedisCache

logger = logging.getLogger(__name__)

# Initialize Redis cache
redis_cache = RedisCache()

# Create router
router = APIRouter(prefix="/api", tags=["batches"])

# ==================== Batch Status Endpoints ====================

@router.get("/batches/{batch_id}")
async def get_batch_status(
    batch_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get batch processing status with comprehensive error handling"""
    try:
        # Validate batch_id format
        if not batch_id or len(batch_id) < 10:
            raise HTTPException(
                status_code=400, 
                detail={
                    "error": "Invalid batch ID",
                    "message": "Batch ID must be a valid UUID format",
                    "error_code": "INVALID_BATCH_ID"
                }
            )
        
        # Get batch from database
        try:
            batch = db.query(Batch).filter(Batch.id == batch_id).first()
        except Exception as e:
            logger.error(f"Database error querying batch {batch_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Database error",
                    "message": "Failed to retrieve batch information. Please try again.",
                    "error_code": "DATABASE_ERROR"
                }
            )
        
        if not batch:
            raise HTTPException(
                status_code=404, 
                detail={
                    "error": "Batch not found",
                    "message": f"No batch found with ID {batch_id}. Please check the batch ID and try again.",
                    "error_code": "BATCH_NOT_FOUND"
                }
            )
        
        # Verify ownership
        if batch.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Access denied",
                    "message": "You don't have permission to access this batch.",
                    "error_code": "ACCESS_DENIED"
                }
            )
        
        # Calculate processing progress
        progress_percentage = 0
        if batch.total_files > 0:
            progress_percentage = (batch.processed_files / batch.total_files) * 100
        
        return {
            "id": batch.id,
            "status": batch.status,
            "total_files": batch.total_files,
            "processed_files": batch.processed_files,
            "progress_percentage": round(progress_percentage, 1),
            "created_at": batch.created_at.isoformat(),
            "completed_at": batch.completed_at.isoformat() if batch.completed_at else None,
            "error_message": batch.error_message,
            "source": "database"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"🚨 Unexpected error getting batch status for {batch_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail={
                "error": "System error",
                "message": "An unexpected error occurred while retrieving batch status. Please try again.",
                "error_code": "SYSTEM_ERROR",
                "batch_id": batch_id
            }
        )


@router.get("/batches/{batch_id}/results")
async def get_batch_results(
    batch_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get scan results for a batch"""
    try:
        # Verify batch exists
        batch = db.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            raise HTTPException(status_code=404, detail="Batch not found")
        
        # Verify ownership
        if batch.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Not authorized to access this batch")
        
        # Get all results for this batch
        results = db.query(DBScanResult).filter(DBScanResult.batch_id == batch_id).all()
        
        # Format results for API response
        batch_results = []
        for result in results:
            # Extract raw_ocr_result if it exists in extracted_data
            extracted_data = result.extracted_data or {}
            raw_ocr_result = None
            if isinstance(extracted_data, dict) and "raw_ocr_result" in extracted_data:
                raw_ocr_result = extracted_data.get("raw_ocr_result")

            result_data = {
                "id": result.id,
                "batch_id": result.batch_id,
                "filename": result.original_filename,
                "document_type": result.document_type,
                "extracted_text": result.extracted_text,
                "extracted_data": result.extracted_data,
                "raw_ocr_result": raw_ocr_result,  # Expose raw OCR at top level
                "confidence": result.confidence,
                "ocr_engine_used": result.ocr_engine_used,
                "created_at": result.created_at.isoformat(),
                "ocr_processing_time": result.ocr_processing_time
            }
            batch_results.append(result_data)
        
        logger.info(f"📊 Retrieved {len(batch_results)} results for batch {batch_id}")
        return batch_results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting batch results: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving batch results: {str(e)}")


@router.get("/batches")
async def get_all_batches(
    limit: Optional[int] = Query(None, description="Number of batches to return (pagination)"),
    offset: Optional[int] = Query(0, description="Number of batches to skip (pagination)"),
    include_files: bool = Query(True, description="Include file details in response"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get batches for current user with pagination and caching

    - **limit**: Number of batches to return (default: all)
    - **offset**: Number of batches to skip (default: 0)
    - **include_files**: Include detailed file information (default: true)

    Uses Redis cache for performance (5 minute TTL)
    """
    try:
        # Generate cache key based on user and params
        cache_key = f"batches:user:{current_user.id}:limit:{limit}:offset:{offset}:files:{include_files}"

        # Try to get from cache first
        if redis_cache.is_connected():
            cached_data = redis_cache.get(cache_key)
            if cached_data:
                logger.info(f"⚡ Cache HIT for batches (user: {current_user.id})")
                try:
                    return json.loads(cached_data)
                except:
                    logger.warning("Failed to parse cached data, fetching from DB")

        # Cache MISS - fetch from database
        logger.info(f"📊 Cache MISS - Fetching batches from database (user: {current_user.id})")

        # Build query with pagination
        query = db.query(Batch).filter(Batch.user_id == current_user.id).order_by(desc(Batch.created_at))

        # Apply pagination if limit is specified
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        batches = query.all()

        batch_list = []
        for batch in batches:
            batch_data = {
                "id": batch.id,
                "status": batch.status,
                "total_files": batch.total_files,
                "processed_files": batch.processed_files,
                "created_at": batch.created_at.isoformat(),
                "completed_at": batch.completed_at.isoformat() if batch.completed_at else None,
                "error_message": batch.error_message
            }

            # Include files if requested
            if include_files:
                files = db.query(DocumentFile).filter(DocumentFile.batch_id == batch.id).all()
                batch_data["files"] = [
                    {
                        "id": f.id,
                        "name": f.name,
                        "type": f.type,
                        "size": f.file_size,
                        "status": f.status
                    }
                    for f in files
                ]

            batch_list.append(batch_data)

        # Cache the result for 5 minutes (300 seconds)
        if redis_cache.is_connected():
            try:
                redis_cache.set(cache_key, json.dumps(batch_list), ttl=300)
                logger.info(f"💾 Cached batches for user {current_user.id} (TTL: 5min)")
            except Exception as cache_error:
                logger.warning(f"Failed to cache batches: {cache_error}")

        logger.info(f"✅ Returned {len(batch_list)} batches (limit: {limit}, offset: {offset})")
        return batch_list if batch_list is not None else []

    except Exception as e:
        logger.error(f"Error getting all batches: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving batches: {str(e)}")


@router.post("/batch/cancel")
async def cancel_batch_processing(
    batch_id: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Cancel ongoing batch processing"""
    try:
        # Verify batch exists and user owns it
        batch = db.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            raise HTTPException(status_code=404, detail="Batch not found")
        
        if batch.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Not authorized to cancel this batch")
        
        # Check if batch is actually processing
        if batch.status not in ["processing", "pending"]:
            return {
                "success": False,
                "message": f"Batch is not in a cancellable state. Current status: {batch.status}"
            }
        
        # Cancel the batch
        success = batch_processor.cancel_batch(batch_id)
        
        if success:
            # Update database status
            batch.status = "cancelled"
            db.commit()
            
            logger.info(f"✅ Cancelled batch {batch_id} by user {current_user.username}")
            
            # Notify via WebSocket
            await manager.send_batch_progress(batch_id, {
                "status": "cancelled",
                "message": "Batch processing cancelled by user"
            })
            
            return {
                "success": True,
                "message": "Batch processing cancelled successfully",
                "batch_id": batch_id
            }
        else:
            return {
                "success": False,
                "message": "Failed to cancel batch. It may have already completed."
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling batch {batch_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to cancel batch: {str(e)}")


@router.delete("/batches/{batch_id}")
async def delete_batch(
    batch_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a batch and all associated data (files, results, etc.)
    Allowed for ANY batch status (completed, error, failed, processing)
    Only owner or admin can delete
    """
    try:
        # Verify batch exists
        batch = db.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            raise HTTPException(
                status_code=404,
                detail="Batch tidak ditemukan"
            )

        # Verify ownership - only batch owner or admin can delete
        if batch.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=403,
                detail="Anda tidak memiliki izin untuk menghapus batch ini"
            )

        # Allow deletion of ANY batch status (completed, error, failed, processing)
        # User requested ability to delete old completed batches to clean up database
        logger.info(f"🗑️ Deleting batch {batch_id} (status: {batch.status}) by user {current_user.username}")

        # Get all document files associated with this batch for cleanup
        document_files = db.query(DocumentFile).filter(DocumentFile.batch_id == batch_id).all()

        # Delete physical files from disk
        upload_dir = Path(get_upload_dir())
        deleted_files_count = 0

        for doc_file in document_files:
            try:
                file_path = Path(doc_file.file_path)
                if file_path.exists():
                    # Security: Verify file is within upload directory
                    file_path_resolved = file_path.resolve()
                    if str(file_path_resolved).startswith(str(upload_dir.resolve())):
                        os.remove(file_path)
                        deleted_files_count += 1
                        logger.debug(f"Deleted file: {file_path}")
                    else:
                        logger.warning(f"Skipped file outside upload dir: {file_path}")
            except Exception as e:
                # Log error but continue deletion process
                logger.error(f"Error deleting file {doc_file.file_path}: {e}")

        # Database cascade delete (configured in models):
        # 1. Delete scan results (ON DELETE CASCADE from scan_results.batch_id)
        # 2. Delete document files (ON DELETE CASCADE from document_files.batch_id)
        # 3. Delete batch

        # Explicitly delete scan results first for cleaner logging
        deleted_results = db.query(DBScanResult).filter(DBScanResult.batch_id == batch_id).delete()

        # Delete document files records
        deleted_doc_files = db.query(DocumentFile).filter(DocumentFile.batch_id == batch_id).delete()

        # Finally delete the batch itself
        db.delete(batch)

        # Commit transaction
        db.commit()

        logger.info(
            f"✅ Successfully deleted batch {batch_id}: "
            f"{deleted_doc_files} document files, "
            f"{deleted_results} scan results, "
            f"{deleted_files_count} physical files"
        )

        return {
            "success": True,
            "message": "Batch berhasil dihapus",
            "batch_id": batch_id,
            "deleted_files": deleted_doc_files,
            "deleted_results": deleted_results
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"🚨 Error deleting batch {batch_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Gagal menghapus batch: {str(e)}"
        )


# ==================== Result Management Endpoints ====================

@router.get("/results")
async def get_all_results(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all scan results for current user"""
    try:
        # Join with Batch to filter by user_id
        results = db.query(DBScanResult).join(
            Batch, DBScanResult.batch_id == Batch.id
        ).filter(
            Batch.user_id == current_user.id
        ).order_by(desc(DBScanResult.created_at)).all()
        
        results_list = []
        for result in results:
            # Parse extracted_data if it's a string
            import json
            extracted_data = result.extracted_data
            if isinstance(extracted_data, str):
                try:
                    extracted_data = json.loads(extracted_data)
                except:
                    extracted_data = {}
            elif not isinstance(extracted_data, dict):
                extracted_data = {}

            # Extract raw_ocr_result if it exists in extracted_data
            raw_ocr_result = None
            if isinstance(extracted_data, dict) and "raw_ocr_result" in extracted_data:
                raw_ocr_result = extracted_data.get("raw_ocr_result")

            result_data = {
                "id": result.id,
                "batch_id": result.batch_id,
                "filename": result.original_filename,
                "document_type": result.document_type,
                "confidence_score": result.confidence,
                "processing_time": result.total_processing_time,
                "created_at": result.created_at.isoformat(),
                "extracted_data": extracted_data,
                "raw_ocr_result": raw_ocr_result  # Expose raw OCR at top level
            }
            results_list.append(result_data)
        
        return results_list if results_list is not None else []
        
    except Exception as e:
        logger.error(f"Error getting all results: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving results: {str(e)}")


@router.patch("/results/{result_id}")
async def update_result(
    result_id: str,
    updated_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update edited OCR result data with transaction safety"""
    try:
        # Validate updated_data is not empty
        if not updated_data:
            raise HTTPException(status_code=400, detail="No data provided for update")

        # Get scan result from database
        result = db.query(DBScanResult).filter(DBScanResult.id == result_id).first()
        if not result:
            raise HTTPException(status_code=404, detail="Scan result not found")

        # Verify ownership through batch
        batch = db.query(Batch).filter(Batch.id == result.batch_id).first()
        if not batch:
            raise HTTPException(status_code=404, detail="Associated batch not found")

        # Only allow user to edit their own results (or admin can edit all)
        if batch.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Not authorized to edit this result")

        # Store old data for history (optional - for version control)
        old_data = result.extracted_data.copy() if result.extracted_data else {}

        # Update extracted_data with edited data
        if result.extracted_data:
            result.extracted_data.update(updated_data)
        else:
            result.extracted_data = updated_data

        # Update timestamp with timezone-aware datetime
        from datetime import datetime, timezone
        result.updated_at = datetime.now(timezone.utc)

        # Commit to database with explicit transaction
        db.commit()
        db.refresh(result)

        logger.info(f"✅ Updated scan result {result_id} by user {current_user.username}")

        return {
            "success": True,
            "message": "Result updated successfully",
            "result_id": result_id,
            "updated_at": result.updated_at.isoformat()
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating result {result_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update result. Please try again.")


@router.get("/results/{result_id}/file")
async def get_result_file(
    result_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Serve the original uploaded file for a scan result"""
    try:
        # Get scan result
        result = db.query(DBScanResult).filter(DBScanResult.id == result_id).first()
        if not result:
            raise HTTPException(status_code=404, detail="Scan result not found")
        
        # Get document file info
        doc_file = db.query(DocumentFile).filter(DocumentFile.id == result.document_file_id).first()
        if not doc_file:
            raise HTTPException(status_code=404, detail="Document file not found")
        
        # Verify ownership
        batch = db.query(Batch).filter(Batch.id == result.batch_id).first()
        if not batch:
            raise HTTPException(status_code=404, detail="Associated batch not found")
        
        if batch.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Not authorized to access this file")
        
        # Construct file path and validate it's within allowed directories
        file_path = Path(doc_file.file_path)

        # Security: Validate file path is within allowed directories
        allowed_dirs = [Path(get_upload_dir()).resolve(), Path(get_results_dir()).resolve()]
        file_path_resolved = file_path.resolve()

        is_safe = any(
            str(file_path_resolved).startswith(str(allowed_dir))
            for allowed_dir in allowed_dirs
        )

        if not is_safe:
            logger.warning(f"Path traversal attempt detected: {file_path}")
            raise HTTPException(status_code=403, detail="Access to this file path is not allowed")

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Original file not found on disk")
        
        # Determine media type based on file extension
        file_extension = file_path.suffix.lower()
        media_type_map = {
            '.pdf': 'application/pdf',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.tiff': 'image/tiff',
            '.tif': 'image/tiff',
            '.bmp': 'image/bmp',
            '.gif': 'image/gif'
        }
        
        media_type = media_type_map.get(file_extension, 'application/octet-stream')
        
        # Return the file
        return FileResponse(
            path=str(file_path),
            filename=doc_file.name,
            media_type=media_type
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving result file {result_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to serve file: {str(e)}")
