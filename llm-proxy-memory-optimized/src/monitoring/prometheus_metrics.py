# src/monitoring/prometheus_metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY
import time
from typing import Dict, Any

# Initialize metrics
REQUEST_COUNT = Counter(
    'llm_requests_total',
    'Total number of LLM requests',
    ['provider', 'model', 'status']
)

REQUEST_DURATION = Histogram(
    'llm_request_duration_seconds',
    'Request duration in seconds',
    ['provider', 'model'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

COST_TOTAL = Counter(
    'llm_cost_dollars_total',
    'Total cost in USD',
    ['provider', 'model']
)

TOKENS_PROMPT = Counter(
    'llm_tokens_prompt_total',
    'Total prompt tokens',
    ['provider', 'model']
)

TOKENS_COMPLETION = Counter(
    'llm_tokens_completion_total',
    'Total completion tokens',
    ['provider', 'model']
)

ACTIVE_REQUESTS = Gauge(
    'llm_active_requests',
    'Number of active requests'
)

PROVIDER_ERRORS = Counter(
    'llm_provider_errors_total',
    'Provider errors',
    ['provider', 'error_type']
)

BUDGET_REMAINING = Gauge(
    'llm_budget_remaining_dollars',
    'Remaining budget in USD',
    ['period']
)

# System metrics
SYSTEM_CPU_USAGE = Gauge('llm_system_cpu_usage_percent', 'System CPU usage percentage')
SYSTEM_MEMORY_USAGE = Gauge('llm_system_memory_usage_percent', 'System memory usage percentage')

def update_request_metrics(provider: str, model: str, duration_ms: float, cost: float, 
                           prompt_tokens: int, completion_tokens: int, success: bool):
    """Update metrics after a request"""
    status = "success" if success else "error"
    
    REQUEST_COUNT.labels(provider=provider, model=model, status=status).inc()
    REQUEST_DURATION.labels(provider=provider, model=model).observe(duration_ms / 1000)
    
    if success:
        COST_TOTAL.labels(provider=provider, model=model).inc(cost)
        TOKENS_PROMPT.labels(provider=provider, model=model).inc(prompt_tokens)
        TOKENS_COMPLETION.labels(provider=provider, model=model).inc(completion_tokens)

def update_error_metrics(provider: str, error_type: str):
    """Update error metrics"""
    PROVIDER_ERRORS.labels(provider=provider, error_type=error_type).inc()

def update_budget_metrics(remaining_daily: float, remaining_hourly: float):
    """Update budget metrics"""
    BUDGET_REMAINING.labels(period="daily").set(remaining_daily)
    BUDGET_REMAINING.labels(period="hourly").set(remaining_hourly)

def get_metrics():
    """Get all metrics in Prometheus format"""
    return generate_latest(REGISTRY)