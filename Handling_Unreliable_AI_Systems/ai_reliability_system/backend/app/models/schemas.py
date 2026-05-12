from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator
from typing import Optional

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class AIRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    context: Optional[str] = None
    max_retries: int = Field(3, ge=0, le=5)
    api_key: Optional[str] = None
    model: Optional[str] = None
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    
    @validator('prompt')
    def prompt_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Prompt cannot be empty')
        return v

class AIResponse(BaseModel):
    output: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    tokens_used: int = Field(..., ge=0)
    model_used: str
    processing_time: float = Field(..., ge=0.0)
    cached: bool = False
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None

class BatchAIRequest(BaseModel):
    requests: List[AIRequest] = Field(..., max_items=100)
    parallel: bool = True

class BatchAIResponse(BaseModel):
    responses: List[AIResponse]
    total_time: float
    success_count: int
    failure_count: int

class HealthStatus(BaseModel):
    status: str
    redis_connected: bool
    ai_service_available: bool
    uptime_seconds: float
    version: str

class MetricsResponse(BaseModel):
    total_requests: int
    avg_response_time: float
    error_rate: float
    cache_hit_rate: float
    avg_confidence: float
    cost_today: float
    rate_limit_hits: int
