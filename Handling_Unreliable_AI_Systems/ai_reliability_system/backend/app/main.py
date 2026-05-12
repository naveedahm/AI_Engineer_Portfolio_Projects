
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import redis
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.config import settings
from app.api.routes import router
from app.api.health import health_router
from app.middleware.logging import LoggingMiddleware
from app.middleware.circuit_breaker import CircuitBreakerMiddleware
from app.services.ai_gateway import AIGateway
from app.utils.metrics import setup_metrics

import traceback
from fastapi import Request
from fastapi.responses import JSONResponse

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
redis_client = None
ai_gateway = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global redis_client, ai_gateway
    
    logger.info("Starting AI Reliability System...")
    
    # Initialize Redis
    redis_client = redis.Redis.from_url(
        settings.redis_url,
        password=settings.redis_password,
        decode_responses=True
    )
    
    # Initialize AI Gateway
    ai_gateway = AIGateway(redis_client)
    
    # Setup metrics
    if settings.enable_metrics:
        setup_metrics()
    
    logger.info("System initialized successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    if redis_client:
        redis_client.close()

# Create FastAPI app
app = FastAPI(
    title="AI Reliability System",
    description="Production-grade AI system with reliability features",
    version="1.0.0",
    lifespan=lifespan
)

# Add middleware


# Configure CORS properly - MOVED BEFORE including routers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development - specify frontend URL in production
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"],
    max_age=600,  # Cache preflight requests for 10 minutes
)

app.add_middleware(LoggingMiddleware)
app.add_middleware(CircuitBreakerMiddleware)

# Include routers
app.include_router(router, prefix="/api/v1")
app.include_router(health_router, prefix="/health")

@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Log full traceback
    error_details = traceback.format_exc()
    print(f"❌ Global exception handler caught:")
    print(f"URL: {request.method} {request.url.path}")
    print(f"Error: {str(exc)}")
    print(f"Traceback:\n{error_details}")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "traceback": error_details if "debug" in request.query_params else None
        }
    )

@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client, ai_gateway
    
    print("🚀 Starting AI Reliability System...")
    
    # Initialize Redis
    try:
        redis_client = redis.Redis(
            host='localhost',
            port=6379,
            decode_responses=True,
            socket_connect_timeout=2
        )
        redis_client.ping()
        print("✅ Redis connected")
    except Exception as e:
        print(f"⚠️ Redis not available: {e}")
        print("✅ Using mock Redis")
        class MockRedis:
            def __init__(self):
                self.data = {}
            def get(self, key): return self.data.get(key)
            def setex(self, key, time, value): self.data[key] = value
            def ping(self): return True
        redis_client = MockRedis()
    
    # Initialize AI Gateway
    try:
        ai_gateway = AIGateway(redis_client)
        print(f"✅ AI Gateway initialized: {type(ai_gateway)}")
    except Exception as e:
        print(f"❌ Failed to initialize AI Gateway: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    print("✅ Startup complete")
    yield
    
    print("🛑 Shutting down...")