from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Depends, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import uvicorn
import os
import uuid
import json
import asyncio
from datetime import datetime
from typing import List, Optional
import aiofiles
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
import logging

# Import our modules
from ai_processor import process_document_ai, create_enhanced_excel_export, create_enhanced_pdf_export, RealOCRProcessor
from models import BatchResponse, ScanResult, BatchStatus, DocumentFile as DocumentFileModel
from database import SessionLocal, engine, Base, Batch, DocumentFile, ScanResult as DBScanResult, ProcessingLog, SystemMetrics
from config import settings, get_upload_dir, get_results_dir, get_exports_dir
from websocket_manager import manager
# Redis cache is optional - only for stats and health monitoring
try:
    from redis_cache import cache
    REDIS_AVAILABLE = True
except ImportError:
    cache = None
    REDIS_AVAILABLE = False
# Temporarily comment out security validator for now
# from utils import FileSecurityValidator

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Document Scanner API", version="1.0.0")

# Create database tables
Base.metadata.create_all(bind=engine)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Environment validation
def validate_environment():
    # Check storage directories
    storage_dirs = {
        'uploads': Path(get_upload_dir()),
        'results': Path(get_results_dir()),
        'exports': Path(get_exports_dir())
    }
    
    for name, dir_path in storage_dirs.items():
        try:
            dir_path.mkdir(exist_ok=True)
            # Test write permissions
            test_file = dir_path / '.test_write'
            test_file.touch()
            test_file.unlink()
            logger.info(f"✅ {name} directory OK: {dir_path}")
        except Exception as e:
            logger.error(f"❌ {name} directory error: {e}")
            raise RuntimeError(f"Storage directory {name} not accessible: {e}")
    
    # Check database
    try:
        with SessionLocal() as db:
            db.execute("SELECT 1")
        logger.info("✅ Database connection OK")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        raise

    # Check OCR system
    try:
        ocr = RealOCRProcessor()
        if not ocr.initialized:
            raise RuntimeError("No OCR engines available")
        logger.info("✅ OCR system OK")
    except Exception as e:
        logger.error(f"❌ OCR system error: {e}")
        raise

# Run environment validation
try:
    validate_environment()
except Exception as e:
    logger.critical(f"❌ Environment validation failed: {e}")
    raise

# Storage directories
UPLOAD_DIR = Path(get_upload_dir())
RESULTS_DIR = Path(get_results_dir())
EXPORTS_DIR = Path(get_exports_dir())

# Simple file validation function
def validate_file(content: bytes, filename: str) -> dict:
    """Simple file validation for error handling demo"""
    errors = []
    warnings = []
    
    # Check file size (max 10MB)
    if len(content) > 10 * 1024 * 1024:
        errors.append("File size exceeds 10MB limit")
    
    # Check file extension
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.pdf', '.tiff', '.tif']
    file_ext = Path(filename).suffix.lower()
    if file_ext not in allowed_extensions:
        errors.append(f"File type '{file_ext}' not supported. Allowed: {', '.join(allowed_extensions)}")
    
    # Check if file has content
    if len(content) == 0:
        errors.append("File is empty")
    
    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "file_info": {
            "mime_type": "application/octet-stream",
            "md5": "temp_md5",
            "sha256": "temp_sha256"
        }
    }

@app.get("/")
async def root():
    return {"message": "AI Document Scanner API", "status": "online"}

