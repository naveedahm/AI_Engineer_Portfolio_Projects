# src/monitoring/metrics.py - Simple version without heavy dependencies
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST, CollectorRegistry
import time
import psutil

# Use default registry
REGISTRY = CollectorRegistry()

# Request metrics
REQUEST_COUNT = Counter(
    'llm_requests_total', 
    'Total number of LLM requests', 
    ['provider', 'model', 'status'],
    registry=REGISTRY
)

REQUEST_LATENCY = Histogram(
    'llm_request_duration_seconds', 
    'Request duration in seconds', 
    ['provider', 'model'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
    registry=REGISTRY
)

COST_TOTAL = Counter(
    'llm_cost_dollars_total', 
    'Total cost in USD', 
    ['provider', 'model'],
    registry=REGISTRY
)

ACTIVE_REQUESTS = Gauge(
    'llm_active_requests', 
    'Number of active requests',
    registry=REGISTRY
)

PROVIDER_ERRORS = Counter(
    'llm_provider_errors_total',
    'Provider errors',
    ['provider', 'error_type'],
    registry=REGISTRY
)

class SimpleMetrics:
    """Simple metrics collector"""
    
    async def record_request(self, provider: str, model: str, success: bool, latency_ms: float, cost: float = 0.0):
        """Record request metrics"""
        status = "success" if success else "error"
        REQUEST_COUNT.labels(provider=provider, model=model, status=status).inc()
        REQUEST_LATENCY.labels(provider=provider, model=model).observe(latency_ms / 1000)
        
        if cost > 0:
            COST_TOTAL.labels(provider=provider, model=model).inc(cost)
    
    def record_error(self, provider: str, error_type: str):
        """Record provider error"""
        PROVIDER_ERRORS.labels(provider=provider, error_type=error_type).inc()
    
    def get_metrics(self):
        """Get current metrics"""
        return generate_latest(REGISTRY)

metrics = SimpleMetrics()

async def metrics_endpoint(request):
    """FastAPI metrics endpoint"""
    from fastapi.responses import Response
    return Response(content=metrics.get_metrics(), media_type=CONTENT_TYPE_LATEST)