from tenacity import (
    retry, 
    stop_after_attempt, 
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log
)
from loguru import logger
import openai
import asyncio

class EnhancedRetryHandler:
    """Enhanced retry logic beyond what's in llm_service.py"""
    
    @staticmethod
    def create_retry_decorator(max_attempts=3, base_delay=1):
        return retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=base_delay, min=1, max=30),
            retry=retry_if_exception_type((
                openai.APIConnectionError,
                openai.RateLimitError,
                openai.APIStatusError,
                asyncio.TimeoutError,
                ConnectionError,
                TimeoutError
            )),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            after=after_log(logger, logging.INFO),
            reraise=True
        )
    
    @staticmethod
    async def circuit_breaker(func, failure_threshold=5, recovery_timeout=60):
        """Circuit breaker pattern for LLM calls"""
        # Implementation for circuit breaker
        pass