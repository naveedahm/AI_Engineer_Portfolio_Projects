from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import List
import asyncio
from datetime import datetime  # Add this import

from app.models.schemas import AIRequest, AIResponse, BatchAIRequest, BatchAIResponse
from app.services.ai_gateway import get_ai_gateway, AIGateway
from app.utils.metrics import track_request
from app.utils.cache import cache_response
from fastapi import APIRouter, HTTPException, Depends
import traceback

router = APIRouter()

@router.delete("/cache/{cache_key}")
async def invalidate_cache(cache_key: str, ai_gateway: AIGateway = Depends(get_ai_gateway)):
    """Invalidate a specific cache entry"""
    full_key = f"ai:response:{cache_key}"
    ai_gateway.cache_manager.delete(full_key)
    return {"status": "cache invalidated", "key": full_key}

@router.delete("/cache")
async def clear_all_cache(ai_gateway: AIGateway = Depends(get_ai_gateway)):
    """Clear all cache (Redis only)"""
    if ai_gateway.redis:
        # Clear all keys with prefix
        keys = ai_gateway.redis.keys("ai:response:*")
        if keys:
            ai_gateway.redis.delete(*keys)
        return {"status": "all cache cleared", "count": len(keys)}
    else:
        return {"status": "cache clear not supported", "message": "Using memory cache"}

@router.get("/cache/stats")
async def get_cache_stats(ai_gateway: AIGateway = Depends(get_ai_gateway)):
    """Get cache statistics"""
    if ai_gateway.redis:
        keys = ai_gateway.redis.keys("ai:response:*")
        return {
            "cached_items": len(keys),
            "cache_type": "redis",
            "keys": keys[:10]  # Return first 10 keys as sample
        }
    else:
        memory_cache_size = len(ai_gateway.cache_manager.memory_cache)
        return {
            "cached_items": memory_cache_size,
            "cache_type": "memory",
            "max_items": "unlimited (memory only)"
        }

@router.post("/process-with-consistency", response_model=AIResponse)
async def process_with_consistency_check(
    request: AIRequest,
    ai_gateway: AIGateway = Depends(get_ai_gateway)
):
    """Process request with enhanced hallucination detection"""
    
    # Process normally first
    result = await ai_gateway.process_request(request)
    
    # If confidence is low or for critical requests, run self-consistency check
    if result.confidence < 0.7 or request.metadata.get("critical", False):
        consistency_score = await ai_gateway.hallucination_detector.self_consistency_check(
            request.prompt, 
            result.output,
            num_samples=3
        )
        
        # Update confidence with consistency score
        result.confidence = (result.confidence + consistency_score) / 2
        
        # If still low confidence, flag as potentially hallucinated
        if result.confidence < 0.6:
            result.metadata = {
                "warning": "Response may be hallucinated",
                "consistency_score": consistency_score
            }
    
    return result

@router.post("/process", response_model=AIResponse)
@track_request
@cache_response(ttl=3600)
async def process_ai_request(
    request: AIRequest,
    background_tasks: BackgroundTasks,
    ai_gateway: AIGateway = Depends(get_ai_gateway)
):
    """Process a single AI request with reliability guarantees"""
    try:
        print("reacched here ... 1")
        result = await asyncio.wait_for(
            ai_gateway.process_request(request),
            timeout=30.0
        )

        # Debug logging
        print(f"📍 Route received result type: {type(result)}")
        print(f"📦 Route received result: {result}")

        return result
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Request timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/batch", response_model=BatchAIResponse)
async def process_batch_requests(
    batch_request: BatchAIRequest,
    ai_gateway: AIGateway = Depends(get_ai_gateway)
):
    """Process multiple AI requests concurrently"""
    start_time = asyncio.get_event_loop().time()
    
    if batch_request.parallel:
        tasks = [ai_gateway.process_request(req) for req in batch_request.requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    else:
        results = []
        for req in batch_request.requests:
            try:
                result = await ai_gateway.process_request(req)
                results.append(result)
            except Exception as e:
                results.append(e)
    
    # Process results
    responses = []
    success_count = 0
    failure_count = 0
    
    for result in results:
        if isinstance(result, Exception):
            failure_count += 1
            responses.append(AIResponse(
                output=f"Error: {str(result)}",
                confidence=0.0,
                tokens_used=0,
                model_used="error",
                processing_time=0.0
            ))
        else:
            success_count += 1
            responses.append(result)
    
    total_time = asyncio.get_event_loop().time() - start_time
    
    return BatchAIResponse(
        responses=responses,
        total_time=total_time,
        success_count=success_count,
        failure_count=failure_count
    )

@router.get("/metrics/health")
async def get_health_metrics(ai_gateway: AIGateway = Depends(get_ai_gateway)):
    """Get health metrics for the AI service"""
    is_healthy = await ai_gateway.health_check()
    return {
        "healthy": is_healthy,
        "service": "ai-gateway",
        "timestamp": datetime.now().isoformat()
    }

@router.get("/stats")
async def get_stats(ai_gateway: AIGateway = Depends(get_ai_gateway)):
    """Get statistics about AI gateway"""
    return {
        "message": "Stats endpoint - would return metrics",
        "note": "Prometheus metrics available at /metrics"
    }

@router.post("/transform-schema")
async def transform_schema_endpoint(
    data: Dict[str, Any],
    target_version: str = "v2"
):
    """Transform data between different schema versions"""
    try:
        transformed = schema_manager.transform_schema(data, target_version)
        return {
            "original": data,
            "transformed": transformed,
            "target_version": target_version
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/schema-versions")
async def get_schema_versions():
    """Get supported schema versions"""
    return {
        "supported_versions": schema_manager.get_supported_versions(),
        "current_version": schema_manager.default_version,
        "target_version": schema_manager.target_version
    }
