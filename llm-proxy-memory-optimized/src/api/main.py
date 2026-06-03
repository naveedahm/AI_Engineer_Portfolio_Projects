# src/api/main.py - Add metrics endpoint
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import time
import os
import yaml
from pathlib import Path
from contextlib import asynccontextmanager
import asyncio
import json

# Fix path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.gateway.router import LLMRouter
from src.cost.cost_tracker import cost_tracker
from src.monitoring.prometheus_metrics import get_metrics, update_request_metrics, update_error_metrics, update_budget_metrics

# Pydantic models
from pydantic import BaseModel
from typing import List, Optional

class Message(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    messages: List[Message]
    model_family: Optional[str] = "default"
    provider: Optional[str] = None
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 1000
    stream: bool = False

# Load configuration
def load_config():
    config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
    if config_path.exists():
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    return {
        "server": {"host": "0.0.0.0", "port": 8000},
        "budget": {"daily_limit": 5.0, "hourly_limit": 1.0}
    }

config = load_config()
router = LLMRouter(config)
ACTIVE_REQUESTS = 0

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\n" + "=" * 50)
    print("LLM Gateway Ready!")
    print("=" * 50)
    print(f"API: http://localhost:8000")
    print(f"Health: http://localhost:8000/health")
    print(f"Metrics: http://localhost:8000/metrics")
    print(f"Dashboard: http://localhost:8000/cost-dashboard")
    print("=" * 50 + "\n")
    
    # Start background task to update system metrics
    async def update_system_metrics():
        import psutil
        while True:
            try:
                SYSTEM_CPU_USAGE = Gauge('llm_system_cpu_usage_percent', 'CPU usage')
                SYSTEM_MEMORY_USAGE = Gauge('llm_system_memory_usage_percent', 'Memory usage')
                SYSTEM_CPU_USAGE.set(psutil.cpu_percent())
                SYSTEM_MEMORY_USAGE.set(psutil.virtual_memory().percent)
            except:
                pass
            await asyncio.sleep(30)
    
    asyncio.create_task(update_system_metrics())
    yield
    print("Shutting down...")

app = FastAPI(title="LLM Gateway", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============= API Endpoints =============

@app.post("/v1/chat/completions")
async def chat_completion(request: Request, chat_request: ChatCompletionRequest):
    """Chat completion endpoint with metrics"""
    global ACTIVE_REQUESTS
    ACTIVE_REQUESTS += 1
    
    # Update active requests gauge
    from src.monitoring.prometheus_metrics import ACTIVE_REQUESTS as ACTIVE_REQUESTS_METRIC
    ACTIVE_REQUESTS_METRIC.inc()
    
    start_time = time.time()
    
    try:
        messages = [{"role": msg.role, "content": msg.content} for msg in chat_request.messages]
        
        result = await router.route(
            messages=messages,
            model_family=chat_request.model_family,
            provider=chat_request.provider,
            model=chat_request.model,
            temperature=chat_request.temperature,
            max_tokens=chat_request.max_tokens,
        )
        
        duration_ms = (time.time() - start_time) * 1000
        
        if "error" in result:
            # Update error metrics
            update_error_metrics(
                provider=chat_request.provider or "unknown",
                error_type=result.get('error', 'unknown')
            )
            raise HTTPException(status_code=500, detail=result.get('error'))
        
        # Update success metrics
        update_request_metrics(
            provider=result.get('provider', 'unknown'),
            model=result.get('model', 'unknown'),
            duration_ms=duration_ms,
            cost=result.get('cost', 0),
            prompt_tokens=result.get('tokens', {}).get('prompt', 0),
            completion_tokens=result.get('tokens', {}).get('completion', 0),
            success=True
        )
        
        # Update budget metrics
        budget_remaining = router.budget_tracker.get_remaining_budget()
        update_budget_metrics(
            remaining_daily=budget_remaining.get('daily_remaining', 0),
            remaining_hourly=budget_remaining.get('hourly_remaining', 0)
        )
        
        result['total_latency_ms'] = duration_ms
        return result
        
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        update_request_metrics(
            provider=chat_request.provider or 'unknown',
            model=chat_request.model or 'unknown',
            duration_ms=duration_ms,
            cost=0,
            prompt_tokens=0,
            completion_tokens=0,
            success=False
        )
        update_error_metrics(
            provider=chat_request.provider or 'unknown',
            error_type=type(e).__name__
        )
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        ACTIVE_REQUESTS -= 1
        ACTIVE_REQUESTS_METRIC.dec()

@app.get("/metrics")
async def metrics_endpoint():
    """Prometheus metrics endpoint"""
    from fastapi.responses import Response
    return Response(content=get_metrics(), media_type="text/plain")

@app.get("/health")
async def health():
    return {
        "status": "healthy", 
        "timestamp": time.time(),
        "active_requests": ACTIVE_REQUESTS,
        "chains": list(router.fallback_chains.keys())
    }

@app.get("/chains")
async def list_chains():
    return {
        "available_chains": list(router.fallback_chains.keys()),
        "chains": router.fallback_chains
    }

# ============= Cost Tracking Endpoints =============

@app.get("/costs/breakdown")
async def get_cost_breakdown():
    return cost_tracker.get_breakdown()

@app.get("/costs/models")
async def get_model_costs():
    return {"models": cost_tracker.get_model_costs()}

@app.post("/costs/reset")
async def reset_costs():
    cost_tracker.reset()
    return {"message": "Cost tracking reset successfully"}

# ============= Simple Dashboard =============

@app.get("/cost-dashboard")
async def cost_dashboard():
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>LLM Gateway Monitor</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
            }
            .header {
                background: white;
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 20px;
            }
            h1 { color: #333; margin: 0; }
            .metrics-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin-bottom: 20px;
            }
            .card {
                background: white;
                border-radius: 10px;
                padding: 20px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .card h3 {
                margin-top: 0;
                color: #667eea;
            }
            .metric-value {
                font-size: 32px;
                font-weight: bold;
                color: #4CAF50;
            }
            button {
                background: #667eea;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
            }
            button:hover { background: #5a67d8; }
            pre {
                background: #f4f4f4;
                padding: 10px;
                border-radius: 5px;
                overflow-x: auto;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>💰 LLM Gateway Monitor</h1>
                <p>Prometheus Metrics: <a href="/metrics">/metrics</a></p>
            </div>
            
            <div class="metrics-grid">
                <div class="card">
                    <h3>Total Cost</h3>
                    <div class="metric-value" id="totalCost">$0.00</div>
                </div>
                <div class="card">
                    <h3>Total Requests</h3>
                    <div class="metric-value" id="totalRequests">0</div>
                </div>
                <div class="card">
                    <h3>Active Requests</h3>
                    <div class="metric-value" id="activeRequests">0</div>
                </div>
            </div>
            
            <div class="card">
                <h3>Cost Breakdown</h3>
                <div id="breakdown">Loading...</div>
            </div>
            
            <div class="card">
                <h3>Prometheus Queries</h3>
                <p>Try these queries in Prometheus (http://localhost:9090):</p>
                <pre>
# Total cost
sum(llm_cost_dollars_total)

# Cost by provider
sum by (provider) (llm_cost_dollars_total)

# Request rate
rate(llm_requests_total[5m])

# Error rate
rate(llm_provider_errors_total[5m])

# Average latency
avg(llm_request_duration_seconds)
                </pre>
            </div>
        </div>
        
        <script>
            async function loadData() {
                try {
                    const response = await fetch('/costs/breakdown');
                    const data = await response.json();
                    
                    document.getElementById('totalCost').textContent = `$${data.summary.total_cost.toFixed(6)}`;
                    document.getElementById('totalRequests').textContent = data.summary.total_requests;
                    
                    const breakdownDiv = document.getElementById('breakdown');
                    breakdownDiv.innerHTML = '';
                    
                    for (const [provider, providerData] of Object.entries(data.by_provider)) {
                        breakdownDiv.innerHTML += `
                            <div style="margin-bottom: 15px;">
                                <strong>${provider.toUpperCase()}</strong>: $${providerData.total_cost.toFixed(6)}
                                <div style="margin-left: 20px;">
                                    ${Object.entries(providerData.models || {}).map(([model, cost]) => 
                                        `<div>${model}: $${cost.toFixed(6)}</div>`
                                    ).join('')}
                                </div>
                            </div>
                        `;
                    }
                } catch(e) {
                    console.error('Error loading data:', e);
                }
            }
            
            loadData();
            setInterval(loadData, 5000);
        </script>
    </body>
    </html>
    """)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)