from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
import time
from typing import Dict
from loguru import logger
from models import ChatRequest, LLMResponse, ErrorResponse, MetricsResponse
from llm_service import LLMService
from monitoring.rate_limiter import RateLimiter
from monitoring.metrics import (
    update_model_info,
    llm_requests_total,
    llm_errors_total
)
from monitoring.cost_tracker import CostTracker
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="LLM Integration API with Monitoring", version="2.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
llm_service = LLMService()
rate_limiter = RateLimiter(os.getenv("REDIS_URL", "redis://localhost:6379"))
cost_tracker = CostTracker()

# Apply rate limiting
rate_limiter.apply_to_app(app)

# Update model info
update_model_info(
    model_name=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
    version="1.0.0",
    deployment="production"
)

@app.get("/")
async def root():
    return {
        "message": "LLM Integration API with Monitoring",
        "version": "2.0.0",
        "features": ["rate_limiting", "cost_tracking", "prometheus_metrics"]
    }

@app.get("/health")
async def health_check() -> Dict:
    return {"status": "healthy", "service": "llm-integration", "monitoring": "enabled"}

@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint"""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

@app.post("/chat", response_model=LLMResponse)
async def chat_endpoint(
    request: Request,
    chat_request: ChatRequest,
    background_tasks: BackgroundTasks
):
    request_start = time.time()
    
    # Apply rate limiting
    await rate_limiter.check_rate_limit(
        request=request,
        user_id=chat_request.user_id,
        user_tier=chat_request.user_tier
    )
    
    # Validate input
    if not chat_request.message or len(chat_request.message.strip()) == 0:
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    if len(chat_request.message) > 2000:
        raise HTTPException(status_code=400, detail="Message exceeds 2000 characters")
    
    try:
        # Process with LLM
        response = await llm_service.process_message(
            message=chat_request.message,
            user_id=chat_request.user_id or "anonymous",
            user_tier=chat_request.user_tier
        )
        
        # Add rate limit info to response
        rate_limit_stats = await rate_limiter.get_user_stats(
            chat_request.user_id or request.client.host
        )
        response.rate_limit_info = rate_limit_stats
        
        # Log metrics in background
        background_tasks.add_task(
            log_metrics,
            chat_request.message,
            response.processing_time_ms,
            response.confidence,
            chat_request.user_tier
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/metrics/dashboard")
async def get_metrics_dashboard():
    """Get aggregated metrics dashboard"""
    total_requests = sum(
        metric.values for metric in llm_requests_total._metrics.values()
    )
    total_errors = sum(
        metric.values for metric in llm_errors_total._metrics.values()
    )
    
    daily_cost = await cost_tracker.get_daily_cost()
    monthly_cost = await cost_tracker.get_monthly_cost()
    
    return MetricsResponse(
        total_requests=total_requests,
        total_errors=total_errors,
        average_latency_ms=0,  # Calculate from histogram
        total_cost_usd=daily_cost,
        cache_hit_rate=0.0  # Calculate from cache metrics
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            fallback_response="An error occurred. Please try again.",
            error_type=exc.__class__.__name__
        ).dict()
    )

async def log_metrics(message: str, processing_time: float, confidence: float, user_tier: str):
    """Background task for analytics logging"""
    logger.info(
        f"Metrics - Message: {message[:50]}, "
        f"Time: {processing_time}ms, "
        f"Confidence: {confidence}, "
        f"Tier: {user_tier}"
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port, 
        reload=False,
        log_level="info"
    )