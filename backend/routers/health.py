"""
Health & Monitoring Router
Handles health checks, cache statistics, WebSocket connections, and system monitoring
"""

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Request
from sqlalchemy.orm import Session
from datetime import datetime
import json
import logging

from models import User
from auth import get_current_active_user
from ai_processor import RealOCRProcessor
from websocket_manager import manager
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


@router.get("/health")
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


# ==================== WebSocket Endpoints ====================

# Note: WebSocket routes need to be registered without the router prefix
# They should be added directly to the app in main.py

async def websocket_general_handler(websocket: WebSocket):
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


async def websocket_batch_handler(websocket: WebSocket, batch_id: str):
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


@router.get("/connections")
async def get_connection_stats(current_user: User = Depends(get_current_active_user)):
    """Get WebSocket connection statistics (requires authentication)"""
    return manager.get_connection_stats()