@app.post("/api/heartbeat")
async def heartbeat():
    """Health check endpoint for production validation"""
    try:
        # Test OCR system health
        ocr_processor = RealOCRProcessor()
        ocr_info = ocr_processor.get_ocr_system_info()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "ocr_system": ocr_info,
            "message": "Production OCR system ready"
        }
    except Exception as e:
        return {
            "status": "unhealthy", 
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/api/health")
async def health_check():
    """Enhanced health check with optional cache status"""
    health_data = {
        "status": "healthy", 
        "service": "doc-scan-ai", 
        "timestamp": datetime.now().isoformat(),
        "database": "connected"
    }
    
    if REDIS_AVAILABLE and cache:
        try:
            cache_stats = cache.get_cache_stats()
            health_data["cache"] = {
                "redis_connected": cache_stats.get("connected", False),
                "total_cached_items": cache_stats.get("total_keys", 0)
            }
        except Exception:
            health_data["cache"] = {"redis_connected": False, "error": "Cache unavailable"}
    else:
        health_data["cache"] = {"status": "disabled"}
    
    return health_data

@app.get("/api/cache/stats")
async def get_cache_statistics():
    """Get comprehensive Redis cache statistics (optional feature)"""
    if not REDIS_AVAILABLE or not cache:
        raise HTTPException(status_code=503, detail="Cache service not available")
    return cache.get_cache_stats()

@app.post("/api/cache/clear")
async def clear_cache():
    """Clear all cache entries (optional feature)"""
    if not REDIS_AVAILABLE or not cache:
        raise HTTPException(status_code=503, detail="Cache service not available")
    
    if cache.clear_all_cache():
        return {"message": "Cache cleared successfully"}
    else:
        return {"message": "Failed to clear cache", "status": "error"}

@app.websocket("/ws")
async def websocket_general(websocket: WebSocket):
    """WebSocket endpoint for general system updates"""
    await manager.connect(websocket)
    try:
        # Send connection confirmation
        await manager.send_personal_message(json.dumps({
            "type": "connection_established",
            "message": "Connected to general updates",
            "timestamp": datetime.now().isoformat()
        }), websocket)
        
        while True:
            # Keep connection alive and handle any client messages
            data = await websocket.receive_text()
            # Echo back for testing
            await manager.send_personal_message(f"Echo: {data}", websocket)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.websocket("/ws/batch/{batch_id}")
async def websocket_batch(websocket: WebSocket, batch_id: str):
    """WebSocket endpoint for specific batch progress updates"""
    await manager.connect(websocket, batch_id)
    try:
        # Send connection confirmation with batch info
        await manager.send_personal_message(json.dumps({
            "type": "batch_connection_established", 
            "batch_id": batch_id,
            "message": f"Connected to batch {batch_id} updates",
            "timestamp": datetime.now().isoformat()
        }), websocket)
        
        while True:
            # Keep connection alive and handle any client messages
            data = await websocket.receive_text()
            # Could handle client commands here (pause, cancel, etc.)
            await manager.send_personal_message(f"Batch {batch_id} Echo: {data}", websocket)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, batch_id)

@app.get("/api/connections")
async def get_connection_stats():
    """Get WebSocket connection statistics"""
    return manager.get_connection_stats()

