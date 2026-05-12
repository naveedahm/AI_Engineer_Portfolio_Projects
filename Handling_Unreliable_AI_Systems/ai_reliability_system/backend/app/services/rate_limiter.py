import time
from typing import Dict, Optional
from redis import Redis
from collections import defaultdict

class RateLimiter:
    def __init__(self, redis_client: Optional[Redis] = None, limit: int = 60):
        self.redis = redis_client
        self.limit = limit
        self.window_size = 60  # 1 minute window
        self.in_memory_limits: Dict[str, list] = defaultdict(list)
        
    async def check_limit(self, key: str) -> bool:
        """Check if request is within rate limit"""
        if self.redis:
            return await self._check_redis_limit(key)
        else:
            return self._check_memory_limit(key)
    
    async def _check_redis_limit(self, key: str) -> bool:
        """Check rate limit using Redis"""
        now = time.time()
        window_key = f"rate_limit:{key}:{int(now / self.window_size)}"
        
        current = self.redis.get(window_key)
        if current and int(current) >= self.limit:
            raise Exception(f"Rate limit exceeded for key: {key}")
        
        # Increment counter
        self.redis.incr(window_key)
        self.redis.expire(window_key, self.window_size + 1)
        return True
    
    def _check_memory_limit(self, key: str) -> bool:
        """Check rate limit in memory (for development)"""
        now = time.time()
        cutoff = now - self.window_size
        
        # Clean old entries
        self.in_memory_limits[key] = [t for t in self.in_memory_limits[key] if t > cutoff]
        
        if len(self.in_memory_limits[key]) >= self.limit:
            raise Exception(f"Rate limit exceeded for key: {key}")
        
        self.in_memory_limits[key].append(now)
        return True
    
    async def get_remaining(self, key: str) -> int:
        """Get remaining requests in current window"""
        if self.redis:
            now = time.time()
            window_key = f"rate_limit:{key}:{int(now / self.window_size)}"
            current = self.redis.get(window_key)
            used = int(current) if current else 0
            return max(0, self.limit - used)
        else:
            now = time.time()
            cutoff = now - self.window_size
            used = len([t for t in self.in_memory_limits[key] if t > cutoff])
            return max(0, self.limit - used)