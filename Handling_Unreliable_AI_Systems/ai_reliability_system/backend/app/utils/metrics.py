from prometheus_client import Counter, Histogram, Gauge, generate_latest
from functools import wraps
import time
from typing import Callable

# Define metrics
ai_requests_total = Counter('ai_requests_total', 'Total AI requests', ['model', 'status'])
ai_request_duration = Histogram('ai_request_duration_seconds', 'AI request duration', ['model'])
ai_tokens_consumed = Counter('ai_tokens_consumed_total', 'Total tokens consumed', ['model'])
ai_errors_total = Counter('ai_errors_total', 'Total AI errors', ['error_type'])
ai_confidence_gauge = Gauge('ai_confidence_score', 'Current AI confidence score')
ai_cost_gauge = Gauge('ai_cost_total', 'Total AI cost', ['period'])
rate_limit_hits = Counter('rate_limit_hits_total', 'Total rate limit hits')
cache_hits = Counter('cache_hits_total', 'Total cache hits')
cache_misses = Counter('cache_misses_total', 'Total cache misses')

def track_request(func: Callable):
    """Decorator to track request metrics"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        model = kwargs.get('model', 'unknown')
        
        try:
            result = await func(*args, **kwargs)
            ai_requests_total.labels(model=model, status='success').inc()
            ai_request_duration.labels(model=model).observe(time.time() - start_time)
            
            if hasattr(result, 'confidence'):
                ai_confidence_gauge.set(result.confidence)
            
            return result
        except Exception as e:
            ai_requests_total.labels(model=model, status='error').inc()
            ai_errors_total.labels(error_type=type(e).__name__).inc()
            raise
    
    return wrapper

def setup_metrics():
    """Setup metrics for monitoring"""
    # Initialize any metrics that need setup
    ai_cost_gauge.labels(period='daily').set(0)
    ai_cost_gauge.labels(period='monthly').set(0)