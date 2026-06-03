# src/resilience/retry.py
import asyncio
import random
from typing import Callable

class LLMRetry:
    def __init__(self, max_attempts: int = 3, base_delay: float = 1.0, max_delay: float = 10.0):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    async def execute(self, func: Callable, *args, **kwargs):
        """Execute function with retry logic"""
        last_exception = None
        
        for attempt in range(self.max_attempts):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                error_str = str(e).lower()
                
                # Don't retry on client errors (4xx except 429)
                if "401" in error_str or "403" in error_str or "404" in error_str:
                    raise
                
                if attempt < self.max_attempts - 1:
                    # Exponential backoff with jitter
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    delay += random.uniform(0, 0.5)
                    await asyncio.sleep(delay)
        
        raise last_exception