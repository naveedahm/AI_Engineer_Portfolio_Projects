"""Prometheus metrics for LLM monitoring"""
from prometheus_client import Counter, Histogram, Gauge, Info
from functools import wraps
import time
from typing import Dict, Optional
from loguru import logger

# Request metrics
llm_requests_total = Counter(
    'llm_requests_total',
    'Total number of LLM requests',
    ['model', 'status', 'endpoint']
)

llm_request_duration = Histogram(
    'llm_request_duration_seconds',
    'LLM request duration in seconds',
    ['model', 'endpoint'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0)
)

# Error metrics
llm_errors_total = Counter(
    'llm_errors_total',
    'Total number of LLM errors',
    ['error_type', 'model', 'endpoint']
)

# Active requests gauge
active_requests = Gauge(
    'llm_active_requests',
    'Number of currently active LLM requests',
    ['model']
)

# Token consumption metrics
token_consumption = Counter(
    'llm_tokens_consumed_total',
    'Total tokens consumed',
    ['model', 'token_type']  # token_type: prompt or completion
)

# Cost tracking
cost_tracker = Counter(
    'llm_cost_total_usd',
    'Total cost incurred in USD',
    ['model', 'operation']
)

# Cache metrics
cache_hits = Counter(
    'llm_cache_hits_total',
    'Number of cache hits',
    ['model']
)

cache_misses = Counter(
    'llm_cache_misses_total',
    'Number of cache misses',
    ['model']
)

# Rate limiting metrics
rate_limit_hits = Counter(
    'rate_limit_hits_total',
    'Number of rate limit hits',
    ['endpoint', 'user_type']
)

# Model info
model_info = Info('llm_model_info', 'Information about LLM models')

def track_llm_request(model: str = "gpt-3.5-turbo", endpoint: str = "/chat"):
    """Decorator to track LLM request metrics"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Track active requests
            active_requests.labels(model=model).inc()
            
            # Start timing
            start_time = time.time()
            
            try:
                # Execute the function
                result = await func(*args, **kwargs)
                
                # Record success
                llm_requests_total.labels(
                    model=model, 
                    status='success',
                    endpoint=endpoint
                ).inc()
                
                return result
                
            except Exception as e:
                # Record error
                error_type = type(e).__name__
                llm_requests_total.labels(
                    model=model,
                    status='error',
                    endpoint=endpoint
                ).inc()
                
                llm_errors_total.labels(
                    error_type=error_type,
                    model=model,
                    endpoint=endpoint
                ).inc()
                
                raise
                
            finally:
                # Record duration
                duration = time.time() - start_time
                llm_request_duration.labels(
                    model=model,
                    endpoint=endpoint
                ).observe(duration)
                
                # Decrement active requests
                active_requests.labels(model=model).dec()
                
        return wrapper
    return decorator

def record_tokens(model: str, prompt_tokens: int, completion_tokens: int):
    """Record token usage metrics"""
    token_consumption.labels(
        model=model,
        token_type='prompt'
    ).inc(prompt_tokens)
    
    token_consumption.labels(
        model=model,
        token_type='completion'
    ).inc(completion_tokens)
    
    logger.info(f"Token usage - Model: {model}, Prompt: {prompt_tokens}, Completion: {completion_tokens}")

def record_cost(model: str, cost_usd: float, operation: str = "api_call"):
    """Record cost metrics"""
    cost_tracker.labels(
        model=model,
        operation=operation
    ).inc(cost_usd)
    
    logger.info(f"Cost incurred - Model: {model}, Cost: ${cost_usd:.6f}")

def record_cache_hit(model: str):
    """Record cache hit"""
    cache_hits.labels(model=model).inc()

def record_cache_miss(model: str):
    """Record cache miss"""
    cache_misses.labels(model=model).inc()

def record_rate_limit(endpoint: str, user_type: str = "free"):
    """Record rate limit hit"""
    rate_limit_hits.labels(endpoint=endpoint, user_type=user_type).inc()

def update_model_info(model_name: str, version: str, deployment: str):
    """Update model information metric"""
    model_info.info({
        'model_name': model_name,
        'version': version,
        'deployment': deployment,
        'environment': 'production'
    })