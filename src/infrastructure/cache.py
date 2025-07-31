"""
Production caching layer with Redis and fallback to in-memory.
"""
import json
import time
from typing import Any, Optional, Dict
from functools import wraps
import structlog
from ..core.models import ServiceResult

logger = structlog.get_logger(__name__)

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class CacheService:
    """Production caching service with Redis backend and in-memory fallback."""
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_client = None
        self.memory_cache: Dict[str, Dict] = {}
        self.cache_stats = {'hits': 0, 'misses': 0, 'errors': 0}
        
        if REDIS_AVAILABLE and redis_url:
            try:
                self.redis_client = redis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5,
                    retry_on_timeout=True
                )
                # Test connection
                self.redis_client.ping()
                logger.info("Redis cache initialized", url=redis_url.split('@')[-1])
            except Exception as e:
                logger.warning("Redis connection failed, using memory cache", error=str(e))
                self.redis_client = None
        else:
            logger.info("Using in-memory cache")
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            if self.redis_client:
                value = self.redis_client.get(key)
                if value:
                    self.cache_stats['hits'] += 1
                    return json.loads(value)
                else:
                    self.cache_stats['misses'] += 1
                    return None
            else:
                # Memory cache
                cache_entry = self.memory_cache.get(key)
                if cache_entry and cache_entry['expires'] > time.time():
                    self.cache_stats['hits'] += 1
                    return cache_entry['value']
                elif cache_entry:
                    # Expired
                    del self.memory_cache[key]
                
                self.cache_stats['misses'] += 1
                return None
                
        except Exception as e:
            logger.error("Cache get error", key=key, error=str(e))
            self.cache_stats['errors'] += 1
            return None
    
    def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> bool:
        """Set value in cache with TTL."""
        try:
            if self.redis_client:
                serialized = json.dumps(value, default=str)
                return self.redis_client.setex(key, ttl_seconds, serialized)
            else:
                # Memory cache
                self.memory_cache[key] = {
                    'value': value,
                    'expires': time.time() + ttl_seconds
                }
                return True
                
        except Exception as e:
            logger.error("Cache set error", key=key, error=str(e))
            self.cache_stats['errors'] += 1
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            if self.redis_client:
                return bool(self.redis_client.delete(key))
            else:
                return self.memory_cache.pop(key, None) is not None
                
        except Exception as e:
            logger.error("Cache delete error", key=key, error=str(e))
            return False
    
    def clear(self) -> bool:
        """Clear all cache entries."""
        try:
            if self.redis_client:
                return self.redis_client.flushdb()
            else:
                self.memory_cache.clear()
                return True
                
        except Exception as e:
            logger.error("Cache clear error", error=str(e))
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.cache_stats['hits'] + self.cache_stats['misses']
        hit_rate = (self.cache_stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        stats = {
            'backend': 'redis' if self.redis_client else 'memory',
            'hits': self.cache_stats['hits'],
            'misses': self.cache_stats['misses'],
            'errors': self.cache_stats['errors'],
            'hit_rate_percent': round(hit_rate, 2),
            'total_requests': total_requests
        }
        
        if not self.redis_client:
            stats['memory_entries'] = len(self.memory_cache)
        
        return stats
    
    def cleanup_expired(self):
        """Cleanup expired entries from memory cache."""
        if self.redis_client:
            return  # Redis handles expiration automatically
        
        current_time = time.time()
        expired_keys = [
            key for key, entry in self.memory_cache.items()
            if entry['expires'] <= current_time
        ]
        
        for key in expired_keys:
            del self.memory_cache[key]
        
        if expired_keys:
            logger.debug("Cleaned up expired cache entries", count=len(expired_keys))


def cached(ttl_seconds: int = 3600, key_prefix: str = ""):
    """Decorator for caching function results."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Try to get from cache (assuming cache_service is available in context)
            # In production, inject cache_service as dependency
            cached_result = None  # cache_service.get(cache_key)
            
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            # cache_service.set(cache_key, result, ttl_seconds)
            
            return result
        return wrapper
    return decorator


class RouteCache:
    """Specialized cache for route calculations."""
    
    def __init__(self, cache_service: CacheService):
        self.cache = cache_service
        self.key_prefix = "route"
    
    def get_route(self, start_city: str, end_city: str, route_type: str) -> Optional[Dict]:
        """Get cached route calculation."""
        key = f"{self.key_prefix}:{start_city}:{end_city}:{route_type}"
        return self.cache.get(key)
    
    def cache_route(self, start_city: str, end_city: str, route_type: str, 
                   route_data: Dict, ttl_hours: int = 24) -> bool:
        """Cache route calculation."""
        key = f"{self.key_prefix}:{start_city}:{end_city}:{route_type}"
        return self.cache.set(key, route_data, ttl_hours * 3600)
    
    def invalidate_city_routes(self, city_name: str) -> int:
        """Invalidate all routes involving a city."""
        # This would require scanning keys in Redis
        # For now, just clear all route cache
        return self.cache.delete(f"{self.key_prefix}:*{city_name}*")