@app.post("/api/upload", response_model=BatchResponse)
async def upload_documents(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    document_types: List[str] = Form(...),
    db: Session = Depends(get_db)
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
                created_at=datetime.now()
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
                             "faktur_pajak", "pph21", "pph23", "rekening_koran", "spt", "npwp"]
                if doc_type not in valid_types:
                    validation_result = {
                        "is_valid": False,
                        "errors": [f"Invalid document type '{doc_type}'. Valid types: {', '.join(valid_types)}"],
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
                
                # Read file content for validation
                try:
                    content = await file.read()
                    await file.seek(0)  # Reset file pointer for later processing
                    
                    if len(content) == 0:
                        validation_result = {
                            "is_valid": False,
                            "errors": ["File is empty"],
                            "warnings": [],
                            "filename": file.filename
                        }
                        validation_results.append(validation_result)
                        continue
                        
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
                validation_result = validate_file(content, file.filename)
                validation_result["filename"] = file.filename
                validation_results.append(validation_result)
                
                if not validation_result["is_valid"]:
                    logger.warning(f"🚫 File {file.filename} failed security validation: {validation_result['errors']}")
                    # Log failed validation
                    log_entry = ProcessingLog(
                        batch_id=batch_id,
                        level="WARNING",
                        message=f"File security validation failed for {file.filename}: {'; '.join(validation_result['errors'])}"
                    )
                    db.add(log_entry)
                    continue
                
                # Save file with comprehensive error handling
                safe_filename = f"{i:03d}_{file.filename}"
                file_path = batch_dir / safe_filename
                
                try:
                    async with aiofiles.open(file_path, 'wb') as f:
                        content = await file.read()
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
                
                # Create database file record with error handling
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
                    # Clean up the saved file if database operation failed
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
                # Log error
                try:
                    log_entry = ProcessingLog(
                        batch_id=batch_id,
                        level="ERROR",
                        message=f"File processing error for {getattr(file, 'filename', 'unknown')}: {str(e)}"
                    )
                    db.add(log_entry)
                except:
                    pass  # Don't fail if logging fails
        
        # Update batch with file count and commit changes
        try:
            db_batch.total_files = len(file_paths)
            db_batch.processed_files = 0
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
            # No valid files - provide detailed feedback
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
                pass  # Don't fail if status update fails
            
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
        
        # Start async processing using FastAPI BackgroundTasks
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
        
        # Success response with comprehensive information
        success_rate = (len(file_paths) / len(files)) * 100 if files else 0
        
        # Create file objects for response
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
            created_at=datetime.now().isoformat(),
            total_files=len(file_paths),
            processed_files=0,
            completed_at=None,
            error=None
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions with their detailed error messages
        raise
    except Exception as e:
        logger.error(f"🚨 Unexpected upload error: {e}", exc_info=True)
        
        # Clean up batch directory if it was created
        if batch_id:
            try:
                batch_dir = UPLOAD_DIR / batch_id
                if batch_dir.exists():
                    import shutil
                    shutil.rmtree(batch_dir)
            except Exception as cleanup_error:
                logger.error(f"Failed to cleanup batch directory {batch_id}: {cleanup_error}")
        
        # Update batch status to failed if batch was created
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
                "timestamp": datetime.now().isoformat()
            }
        )
        import traceback
        logger.error(f"Upload error traceback: {traceback.format_exc()}")
        
        # Update batch status in database
        if 'batch_id' in locals():
            try:
                db_batch = db.query(Batch).filter(Batch.id == batch_id).first()
                if db_batch:
                    db_batch.status = "failed"
                    db_batch.error_message = str(e)
                    db.commit()
            except:
                pass
        
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

