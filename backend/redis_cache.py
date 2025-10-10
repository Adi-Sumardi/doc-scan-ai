"""
Redis Cache Manager for Document Processing Results
Provides caching for OCR results, processed data, and frequently accessed data
"""

import redis
import json
import hashlib
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import pickle

logger = logging.getLogger(__name__)

class RedisCache:
    """Redis cache manager for document processing optimization"""
    
    def __init__(self, host='localhost', port=6379, db=0, decode_responses=False):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.Redis(
                host=host, 
                port=port, 
                db=db, 
                decode_responses=decode_responses
            )
            # Test connection
            self.redis_client.ping()
            logger.info("✅ Redis connection established successfully")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            self.redis_client = None
    
    def is_connected(self) -> bool:
        """Check if Redis is connected and available"""
        if not self.redis_client:
            return False
        try:
            self.redis_client.ping()
            return True
        except:
            return False
    
    def _generate_key(self, prefix: str, *args) -> str:
        """Generate consistent cache key"""
        key_data = ":".join(str(arg) for arg in args)
        key_hash = hashlib.md5(key_data.encode()).hexdigest()[:8]
        return f"{prefix}:{key_hash}:{key_data}"
    
    def _serialize_data(self, data: Any) -> bytes:
        """Serialize data for Redis storage"""
        return pickle.dumps(data)
    
    def _deserialize_data(self, data: bytes) -> Any:
        """Deserialize data from Redis"""
        return pickle.loads(data)
    
    # OCR Results Caching
    def cache_ocr_result(self, file_hash: str, ocr_result: Dict[str, Any], ttl: int = 3600):
        """Cache OCR processing result"""
        if not self.is_connected():
            return False
        
        try:
            key = self._generate_key("ocr", file_hash)
            serialized_data = self._serialize_data({
                "result": ocr_result,
                "cached_at": datetime.now(timezone.utc).isoformat(),
                "file_hash": file_hash
            })
            
            self.redis_client.setex(key, ttl, serialized_data)
            logger.info(f"🔄 Cached OCR result for file hash: {file_hash[:8]}...")
            return True
        except Exception as e:
            logger.error(f"❌ Error caching OCR result: {e}")
            return False
    
    def get_ocr_result(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached OCR result"""
        if not self.is_connected():
            return None
        
        try:
            key = self._generate_key("ocr", file_hash)
            cached_data = self.redis_client.get(key)
            
            if cached_data:
                data = self._deserialize_data(cached_data)
                logger.info(f"✅ Retrieved cached OCR result for file hash: {file_hash[:8]}...")
                return data["result"]
            
            return None
        except Exception as e:
            logger.error(f"❌ Error retrieving OCR result: {e}")
            return None
    
    # Processed Document Data Caching
    def cache_processed_document(self, batch_id: str, file_id: str, processed_data: Dict[str, Any], ttl: int = 7200):
        """Cache processed document data"""
        if not self.is_connected():
            return False
        
        try:
            key = self._generate_key("processed", batch_id, file_id)
            serialized_data = self._serialize_data({
                "data": processed_data,
                "cached_at": datetime.now(timezone.utc).isoformat(),
                "batch_id": batch_id,
                "file_id": file_id
            })
            
            self.redis_client.setex(key, ttl, serialized_data)
            logger.info(f"🔄 Cached processed document: {batch_id[:8]}.../{file_id[:8]}...")
            return True
        except Exception as e:
            logger.error(f"❌ Error caching processed document: {e}")
            return False
    
    def get_processed_document(self, batch_id: str, file_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached processed document"""
        if not self.is_connected():
            return None
        
        try:
            key = self._generate_key("processed", batch_id, file_id)
            cached_data = self.redis_client.get(key)
            
            if cached_data:
                data = self._deserialize_data(cached_data)
                logger.info(f"✅ Retrieved cached processed document: {batch_id[:8]}.../{file_id[:8]}...")
                return data["data"]
            
            return None
        except Exception as e:
            logger.error(f"❌ Error retrieving processed document: {e}")
            return None
    
    # Batch Results Caching
    def cache_batch_results(self, batch_id: str, results: List[Dict[str, Any]], ttl: int = 3600):
        """Cache complete batch results"""
        if not self.is_connected():
            return False
        
        try:
            key = self._generate_key("batch_results", batch_id)
            serialized_data = self._serialize_data({
                "results": results,
                "cached_at": datetime.now(timezone.utc).isoformat(),
                "batch_id": batch_id,
                "count": len(results)
            })
            
            self.redis_client.setex(key, ttl, serialized_data)
            logger.info(f"🔄 Cached batch results: {batch_id[:8]}... ({len(results)} files)")
            return True
        except Exception as e:
            logger.error(f"❌ Error caching batch results: {e}")
            return False
    
    def get_batch_results(self, batch_id: str) -> Optional[List[Dict[str, Any]]]:
        """Retrieve cached batch results"""
        if not self.is_connected():
            return None
        
        try:
            key = self._generate_key("batch_results", batch_id)
            cached_data = self.redis_client.get(key)
            
            if cached_data:
                data = self._deserialize_data(cached_data)
                logger.info(f"✅ Retrieved cached batch results: {batch_id[:8]}... ({data['count']} files)")
                return data["results"]
            
            return None
        except Exception as e:
            logger.error(f"❌ Error retrieving batch results: {e}")
            return None
    
    # Document Type Templates Caching
    def cache_document_template(self, doc_type: str, template_data: Dict[str, Any], ttl: int = 86400):
        """Cache document type processing templates"""
        if not self.is_connected():
            return False
        
        try:
            key = self._generate_key("template", doc_type)
            serialized_data = self._serialize_data({
                "template": template_data,
                "cached_at": datetime.now(timezone.utc).isoformat(),
                "doc_type": doc_type
            })
            
            self.redis_client.setex(key, ttl, serialized_data)
            logger.info(f"🔄 Cached document template: {doc_type}")
            return True
        except Exception as e:
            logger.error(f"❌ Error caching document template: {e}")
            return False
    
    def get_document_template(self, doc_type: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached document template"""
        if not self.is_connected():
            return None
        
        try:
            key = self._generate_key("template", doc_type)
            cached_data = self.redis_client.get(key)
            
            if cached_data:
                data = self._deserialize_data(cached_data)
                logger.info(f"✅ Retrieved cached document template: {doc_type}")
                return data["template"]
            
            return None
        except Exception as e:
            logger.error(f"❌ Error retrieving document template: {e}")
            return None
    
    # Batch Status Caching for Performance
    def cache_batch_status(self, batch_id: str, status_data: Dict[str, Any], ttl: int = 300):
        """Cache batch status for frequent polling"""
        if not self.is_connected():
            return False
        
        try:
            key = self._generate_key("batch_status", batch_id)
            serialized_data = self._serialize_data({
                "status": status_data,
                "cached_at": datetime.now(timezone.utc).isoformat(),
                "batch_id": batch_id
            })
            
            self.redis_client.setex(key, ttl, serialized_data)
            return True
        except Exception as e:
            logger.error(f"❌ Error caching batch status: {e}")
            return False
    
    def get_batch_status(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached batch status"""
        if not self.is_connected():
            return None
        
        try:
            key = self._generate_key("batch_status", batch_id)
            cached_data = self.redis_client.get(key)
            
            if cached_data:
                data = self._deserialize_data(cached_data)
                return data["status"]
            
            return None
        except Exception as e:
            logger.error(f"❌ Error retrieving batch status: {e}")
            return None
    
    # Cache Management
    def invalidate_batch_cache(self, batch_id: str):
        """Invalidate all cache entries for a specific batch"""
        if not self.is_connected():
            return False
        
        try:
            patterns = [
                f"*batch_results*{batch_id}*",
                f"*batch_status*{batch_id}*",
                f"*processed*{batch_id}*"
            ]
            
            deleted_count = 0
            for pattern in patterns:
                keys = self.redis_client.keys(pattern)
                if keys:
                    deleted_count += self.redis_client.delete(*keys)
            
            logger.info(f"🗑️ Invalidated {deleted_count} cache entries for batch: {batch_id[:8]}...")
            return True
        except Exception as e:
            logger.error(f"❌ Error invalidating batch cache: {e}")
            return False
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get Redis cache statistics"""
        if not self.is_connected():
            return {"connected": False}
        
        try:
            info = self.redis_client.info()
            
            # Count keys by prefix
            key_counts = {}
            prefixes = ["ocr", "processed", "batch_results", "template", "batch_status"]
            
            for prefix in prefixes:
                pattern = f"{prefix}:*"
                keys = self.redis_client.keys(pattern)
                key_counts[prefix] = len(keys)
            
            return {
                "connected": True,
                "redis_version": info.get("redis_version", "unknown"),
                "used_memory": info.get("used_memory_human", "unknown"),
                "total_connections": info.get("total_connections_received", 0),
                "key_counts": key_counts,
                "total_keys": sum(key_counts.values()),
                "uptime_seconds": info.get("uptime_in_seconds", 0)
            }
        except Exception as e:
            logger.error(f"❌ Error getting cache stats: {e}")
            return {"connected": False, "error": str(e)}
    
    def clear_all_cache(self):
        """Clear all cache entries (use with caution)"""
        if not self.is_connected():
            return False
        
        try:
            self.redis_client.flushdb()
            logger.warning("🗑️ All cache entries cleared")
            return True
        except Exception as e:
            logger.error(f"❌ Error clearing cache: {e}")
            return False

# Global cache instance
cache = RedisCache()