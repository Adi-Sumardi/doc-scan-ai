"""
Health & Monitoring Router
Handles health checks, cache statistics, and system monitoring
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import logging

from database import User, SessionLocal
from auth import get_current_active_user
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

# Redis cache is optional
try:
    from redis_cache import cache
    REDIS_AVAILABLE = True
except ImportError:
    cache = None
    REDIS_AVAILABLE = False

# Create router
router = APIRouter(prefix="/api", tags=["health"])

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


# ==================== Health Check Endpoints ====================

@router.post("/heartbeat")
async def heartbeat():
    """Health check endpoint for production validation"""
    try:
        # Lazy import to avoid heavy module load at startup
        from ai_processor import get_ocr_processor
        ocr_processor = get_ocr_processor()
        ocr_info = ocr_processor.get_ocr_system_info()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ocr_system": ocr_info,
            "message": "Production OCR system ready"
        }
    except Exception as e:
        return {
            "status": "unhealthy", 
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@router.get("/health")
async def health_check():
    """Enhanced health check with optional cache status"""
    health_data = {
        "status": "healthy", 
        "service": "doc-scan-ai", 
        "timestamp": datetime.now(timezone.utc).isoformat(),
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


# ==================== Cache Management Endpoints ====================

@router.get("/cache/stats")
async def get_cache_statistics(current_user: User = Depends(get_current_active_user)):
    """Get comprehensive Redis cache statistics (requires authentication)"""
    if not REDIS_AVAILABLE or not cache:
        raise HTTPException(status_code=503, detail="Cache service not available")
    return cache.get_cache_stats()


@router.post("/cache/clear")
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
