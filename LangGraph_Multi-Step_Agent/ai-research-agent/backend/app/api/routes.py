
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import json
import asyncio
import logging
from app.agent.graph import ResearchAgent

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()
agent = ResearchAgent()

# Request/Response Models
class ChatRequest(BaseModel):
    message: str
    thread_id: str
    stream: Optional[bool] = False

class ChatResponse(BaseModel):
    message: str
    thread_id: str
    metadata: Dict[str, Any] = {}
    timestamp: datetime = datetime.now()

class SessionResponse(BaseModel):
    thread_id: str
    messages: List[Dict] = []


@router.get("/health")
async def api_health_check():
    """API health check endpoint"""
    return {"status": "healthy", "api": "research-agent", "timestamp": datetime.now().isoformat()}

@router.get("/test")
async def test_endpoint():
    """Test endpoint to verify routing"""
    return {
        "status": "success",
        "message": "API routing is working correctly!",
        "timestamp": datetime.now().isoformat(),
        "available_endpoints": [
            "GET  /api/health",
            "POST /api/chat",
            "POST /api/chat/stream",
            "POST /api/chat/simple",
            "GET  /api/test",
            "GET  /api/sessions/{thread_id}",
            "DELETE /api/sessions/{thread_id}"
        ]
    }

@router.post("/chat/simple")
async def simple_chat(request: ChatRequest):
    """Simple chat endpoint for testing"""
    logger.info(f"Simple chat request: {request.message[:50]}...")
    
    try:
        result = await agent.process_message(request.message, request.thread_id)
        return ChatResponse(
            message=result["final_answer"],
            thread_id=request.thread_id,
            metadata={"mode": "simple", "timestamp": datetime.now().isoformat()}
        )
    except Exception as e:
        logger.error(f"Error in simple chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat")
async def chat(request: ChatRequest):
    """Main chat endpoint"""
    logger.info(f"Chat request: {request.message[:50]}...")
    
    try:
        result = await agent.process_message(request.message, request.thread_id)
        return ChatResponse(
            message=result["final_answer"],
            thread_id=request.thread_id,
            metadata={
                "search_queries": result.get("search_queries", []),
                "research_loops": result.get("research_loop_count", 0),
                "mode": "standard"
            }
        )
    except Exception as e:
        logger.error(f"Error in chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Streaming chat endpoint"""
    logger.info(f"Stream request: {request.message[:50]}...")
    
    async def generate():
        try:
            # Send start event
            yield f"data: {json.dumps({'type': 'start', 'content': 'Processing your request...'})}\n\n"
            await asyncio.sleep(0.1)
            
            # Get response from agent
            result = await agent.process_message(request.message, request.thread_id)
            response_text = result["final_answer"]
            
            # Stream character by character
            for i, char in enumerate(response_text):
                yield f"data: {json.dumps({'type': 'token', 'content': char})}\n\n"
                await asyncio.sleep(0.01)  # Small delay for realistic streaming
                
                # Simulate tool usage for demo
                if i == 20 and "search" in response_text.lower():
                    yield f"data: {json.dumps({'type': 'tool_start', 'tool': 'web_search'})}\n\n"
                    await asyncio.sleep(0.5)
                    yield f"data: {json.dumps({'type': 'tool_end', 'tool': 'web_search'})}\n\n"
            
            # Send final event
            yield f"data: {json.dumps({'type': 'final', 'content': response_text})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
        except Exception as e:
            logger.error(f"Stream error: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

@router.get("/sessions/{thread_id}")
async def get_session(thread_id: str):
    """Get session history"""
    return SessionResponse(
        thread_id=thread_id,
        messages=[]  # Return empty for now
    )

@router.delete("/sessions/{thread_id}")
async def delete_session(thread_id: str):
    """Delete a session"""
    return {"status": "deleted", "thread_id": thread_id}