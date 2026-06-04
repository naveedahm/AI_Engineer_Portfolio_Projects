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
os.environ['CURL_CA_BUNDLE'] = ''
from dotenv import load_dotenv


# Load variables from the .env file
load_dotenv()

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

class OllamaClient(BaseProvider):
    """Ollama Local Client - Free, private LLM inference"""
    
    def __init__(self, base_url: str = "http://localhost:11434", timeout: int = 120, **kwargs):
        self.base_url = base_url
        self.timeout = timeout
        self._session = None
        self.enabled = True
        print(f"✅ Ollama client initialized (url={base_url}, timeout={timeout}s)")
    
    async def _get_session(self):
        if not self._session:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def chat_completion(self, messages: List[Dict], model: str, **kwargs) -> LLMResponse:
        start_time = time.time()
        session = await self._get_session()
        
        # Check if Ollama is running
        try:
            async with session.get(f"{self.base_url}/api/tags", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status != 200:
                    raise Exception("Ollama service not running")
        except Exception as e:
            raise Exception(f"Cannot connect to Ollama at {self.base_url}. Is Ollama running? Error: {e}")
        
        # Convert messages to Ollama format
        # Ollama expects 'prompt' for non-chat models, but supports chat format
        last_message = messages[-1]["content"]
        
        # Build context from previous messages
        context = ""
        if len(messages) > 1:
            context = "\n".join([f"{m['role']}: {m['content']}" for m in messages[:-1]])
        
        payload = {
            "model": model,
            "prompt": last_message,
            "system": context if context else "",
            "temperature": kwargs.get("temperature", 0.7),
            "top_p": kwargs.get("top_p", 0.9),
            "stream": False,
            "options": {
                "num_predict": kwargs.get("max_tokens", 1000),
                "stop": kwargs.get("stop", [])
            }
        }
        
        async with session.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        ) as resp:
            if resp.status != 200:
                error_data = await resp.text()
                raise Exception(f"Ollama error {resp.status}: {error_data}")
            data = await resp.json()
        
        latency = (time.time() - start_time) * 1000
        
        # Ollama provides token counts
        prompt_tokens = data.get("prompt_eval_count", 0)
        completion_tokens = data.get("eval_count", 0)
        
        return LLMResponse(
            text=data.get("response", ""),
            provider="ollama",
            model=model,
            latency_ms=latency,
            cost=0.0,  # Free! Local inference
            tokens_prompt=prompt_tokens,
            tokens_completion=completion_tokens,
            timestamp=datetime.utcnow(),
            metadata={
                "total_duration": data.get("total_duration", 0),
                "load_duration": data.get("load_duration", 0),
                "prompt_eval_duration": data.get("prompt_eval_duration", 0),
                "eval_duration": data.get("eval_duration", 0)
            }
        )
    
    async def stream_completion(self, messages: List[Dict], model: str, **kwargs) -> AsyncIterator[str]:
        """Streaming completion for Ollama"""
        session = await self._get_session()
        
        last_message = messages[-1]["content"]
        context = "\n".join([f"{m['role']}: {m['content']}" for m in messages[:-1]]) if len(messages) > 1 else ""
        
        payload = {
            "model": model,
            "prompt": last_message,
            "system": context,
            "temperature": kwargs.get("temperature", 0.7),
            "stream": True
        }
        
        async with session.post(
            f"{self.base_url}/api/generate",
            json=payload
        ) as resp:
            async for line in resp.content:
                if line:
                    try:
                        data = json.loads(line.decode('utf-8'))
                        if data.get("response"):
                            yield data["response"]
                        if data.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue
    
    async def close(self):
        if self._session:
            await self._session.close()

# src/gateway/providers.py - Add HuggingFaceClient

# src/gateway/providers.py - Updated HuggingFaceClient using huggingface_hub

class HuggingFaceClient(BaseProvider):
    """Hugging Face Client using official huggingface_hub library"""
    
    def __init__(self, api_key: str = None, timeout: int = 90, **kwargs):
        self.api_key = api_key or os.getenv('HUGGINGFACE_TOKEN')
        self.timeout = timeout
        
        # Initialize the official InferenceClient
        try:
            from huggingface_hub import InferenceClient
            if self.api_key:
                self.client = InferenceClient(token=self.api_key, timeout=timeout)
                print(f"✅ Hugging Face client initialized with API key (timeout={timeout}s)")
            else:
                # No API key - use free tier with rate limits
                self.client = InferenceClient(timeout=timeout)
                print(f"⚠️  Hugging Face client initialized without API key (rate-limited)")
        except ImportError:
            raise ImportError("huggingface_hub not installed. Run: pip install huggingface_hub")
        
        self._session = None
    
    async def chat_completion(self, messages: List[Dict], model: str, **kwargs) -> LLMResponse:
        """Chat completion using huggingface_hub InferenceClient"""
        start_time = time.time()
        
        # Convert messages to the format expected by huggingface_hub
        prompt = self._format_messages(messages)
        
        try:
            # Run the inference (this is synchronous, so we need to run it in a thread pool)
            import asyncio
            loop = asyncio.get_event_loop()
            
            # Prepare parameters
            params = {
                "temperature": kwargs.get("temperature", 0.7),
                "max_new_tokens": kwargs.get("max_tokens", 1000),
                "top_p": kwargs.get("top_p", 0.95),
                "do_sample": True,
                "return_full_text": False
            }
            
            # Make the API call
            result = await loop.run_in_executor(
                None,
                lambda: self.client.text_generation(
                    prompt,
                    model=model,
                    **params
                )
            )
            
            latency = (time.time() - start_time) * 1000
            
            # Estimate tokens (simplified)
            prompt_tokens = len(prompt.split())
            completion_tokens = len(result.split())
            
            return LLMResponse(
                text=result.strip(),
                provider="huggingface",
                model=model,
                latency_ms=latency,
                cost=0.0,  # Free tier
                tokens_prompt=prompt_tokens,
                tokens_completion=completion_tokens,
                timestamp=datetime.utcnow(),
                metadata={"api_type": "huggingface_hub", "auth": self.api_key is not None}
            )
            
        except Exception as e:
            raise Exception(f"Hugging Face inference failed: {e}")
    
    async def stream_completion(self, messages: List[Dict], model: str, **kwargs) -> AsyncIterator[str]:
        """Streaming completion using huggingface_hub"""
        prompt = self._format_messages(messages)
        
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            
            # Prepare parameters
            params = {
                "temperature": kwargs.get("temperature", 0.7),
                "max_new_tokens": kwargs.get("max_tokens", 1000),
                "top_p": kwargs.get("top_p", 0.95),
                "do_sample": True
            }
            
            # Use streaming
            stream = await loop.run_in_executor(
                None,
                lambda: self.client.text_generation(
                    prompt,
                    model=model,
                    stream=True,
                    **params
                )
            )
            
            # Yield tokens as they arrive
            for token in stream:
                if token:
                    yield token
                    
        except Exception as e:
            raise Exception(f"Hugging Face streaming failed: {e}")
    
    def _format_messages(self, messages: List[Dict]) -> str:
        """Convert OpenAI-style messages to prompt format"""
        formatted = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            
            if role == "system":
                formatted.append(f"System: {content}")
            elif role == "user":
                formatted.append(f"User: {content}")
            elif role == "assistant":
                formatted.append(f"Assistant: {content}")
        
        # Add assistant prefix for generation
        formatted.append("Assistant:")
        return "\n".join(formatted)
    
    async def close(self):
        if self._session:
            await self._session.close()