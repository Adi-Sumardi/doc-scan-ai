"""
Documents Router
Handles document upload and batch processing
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, Request
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List
from datetime import datetime, timezone
from pathlib import Path
import uuid
import json
import aiofiles
import logging

from database import SessionLocal, get_db, Batch, DocumentFile, ProcessingLog, User
from database import ScanResult as DBScanResult
from models import BatchResponse, DocumentFile as DocumentFileModel
from auth import get_current_active_user
from security import file_security, SecurityValidator
from ai_processor import process_document_ai
from batch_processor import batch_processor
from config import get_upload_dir
from slowapi import Limiter
from slowapi.util import get_remote_address
from utils.zip_handler import ZipHandler

logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create router
router = APIRouter(prefix="/api", tags=["documents"])

# Storage directory
UPLOAD_DIR = Path(get_upload_dir())


# ==================== Document Upload Endpoint ====================

@router.post("/upload", response_model=BatchResponse)
@limiter.limit("10/minute")  # Rate limit: 10 uploads per minute per IP
async def upload_documents(
    request: Request,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    document_types: List[str] = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Upload multiple documents for batch processing with comprehensive error handling and security validation"""
    batch_id = None
    try:
        # Input validation
        if not files:
            raise HTTPException(
                status_code=400, 
                detail={
                    "error": "No files provided",
                    "message": "Please select at least one file to upload",
                    "error_code": "NO_FILES"
                }
            )
        
        if not document_types:
            raise HTTPException(
                status_code=400, 
                detail={
                    "error": "No document types provided",
                    "message": "Please specify document types for each file",
                    "error_code": "NO_DOCUMENT_TYPES"
                }
            )
        
        if len(files) != len(document_types):
            raise HTTPException(
                status_code=400, 
                detail={
                    "error": "File count mismatch",
                    "message": f"Number of files ({len(files)}) must match number of document types ({len(document_types)})",
                    "error_code": "COUNT_MISMATCH"
                }
            )
        
        # Validate file limits
        if len(files) > 50:  # Maximum batch size
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Too many files",
                    "message": f"Maximum batch size is 50 files. You provided {len(files)} files.",
                    "error_code": "BATCH_SIZE_EXCEEDED"
                }
            )
        
        batch_id = str(uuid.uuid4())
        batch_dir = UPLOAD_DIR / batch_id
        
        try:
            batch_dir.mkdir(exist_ok=True)
        except OSError as e:
            logger.error(f"Failed to create batch directory {batch_dir}: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Storage error",
                    "message": "Failed to prepare storage for file upload. Please try again.",
                    "error_code": "STORAGE_ERROR"
                }
            )
        
        # Create database batch with error handling
        try:
            db_batch = Batch(
                id=batch_id,
                status="processing",
                created_at=datetime.now(timezone.utc),
                user_id=current_user.id,
                total_files=len(files),  # Set total files count
                processed_files=0
            )
            db.add(db_batch)
            db.commit()
        except Exception as e:
            logger.error(f"Database error creating batch {batch_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Database error",
                    "message": "Failed to create batch record. Please try again.",
                    "error_code": "DATABASE_ERROR"
                }
            )
        
        logger.info(f"📁 Created batch {batch_id} with {len(files)} files")
        
        # Process each file with security validation and comprehensive error handling
        file_paths = []
        validation_results = []
        
        for i, (file, doc_type) in enumerate(zip(files, document_types)):
            try:
                # Validate document type
                valid_types = ["invoice", "receipt", "id_card", "passport", "driver_license", "other",
                               "faktur_pajak", "pph21", "pph23", "rekening_koran", "spt", "npwp", "faktur"]
                
                # Normalize the input document type
                doc_type = doc_type.lower().strip()
                
                if doc_type not in valid_types:
                    validation_result = {
                        "is_valid": False,
                        "errors": [f"Invalid document type '{doc_type}'. Supported types are: {', '.join(valid_types)}"],
                        "warnings": [],
                        "filename": file.filename
                    }
                    validation_results.append(validation_result)
                    continue
                
                # Validate file content exists
                if not file.filename:
                    validation_result = {
                        "is_valid": False,
                        "errors": ["File has no filename"],
                        "warnings": [],
                        "filename": "unknown"
                    }
                    validation_results.append(validation_result)
                    continue
                
                # Read file content ONCE for validation and saving
                try:
                    content = await file.read()
                    
                    if len(content) == 0:
                        validation_result = {
                            "is_valid": False,
                            "errors": ["File is empty"],
                            "warnings": [],
                            "filename": file.filename
                        }
                        validation_results.append(validation_result)
                        continue
                    
                    # Reset file pointer for security validation
                    await file.seek(0)
                        
                except Exception as e:
                    logger.error(f"Failed to read file {file.filename}: {e}")
                    validation_result = {
                        "is_valid": False,
                        "errors": [f"Failed to read file content: {str(e)}"],
                        "warnings": [],
                        "filename": file.filename
                    }
                    validation_results.append(validation_result)
                    continue
                
                # Perform security validation
                validation_result = await file_security.validate_file(file)
                validation_result["filename"] = file.filename
                validation_results.append(validation_result)
                
                if not validation_result["is_valid"]:
                    logger.warning(f"🚫 File {file.filename} failed security validation: {validation_result['errors']}")
                    log_entry = ProcessingLog(
                        batch_id=batch_id,
                        level="WARNING",
                        message=f"File security validation failed for {file.filename}: {'; '.join(validation_result['errors'])}"
                    )
                    db.add(log_entry)
                    continue
                
                # Save file with error handling
                safe_filename = f"{i:03d}_{SecurityValidator.validate_filename(file.filename)}"
                file_path = batch_dir / safe_filename
                
                try:
                    async with aiofiles.open(file_path, 'wb') as f:
                        await f.write(content)
                    
                    # Verify file was written correctly
                    if not file_path.exists() or file_path.stat().st_size == 0:
                        raise Exception("File was not saved properly")
                        
                except Exception as e:
                    logger.error(f"Failed to save file {file.filename}: {e}")
                    validation_result = {
                        "is_valid": False,
                        "errors": [f"Failed to save file: {str(e)}"],
                        "warnings": [],
                        "filename": file.filename
                    }
                    validation_results.append(validation_result)
                    continue
                
                # Create database file record
                try:
                    db_file = DocumentFile(
                        id=str(uuid.uuid4()),
                        batch_id=batch_id,
                        name=file.filename,
                        file_path=str(file_path),
                        type=doc_type,
                        file_size=len(content),
                        mime_type=validation_result["file_info"].get("mime_type", "unknown"),
                        file_hash=validation_result["file_info"].get("md5", "")
                    )
                    db.add(db_file)
                    
                    file_paths.append({
                        "path": str(file_path),
                        "filename": file.filename,
                        "document_type": doc_type,
                        "security_validation": validation_result
                    })
                    
                    logger.info(f"✅ Successfully uploaded and validated: {file.filename}")
                    
                except Exception as e:
                    logger.error(f"Database error for file {file.filename}: {e}")
                    try:
                        file_path.unlink()
                    except:
                        pass
                    validation_result = {
                        "is_valid": False,
                        "errors": [f"Database error: {str(e)}"],
                        "warnings": [],
                        "filename": file.filename
                    }
                    validation_results.append(validation_result)
                    continue
                
            except Exception as e:
                logger.error(f"Unexpected error processing file {getattr(file, 'filename', 'unknown')}: {e}")
                try:
                    log_entry = ProcessingLog(
                        batch_id=batch_id,
                        level="ERROR",
                        message=f"File processing error for {getattr(file, 'filename', 'unknown')}: {str(e)}"
                    )
                    db.add(log_entry)
                except:
                    pass
        
        # Commit all file records
        try:
            db.commit()
        except Exception as e:
            logger.error(f"Failed to update batch {batch_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Database error",
                    "message": "Failed to save batch information. Please try again.",
                    "error_code": "BATCH_UPDATE_ERROR"
                }
            )
        
        # Check if any files passed validation
        if not file_paths:
            failed_files = [r for r in validation_results if not r.get("is_valid", False)]
            error_summary = {}
            
            for result in failed_files:
                for error in result.get("errors", []):
                    if error in error_summary:
                        error_summary[error] += 1
                    else:
                        error_summary[error] = 1
            
            try:
                db_batch.status = "failed"
                db_batch.error_message = "No valid files passed security validation"
                db.commit()
            except:
                pass
            
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "No valid files",
                    "message": f"None of the {len(files)} uploaded files passed security validation",
                    "error_code": "NO_VALID_FILES",
                    "validation_summary": {
                        "total_files": len(files),
                        "failed_files": len(failed_files),
                        "common_errors": error_summary
                    },
                    "failed_files": [
                        {
                            "filename": r.get("filename", "unknown"),
                            "errors": r.get("errors", [])
                        } for r in failed_files
                    ]
                }
            )
        
        # Start async processing
        try:
            background_tasks.add_task(process_batch_async, batch_id, file_paths)
        except Exception as e:
            logger.error(f"Failed to start background processing for batch {batch_id}: {e}")
            try:
                db_batch.status = "failed"
                db_batch.error_message = f"Failed to start processing: {str(e)}"
                db.commit()
            except:
                pass
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Processing error",
                    "message": "Failed to start document processing. Please try again.",
                    "error_code": "PROCESSING_START_ERROR"
                }
            )
        
        # Success response
        file_objects = []
        for file_path_info in file_paths:
            file_objects.append(DocumentFileModel(
                id=str(uuid.uuid4()),
                name=file_path_info["filename"],
                type=file_path_info["document_type"],
                status="processing",
                progress=0
            ))
        
        return BatchResponse(
            id=batch_id,
            files=file_objects,
            status="processing",
            created_at=datetime.now(timezone.utc).isoformat(),
            total_files=len(file_paths),
            processed_files=0,
            completed_at=None,
            error=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"🚨 Unexpected upload error: {e}", exc_info=True)
        
        # Clean up batch directory
        if batch_id:
            try:
                batch_dir = UPLOAD_DIR / batch_id
                if batch_dir.exists():
                    import shutil
                    shutil.rmtree(batch_dir)
            except Exception as cleanup_error:
                logger.error(f"Failed to cleanup batch directory {batch_id}: {cleanup_error}")
        
        # Update batch status to failed
        if batch_id:
            try:
                db = SessionLocal()
                batch = db.query(Batch).filter(Batch.id == batch_id).first()
                if batch:
                    batch.status = "failed"
                    batch.error_message = f"System error: {str(e)}"
                    db.commit()
                db.close()
            except Exception as db_error:
                logger.error(f"Failed to update failed batch status: {db_error}")
        
        raise HTTPException(
            status_code=500, 
            detail={
                "error": "System error",
                "message": "An unexpected error occurred while processing your upload. Please try again.",
                "error_code": "SYSTEM_ERROR",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )


# ==================== Background Processing Function ====================

async def process_batch_async(batch_id: str, file_paths: List[dict]):
    """Background task to process documents with AI using database with real-time progress"""
    db = SessionLocal()
    try:
        logger.info(f"Starting async processing for batch {batch_id}")
        
        # Send batch processing started notification
        # WebSocket removed: await manager.send_batch_progress(batch_id, {
        # "status": "started",
        # "total_files": len(file_paths),
        # "processed_files": 0,
        # "message": f"Starting processing of {len(file_paths)} files"
        # })
        
        batch = db.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            logger.error(f"Batch {batch_id} not found in database")
            # WebSocket removed: await manager.send_batch_error(batch_id, {
            # "error": "Batch not found in database",
            # "batch_id": batch_id
            # })
            return

        if batch_processor.is_cancelled(batch_id):
            logger.info(f"Batch {batch_id} was cancelled before processing started")
            batch.status = "cancelled"
            batch.completed_at = datetime.now(timezone.utc)
            db.commit()

            # WebSocket removed: await manager.send_batch_complete(batch_id, {
            # "status": "cancelled",
            # "total_files": len(file_paths),
            # "processed_files": 0,
            # "success_rate": 0,
            # "message": "Batch processing cancelled by user"
            # })
            batch_processor.clear_cancel_request(batch_id)
            return

        # Set processing start time for ETA calculation
        batch.processing_start = datetime.now(timezone.utc)
        db.commit()

        processed_count = 0
        
        for i, file_info in enumerate(file_paths):
            if batch_processor.is_cancelled(batch_id):
                logger.info(f"Batch {batch_id} cancellation detected before processing file {i + 1}")
                batch.status = "cancelled"
                batch.completed_at = datetime.now(timezone.utc)
                db.commit()

                # WebSocket removed: await manager.send_batch_complete(batch_id, {
                # "status": "cancelled",
                # "total_files": len(file_paths),
                # "processed_files": processed_count,
                # "success_rate": (processed_count / len(file_paths)) * 100 if file_paths else 0,
                # "message": "Batch processing cancelled by user"
                # })
                batch_processor.clear_cancel_request(batch_id)
                return
            try:
                # Send file processing started notification
                # WebSocket removed: await manager.send_file_progress(batch_id, {
                # "filename": file_info.get("filename", "unknown"),
                # "file_index": i + 1,
                # "total_files": len(file_paths),
                # "status": "processing",
                # "message": f"Processing file {i + 1} of {len(file_paths)}"
                # })
                
                # Get file record from database
                db_file = db.query(DocumentFile).filter(
                    and_(DocumentFile.batch_id == batch_id, 
                         DocumentFile.file_path == file_info["path"])
                ).first()
                
                if not db_file:
                    logger.error(f"File record not found for {file_info['path']}")
                    # WebSocket removed: await manager.send_file_progress(batch_id, {
                    # "filename": file_info.get("filename", "unknown"),
                    # "file_index": i + 1,
                    # "status": "error",
                    # "error": "File record not found in database"
                    # })
                    continue
                
                # Update file status to processing
                db_file.status = "processing"
                db_file.processing_start = datetime.now(timezone.utc)
                db.commit()
                
                # Log processing start
                log_entry = ProcessingLog(
                    batch_id=batch_id,
                    level="INFO",
                    message=f"Starting AI processing for {db_file.name}"
                )
                db.add(log_entry)
                db.commit()
                
                # Send OCR processing notification
                # WebSocket removed: await manager.send_file_progress(batch_id, {
                # "filename": db_file.name,
                # "file_index": i + 1,
                # "status": "ocr_processing",
                # "message": f"Running OCR and AI analysis on {db_file.name}"
                # })
                
                # Process with AI
                result = await process_document_ai(
                    file_info["path"],
                    file_info["document_type"]
                )

                # Ensure extracted_data is a dictionary
                extracted_data = result.get("extracted_data", {})
                if isinstance(extracted_data, str):
                    try:
                        parsed_data = json.loads(extracted_data)
                        if isinstance(parsed_data, dict):
                            extracted_data = parsed_data
                        else:
                            logger.warning(f"Parsed data is not a dict for {db_file.name}")
                            extracted_data = {"raw_text": str(extracted_data), "parse_error": "Invalid type after parsing"}
                    except json.JSONDecodeError as e:
                        logger.warning(f"JSON decode failed for {db_file.name}: {e}")
                        extracted_data = {"raw_text": extracted_data, "parse_error": str(e)}
                elif not isinstance(extracted_data, dict):
                    logger.warning(f"extracted_data has unexpected type {type(extracted_data)} for {db_file.name}")
                    extracted_data = {"raw_text": str(extracted_data), "type_error": str(type(extracted_data))}

                # Include raw_ocr_result if available (for debugging/inspection)
                if "raw_ocr_result" in result and result["raw_ocr_result"] is not None:
                    extracted_data["raw_ocr_result"] = result["raw_ocr_result"]
                    logger.info(f"✅ Including raw OCR result in extracted_data for {db_file.name}")

                # Persist normalized extracted data back to result payload for downstream consumers
                result["extracted_data"] = extracted_data

                processing_info = extracted_data.get("processing_info", {}) if isinstance(extracted_data, dict) else {}
                parsing_method = processing_info.get("parsing_method") or result.get("ocr_engine_used", "Google Document AI")
                
                # ✅ DEBUG: Log what we're saving for rekening_koran
                if file_info["document_type"] == "rekening_koran":
                    logger.info(f"🔍 Saving Rekening Koran to DB for {db_file.name}")
                    logger.info(f"   - extracted_data keys: {list(extracted_data.keys()) if isinstance(extracted_data, dict) else 'N/A'}")
                    logger.info(f"   - has smart_mapped: {'smart_mapped' in extracted_data if isinstance(extracted_data, dict) else False}")
                    logger.info(f"   - has transactions: {'transactions' in extracted_data if isinstance(extracted_data, dict) else False}")
                    if isinstance(extracted_data, dict) and 'transactions' in extracted_data:
                        txn_count = len(extracted_data.get('transactions', []))
                        logger.info(f"   - transactions count: {txn_count}")
                    if isinstance(extracted_data, dict) and 'smart_mapped' in extracted_data:
                        smart_mapped = extracted_data.get('smart_mapped', {})
                        if isinstance(smart_mapped, dict) and 'transactions' in smart_mapped:
                            smart_txn_count = len(smart_mapped.get('transactions', []))
                            logger.info(f"   - smart_mapped transactions count: {smart_txn_count}")
                
                # Create scan result in database
                scan_result = DBScanResult(
                    id=str(uuid.uuid4()),
                    batch_id=batch_id,
                    document_file_id=db_file.id,
                    document_type=db_file.type,
                    original_filename=db_file.name,
                    extracted_text=result.get("raw_text", ""),
                    extracted_data=extracted_data,
                    confidence=result.get("confidence", 0.0),
                    ocr_engine_used=parsing_method,
                    total_processing_time=result.get("processing_time", 0.0)
                )
                db.add(scan_result)
                
                # ✅ DEBUG: Confirm save
                if file_info["document_type"] == "rekening_koran":
                    logger.info(f"✅ Rekening Koran saved to DB with scan_result_id: {scan_result.id}")
                
                # Update file status
                db_file.status = "completed"
                db_file.processing_end = datetime.now(timezone.utc)
                db_file.result_id = scan_result.id
                
                processed_count += 1
                
                # Update batch progress
                batch.processed_files = processed_count
                
                db.commit()
                
                # Send file completion notification
                # WebSocket removed: await manager.send_file_progress(batch_id, {
                # "filename": db_file.name,
                # "file_index": i + 1,
                # "status": "completed",
                # "confidence": result.get("confidence", 0.0) * 100,
                # "processing_time": result.get("processing_time", 0.0),
                # "message": f"Successfully processed {db_file.name}"
                # })
                
                # Send overall batch progress update
                # WebSocket removed: await manager.send_batch_progress(batch_id, {
                # "status": "processing",
                # "total_files": len(file_paths),
                # "processed_files": processed_count,
                # "current_file": db_file.name,
                # "progress_percentage": (processed_count / len(file_paths)) * 100,
                # "message": f"Processed {processed_count} of {len(file_paths)} files"
                # })
                
                # Log success
                log_entry = ProcessingLog(
                    batch_id=batch_id,
                    level="INFO",
                    message=f"Successfully processed {db_file.name}"
                )
                db.add(log_entry)
                db.commit()
                
                logger.info(f"Successfully processed {db_file.name} with confidence {result.get('confidence', 0.0)*100:.2f}%")
                
            except Exception as e:
                logger.error(f"Error processing file {file_info.get('filename', 'unknown')}: {e}")
                
                # Send file error notification
                # WebSocket removed: await manager.send_file_progress(batch_id, {
                # "filename": file_info.get("filename", "unknown"),
                # "file_index": i + 1,
                # "status": "error",
                # "error": str(e),
                # "message": f"Failed to process {file_info.get('filename', 'unknown')}"
                # })
                
                # Update file status to failed
                if 'db_file' in locals() and db_file:
                    db_file.status = "failed"
                    db_file.processing_end = datetime.now(timezone.utc)
                    
                # Log error
                log_entry = ProcessingLog(
                    batch_id=batch_id,
                    level="ERROR",
                    message=f"Processing failed: {str(e)}"
                )
                db.add(log_entry)
                db.commit()
        
        # Update batch final status
        if processed_count == len(file_paths):
            batch.status = "completed"
            batch.completed_at = datetime.now(timezone.utc)
            # WebSocket removed: await manager.send_batch_complete(batch_id, {
            # "status": "completed",
            # "total_files": len(file_paths),
            # "processed_files": processed_count,
            # "success_rate": 100.0,
            # "message": f"All {len(file_paths)} files processed successfully"
            # })
            logger.info(f"Batch {batch_id} completed successfully")
        elif processed_count > 0:
            batch.status = "partial"
            batch.completed_at = datetime.now(timezone.utc)
            success_rate = (processed_count / len(file_paths)) * 100
            # WebSocket removed: await manager.send_batch_complete(batch_id, {
            # "status": "partial",
            # "total_files": len(file_paths),
            # "processed_files": processed_count,
            # "success_rate": success_rate,
            # "message": f"Partially completed: {processed_count} of {len(file_paths)} files processed ({success_rate:.1f}%)"
            # })
            logger.info(f"Batch {batch_id} partially completed ({processed_count}/{len(file_paths)})")
        else:
            batch.status = "failed"
            batch.error_message = "No files processed successfully"
            batch.completed_at = datetime.now(timezone.utc)
            # WebSocket removed: await manager.send_batch_error(batch_id, {
            # "error": "No files processed successfully",
            # "total_files": len(file_paths),
            # "processed_files": 0,
            # "message": "Batch processing failed - no files could be processed"
            # })
            logger.error(f"Batch {batch_id} failed - no files processed")
        
        db.commit()
        batch_processor.clear_cancel_request(batch_id)
        
    except Exception as e:
        logger.error(f"Batch processing error for {batch_id}: {e}")
        # WebSocket removed: await manager.send_batch_error(batch_id, {
        # "error": str(e),
        # "message": f"Critical error during batch processing: {str(e)}"
        # })
        # Update batch status to failed
        try:
            batch = db.query(Batch).filter(Batch.id == batch_id).first()
            if batch:
                batch.status = "failed"
                batch.error_message = str(e)
                batch.completed_at = datetime.now(timezone.utc)
                db.commit()
        except:
            pass
    finally:
        batch_processor.clear_cancel_request(batch_id)
        db.close()


@router.post("/upload-zip", response_model=BatchResponse)
@limiter.limit("5/minute")  # Rate limit: 5 ZIP uploads per minute per IP
async def upload_zip_file(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    document_type: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Upload a ZIP file containing multiple documents for batch processing.

    ⚠️ RESTRICTED: ZIP upload is only available for tax documents to prevent token waste.
    For rekening_koran and invoice (which can be 50+ pages), please upload individual files.

    Supported ZIP document types:
    - faktur_pajak (Tax Invoice)
    - pph21 (Income Tax)
    - pph23 (Withholding Tax)
    - spt (Tax Return)
    - npwp (Tax ID)

    NOT supported in ZIP (upload individually):
    - rekening_koran (Bank Statements - can be 50+ pages)
    - invoice (Invoices - can be many pages)

    Args:
        file: ZIP file containing tax documents
        document_type: Document type (faktur_pajak, pph21, pph23, spt, npwp only)

    Returns:
        BatchResponse with batch_id and extraction info
    """
    batch_id = None
    temp_zip_path = None
    extract_dir = None

    try:
        # Validate document type - RESTRICTED to tax documents only
        # Rekening koran and invoice excluded due to high page counts (50+ pages = token waste)
        valid_zip_types = ["faktur_pajak", "pph21", "pph23", "spt", "npwp", "faktur"]
        restricted_types = ["rekening_koran", "invoice"]  # Must upload individually

        document_type = document_type.lower().strip()

        # Check if document type is restricted
        if document_type in restricted_types:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Document type not allowed for ZIP upload",
                    "message": f"'{document_type}' cannot be uploaded via ZIP because these documents typically have 50+ pages, which would consume excessive API tokens. Please upload {document_type} files individually instead.",
                    "error_code": "RESTRICTED_DOCUMENT_TYPE",
                    "suggestion": f"Upload {document_type} files one by one through the regular upload endpoint.",
                    "allowed_zip_types": valid_zip_types
                }
            )

        if document_type not in valid_zip_types:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid document type for ZIP upload",
                    "message": f"Document type '{document_type}' is not supported for ZIP upload. Supported types: {', '.join(valid_zip_types)}",
                    "error_code": "INVALID_DOCUMENT_TYPE",
                    "allowed_zip_types": valid_zip_types
                }
            )

        # Validate file is ZIP
        if not file.filename.lower().endswith('.zip'):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid file type",
                    "message": "File must be a ZIP archive (.zip extension)",
                    "error_code": "NOT_ZIP_FILE"
                }
            )

        # Create batch ID
        batch_id = str(uuid.uuid4())
        batch_dir = UPLOAD_DIR / batch_id

        try:
            batch_dir.mkdir(exist_ok=True)
        except OSError as e:
            logger.error(f"Failed to create batch directory {batch_dir}: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Storage error",
                    "message": "Failed to prepare storage. Please try again.",
                    "error_code": "STORAGE_ERROR"
                }
            )

        # Save ZIP file temporarily
        temp_zip_path = batch_dir / f"temp_{file.filename}"

        try:
            async with aiofiles.open(temp_zip_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
            logger.info(f"📦 Saved ZIP file: {temp_zip_path}")
        except Exception as e:
            logger.error(f"Failed to save ZIP file: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "File save error",
                    "message": "Failed to save uploaded ZIP file. Please try again.",
                    "error_code": "FILE_SAVE_ERROR"
                }
            )

        # Extract and validate ZIP
        zip_handler = ZipHandler()

        # Validate ZIP
        is_valid, message = zip_handler.validate_zip_file(str(temp_zip_path))
        if not is_valid:
            logger.warning(f"🚫 Invalid ZIP file from {current_user.email}: {message}")
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid ZIP file",
                    "message": message,
                    "error_code": "ZIP_VALIDATION_FAILED"
                }
            )

        # Extract ZIP
        extract_dir = batch_dir / "extracted"
        success, extracted_files, extract_message = zip_handler.extract_zip_file(
            str(temp_zip_path),
            str(extract_dir)
        )

        if not success or not extracted_files:
            logger.warning(f"🚫 ZIP extraction failed: {extract_message}")
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Extraction failed",
                    "message": extract_message,
                    "error_code": "ZIP_EXTRACTION_FAILED"
                }
            )

        logger.info(f"✅ Extracted {len(extracted_files)} files from ZIP")

        # Create database batch
        try:
            db_batch = Batch(
                id=batch_id,
                status="processing",
                created_at=datetime.now(timezone.utc),
                user_id=current_user.id,
                total_files=len(extracted_files),  # Set total files from extracted count
                processed_files=0
            )
            db.add(db_batch)
            db.commit()
        except Exception as e:
            logger.error(f"Database error creating batch {batch_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Database error",
                    "message": "Failed to create batch record. Please try again.",
                    "error_code": "DATABASE_ERROR"
                }
            )

        # Process extracted files
        file_paths = []
        file_objects = []

        for i, file_path in enumerate(extracted_files):
            try:
                # Get filename
                original_filename = Path(file_path).name
                safe_filename = f"{i:03d}_{SecurityValidator.validate_filename(original_filename)}"
                final_file_path = batch_dir / safe_filename

                # Get file size BEFORE moving
                file_size = Path(file_path).stat().st_size

                # Move file from extract dir to batch dir
                import shutil
                shutil.move(file_path, final_file_path)

                # Generate file ID
                file_id = str(uuid.uuid4())

                # Create DocumentFile record
                doc_file = DocumentFile(
                    id=file_id,
                    batch_id=batch_id,
                    name=original_filename,
                    file_path=str(final_file_path),
                    type=document_type,
                    file_size=file_size,
                    status="pending"
                )
                db.add(doc_file)
                file_paths.append(str(final_file_path))

                # Create file object for response
                file_objects.append(DocumentFileModel(
                    id=file_id,
                    filename=original_filename,
                    type=document_type,
                    status="processing",
                    progress=0
                ))

                logger.info(f"  ✅ Prepared file {i+1}/{len(extracted_files)}: {original_filename}")

            except Exception as e:
                logger.error(f"Error processing extracted file {file_path}: {e}")

        # Commit all DocumentFile records
        try:
            db.commit()
        except Exception as e:
            logger.error(f"Failed to commit document files: {e}")
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Database error",
                    "message": "Failed to save document records.",
                    "error_code": "DATABASE_COMMIT_ERROR"
                }
            )

        # Cleanup temporary ZIP and extract directory
        try:
            if temp_zip_path and temp_zip_path.exists():
                temp_zip_path.unlink()
            if extract_dir and extract_dir.exists():
                import shutil
                shutil.rmtree(extract_dir)
            logger.info(f"🗑️  Cleaned up temporary files")
        except Exception as e:
            logger.warning(f"Failed to cleanup temp files: {e}")

        # Prepare file paths for background processing
        file_paths_data = []
        for i, file_path in enumerate(file_paths):
            # Get filename from path
            filename = Path(file_path).name
            file_paths_data.append({
                "path": file_path,
                "document_type": document_type,
                "filename": filename  # Add filename for progress notifications
            })

        # Start background processing
        background_tasks.add_task(process_batch_async, batch_id, file_paths_data)

        logger.info(f"🚀 Started batch processing for {batch_id} with {len(file_paths)} files from ZIP")

        return BatchResponse(
            id=batch_id,
            files=file_objects,
            status="processing",
            created_at=datetime.now(timezone.utc).isoformat(),
            total_files=len(file_paths),
            processed_files=0,
            completed_at=None,
            error=None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ZIP upload error: {e}", exc_info=True)

        # Cleanup on error
        if batch_id:
            batch_dir = UPLOAD_DIR / batch_id
            if batch_dir.exists():
                import shutil
                shutil.rmtree(batch_dir)

        raise HTTPException(
            status_code=500,
            detail={
                "error": "Upload failed",
                "message": f"An unexpected error occurred: {str(e)}",
                "error_code": "UPLOAD_ERROR"
            }
        )