async def process_batch_async(batch_id: str, file_paths: List[dict]):
    """Background task to process documents with AI using database with real-time progress"""
    db = SessionLocal()
    try:
        logger.info(f"Starting async processing for batch {batch_id}")
        
        # Send batch processing started notification
        await manager.send_batch_progress(batch_id, {
            "status": "started",
            "total_files": len(file_paths),
            "processed_files": 0,
            "message": f"Starting processing of {len(file_paths)} files"
        })
        
        batch = db.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            logger.error(f"Batch {batch_id} not found in database")
            await manager.send_batch_error(batch_id, {
                "error": "Batch not found in database",
                "batch_id": batch_id
            })
            return
        
        processed_count = 0
        
        for i, file_info in enumerate(file_paths):
            try:
                # Send file processing started notification
                await manager.send_file_progress(batch_id, {
                    "filename": file_info.get("filename", "unknown"),
                    "file_index": i + 1,
                    "total_files": len(file_paths),
                    "status": "processing",
                    "message": f"Processing file {i + 1} of {len(file_paths)}"
                })
                
                # Get file record from database
                db_file = db.query(DocumentFile).filter(
                    and_(DocumentFile.batch_id == batch_id, 
                         DocumentFile.file_path == file_info["path"])
                ).first()
                
                if not db_file:
                    logger.error(f"File record not found for {file_info['path']}")
                    await manager.send_file_progress(batch_id, {
                        "filename": file_info.get("filename", "unknown"),
                        "file_index": i + 1,
                        "status": "error",
                        "error": "File record not found in database"
                    })
                    continue
                
                # Update file status to processing
                db_file.status = "processing"
                db_file.processing_start = datetime.now()
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
                await manager.send_file_progress(batch_id, {
                    "filename": db_file.name,
                    "file_index": i + 1,
                    "status": "ocr_processing",
                    "message": f"Running OCR and AI analysis on {db_file.name}"
                })
                
                # Process with AI
                result = await process_document_ai(
                    file_info["path"], 
                    file_info["document_type"]
                )
                
                # Data will be saved directly to database - no cache needed
                
                # Create scan result in database
                scan_result = DBScanResult(
                    id=str(uuid.uuid4()),
                    batch_id=batch_id,
                    document_file_id=db_file.id,
                    document_type=db_file.type,
                    original_filename=db_file.name,
                    extracted_text=result.get("raw_text", ""),
                    extracted_data=result.get("extracted_data", {}),
                    confidence=result.get("confidence_score", 0.0),
                    ocr_engine_used="NextGen OCR",
                    ocr_processing_time=result.get("processing_time", 0.0)
                )
                db.add(scan_result)
                
                # Update file status
                db_file.status = "completed"
                db_file.processing_end = datetime.now()
                db_file.result_id = scan_result.id
                
                processed_count += 1
                
                # Update batch progress
                batch.processed_files = processed_count
                
                db.commit()
                
                # Send file completion notification
                await manager.send_file_progress(batch_id, {
                    "filename": db_file.name,
                    "file_index": i + 1,
                    "status": "completed",
                    "confidence_score": result.get("confidence_score", 0.0),
                    "processing_time": result.get("processing_time", 0.0),
                    "message": f"Successfully processed {db_file.name}"
                })
                
                # Send overall batch progress update
                await manager.send_batch_progress(batch_id, {
                    "status": "processing",
                    "total_files": len(file_paths),
                    "processed_files": processed_count,
                    "current_file": db_file.name,
                    "progress_percentage": (processed_count / len(file_paths)) * 100,
                    "message": f"Processed {processed_count} of {len(file_paths)} files"
                })
                
                # Log success
                log_entry = ProcessingLog(
                    batch_id=batch_id,
                    level="INFO",
                    message=f"Successfully processed {db_file.name}"
                )
                db.add(log_entry)
                db.commit()
                
                logger.info(f"Successfully processed {db_file.name} with confidence {result.get('confidence_score', 0.0):.2f}%")
                
            except Exception as e:
                logger.error(f"Error processing file {file_info.get('filename', 'unknown')}: {e}")
                
                # Send file error notification
                await manager.send_file_progress(batch_id, {
                    "filename": file_info.get("filename", "unknown"),
                    "file_index": i + 1,
                    "status": "error",
                    "error": str(e),
                    "message": f"Failed to process {file_info.get('filename', 'unknown')}"
                })
                
                # Update file status to failed
                if 'db_file' in locals() and db_file:
                    db_file.status = "failed"
                    db_file.processing_end = datetime.now()
                    
                # Log error
                log_entry = ProcessingLog(
                    batch_id=batch_id,
                    level="ERROR",
                    message=f"Processing failed: {str(e)}"
                )
                db.add(log_entry)
                db.commit()
        
        # Update batch final status and send completion notification
        if processed_count == len(file_paths):
            batch.status = "completed"
            batch.completed_at = datetime.now()
            # Cache the completed batch status
            # Batch completed - status saved in database
            await manager.send_batch_complete(batch_id, {
                "status": "completed",
                "total_files": len(file_paths),
                "processed_files": processed_count,
                "success_rate": 100.0,
                "message": f"All {len(file_paths)} files processed successfully"
            })
            logger.info(f"Batch {batch_id} completed successfully")
        elif processed_count > 0:
            batch.status = "partial"
            batch.completed_at = datetime.now()
            success_rate = (processed_count / len(file_paths)) * 100
            # Cache the partial batch status
            # Batch partially completed - status saved in database
            await manager.send_batch_complete(batch_id, {
                "status": "partial",
                "total_files": len(file_paths),
                "processed_files": processed_count,
                "success_rate": success_rate,
                "message": f"Partially completed: {processed_count} of {len(file_paths)} files processed ({success_rate:.1f}%)"
            })
            logger.info(f"Batch {batch_id} partially completed ({processed_count}/{len(file_paths)})")
        else:
            batch.status = "failed"
            batch.error_message = "No files processed successfully"
            batch.completed_at = datetime.now()
            # Cache the failed batch status
            # Batch failed - status saved in database
            await manager.send_batch_error(batch_id, {
                "error": "No files processed successfully",
                "total_files": len(file_paths),
                "processed_files": 0,
                "message": "Batch processing failed - no files could be processed"
            })
            logger.error(f"Batch {batch_id} failed - no files processed")
        
        db.commit()
        
    except Exception as e:
        logger.error(f"Batch processing error for {batch_id}: {e}")
        await manager.send_batch_error(batch_id, {
            "error": str(e),
            "message": f"Critical error during batch processing: {str(e)}"
        })
        # Update batch status to failed
        try:
            batch = db.query(Batch).filter(Batch.id == batch_id).first()
            if batch:
                batch.status = "failed"
                batch.error_message = str(e)
                batch.completed_at = datetime.now()
                db.commit()
        except:
            pass
    finally:
        db.close()

