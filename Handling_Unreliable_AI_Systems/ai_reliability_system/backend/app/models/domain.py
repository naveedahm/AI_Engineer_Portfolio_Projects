from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

class ErrorType(str, Enum):
    HALLUCINATION = "hallucination"
    RATE_LIMIT = "rate_limit"
    CONTEXT_WINDOW = "context_window"
    SCHEMA_MISMATCH = "schema_mismatch"
    COST_SPIKE = "cost_spike"
    PROMPT_DRIFT = "prompt_drift"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"

@dataclass
class ProcessingContext:
    request_id: str
    start_time: datetime
    prompt_tokens: int
    completion_tokens: int
    model: str
    temperature: float
    retry_count: int = 0
    metadata: Dict[str, Any] = None

@dataclass
class ErrorRecord:
    error_type: ErrorType
    timestamp: datetime
    message: str
    context: ProcessingContext
    stack_trace: Optional[str] = None

@dataclass
class CacheEntry:
    key: str
    value: str
    created_at: datetime
    ttl: int
    hit_count: int = 0