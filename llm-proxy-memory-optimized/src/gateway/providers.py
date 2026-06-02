# src/gateway/providers.py - Fixed version
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, AsyncIterator, List
from dataclasses import dataclass
from datetime import datetime
import asyncio
import aiohttp
import os

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
    metadata: Dict[str, Any] = None

class BaseProvider(ABC):
    @abstractmethod
    async def chat_completion(self, messages: List[Dict], model: str, **kwargs) -> LLMResponse:
        pass

# Fixed GroqClient - no 'enabled' parameter
class GroqClient(BaseProvider):
    def __init__(self, api_key: str = None, timeout: int = 30):
        self.api_key = api_key or os.getenv('GROQ_API_KEY')
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable not set")
        self.base_url = "https://api.groq.com/openai/v1"
        self.timeout = timeout
        self._session = None
    
    async def _get_session(self):
        if not self._session:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def chat_completion(self, messages: List[Dict], model: str, **kwargs) -> LLMResponse:
        start_time = asyncio.get_event_loop().time()
        
        session = await self._get_session()
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 1000),
        }
        
        async with session.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        ) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise Exception(f"Groq API error {resp.status}: {error_text}")
            data = await resp.json()
        
        latency = (asyncio.get_event_loop().time() - start_time) * 1000
        
        # Simple cost calculation (Groq is very cheap)
        prompt_tokens = data.get("usage", {}).get("prompt_tokens", 0)
        completion_tokens = data.get("usage", {}).get("completion_tokens", 0)
        cost = (prompt_tokens + completion_tokens) / 1000000  # ~$0.000001 per 1K tokens
        
        return LLMResponse(
            text=data["choices"][0]["message"]["content"],
            provider="groq",
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

# Fixed OpenAIClient
class OpenAIClient(BaseProvider):
    def __init__(self, api_key: str = None, timeout: int = 30):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        self.base_url = "https://api.openai.com/v1"
        self.timeout = timeout
        self._session = None
    
    async def _get_session(self):
        if not self._session:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def chat_completion(self, messages: List[Dict], model: str, **kwargs) -> LLMResponse:
        start_time = asyncio.get_event_loop().time()
        
        session = await self._get_session()
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 1000),
        }
        
        async with session.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        ) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise Exception(f"OpenAI API error {resp.status}: {error_text}")
            data = await resp.json()
        
        latency = (asyncio.get_event_loop().time() - start_time) * 1000
        
        prompt_tokens = data.get("usage", {}).get("prompt_tokens", 0)
        completion_tokens = data.get("usage", {}).get("completion_tokens", 0)
        cost = (prompt_tokens * 0.000001) + (completion_tokens * 0.000002)  # Approximate
        
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

# Fixed TogetherClient
class TogetherClient(BaseProvider):
    def __init__(self, api_key: str = None, timeout: int = 30):
        self.api_key = api_key or os.getenv('TOGETHER_API_KEY')
        if not self.api_key:
            raise ValueError("TOGETHER_API_KEY environment variable not set")
        self.base_url = "https://api.together.xyz/v1"
        self.timeout = timeout
        self._session = None
    
    async def _get_session(self):
        if not self._session:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def chat_completion(self, messages: List[Dict], model: str, **kwargs) -> LLMResponse:
        start_time = asyncio.get_event_loop().time()
        
        session = await self._get_session()
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 1000),
        }
        
        async with session.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        ) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise Exception(f"Together API error {resp.status}: {error_text}")
            data = await resp.json()
        
        latency = (asyncio.get_event_loop().time() - start_time) * 1000
        
        prompt_tokens = data.get("usage", {}).get("prompt_tokens", 0)
        completion_tokens = data.get("usage", {}).get("completion_tokens", 0)
        cost = (prompt_tokens + completion_tokens) / 1000000
        
        return LLMResponse(
            text=data["choices"][0]["message"]["content"],
            provider="together",
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