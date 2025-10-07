"""
FastAPI Main Application (Refactored)
Minimal entry point that registers all routers
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import uvicorn
import logging
from pathlib import Path

# Import config first
from config import settings, get_upload_dir, get_results_dir, get_exports_dir

# Import routers
from routers import auth, admin, health, documents, batches, exports

# Import database initialization
from database import Base, engine

# Apply nest_asyncio for gRPC compatibility
import nest_asyncio
nest_asyncio.apply()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== FastAPI App Setup ====================

app = FastAPI(title="AI Document Scanner API", version="2.0.0")

# Rate Limiting Setup
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Create database tables
Base.metadata.create_all(bind=engine)

# ==================== Middleware ====================

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Accept",
        "Accept-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
    ],
    max_age=600,
)

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)
    
    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    if settings.environment == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
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
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    
    return response

# ==================== Environment Validation ====================

def validate_environment():
    """Validate required directories and services"""
    from sqlalchemy import text
    from database import SessionLocal
    from ai_processor import RealOCRProcessor
    
    # Check storage directories
    storage_dirs = {
        'uploads': Path(get_upload_dir()),
        'results': Path(get_results_dir()),
        'exports': Path(get_exports_dir())
    }
    
    for name, dir_path in storage_dirs.items():
        try:
            dir_path.mkdir(exist_ok=True)
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

# Run validation
try:
    validate_environment()
except Exception as e:
    logger.critical(f"❌ Environment validation failed: {e}")
    raise

# Storage directories
UPLOAD_DIR = Path(get_upload_dir())
RESULTS_DIR = Path(get_results_dir())
EXPORTS_DIR = Path(get_exports_dir())

# Initialize batch processor
from batch_processor import BatchProcessor
batch_processor = BatchProcessor()

# ==================== Register Routers ====================

# Root endpoint
@app.get("/")
async def root():
    """API root endpoint"""
    return {"message": "AI Document Scanner API", "version": "2.0.0", "status": "running"}

# Register routers
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(health.router)
app.include_router(documents.router)
app.include_router(batches.router)
app.include_router(exports.router)

# ==================== WebSocket Routes ====================
# WebSocket routes must be registered directly (not through router)

from fastapi import WebSocket
from routers.health import websocket_general_handler, websocket_batch_handler

@app.websocket("/ws")
async def websocket_general(websocket: WebSocket):
    """WebSocket endpoint for general system updates"""
    await websocket_general_handler(websocket)

@app.websocket("/ws/batch/{batch_id}")
async def websocket_batch(websocket: WebSocket, batch_id: str):
    """WebSocket endpoint for specific batch progress updates"""
    await websocket_batch_handler(websocket, batch_id)

# ==================== Run Application ====================

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
