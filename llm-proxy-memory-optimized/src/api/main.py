# src/api/main.py - Complete working version
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import time
import os
import yaml
from pathlib import Path
from contextlib import asynccontextmanager
from src.cost.cost_tracker import cost_tracker
from fastapi import WebSocket

# Fix path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.gateway.router import LLMRouter
from src.api.models import ChatCompletionRequest

# Simple metrics (without prometheus for now to avoid issues)
REQUEST_COUNT = {}
REQUEST_LATENCY = {}
ACTIVE_REQUESTS = 0

# Load configuration
def load_config():
    config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
    if config_path.exists():
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    return {
        "server": {"host": "0.0.0.0", "port": 8000},
        "budget": {"daily_limit": 5.0, "hourly_limit": 1.0},
        "providers": {
            "groq": {"timeout": 30},
            "openai": {"timeout": 30}
        },
        "models": {
            "default": {
                "primary": {"provider": "groq", "model": "llama-3.1-8b-instant"},
                "fallbacks": [{"provider": "openai", "model": "gpt-3.5-turbo"}]
            },
            "premium": {
                "primary": {"provider": "groq", "model": "llama-3.3-70b-versatile"},
                "fallbacks": [
                    {"provider": "openai", "model": "gpt-4o-mini"},
                    {"provider": "groq", "model": "mixtral-8x7b-32768"}
                ]
            }
        }
    }

config = load_config()

# Initialize router
router = LLMRouter(config)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    print("\n" + "=" * 50)
    print("LLM Gateway Ready!")
    print("=" * 50)
    print(f"API: http://localhost:8000")
    print(f"Health: http://localhost:8000/health")
    print(f"Chains: http://localhost:8000/chains")
    print("=" * 50 + "\n")
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

@app.post("/v1/chat/completions")
async def chat_completion(request: Request, chat_request: ChatCompletionRequest):
    """Chat completion endpoint"""
    global ACTIVE_REQUESTS
    ACTIVE_REQUESTS += 1
    start_time = time.time()
    
    try:
        # Convert messages to dict format
        messages = [{"role": msg.role, "content": msg.content} for msg in chat_request.messages]
        
        # Route the request
        result = await router.route(
            messages=messages,
            model_family=chat_request.model_family or "default",
            provider=getattr(chat_request, 'provider', None),
            model=getattr(chat_request, 'model', None),
            temperature=chat_request.temperature,
            max_tokens=chat_request.max_tokens,
        )
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result.get('error'))
        
        # Add latency to result
        result['total_latency_ms'] = (time.time() - start_time) * 1000
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        ACTIVE_REQUESTS -= 1

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "timestamp": time.time(),
        "active_requests": ACTIVE_REQUESTS,
        "chains": list(router.fallback_chains.keys())
    }

@app.get("/chains")
async def list_chains():
    """List available model chains"""
    return {
        "available_chains": list(router.fallback_chains.keys()),
        "chains": router.fallback_chains
    }

# Add this to src/api/main.py

@app.get("/budget")
async def get_budget_status():
    """Get current budget usage"""
    remaining = router.budget_tracker.get_remaining_budget()
    return {
        "daily": {
            "used": remaining.get('daily_used', 0),
            "limit": router.budget_tracker.daily_limit,
            "remaining": remaining.get('daily_remaining', 0),
            "percentage": (remaining.get('daily_used', 0) / router.budget_tracker.daily_limit) * 100
        },
        "hourly": {
            "used": remaining.get('hourly_used', 0),
            "limit": router.budget_tracker.hourly_limit,
            "remaining": remaining.get('hourly_remaining', 0),
            "percentage": (remaining.get('hourly_used', 0) / router.budget_tracker.hourly_limit) * 100
        }
    }

@app.get("/costs/breakdown")
async def get_cost_breakdown(period: str = "all", limit: int = 100):
    """Get detailed cost breakdown by provider and model"""
    breakdown = cost_tracker.get_breakdown(period=period, limit=limit)
    return breakdown

@app.get("/costs/models")
async def get_model_costs():
    """Get detailed costs by individual model"""
    model_costs = cost_tracker.get_model_costs()
    return {
        "models": model_costs,
        "total_models": len(model_costs),
        "total_cost": sum(m["total_cost"] for m in model_costs.values())
    }

@app.get("/costs/reset")
async def reset_costs(confirm: bool = False):
    """Reset cost tracking (use with caution)"""
    return cost_tracker.reset_costs(confirm=confirm)

@app.websocket("/ws/costs")
async def websocket_costs(websocket: WebSocket):
    """WebSocket endpoint for real-time cost updates"""
    await websocket.accept()
    
    try:
        last_update = datetime.now()
        while True:
            # Send cost updates every 5 seconds
            if (datetime.now() - last_update).seconds >= 5:
                breakdown = cost_tracker.get_breakdown(period="today")
                await websocket.send_json(breakdown)
                last_update = datetime.now()
            
            await asyncio.sleep(1)
    except Exception as e:
        print(f"WebSocket error: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app", 
        host="0.0.0.0", 
        port=8000,
        reload=False,
        workers=1
    )