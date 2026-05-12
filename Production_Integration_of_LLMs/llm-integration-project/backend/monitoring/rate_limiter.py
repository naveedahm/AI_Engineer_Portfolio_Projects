"""Rate limiting with Redis and Prometheus metrics"""
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import FastAPI, Request, HTTPException
import redis
from typing import Dict, Optional
from loguru import logger
from .metrics import record_rate_limit

class RateLimiter:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        """Initialize rate limiter with Redis backend"""
        try:
            self.redis_client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            logger.info(f"Connected to Redis at {redis_url}")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Using in-memory rate limiting.")
            self.redis_client = None
        
        # Configure rate limiter
        self.limiter = Limiter(
            key_func=get_remote_address,
            storage_uri=redis_url if self.redis_client else "memory://",
            default_limits=["100 per minute", "1000 per hour"],
            enabled=True
        )
        
        # User tier limits (requests per minute)
        self.user_limits = {
            "free": {"per_minute": 10, "per_hour": 100, "burst": 20},
            "premium": {"per_minute": 100, "per_hour": 1000, "burst": 200},
            "enterprise": {"per_minute": 1000, "per_hour": 10000, "burst": 2000}
        }
    
    def apply_to_app(self, app: FastAPI):
        """Apply rate limiting middleware to FastAPI app"""
        app.state.limiter = self.limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        logger.info("Rate limiting middleware applied")
    
    async def check_rate_limit(
        self, 
        request: Request, 
        user_id: Optional[str] = None,
        user_tier: str = "free"
    ) -> bool:
        """Check if request is within rate limits"""
        
        # Get client identifier
        client_id = user_id or request.client.host
        limits = self.user_limits.get(user_tier, self.user_limits["free"])
        
        # Check minute limit
        minute_key = f"rate_limit:{client_id}:minute"
        hour_key = f"rate_limit:{client_id}:hour"
        
        current_minute = self._get_current_minute_count(minute_key)
        current_hour = self._get_current_hour_count(hour_key)
        
        endpoint = request.url.path
        
        # Check limits
        if current_minute >= limits["per_minute"]:
            record_rate_limit(endpoint, user_tier)
            logger.warning(f"Rate limit exceeded for {client_id} on {endpoint}")
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Maximum {limits['per_minute']} requests per minute."
            )
        
        if current_hour >= limits["per_hour"]:
            record_rate_limit(endpoint, user_tier)
            logger.warning(f"Hourly rate limit exceeded for {client_id}")
            raise HTTPException(
                status_code=429,
                detail=f"Hourly rate limit exceeded. Maximum {limits['per_hour']} requests per hour."
            )
        
        # Increment counters
        self._increment_counter(minute_key, 60)  # 1 minute expiry
        self._increment_counter(hour_key, 3600)  # 1 hour expiry
        
        return True
    
    def _get_current_minute_count(self, key: str) -> int:
        """Get current minute request count"""
        if self.redis_client:
            count = self.redis_client.get(key)
            return int(count) if count else 0
        # Fallback to in-memory (simplified)
        return 0
    
    def _get_current_hour_count(self, key: str) -> int:
        """Get current hour request count"""
        if self.redis_client:
            count = self.redis_client.get(key)
            return int(count) if count else 0
        return 0
    
    def _increment_counter(self, key: str, expiry: int):
        """Increment counter with expiry"""
        if self.redis_client:
            self.redis_client.incr(key)
            self.redis_client.expire(key, expiry)
    
    async def get_user_stats(self, user_id: str) -> Dict:
        """Get rate limit statistics for a user"""
        minute_key = f"rate_limit:{user_id}:minute"
        hour_key = f"rate_limit:{user_id}:hour"
        
        return {
            "current_minute_requests": self._get_current_minute_count(minute_key),
            "current_hour_requests": self._get_current_hour_count(hour_key),
            "limits": self.user_limits
        }