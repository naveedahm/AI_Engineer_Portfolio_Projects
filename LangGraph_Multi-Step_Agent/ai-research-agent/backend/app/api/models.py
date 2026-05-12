from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    """Role of the message sender"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(BaseModel):
    """Individual chat message"""
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None


class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    message: str = Field(..., description="User's message", min_length=1, max_length=5000)
    thread_id: str = Field(..., description="Conversation thread ID", min_length=1)
    stream: bool = Field(False, description="Whether to stream the response")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "What are the latest developments in quantum computing?",
                "thread_id": "thread_123456",
                "stream": False
            }
        }
    )


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""
    message: str = Field(..., description="Assistant's response")
    thread_id: str = Field(..., description="Conversation thread ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    timestamp: datetime = Field(default_factory=datetime.now)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Based on my research, quantum computing advancements include...",
                "thread_id": "thread_123456",
                "metadata": {
                    "search_queries": ["quantum computing 2024 breakthroughs", "latest quantum supremacy"],
                    "research_loops": 2,
                    "sources_used": 4
                }
            }
        }
    )


class StreamEvent(BaseModel):
    """Event model for streaming responses"""
    type: Literal["token", "tool_start", "tool_end", "final", "error", "done"]
    content: Optional[str] = None
    tool: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class SessionInfo(BaseModel):
    """Information about a chat session"""
    thread_id: str
    created_at: datetime
    last_updated: datetime
    message_count: int
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SessionResponse(BaseModel):
    """Response model for session endpoints"""
    thread_id: str
    messages: List[Message] = Field(default_factory=list)
    session_info: Optional[SessionInfo] = None


class SearchQuery(BaseModel):
    """Model for search query"""
    query: str
    timestamp: datetime = Field(default_factory=datetime.now)
    results_count: Optional[int] = None


class SearchResult(BaseModel):
    """Model for individual search result"""
    query: str
    result: str
    source: Optional[str] = None
    relevance_score: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class ResearchStep(BaseModel):
    """Record of a research step in the agent's workflow"""
    step_type: Literal["generate_queries", "execute_search", "reflect_on_results", "finalize_answer"]
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    duration_ms: float
    timestamp: datetime = Field(default_factory=datetime.now)


class AgentState(BaseModel):
    """Full state of the research agent for a thread"""
    thread_id: str
    messages: List[Message]
    search_queries: List[str] = Field(default_factory=list)
    search_results: List[SearchResult] = Field(default_factory=list)
    research_loop_count: int = 0
    is_information_sufficient: bool = False
    final_answer: Optional[str] = None
    error_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    research_steps: List[ResearchStep] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.now)


class ErrorResponse(BaseModel):
    """Standard error response model"""
    error: str
    code: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "Rate limit exceeded",
                "code": "RATE_LIMIT_ERROR",
                "details": {"retry_after": 60}
            }
        }
    )


class HealthResponse(BaseModel):
    """Health check response model"""
    status: Literal["healthy", "degraded", "unhealthy"]
    version: str
    timestamp: datetime = Field(default_factory=datetime.now)
    components: Dict[str, str] = Field(default_factory=dict)


class ConfigUpdateRequest(BaseModel):
    """Request model for updating agent configuration"""
    max_research_loops: Optional[int] = Field(None, ge=1, le=10)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    model_name: Optional[str] = None
    search_provider: Optional[Literal["duckduckgo", "google", "bing"]] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "max_research_loops": 3,
                "temperature": 0.7,
                "model_name": "gpt-4"
            }
        }
    )


class BatchRequest(BaseModel):
    """Request model for batch processing"""
    messages: List[str] = Field(..., min_items=1, max_items=10)
    thread_id: str
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "messages": [
                    "What is machine learning?",
                    "Explain neural networks",
                    "Compare supervised and unsupervised learning"
                ],
                "thread_id": "batch_thread_123"
            }
        }
    )


class BatchResponse(BaseModel):
    """Response model for batch processing"""
    thread_id: str
    responses: List[ChatResponse]
    total_duration_ms: float
    successful_count: int
    failed_count: int


class FeedbackRequest(BaseModel):
    """Request model for user feedback"""
    thread_id: str
    message_id: Optional[str] = None
    rating: Literal[1, 2, 3, 4, 5] = Field(..., description="Rating from 1-5")
    comment: Optional[str] = Field(None, max_length=500)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MetricsResponse(BaseModel):
    """Response model for agent metrics"""
    total_requests: int
    average_response_time_ms: float
    average_search_queries_per_request: float
    average_research_loops: float
    success_rate: float
    time_range: Dict[str, datetime]
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_requests": 1234,
                "average_response_time_ms": 2450.5,
                "average_search_queries_per_request": 2.3,
                "average_research_loops": 1.8,
                "success_rate": 0.95,
                "time_range": {
                    "start": "2024-01-01T00:00:00",
                    "end": "2024-01-31T23:59:59"
                }
            }
        }
    )