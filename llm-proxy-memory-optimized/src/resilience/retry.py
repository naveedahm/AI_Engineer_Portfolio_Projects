# src/resilience/retry.py - Simplified version
import asyncio
import random

class LLMRetry:
    def __init__(
        self,
        max_attempts: int = 2,
        base_delay: float = 0.5,
        max_delay: float = 5.0
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    async def execute(self, func, *args, **kwargs):
        last_exception = None
        
        for attempt in range(self.max_attempts):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_attempts - 1:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    delay += random.uniform(0, 0.5)
                    await asyncio.sleep(delay)
        
        raise last_exception