@app.get("/api/batches/{batch_id}")
async def get_batch_status(batch_id: str, db: Session = Depends(get_db)):
    """Get batch processing status with comprehensive error handling and Redis caching"""
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
        
        # Get batch from database directly - no cache needed
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
        
        # Status retrieved directly from database
        
        # Get files in batch with error handling
        try:
            files = db.query(DocumentFile).filter(DocumentFile.batch_id == batch_id).all()
            results = db.query(DBScanResult).filter(DBScanResult.batch_id == batch_id).all()
        except Exception as e:
            logger.error(f"Database error retrieving batch details for {batch_id}: {e}")
            # Return basic batch info if detailed query fails
            return {
                "id": batch.id,
                "status": batch.status,
                "total_files": batch.total_files,
                "processed_files": batch.processed_files,
                "created_at": batch.created_at.isoformat(),
                "completed_at": batch.completed_at.isoformat() if batch.completed_at else None,
                "error_message": batch.error_message,
                "files": [],
                "warning": "Detailed file information unavailable due to database error"
            }
        
        # Format file information with error handling
        file_info = []
        for file in files:
            try:
                file_data = {
                    "id": file.id,
                    "filename": file.name,
                    "document_type": file.type,
                    "status": file.status,
                    "file_size": file.file_size,
                    "processing_started_at": file.processing_start.isoformat() if file.processing_start else None,
                    "processing_completed_at": file.processing_end.isoformat() if file.processing_end else None,
                    "processing_time": file.processing_time
                }
                
                # Add result if available
                result = next((r for r in results if r.document_file_id == file.id), None)
                if result:
                    file_data["result_id"] = result.id
                    file_data["confidence"] = result.confidence
                    file_data["ocr_processing_time"] = result.ocr_processing_time
                
                file_info.append(file_data)
                
            except Exception as e:
                logger.error(f"Error processing file info for file {file.id}: {e}")
                # Add basic file info even if there's an error
                file_info.append({
                    "id": file.id,
                    "filename": getattr(file, 'name', 'unknown'),
                    "status": "error",
                    "error_message": f"Error retrieving file information: {str(e)}"
                })
        
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
            "files": file_info,
            "source": "database"
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions (they already have proper error format)
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

@app.get("/api/batches/{batch_id}/results")
async def get_batch_results(batch_id: str, db: Session = Depends(get_db)):
    """Get scan results for a batch directly from database"""
    try:
        
        # Verify batch exists
        batch = db.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            raise HTTPException(status_code=404, detail="Batch not found")
        
        # Get all results for this batch from database
        results = db.query(DBScanResult).filter(DBScanResult.batch_id == batch_id).all()
        
        # Format results for API response
        batch_results = []
        for result in results:
            result_data = {
                "id": result.id,
                "batch_id": result.batch_id,
                "filename": result.original_filename,
                "document_type": result.document_type,
                "extracted_text": result.extracted_text,
                "extracted_data": result.extracted_data,
                "confidence": result.confidence,
                "ocr_engine_used": result.ocr_engine_used,
                "created_at": result.created_at.isoformat(),
                "ocr_processing_time": result.ocr_processing_time
            }
            batch_results.append(result_data)
        
        # Cache the results for future requests
        # Results saved directly in database - no cache needed
        
        logger.info(f"📊 Retrieved {len(batch_results)} results for batch {batch_id} from database and cached")
        return {
            "batch_id": batch_id,
            "results": batch_results,
            "source": "database",
            "retrieved_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting batch results: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving batch results: {str(e)}")

