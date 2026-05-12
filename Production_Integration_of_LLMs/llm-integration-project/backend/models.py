from pydantic import BaseModel, Field, validator
from typing import Optional, List
from enum import Enum
from datetime import datetime

class SentimentEnum(str, Enum):
    positive = "positive"
    negative = "negative"
    neutral = "neutral"

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    user_id: Optional[str] = None
    user_tier: str = Field("free", pattern="^(free|premium|enterprise)$")
    context: Optional[dict] = {}
    
    @validator('message')
    def validate_message(cls, v):
        if not v.strip():
            raise ValueError('Message cannot be empty')
        return v

class LLMResponse(BaseModel):
    sentiment: SentimentEnum
    confidence: float = Field(..., ge=0, le=1)
    response_text: str
    suggested_actions: List[str] = []
    processing_time_ms: float
    cost_info: Optional[dict] = None
    rate_limit_info: Optional[dict] = None
    
    @validator('confidence')
    def validate_confidence(cls, v):
        if v < 0 or v > 1:
            raise ValueError('Confidence must be between 0 and 1')
        return v

class ErrorResponse(BaseModel):
    error: str
    fallback_response: str
    error_type: str
    timestamp: datetime = Field(default_factory=datetime.now)

class MetricsResponse(BaseModel):
    total_requests: int
    total_errors: int
    average_latency_ms: float
    total_cost_usd: float
    cache_hit_rate: float