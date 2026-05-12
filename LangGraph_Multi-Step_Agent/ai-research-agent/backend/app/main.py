from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="AI Research Agent API",
    description="Multi-step research agent using LangGraph",
    version="1.0.0"
)

# Configure CORS - Allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
from app.api.routes import router as api_router
app.include_router(api_router, prefix="/api")

@app.on_event("startup")
async def startup_event():
    logger.info("Starting AI Research Agent API")
    logger.info(f"Available endpoints:")
    for route in app.routes:
        logger.info(f"  {route.path}")

@app.get("/")
async def root():
    return {
        "service": "AI Research Agent",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "api_health": "/api/health",
            "chat": "/api/chat",
            "stream": "/api/chat/stream",
            "simple": "/api/chat/simple",
            "test": "/api/test",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    """Simple health check at root level"""
    return {"status": "healthy", "service": "research-agent"}