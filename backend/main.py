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
try:  # Support running as package (`backend.main`) and as script (`python main.py`)
    from config import settings, get_upload_dir, get_results_dir, get_exports_dir
    from routers import auth, admin, health, documents, batches, exports, reconciliation_ppn
    from database import Base, engine
except ModuleNotFoundError:  # pragma: no cover - fallback for package context
    from .config import settings, get_upload_dir, get_results_dir, get_exports_dir
    from .routers import auth, admin, health, documents, batches, exports, reconciliation_ppn
    from .database import Base, engine

# Apply nest_asyncio for gRPC compatibility (disabled for uvloop)
# import nest_asyncio
# nest_asyncio.apply()

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
    
    # CSP: restrict connect-src in production
    connect_src = "'self'"
    if settings.environment != "production":
        connect_src += " http://localhost:* http://127.0.0.1:*"

    csp_policy = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        f"connect-src {connect_src}; "
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
    try:
        from database import SessionLocal
        from ai_processor import RealOCRProcessor
    except ModuleNotFoundError:  # pragma: no cover - package context fallback
        from .database import SessionLocal
        from .ai_processor import RealOCRProcessor
    
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

# Initialize batch processor (import ensures module setup)
try:
    from batch_processor import batch_processor
except ModuleNotFoundError:  # pragma: no cover - package context fallback
    from .batch_processor import batch_processor

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
app.include_router(reconciliation_ppn.router)

# ==================== Run Application ====================

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
