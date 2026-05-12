
from functools import wraps
import hashlib
import json
from typing import Any, Callable, Optional
from redis import Redis
import asyncio

class CacheManager:

    def __init__(self, redis_client: Optional[Redis] = None, default_ttl: int = 3600):
        self.redis = redis_client
        self.default_ttl = default_ttl
        self.memory_cache = {}

    def warm_up(self, key: str, value: Any, ttl: Optional[int] = None):
        """Pre-populate cache with known values"""
        self.set(key, value, ttl)
        print(f"🔥 Cache warmed up for key: {key}")
    
    def get_or_set(self, key: str, factory_func, ttl: Optional[int] = None):
        """Get from cache or compute and store"""
        cached = self.get(key)
        if cached is not None:
            return cached
        
        # Compute value using factory function
        value = factory_func()
        self.set(key, value, ttl)
        return value
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if self.redis:
            return bool(self.redis.exists(key))
        else:
            return key in self.memory_cache
    
    def increment(self, key: str, amount: int = 1) -> int:
        """Increment a counter in cache"""
        if self.redis:
            return self.redis.incrby(key, amount)
        else:
            if key not in self.memory_cache:
                self.memory_cache[key] = {"value": 0, "expires": float('inf')}
            self.memory_cache[key]["value"] += amount
            return self.memory_cache[key]["value"]

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if self.redis:
            value = self.redis.get(key)
            if value:
                return json.loads(value)
        else:
            if key in self.memory_cache:
                entry = self.memory_cache[key]
                import time
                if time.time() < entry['expires']:
                    return entry['value']
                else:
                    del self.memory_cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache"""
        ttl = ttl or self.default_ttl
        
        if self.redis:
            self.redis.setex(key, ttl, json.dumps(value))
        else:
            import time
            self.memory_cache[key] = {
                'value': value,
                'expires': time.time() + ttl
            }
    
    def delete(self, key: str):
        """Delete from cache"""
        if self.redis:
            self.redis.delete(key)
        elif key in self.memory_cache:
            del self.memory_cache[key]

def cache_response(ttl: int = 3600, prefix: str = "ai_response"):
    """Decorator to cache API responses"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from args or kwargs
            request = None
            for arg in args:
                if hasattr(arg, 'prompt'):
                    request = arg
                    break
            
            if not request and 'request' in kwargs:
                request = kwargs['request']
            
            if request and hasattr(request, 'prompt'):
                # Generate cache key
                cache_key = f"{prefix}:{hashlib.md5(request.prompt.encode()).hexdigest()}"
                
                # Get from cache (would need cache manager instance)
                # For now, just call the function
                return await func(*args, **kwargs)
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator
