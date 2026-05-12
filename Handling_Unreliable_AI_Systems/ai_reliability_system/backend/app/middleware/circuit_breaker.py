from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Optional
from datetime import datetime, timedelta
import asyncio
from collections import deque

class CircuitBreaker:
    def __init__(self, name: str, failure_threshold: int = 5, 
                 timeout: int = 60, half_open_timeout: int = 30):
        self.name = name
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.half_open_timeout = half_open_timeout
        self.failures = deque(maxlen=failure_threshold)
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.last_failure_time = None
        self.last_success_time = None
        
    def record_failure(self):
        now = datetime.now()
        self.failures.append(now)
        self.last_failure_time = now
        
        if len(self.failures) >= self.failure_threshold:
            self.state = "OPEN"
            
    def record_success(self):
        self.last_success_time = datetime.now()
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            self.failures.clear()
            
    def can_execute(self) -> bool:
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if self.last_failure_time and \
               datetime.now() - self.last_failure_time > timedelta(seconds=self.timeout):
                self.state = "HALF_OPEN"
                return True
            return False
        elif self.state == "HALF_OPEN":
            return True
        return False

class CircuitBreakerMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        
    async def dispatch(self, request: Request, call_next):
        # Determine which circuit breaker to use
        endpoint = request.url.path
        cb_key = f"ai_{endpoint}"
        
        if cb_key not in self.circuit_breakers:
            self.circuit_breakers[cb_key] = CircuitBreaker(cb_key)
        
        cb = self.circuit_breakers[cb_key]
        
        if not cb.can_execute():
            raise HTTPException(
                status_code=503,
                detail=f"Circuit breaker {cb_key} is OPEN. Service temporarily unavailable."
            )

        try:
            response = await call_next(request)
            if response.status_code < 500:
                cb.record_success()
            else:
                cb.record_failure()
            return response
        except Exception as e:
            cb.record_failure()
            raise