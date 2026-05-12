from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import time
import uuid
from typing import Dict, Any

logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Log request
        start_time = time.time()
        logger.info(f"Request started: {request.method} {request.url.path} | ID: {request_id}")
        
        # Process request
        try:
            response = await call_next(request)
            
            # Log response
            process_time = time.time() - start_time
            logger.info(
                f"Request completed: {request.method} {request.url.path} | "
                f"Status: {response.status_code} | Time: {process_time:.3f}s | "
                f"ID: {request_id}"
            )
            
            # Add custom headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"Request failed: {request.method} {request.url.path} | "
                f"Error: {str(e)} | Time: {process_time:.3f}s | ID: {request_id}",
                exc_info=True
            )
            raise

class StructuredLogger:
    @staticmethod
    def log_event(name: str, attributes: Dict[str, Any]):
        logger.info(f"EVENT: {name}", extra=attributes)
    
    @staticmethod
    def log_ai_call(prompt: str, model: str, tokens: int, duration: float):
        StructuredLogger.log_event("ai_call", {
            "prompt_length": len(prompt),
            "model": model,
            "tokens_used": tokens,
            "duration_ms": duration * 1000
        })