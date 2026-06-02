# src/monitoring/metrics.py - Memory-optimized version
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST, CollectorRegistry
from typing import Dict, Any, Optional
import time
import psutil
import asyncio
from collections import defaultdict

# Use default registry for simplicity
REGISTRY = CollectorRegistry()

# Core metrics only (reduced from original)
REQUEST_COUNT = Counter(
    'llm_requests_total', 
    'Total requests', 
    ['provider', 'model', 'status'],
    registry=REGISTRY
)

REQUEST_LATENCY = Histogram(
    'llm_request_duration_seconds', 
    'Request latency in seconds', 
    ['provider', 'model'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
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
    'Active requests',
    registry=REGISTRY
)

PROVIDER_ERRORS = Counter(
    'llm_provider_errors_total',
    'Provider errors',
    ['provider', 'error_type'],
    registry=REGISTRY
)

BUDGET_REMAINING = Gauge(
    'llm_budget_remaining_dollars',
    'Remaining budget',
    ['period'],
    registry=REGISTRY
)

# Memory monitoring metrics
MEMORY_USAGE = Gauge(
    'process_memory_usage_bytes',
    'Process memory usage',
    registry=REGISTRY
)

class OptimizedMetrics:
    """Memory-optimized metrics collector"""
    
    def __init__(self):
        self._last_memory_check = 0
        self._metrics_buffer = defaultdict(float)
        self._buffer_size = 10
        
    async def record_request(
        self, 
        provider: str, 
        model: str, 
        success: bool, 
        latency_ms: float,
        cost: float = 0.0
    ):
        """Record request metrics with buffering"""
        status = "success" if success else "error"
        
        # Update metrics directly (prometheus client is efficient)
        REQUEST_COUNT.labels(provider=provider, model=model, status=status).inc()
        REQUEST_LATENCY.labels(provider=provider, model=model).observe(latency_ms / 1000)
        
        if cost > 0:
            COST_TOTAL.labels(provider=provider, model=model).inc(cost)
        
        # Update memory metrics periodically
        await self._update_memory_metrics()
    
    async def _update_memory_metrics(self):
        """Update memory metrics every 30 seconds"""
        now = time.time()
        if now - self._last_memory_check > 30:
            self._last_memory_check = now
            process = psutil.Process()
            MEMORY_USAGE.set(process.memory_info().rss)
    
    def record_error(self, provider: str, error_type: str):
        """Record provider error"""
        PROVIDER_ERRORS.labels(provider=provider, error_type=error_type).inc()
    
    def record_budget(self, period: str, remaining: float):
        """Record budget remaining"""
        BUDGET_REMAINING.labels(period=period).set(remaining)
    
    def get_metrics(self):
        """Get current metrics"""
        return generate_latest(REGISTRY)

# Global instance
metrics = OptimizedMetrics()

async def metrics_endpoint(request):
    """FastAPI metrics endpoint"""
    from fastapi.responses import Response
    return Response(
        content=metrics.get_metrics(),
        media_type=CONTENT_TYPE_LATEST
    )