# src/api/models.py - Add provider and model fields
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from enum import Enum

class Role(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class Message(BaseModel):
    role: Role
    content: str

class ChatCompletionRequest(BaseModel):
    messages: List[Message]
    model_family: Optional[str] = Field(default="default")
    provider: Optional[str] = Field(default=None)  # New: force specific provider
    model: Optional[str] = Field(default=None)     # New: force specific model
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1000, ge=1, le=4000)
    stream: bool = False