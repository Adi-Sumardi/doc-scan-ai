from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Depends, WebSocket, WebSocketDisconnect, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
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
from sqlalchemy import desc, and_, text

# Import config first to load environment variables
from config import settings, get_upload_dir, get_results_dir, get_exports_dir
# Import our modules
from ai_processor import process_document_ai, create_enhanced_excel_export, create_enhanced_pdf_export, RealOCRProcessor, create_batch_excel_export, create_batch_pdf_export
from models import BatchResponse, ScanResult, BatchStatus, DocumentFile as DocumentFileModel, UserRegister, UserLogin, UserResponse, Token
from database import SessionLocal, engine, Base, Batch, DocumentFile, ScanResult as DBScanResult, ProcessingLog, SystemMetrics, get_db, User
from websocket_manager import manager
from auth import get_password_hash, verify_password, create_access_token, get_current_user, get_current_active_user
from datetime import timedelta
from audit_logger import (
    log_login_success, log_login_failure, log_registration,
    log_password_reset, log_user_status_change, log_rate_limit_exceeded
)
# Redis cache is optional - only for stats and health monitoring
try:
    from redis_cache import cache
    REDIS_AVAILABLE = True
except ImportError:
    cache = None
    REDIS_AVAILABLE = False
# Import the robust security validator
from security import file_security, SecurityValidator
import logging

# Apply nest_asyncio patch to allow nested event loops (for gRPC compatibility)
import nest_asyncio
nest_asyncio.apply()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Request size limiting middleware
class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to limit request body size (max 10MB)"""
    MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB in bytes
    
    async def dispatch(self, request: Request, call_next):
        if request.method in ["POST", "PUT", "PATCH"]:
            content_length = request.headers.get("content-length")
            if content_length:
                content_length = int(content_length)
                if content_length > self.MAX_REQUEST_SIZE:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "detail": f"Request entity too large. Maximum size is {self.MAX_REQUEST_SIZE / (1024 * 1024):.0f}MB"
                        }
                    )
        return await call_next(request)

app = FastAPI(title="AI Document Scanner API", version="1.0.0")

# Rate Limiting Setup
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Create database tables
Base.metadata.create_all(bind=engine)

# CORS middleware - Security hardened
# Only allow specific origins (no wildcards)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,  # Specific origins only from .env
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],  # Explicit methods
    allow_headers=[
        "Accept",
        "Accept-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
    ],  # Only necessary headers
    max_age=600,  # Cache preflight requests for 10 minutes
)

# Add request size limiting middleware
app.add_middleware(RequestSizeLimitMiddleware)

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)
    
    # Prevent MIME type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    
    # Prevent clickjacking attacks
    response.headers["X-Frame-Options"] = "DENY"
    
    # Enable XSS protection
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    # Enforce HTTPS (if in production)
    if settings.environment == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    # Content Security Policy
    csp_policy = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "connect-src 'self' http://localhost:* http://127.0.0.1:*; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    response.headers["Content-Security-Policy"] = csp_policy
    
    # Referrer policy
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    # Permissions policy (restrict browser features)
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    
    return response

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
            db.execute(text("SELECT 1"))
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

@app.get("/")
async def root():
    return {"message": "AI Document Scanner API", "status": "online"}

# ==================== Authentication Endpoints ====================

@app.post("/api/register", response_model=UserResponse)
@limiter.limit("5/minute")  # Max 5 registration attempts per minute per IP
async def register(request: Request, user: UserRegister, db: Session = Depends(get_db)):
    """Register a new user with input validation and password strength check"""
    # Validate username (prevent XSS and SQL injection)
    validated_username = SecurityValidator.validate_username(user.username)
    
    # Validate email format
    validated_email = SecurityValidator.validate_email(user.email)
    
    # Validate password strength
    SecurityValidator.validate_password_strength(user.password)
    
    # Sanitize full name (prevent XSS)
    validated_full_name = SecurityValidator.sanitize_input(user.full_name, max_length=100)
    
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == validated_username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Check if email already exists
    existing_email = db.query(User).filter(User.email == validated_email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    db_user = User(
        id=str(uuid.uuid4()),
        username=validated_username,
        email=validated_email,
        hashed_password=get_password_hash(user.password),
        full_name=validated_full_name,
        is_active=True,
        is_admin=False,
        created_at=datetime.utcnow()
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Log successful registration
    log_registration(validated_username, request.client.host, "success")
    logger.info(f"New user registered: {validated_username}")
    return db_user

@app.post("/api/login", response_model=Token)
@limiter.limit("10/minute")  # Max 10 login attempts per minute per IP
async def login(request: Request, user: UserLogin, db: Session = Depends(get_db)):
    """Login and get JWT token with rate limiting"""
    # Find user by username
    db_user = db.query(User).filter(User.username == user.username).first()
    
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        # Log failed login attempt
        log_login_failure(user.username, request.client.host, "invalid_credentials")
        logger.warning(f"Failed login attempt for username: {user.username} from IP: {request.client.host}")
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not db_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    # Update last login
    db_user.last_login = datetime.utcnow()
    db.commit()
    
    # Create access token
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": db_user.id, "username": db_user.username},
        expires_delta=access_token_expires
    )
    
    # Log successful login
    log_login_success(db_user.username, request.client.host)
    logger.info(f"User logged in: {user.username}")
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return current_user

# ==================== Admin Endpoints ====================

async def get_current_admin_user(current_user: User = Depends(get_current_active_user)):
    """Dependency to verify admin access"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

