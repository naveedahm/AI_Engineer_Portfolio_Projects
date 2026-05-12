import asyncio
import hashlib
import json
from typing import Optional, Dict
import openai
from tenacity import retry, stop_after_attempt, wait_exponential
from loguru import logger
from models import LLMResponse, SentimentEnum
from monitoring.metrics import (
    track_llm_request, 
    record_tokens, 
    record_cache_hit, 
    record_cache_miss
)
from monitoring.cost_tracker import CostTracker
import os
from dotenv import load_dotenv

load_dotenv()

class LLMService:
    def __init__(self):
        openai.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        self.cache = {}
        self.cost_tracker = CostTracker()
        
    @track_llm_request(model="gpt-3.5-turbo", endpoint="/chat")
    async def process_message(self, message: str, user_id: str, user_tier: str = "free") -> LLMResponse:
        # Check cache
        cache_key = hashlib.md5(f"{message}:{user_id}".encode()).hexdigest()
        if cache_key in self.cache:
            logger.info(f"Cache hit for {cache_key}")
            record_cache_hit(self.model)
            return self.cache[cache_key]
        
        record_cache_miss(self.model)
        
        prompt = self._create_prompt(message)
        start_time = asyncio.get_event_loop().time()
        
        try:
            response_text, prompt_tokens, completion_tokens = await self._call_openai_with_retry(prompt)
            parsed_response = self._parse_llm_response(response_text)
            
            # Record token usage
            record_tokens(self.model, prompt_tokens, completion_tokens)
            
            # Track costs
            cost_info = await self.cost_tracker.track_usage(
                model=self.model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                user_id=user_id
            )
            
            llm_response = LLMResponse(
                sentiment=parsed_response.get("sentiment", "neutral"),
                confidence=float(parsed_response.get("confidence", 0.5)),
                response_text=parsed_response.get("response", "I'm not sure how to respond."),
                suggested_actions=parsed_response.get("actions", []),
                processing_time_ms=(asyncio.get_event_loop().time() - start_time) * 1000,
                cost_info=cost_info
            )
            
            self.cache[cache_key] = llm_response
            return llm_response
            
        except Exception as e:
            logger.error(f"LLM processing failed: {e}")
            return self._create_fallback_response(start_time, str(e))
    
    def _create_prompt(self, message: str) -> str:
        return f"""You are a helpful customer support AI. Analyze this user message and respond appropriately.

User message: "{message}"

Respond with valid JSON only (no markdown, no extra text):
{{
    "sentiment": "positive" or "negative" or "neutral",
    "confidence": 0.0 to 1.0,
    "response": "your empathetic and helpful response",
    "actions": ["action1", "action2"]
}}

Examples of actions: "escalate_to_human", "offer_discount", "request_clarification", "none"
"""
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def _call_openai_with_retry(self, prompt: str):
        try:
            response = await asyncio.wait_for(
                self._async_openai_call(prompt),
                timeout=30.0
            )
            # Estimate tokens (simplified - use actual token counting in production)
            prompt_tokens = len(prompt) // 4
            completion_tokens = len(response) // 4
            return response, prompt_tokens, completion_tokens
        except asyncio.TimeoutError:
            logger.error("OpenAI API timeout")
            raise
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    async def _async_openai_call(self, prompt: str) -> str:
        client = openai.AsyncOpenAI()
        response = await client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=200
        )
        return response.choices[0].message.content
    
    def _parse_llm_response(self, response_text: str) -> Dict:
        try:
            response_text = response_text.strip()
            
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            response_json = json.loads(response_text)
            return response_json
            
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON: {response_text}")
            return {
                "sentiment": "neutral",
                "confidence": 0.3,
                "response": "I'm having trouble processing that. Could you rephrase?",
                "actions": ["request_clarification"]
            }
    
    def _create_fallback_response(self, start_time: float, error_msg: str) -> LLMResponse:
        return LLMResponse(
            sentiment=SentimentEnum.neutral,
            confidence=0.0,
            response_text="I'm currently experiencing technical difficulties. Please try again in a moment or contact support directly.",
            suggested_actions=["escalate_to_human", "retry_later"],
            processing_time_ms=(asyncio.get_event_loop().time() - start_time) * 1000
        )