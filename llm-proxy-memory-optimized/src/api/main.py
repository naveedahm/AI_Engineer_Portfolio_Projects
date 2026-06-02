# src/api/main.py - Complete working version
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter, Histogram, Gauge
import time
import os
import yaml
from pathlib import Path
from contextlib import asynccontextmanager
from typing import List, Dict, Any

# Fix path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.gateway.router import LLMRouter
from src.api.models import ChatCompletionRequest, Message

# Initialize Prometheus metrics
REQUEST_COUNT = Counter('llm_requests_total', 'Total requests', ['provider', 'model', 'status'])
REQUEST_LATENCY = Histogram('llm_request_duration_seconds', 'Request latency', ['provider', 'model'])
COST_TOTAL = Counter('llm_cost_dollars_total', 'Total cost in USD', ['provider', 'model'])
ACTIVE_REQUESTS = Gauge('llm_active_requests', 'Active requests')
PROVIDER_ERRORS = Counter('llm_provider_errors_total', 'Provider errors', ['provider', 'error_type'])

# Load configuration
def load_config():
    config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
    if config_path.exists():
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    return {
        "server": {"host": "0.0.0.0", "port": 8000},
        "budget": {"daily_limit": 5.0, "hourly_limit": 1.0},
        "models": {
            "default": {
                "primary": {"provider": "groq", "model": "llama-3.1-8b-instant"},
                "fallbacks": [{"provider": "openai", "model": "gpt-3.5-turbo"}]
            }
        },
        "providers": {
            "groq": {"enabled": True, "timeout": 30},
            "openai": {"enabled": True, "timeout": 30}
        }
    }

config = load_config()

# Initialize router
print("\n" + "="*50)
print("Initializing LLM Router...")
print("="*50)
router = LLMRouter(config)
print("="*50 + "\n")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    print("\n" + "="*50)
    print("LLM Gateway Starting...")
    print("="*50)
    print(f"API Server: http://{config['server']['host']}:{config['server']['port']}")
    print(f"Health Check: http://localhost:{config['server']['port']}/health")
    print(f"Metrics: http://localhost:{config['server']['port']}/metrics")
    print("="*50 + "\n")
    
    yield
    
    print("\nShutting down LLM Gateway...")
    await router.close()
    print("Shutdown complete.\n")

# Create FastAPI app
app = FastAPI(
    title="LLM Gateway",
    description="Unified API Gateway for Multiple LLM Providers",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "LLM Gateway",
        "version": "1.0.0",
        "status": "running",
        "providers": list(router.providers.keys()),
        "chains": list(router.fallback_chains.keys()),
        "endpoints": {
            "chat": "/v1/chat/completions",
            "health": "/health",
            "metrics": "/metrics"
        }
    }

@app.post("/v1/chat/completions")
async def chat_completion(chat_request: ChatCompletionRequest):
    """Chat completion endpoint"""
    ACTIVE_REQUESTS.inc()
    start_time = time.time()
    
    try:
        # Convert messages to dict format
        messages = [{"role": msg.role, "content": msg.content} for msg in chat_request.messages]

        # Route the request
        print("before sending call to router")
        result = await router.route(
            messages=messages,
            model_family=chat_request.model_family or "default",
            temperature=chat_request.temperature,
            max_tokens=chat_request.max_tokens,
        )
        print("after sending call to router")


        latency_ms = (time.time() - start_time) * 1000
        
        if "error" not in result:
            # Record success metrics
            REQUEST_COUNT.labels(
                provider=result.get('provider', 'unknown'),
                model=result.get('model', 'unknown'),
                status='success'
            ).inc()
            
            REQUEST_LATENCY.labels(
                provider=result.get('provider', 'unknown'),
                model=result.get('model', 'unknown')
            ).observe(latency_ms / 1000)
            
            if result.get('cost'):
                COST_TOTAL.labels(
                    provider=result.get('provider', 'unknown'),
                    model=result.get('model', 'unknown')
                ).inc(result['cost'])
            
            return result
        else:
            # Record error metrics
            REQUEST_COUNT.labels(
                provider='unknown',
                model='unknown',
                status='error'
            ).inc()
            
            PROVIDER_ERRORS.labels(
                provider='all',
                error_type='routing_failure'
            ).inc()
            
            raise HTTPException(status_code=503, detail=result.get('error'))
            
    except HTTPException:
        raise
    except Exception as e:
        # Record error metrics
        REQUEST_COUNT.labels(
            provider='unknown',
            model='unknown',
            status='error'
        ).inc()
        
        PROVIDER_ERRORS.labels(
            provider='gateway',
            error_type=type(e).__name__
        ).inc()
        
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        ACTIVE_REQUESTS.dec()

@app.get("/metrics")
async def metrics_endpoint():
    """Prometheus metrics endpoint"""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

@app.get("/health")
async def health():
    """Health check endpoint"""
    provider_status = {}
    for name, provider in router.providers.items():
        provider_status[name] = "available"
    
    return {
        "status": "healthy" if router.providers else "degraded",
        "timestamp": time.time(),
        "providers": provider_status,
        "active_requests": ACTIVE_REQUESTS._value.get(),
        "chains_available": len(router.fallback_chains)
    }

@app.get("/providers")
async def list_providers():
    """List available providers"""
    return {
        "initialized_providers": list(router.providers.keys()),
        "fallback_chains": {
            name: [p['provider'] for p in chain] 
            for name, chain in router.fallback_chains.items()
        },
        "circuit_breakers": list(router.circuit_breakers.keys())
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host=config['server']['host'],
        port=config['server']['port'],
        reload=False,
        log_level="info"
    )