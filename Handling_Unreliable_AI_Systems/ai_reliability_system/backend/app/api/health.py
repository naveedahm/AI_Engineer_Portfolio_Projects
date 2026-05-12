from fastapi import APIRouter
from datetime import datetime
import time
import os

# Create the router - THIS MUST BE NAMED 'router' or export as 'health_router'
router = APIRouter()

# Global variable for uptime tracking
_start_time = time.time()

@router.get("/")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": get_uptime(),
        "version": "1.0.0",
        "services": {
            "api": "running",
            "ai_service": "mock_mode"
        }
    }

@router.get("/detailed")
async def detailed_health():
    """Detailed health check with system metrics"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": get_uptime(),
        "system": {
            "pid": os.getpid(),
            "python_version": os.sys.version,
            "platform": os.name,
        },
        "services": {
            "api": "running",
            "cache": "mock_mode",
            "ai_gateway": "active"
        }
    }

@router.get("/readiness")
async def readiness_check():
    """Kubernetes readiness probe"""
    return {"status": "ready"}

@router.get("/liveness")
async def liveness_check():
    """Kubernetes liveness probe"""
    return {"status": "alive"}

def get_uptime() -> float:
    """Get process uptime in seconds"""
    return time.time() - _start_time

# Export the router (optional, but good practice)
health_router = router