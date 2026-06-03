# src/gateway/providers.py - Updated to handle config arguments
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, AsyncIterator, List
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import aiohttp
import json
import os
import time

@dataclass
class LLMResponse:
    text: str
    provider: str
    model: str
    latency_ms: float
    cost: float
    tokens_prompt: int
    tokens_completion: int
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

class BaseProvider(ABC):
    @abstractmethod
    async def chat_completion(self, messages: List[Dict], model: str, **kwargs) -> LLMResponse:
        pass

class OpenAIClient(BaseProvider):
    def __init__(self, api_key: str = None, timeout: int = 30, **kwargs):
        # Accept any kwargs and ignore them
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key required")
        self.base_url = "https://api.openai.com/v1"
        self.timeout = timeout
        self._session = None
        print(f"✅ OpenAI client initialized (timeout={timeout}s)")
    
    async def _get_session(self):
        if not self._session:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def chat_completion(self, messages: List[Dict], model: str, **kwargs) -> LLMResponse:
        start_time = time.time()
        
        session = await self._get_session()
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 1000),
            "top_p": kwargs.get("top_p", 1.0),
        }
        
        async with session.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        ) as resp:
            if resp.status != 200:
                error_data = await resp.text()
                raise Exception(f"OpenAI API error {resp.status}: {error_data}")
            data = await resp.json()
        
        latency = (time.time() - start_time) * 1000
        
        # Simple cost calculation
        prompt_tokens = data.get("usage", {}).get("prompt_tokens", 0)
        completion_tokens = data.get("usage", {}).get("completion_tokens", 0)
        cost = (prompt_tokens * 0.0000015) + (completion_tokens * 0.000002)
        
        return LLMResponse(
            text=data["choices"][0]["message"]["content"],
            provider="openai",
            model=model,
            latency_ms=latency,
            cost=cost,
            tokens_prompt=prompt_tokens,
            tokens_completion=completion_tokens,
            timestamp=datetime.utcnow(),
            metadata={"finish_reason": data["choices"][0]["finish_reason"]}
        )
    
    async def close(self):
        if self._session:
            await self._session.close()

class GroqClient(BaseProvider):
    def __init__(self, api_key: str = None, timeout: int = 30, **kwargs):
        # Accept any kwargs and ignore them
        self.api_key = api_key or os.getenv('GROQ_API_KEY')
        if not self.api_key:
            raise ValueError("Groq API key required")
        self.base_url = "https://api.groq.com/openai/v1"
        self.timeout = timeout
        self._session = None
        print(f"✅ Groq client initialized (timeout={timeout}s)")
    
    async def _get_session(self):
        if not self._session:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def chat_completion(self, messages: List[Dict], model: str, **kwargs) -> LLMResponse:
        start_time = time.time()
        
        session = await self._get_session()
        
        # Map old model names to new ones
        model_mapping = {
            "llama3-8b-8192": "llama-3.1-8b-instant",
            "llama3-70b-8192": "llama-3.3-70b-versatile",
            "llama-3.3-70b-versatile": "llama-3.3-70b-versatile",
            "mixtral-8x7b-32768": "mixtral-8x7b-32768",
            "llama-3.1-8b-instant": "llama-3.1-8b-instant",
            "gemma2-9b-it": "gemma2-9b-it",
        }
        actual_model = model_mapping.get(model, model)
        
        payload = {
            "model": actual_model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 1000),
            "top_p": kwargs.get("top_p", 1.0),
        }
        
        async with session.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        ) as resp:
            if resp.status != 200:
                error_data = await resp.text()
                raise Exception(f"Groq API error {resp.status}: {error_data}")
            data = await resp.json()
        
        latency = (time.time() - start_time) * 1000
        
        # Simple cost calculation for Groq
        prompt_tokens = data.get("usage", {}).get("prompt_tokens", 0)
        completion_tokens = data.get("usage", {}).get("completion_tokens", 0)
        
        # Groq pricing
        if "70b" in actual_model:
            cost = (prompt_tokens * 0.0000007) + (completion_tokens * 0.0000008)
        elif "mixtral" in actual_model:
            cost = (prompt_tokens * 0.0000005) + (completion_tokens * 0.0000005)
        else:
            cost = (prompt_tokens * 0.0000001) + (completion_tokens * 0.0000001)
        
        return LLMResponse(
            text=data["choices"][0]["message"]["content"],
            provider="groq",
            model=actual_model,
            latency_ms=latency,
            cost=cost,
            tokens_prompt=prompt_tokens,
            tokens_completion=completion_tokens,
            timestamp=datetime.utcnow(),
            metadata={"finish_reason": data["choices"][0]["finish_reason"]}
        )
    
    async def close(self):
        if self._session:
            await self._session.close()

class TogetherClient(BaseProvider):
    def __init__(self, api_key: str = None, timeout: int = 30, **kwargs):
        self.api_key = api_key or os.getenv('TOGETHER_API_KEY')
        self.timeout = timeout
        self._session = None
        print(f"✅ Together client initialized (timeout={timeout}s)")
    
    async def _get_session(self):
        if not self._session:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def chat_completion(self, messages: List[Dict], model: str, **kwargs) -> LLMResponse:
        if not self.api_key:
            raise Exception("Together API key not configured")
        
        start_time = time.time()
        session = await self._get_session()
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 1000),
        }
        
        async with session.post(
            "https://api.together.xyz/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        ) as resp:
            if resp.status != 200:
                raise Exception(f"Together API error {resp.status}")
            data = await resp.json()
        
        latency = (time.time() - start_time) * 1000
        
        return LLMResponse(
            text=data["choices"][0]["message"]["content"],
            provider="together",
            model=model,
            latency_ms=latency,
            cost=0.0001,  # Approximate
            tokens_prompt=0,
            tokens_completion=0,
            timestamp=datetime.utcnow(),
            metadata={}
        )
    
    async def close(self):
        if self._session:
            await self._session.close()