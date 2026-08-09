"""
Redis-based caching service for performance optimization
"""
import json
import logging
import hashlib
from typing import Any, Optional, Dict, List
from datetime import timedelta
import redis.asyncio as redis
from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Async Redis cache service for performance optimization"""
    
    def __init__(self):
        self.redis_client = None
        self._connection_pool = None
    
    async def connect(self):
        """Initialize Redis connection pool"""
        if self.redis_client is None:
            try:
                self._connection_pool = redis.ConnectionPool.from_url(
                    settings.REDIS_URL,
                    max_connections=20,
                    retry_on_timeout=True,
                    socket_keepalive=True,
                    socket_keepalive_options={},
                    health_check_interval=30
                )
                self.redis_client = redis.Redis(connection_pool=self._connection_pool)
                # Test connection
                await self.redis_client.ping()
                logger.info("Redis cache service connected")
            except Exception as e:
                logger.error(f"Redis connection failed: {e}")
                self.redis_client = None
    
    async def disconnect(self):
        """Close Redis connections"""
        if self.redis_client:
            await self.redis_client.close()
            if self._connection_pool:
                await self._connection_pool.disconnect()
    
    def _make_key(self, prefix: str, *args) -> str:
        """Generate cache key from prefix and arguments"""
        key_data = f"{prefix}:{':'.join(str(arg) for arg in args)}"
        # Hash long keys to avoid Redis key length limits
        if len(key_data) > 200:
            return f"{prefix}:{hashlib.md5(key_data.encode()).hexdigest()}"
        return key_data
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.redis_client:
            await self.connect()
        if not self.redis_client:
            return None
        
        try:
            value = await self.redis_client.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            logger.warning(f"Cache get error for key {key}: {e}")
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in cache with TTL"""
        if not self.redis_client:
            await self.connect()
        if not self.redis_client:
            return False
        
        try:
            serialized = json.dumps(value, default=str)
            await self.redis_client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.warning(f"Cache set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.redis_client:
            return False
        
        try:
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Cache delete error for key {key}: {e}")
            return False
    
    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from cache"""
        if not self.redis_client or not keys:
            return {}
        
        try:
            values = await self.redis_client.mget(keys)
            result = {}
            for key, value in zip(keys, values):
                if value:
                    try:
                        result[key] = json.loads(value)
                    except json.JSONDecodeError:
                        continue
            return result
        except Exception as e:
            logger.warning(f"Cache mget error: {e}")
            return {}
    
    async def set_many(self, items: Dict[str, Any], ttl: int = 3600) -> bool:
        """Set multiple values in cache"""
        if not self.redis_client or not items:
            return False
        
        try:
            pipe = self.redis_client.pipeline()
            for key, value in items.items():
                serialized = json.dumps(value, default=str)
                pipe.setex(key, ttl, serialized)
            await pipe.execute()
            return True
        except Exception as e:
            logger.warning(f"Cache mset error: {e}")
            return False
    
    # Specialized cache methods for common use cases
    async def cache_llm_response(self, prompt: str, context: str, model: str, response: str, ttl: int = 1800) -> bool:
        """Cache LLM response for 30 minutes"""
        cache_key = self._make_key("llm", hashlib.md5(f"{prompt}:{context}:{model}".encode()).hexdigest())
        return await self.set(cache_key, {"response": response, "model": model}, ttl)
    
    async def get_cached_llm_response(self, prompt: str, context: str, model: str) -> Optional[str]:
        """Get cached LLM response"""
        cache_key = self._make_key("llm", hashlib.md5(f"{prompt}:{context}:{model}".encode()).hexdigest())
        cached = await self.get(cache_key)
        return cached.get("response") if cached else None
    
    async def cache_document_content(self, doc_id: str, content: Dict[str, Any], ttl: int = 3600) -> bool:
        """Cache document content for 1 hour"""
        cache_key = self._make_key("doc", doc_id)
        return await self.set(cache_key, content, ttl)
    
    async def get_cached_document_content(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get cached document content"""
        cache_key = self._make_key("doc", doc_id)
        return await self.get(cache_key)
    
    async def cache_search_results(self, query: str, filters: Dict, results: List[Dict], ttl: int = 600) -> bool:
        """Cache search results for 10 minutes"""
        cache_key = self._make_key("search", hashlib.md5(f"{query}:{json.dumps(filters, sort_keys=True)}".encode()).hexdigest())
        return await self.set(cache_key, results, ttl)
    
    async def get_cached_search_results(self, query: str, filters: Dict) -> Optional[List[Dict]]:
        """Get cached search results"""
        cache_key = self._make_key("search", hashlib.md5(f"{query}:{json.dumps(filters, sort_keys=True)}".encode()).hexdigest())
        return await self.get(cache_key)
    
    async def invalidate_document_cache(self, doc_id: str) -> bool:
        """Invalidate all caches related to a document"""
        try:
            # Delete document content cache
            doc_key = self._make_key("doc", doc_id)
            await self.delete(doc_key)
            
            # Delete search caches (would need pattern matching in production)
            # For now, we'll let them expire naturally
            return True
        except Exception as e:
            logger.warning(f"Cache invalidation error for doc {doc_id}: {e}")
            return False


# Global cache instance
cache_service = CacheService()