@app.get("/api/batches")
async def get_all_batches(db: Session = Depends(get_db)):
    """Get all batches from database"""
    try:
        batches = db.query(Batch).order_by(desc(Batch.created_at)).all()
        
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
            batch_list.append(batch_data)
        
        return batch_list
        
    except Exception as e:
        logger.error(f"Error getting all batches: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving batches: {str(e)}")

@app.get("/api/results")
async def get_all_results(db: Session = Depends(get_db)):
    """Get all scan results from database"""
    try:
        results = db.query(DBScanResult).order_by(desc(DBScanResult.created_at)).all()
        
        results_list = []
        for result in results:
            result_data = {
                "id": result.id,
                "batch_id": result.batch_id,
                "filename": result.original_filename,
                "document_type": result.document_type,
                "confidence_score": result.confidence,
                "processing_time": result.total_processing_time,
                "created_at": result.created_at.isoformat(),
                "extracted_data": result.extracted_data if isinstance(result.extracted_data, dict) else (json.loads(result.extracted_data) if result.extracted_data else {})
            }
            results_list.append(result_data)
        
        return results_list
        
    except Exception as e:
        logger.error(f"Error getting all results: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving results: {str(e)}")

@app.delete("/api/debug/clear-storage")
async def clear_all_storage(db: Session = Depends(get_db)):
    """Clear all storage - FOR DEBUGGING ONLY"""
    try:
        # Count existing records
        batches_count = db.query(Batch).count()
        results_count = db.query(DBScanResult).count()
        files_count = db.query(DocumentFile).count()
        logs_count = db.query(ProcessingLog).count()
        
        # Clear all tables
        db.query(ProcessingLog).delete()
        db.query(DBScanResult).delete()
        db.query(DocumentFile).delete()
        db.query(Batch).delete()
        db.commit()
        
        logger.warning("Database storage cleared for debugging")
        
        return {
            "message": "Database storage cleared",
            "cleared": {
                "batches": batches_count,
                "results": results_count,
                "files": files_count,
                "logs": logs_count
            }
        }
        
    except Exception as e:
        logger.error(f"Error clearing storage: {e}")
        raise HTTPException(status_code=500, detail=f"Error clearing storage: {str(e)}")

@app.get("/api/results/{result_id}/export/{format}")
async def export_result(result_id: str, format: str, db: Session = Depends(get_db)):
    """Export single scan result to Excel or PDF"""
    try:
        # Validate format
        if format not in ['excel', 'pdf']:
            raise HTTPException(status_code=400, detail="Format must be 'excel' or 'pdf'")
        
        # Get scan result from database
        result = db.query(DBScanResult).filter(DBScanResult.id == result_id).first()
        if not result:
            raise HTTPException(status_code=404, detail="Scan result not found")
        
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
            'created_at': result.created_at.isoformat() if result.created_at else None
        }
        
        # Create filename
        safe_filename = "".join(c for c in (file_info.name if file_info else 'document') 
                               if c.isalnum() or c in (' ', '-', '_')).rstrip()
        export_filename = f"{safe_filename}_scan_result.{format}"
        export_path = EXPORTS_DIR / export_filename
        
        # Create export
        if format == 'excel':
            success = create_enhanced_excel_export(result_data, str(export_path))
        else:  # PDF
            success = create_enhanced_pdf_export(result_data, str(export_path))
        
        if not success:
            raise HTTPException(status_code=500, detail=f"Failed to create {format.upper()} export")
        
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

