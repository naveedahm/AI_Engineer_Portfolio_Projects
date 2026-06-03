# src/monitoring/logging.py
import logging
import json
import sys
import uuid
import traceback
from datetime import datetime
from typing import Dict, Any, Optional
from contextvars import ContextVar

# ============= Logging Setup =============

class StructuredLogger:
    """Simple structured logger without heavy dependencies"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._setup_logger()
        return cls._instance
    
    def _setup_logger(self):
        """Setup basic logger"""
        self.logger = logging.getLogger("llm_gateway")
        self.logger.setLevel(logging.INFO)
        
        # Console handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(handler)
        
        # File handler for errors
        file_handler = logging.FileHandler("logs/error.log")
        file_handler.setLevel(logging.ERROR)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(file_handler)
    
    def log_request_start(self, request_id: str, method: str, path: str, user_id: str = None, metadata: Dict = None):
        """Log request start"""
        self.logger.info(f"Request started: {method} {path}", extra={
            'request_id': request_id,
            'user_id': user_id,
            'metadata': metadata
        })
    
    def log_request_end(self, request_id: str, status_code: int, duration_ms: float, user_id: str = None, metadata: Dict = None):
        """Log request end"""
        level = logging.INFO if status_code < 400 else logging.ERROR
        self.logger.log(level, f"Request completed: {status_code} in {duration_ms:.2f}ms", extra={
            'request_id': request_id,
            'user_id': user_id,
            'metadata': metadata
        })
    
    def log_provider_call(self, provider: str, model: str, request_id: str, start: bool = True, 
                          latency_ms: float = None, error: str = None, tokens_used: int = None, cost_usd: float = None):
        """Log provider API calls"""
        if start:
            self.logger.debug(f"Provider call started: {provider}/{model}", extra={
                'request_id': request_id,
                'provider': provider,
                'model': model
            })
        else:
            if error:
                self.logger.error(f"Provider call failed: {provider}/{model} - {error}", extra={
                    'request_id': request_id,
                    'provider': provider,
                    'model': model,
                    'error': error
                })
            else:
                self.logger.info(f"Provider call succeeded: {provider}/{model} in {latency_ms:.2f}ms", extra={
                    'request_id': request_id,
                    'provider': provider,
                    'model': model,
                    'latency_ms': latency_ms,
                    'tokens_used': tokens_used,
                    'cost_usd': cost_usd
                })
    
    def log_error(self, error: Exception, context: str, request_id: str = None, 
                  provider: str = None, model: str = None, metadata: Dict = None):
        """Log errors"""
        self.logger.error(f"Error in {context}: {str(error)}", extra={
            'request_id': request_id,
            'provider': provider,
            'model': model,
            'error_type': type(error).__name__,
            'traceback': traceback.format_exc(),
            'metadata': metadata
        })
    
    def log_cost_event(self, provider: str, model: str, cost_usd: float, tokens_prompt: int, 
                       tokens_completion: int, request_id: str, is_budget_warning: bool = False,
                       budget_remaining: float = None):
        """Log cost tracking events"""
        level = logging.WARNING if is_budget_warning else logging.INFO
        self.logger.log(level, f"Cost: ${cost_usd:.6f} for {provider}/{model}", extra={
            'request_id': request_id,
            'provider': provider,
            'model': model,
            'cost_usd': cost_usd,
            'tokens_prompt': tokens_prompt,
            'tokens_completion': tokens_completion,
            'budget_remaining_usd': budget_remaining
        })
    
    def get_logger(self, name: str = None):
        """Get logger instance"""
        return self.logger

# Singleton instance
LLMLogger = StructuredLogger

# Convenience function
def get_logger(name: str = "default"):
    return StructuredLogger().get_logger()