async def get_user_by_id_from_path(user_id: str, db: Session = Depends(get_db)):
    """Dependency to get a user by ID from the URL path and handle not found cases."""
    # Centralized validation
    if SecurityValidator.check_sql_injection(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.get("/api/admin/users")
async def get_all_users(
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get all users with their activity stats (Admin only)"""
    users = db.query(User).all()
    
    # Get activity stats for each user
    user_list = []
    for user in users:
        # Count batches created by user
        batch_count = db.query(Batch).filter(Batch.user_id == user.id).count()
        
        # Get latest batch
        latest_batch = db.query(Batch).filter(Batch.user_id == user.id).order_by(Batch.created_at.desc()).first()
        
        user_data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "created_at": user.created_at,
            "last_login": user.last_login,
            "total_batches": batch_count,
            "last_activity": latest_batch.created_at if latest_batch else None
        }
        user_list.append(user_data)
    
    return user_list

@app.get("/api/admin/users/{user_id}/activities")
async def get_user_activities(
    user: User = Depends(get_user_by_id_from_path),
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get detailed activity history for a specific user (Admin only)"""
    # Get all batches by user
    batches = db.query(Batch).filter(Batch.user_id == user.id).order_by(Batch.created_at.desc()).all()
    
    batch_list = []
    for batch in batches:
        # Get file count for this batch
        files = db.query(DocumentFile).filter(DocumentFile.batch_id == batch.id).all()
        
        batch_data = {
            "id": batch.id,
            "status": batch.status,
            "created_at": batch.created_at,
            "completed_at": batch.completed_at,
            "file_count": len(files),  # Changed from total_files to file_count
            "processed_files": batch.processed_files,
            "file_names": [f.name for f in files[:5]],  # First 5 files
            "processing_time": batch.total_processing_time
        }
        batch_list.append(batch_data)
    
    return {
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "last_login": user.last_login
        },
        "batches": batch_list,  # Changed from activities to batches
        "total_batches": len(batch_list)
    }

@app.patch("/api/admin/users/{user_id}/status")
async def update_user_status(
    is_active: bool,
    user: User = Depends(get_user_by_id_from_path),
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update user active status (Admin only)"""
    # Prevent admin from deactivating themselves
    if user.id == current_admin.id:
        raise HTTPException(status_code=400, detail="Cannot change your own status")
    
    user.is_active = is_active
    db.commit()
    
    # Audit log for admin action
    log_user_status_change(
        admin=current_admin.username,
        target=user.username,
        new_status="active" if is_active else "inactive",
        ip="admin_action"  # Could get real IP if Request is passed
    )
    
    logger.info(f"Admin {current_admin.username} changed user {user.username} status to {'active' if is_active else 'inactive'}")
    
    return {"message": f"User {user.username} has been {'activated' if is_active else 'deactivated'}"}

@app.post("/api/admin/users/{user_id}/reset-password")
async def reset_user_password(
    new_password: str,
    user: User = Depends(get_user_by_id_from_path),
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Reset user password (Admin only) with password strength validation"""
    # Validate password strength
    SecurityValidator.validate_password_strength(new_password)
    
    # Hash new password
    from auth import get_password_hash
    user.hashed_password = get_password_hash(new_password)
    db.commit()
    
    # Audit log for admin action
    log_password_reset(
        admin=current_admin.username,
        target=user.username,
        ip="admin_action"  # Could get real IP if Request is passed
    )
    
    logger.info(f"Admin {current_admin.username} reset password for user {user.username}")
    
    return {
        "message": f"Password for user {user.username} has been reset successfully",
        "username": user.username,
        "email": user.email
    }

@app.post("/api/admin/users/{user_id}/generate-temp-password")
async def generate_temp_password(
    user: User = Depends(get_user_by_id_from_path),
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Generate and set a temporary password for user (Admin only)"""
    import secrets
    import string
    
    # Generate secure random password (8 chars: letters, digits, special chars)
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    temp_password = ''.join(secrets.choice(alphabet) for i in range(10))
    
    # Hash and set new password
    from auth import get_password_hash
    user.hashed_password = get_password_hash(temp_password)
    db.commit()
    
    logger.info(f"Admin {current_admin.username} generated temporary password for user {user.username}")
    
    return {
        "message": f"Temporary password generated for user {user.username}",
        "username": user.username,
        "email": user.email,
        "temp_password": temp_password,
        "note": "This password is shown only once. Please share it securely with the user."
    }

@app.get("/api/admin/dashboard/stats")
async def get_dashboard_stats(
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get overall system statistics (Admin only)"""
    from sqlalchemy import func
    
    # Count users
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    admin_users = db.query(User).filter(User.is_admin == True).count()
    
    # Count batches
    total_batches = db.query(Batch).count()
    completed_batches = db.query(Batch).filter(Batch.status == "completed").count()
    processing_batches = db.query(Batch).filter(Batch.status == "processing").count()
    failed_batches = db.query(Batch).filter(Batch.status == "error").count()
    
    # Count files
    total_files = db.query(DocumentFile).count()
    
    # Recent activity (last 7 days)
    from datetime import datetime, timedelta
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_batches = db.query(Batch).filter(Batch.created_at >= seven_days_ago).count()
    recent_users = db.query(User).filter(User.created_at >= seven_days_ago).count()
    
    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "inactive": total_users - active_users,
            "admins": admin_users,
            "new_this_week": recent_users
        },
        "batches": {
            "total": total_batches,
            "completed": completed_batches,
            "processing": processing_batches,
            "failed": failed_batches,
            "this_week": recent_batches
        },
        "files": {
            "total": total_files
        }
    }

# ==================== Public Endpoints ====================

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
async def get_cache_statistics(current_user: User = Depends(get_current_active_user)):
    """Get comprehensive Redis cache statistics (requires authentication)"""
    if not REDIS_AVAILABLE or not cache:
        raise HTTPException(status_code=503, detail="Cache service not available")
    return cache.get_cache_stats()

@app.post("/api/cache/clear")
@limiter.limit("5/minute")  # Rate limit to prevent DoS
async def clear_cache(request: Request, current_user: User = Depends(get_current_active_user)):
    """Clear all cache entries (requires authentication, rate limited)"""
    if not REDIS_AVAILABLE or not cache:
        raise HTTPException(status_code=503, detail="Cache service not available")
    
    # Only admin can clear cache
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if cache.clear_all_cache():
        logger.warning(f"Cache cleared by admin: {current_user.username}")
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
async def get_connection_stats(current_user: User = Depends(get_current_active_user)):
    """Get WebSocket connection statistics (requires authentication)"""
    return manager.get_connection_stats()

@app.post("/api/upload", response_model=BatchResponse)
async def upload_documents(
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
                created_at=datetime.now(),
                user_id=current_user.id
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
                # Make validation case-insensitive and more robust
                valid_types = ["invoice", "receipt", "id_card", "passport", "driver_license", "other",
                               "faktur_pajak", "pph21", "pph23", "rekening_koran", "spt", "npwp", "faktur"]
                
                # Normalize the input document type for validation AND storage
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
                
                # Perform security validation (using already-read content)
                validation_result = await file_security.validate_file(file)
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
                
                # Save file with comprehensive error handling (reuse content)
                safe_filename = f"{i:03d}_{SecurityValidator.validate_filename(file.filename)}"
                file_path = batch_dir / safe_filename
                
                try:
                    async with aiofiles.open(file_path, 'wb') as f:
                        # Reuse content from first read - NO DOUBLE READ!
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
                        name=file.filename, # Use original filename for display
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

                # Ensure extracted_data is a dictionary with proper validation
                extracted_data = result.get("extracted_data", {})
                if isinstance(extracted_data, str):
                    try:
                        parsed_data = json.loads(extracted_data)
                        # Validate that parsed result is actually a dict
                        if isinstance(parsed_data, dict):
                            extracted_data = parsed_data
                        else:
                            logger.warning(f"Parsed data is not a dict for {db_file.name}. Type: {type(parsed_data)}")
                            extracted_data = {"raw_text": str(extracted_data), "parse_error": "Invalid type after parsing"}
                    except json.JSONDecodeError as e:
                        logger.warning(f"JSON decode failed for {db_file.name}: {e}. Storing as raw text.")
                        extracted_data = {"raw_text": extracted_data, "parse_error": str(e)}
                    except Exception as e:
                        logger.error(f"Unexpected error parsing extracted_data for {db_file.name}: {e}")
                        extracted_data = {"raw_text": str(extracted_data), "parse_error": f"Unexpected: {str(e)}"}
                elif not isinstance(extracted_data, dict):
                    # Handle any non-dict, non-string types
                    logger.warning(f"extracted_data has unexpected type {type(extracted_data)} for {db_file.name}")
                    extracted_data = {"raw_text": str(extracted_data), "type_error": str(type(extracted_data))}
                
                # Create scan result in database
                scan_result = DBScanResult(
                    id=str(uuid.uuid4()),
                    batch_id=batch_id,
                    document_file_id=db_file.id,
                    document_type=db_file.type,
                    original_filename=db_file.name,
                    extracted_text=result.get("raw_text", ""), # Use raw_text from the result
                    extracted_data=extracted_data,
                    confidence=result.get("confidence", 0.0),
                    ocr_engine_used=result.get("extracted_data", {}).get("processing_info", {}).get("parsing_method", "Google Document AI"),
                    total_processing_time=result.get("processing_time", 0.0) # Use total_processing_time
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
                    "confidence": result.get("confidence", 0.0) * 100, # Send as percentage
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
                
                logger.info(f"Successfully processed {db_file.name} with confidence {result.get('confidence', 0.0)*100:.2f}%")
                
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
async def get_batch_status(batch_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
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
async def get_batch_results(batch_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
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
        return batch_results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting batch results: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving batch results: {str(e)}")

@app.get("/api/batches")
async def get_all_batches(db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    """Get all batches from database for current user"""
    try:
        # Filter batches by user_id
        batches = db.query(Batch).filter(Batch.user_id == current_user.id).order_by(desc(Batch.created_at)).all()
        
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
        
        return batch_list if batch_list is not None else []
        
    except Exception as e:
        logger.error(f"Error getting all batches: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving batches: {str(e)}")

@app.get("/api/results")
async def get_all_results(db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    """Get all scan results from database for current user"""
    try:
        # Join with Batch to filter by user_id
        results = db.query(DBScanResult).join(Batch, DBScanResult.batch_id == Batch.id).filter(Batch.user_id == current_user.id).order_by(desc(DBScanResult.created_at)).all()
        
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
        
        return results_list if results_list is not None else []
        
    except Exception as e:
        logger.error(f"Error getting all results: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving results: {str(e)}")

# DEBUG ENDPOINT REMOVED FOR PRODUCTION SECURITY
# This endpoint was removed because it allowed unauthorized users to delete all database data
# If you need this functionality for development, add it back with admin authentication:
# @app.delete("/api/debug/clear-storage")
# async def clear_all_storage(db: Session = Depends(get_db), current_user: User = Depends(get_current_admin_user)):
#     ... implementation ...

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
async def export_batch(batch_id: str, format: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
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
        
        # Optimization: Fetch all file info in one query to avoid N+1 problem
        file_ids = [r.document_file_id for r in results]
        file_infos = db.query(DocumentFile).filter(DocumentFile.id.in_(file_ids)).all()
        file_info_map = {f.id: f for f in file_infos}

        # For batch export, we'll create a combined file with all results
        export_filename = f"batch_{batch_id[:8]}_results.{format}"
        export_path = EXPORTS_DIR / export_filename
        
        if format == 'excel':
            # Create Excel workbook with multiple sheets
            from openpyxl import Workbook
            results_data = [
                {**r.__dict__, 'original_filename': file_info_map.get(r.document_file_id).name if file_info_map.get(r.document_file_id) else 'Unknown'}
                for r in results
            ]
            success = create_batch_excel_export(batch_id, results_data, str(export_path))
            
        else:  # PDF - combine all results
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
            from reportlab.lib.styles import getSampleStyleSheet
            results_data = [
                {**r.__dict__, 'original_filename': file_info_map.get(r.document_file_id).name if file_info_map.get(r.document_file_id) else 'Unknown'}
                for r in results
            ]
            success = create_batch_pdf_export(batch_id, results_data, str(export_path))

        if not success:
            raise HTTPException(status_code=500, detail=f"Failed to create batch {format.upper()} export")
        
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

@app.patch("/api/results/{result_id}")
async def update_result(
    result_id: str, 
    updated_data: dict,
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_active_user)
):
    """Update edited OCR result data"""
    try:
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
        
        # Update timestamp
        result.updated_at = datetime.utcnow()
        
        # Commit to database
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
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating result {result_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update result: {str(e)}")

@app.get("/api/results/{result_id}/file")
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
        
        # Construct file path
        file_path = Path(doc_file.file_path)
        
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
            '.bmp': 'image/bmp'
        }
        media_type = media_type_map.get(file_extension, 'application/octet-stream')
        
        # Return file
        return FileResponse(
            path=str(file_path),
            filename=doc_file.name,
            media_type=media_type
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving file for result {result_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to serve file: {str(e)}")

if __name__ == "__main__":
    logger.info("Starting AI Document Scanner API with MySQL database")
    uvicorn.run(app, host="0.0.0.0", port=8000)