@app.get("/api/batches/{batch_id}/export/{format}")
async def export_batch(batch_id: str, format: str, db: Session = Depends(get_db)):
    """Export all scan results in a batch to Excel or PDF"""
    try:
        # Validate format
        if format not in ['excel', 'pdf']:
            raise HTTPException(status_code=400, detail="Format must be 'excel' or 'pdf'")
        
        # Get batch info
        batch = db.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            raise HTTPException(status_code=404, detail="Batch not found")
        
        # Get all scan results for this batch
        results = db.query(DBScanResult).filter(DBScanResult.batch_id == batch_id).all()
        if not results:
            raise HTTPException(status_code=404, detail="No scan results found for this batch")
        
        # For batch export, we'll create a combined file with all results
        export_filename = f"batch_{batch_id[:8]}_results.{format}"
        export_path = EXPORTS_DIR / export_filename
        
        if format == 'excel':
            # Create Excel workbook with multiple sheets
            from openpyxl import Workbook
            wb = Workbook()
            
            # Remove default sheet
            wb.remove(wb.active)
            
            # Create summary sheet
            summary_ws = wb.create_sheet("Batch Summary")
            summary_ws['A1'] = "Batch Export Summary"
            summary_ws['A3'] = "Batch ID:"
            summary_ws['B3'] = batch_id
            summary_ws['A4'] = "Total Files:"
            summary_ws['B4'] = len(results)
            summary_ws['A5'] = "Export Date:"
            summary_ws['B5'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Add sheet for each result
            for i, result in enumerate(results):
                file_info = db.query(DocumentFile).filter(DocumentFile.id == result.document_file_id).first()
                sheet_name = f"File_{i+1}"[:31]  # Excel sheet name limit
                
                ws = wb.create_sheet(sheet_name)
                
                # Add file info
                ws['A1'] = "Document Information"
                ws['A3'] = "Filename:"
                ws['B3'] = file_info.name if file_info else 'Unknown'
                ws['A4'] = "Document Type:"
                ws['B4'] = result.document_type or 'Unknown'
                ws['A5'] = "Confidence:"
                ws['B5'] = f"{(result.confidence or 0)*100:.1f}%"
                
                # Add raw text
                extracted_data = result.extracted_data or {}
                raw_text = extracted_data.get('raw_text', result.extracted_text or '')
                
                ws['A7'] = "Raw OCR Text:"
                if raw_text:
                    lines = raw_text.split('\n')
                    for j, line in enumerate(lines[:100]):  # Limit lines
                        if line.strip():
                            ws[f'A{8+j}'] = line.strip()
            
            wb.save(str(export_path))
            
        else:  # PDF - combine all results
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
            from reportlab.lib.styles import getSampleStyleSheet
            
            doc = SimpleDocTemplate(str(export_path), pagesize=A4)
            styles = getSampleStyleSheet()
            story = []
            
            # Title page
            story.append(Paragraph(f"Batch Scan Results", styles['Title']))
            story.append(Spacer(1, 12))
            story.append(Paragraph(f"Batch ID: {batch_id}", styles['Normal']))
            story.append(Paragraph(f"Total Files: {len(results)}", styles['Normal']))
            story.append(Paragraph(f"Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
            story.append(PageBreak())
            
            # Add each result
            for i, result in enumerate(results):
                file_info = db.query(DocumentFile).filter(DocumentFile.id == result.document_file_id).first()
                
                story.append(Paragraph(f"Document {i+1}: {file_info.name if file_info else 'Unknown'}", styles['Heading1']))
                story.append(Spacer(1, 12))
                
                story.append(Paragraph(f"Document Type: {result.document_type or 'Unknown'}", styles['Normal']))
                story.append(Paragraph(f"Confidence: {(result.confidence or 0)*100:.1f}%", styles['Normal']))
                story.append(Spacer(1, 12))
                
                story.append(Paragraph("Raw OCR Text:", styles['Heading2']))
                story.append(Spacer(1, 6))
                
                extracted_data = result.extracted_data or {}
                raw_text = extracted_data.get('raw_text', result.extracted_text or '')
                
                if raw_text:
                    lines = raw_text.split('\n')
                    for line in lines[:50]:  # Limit lines per document
                        if line.strip():
                            safe_line = line.strip().replace('<', '&lt;').replace('>', '&gt;')
                            story.append(Paragraph(safe_line, styles['Normal']))
                else:
                    story.append(Paragraph("No text extracted", styles['Normal']))
                
                if i < len(results) - 1:  # Add page break except for last document
                    story.append(PageBreak())
            
            doc.build(story)
        
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

if __name__ == "__main__":
    logger.info("Starting AI Document Scanner API with MySQL database")
    uvicorn.run(app, host="0.0.0.0", port=8000)