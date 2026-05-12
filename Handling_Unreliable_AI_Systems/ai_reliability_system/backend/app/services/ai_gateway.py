from typing import Optional, Dict, Any
import time
import hashlib
import json
from datetime import datetime
from redis import Redis

from app.models.schemas import AIRequest, AIResponse
from app.services.hallucination_detector import HallucinationDetector
from app.services.schema_manager import SchemaManager
from app.services.cost_manager import CostManager
from app.services.rate_limiter import RateLimiter
from app.services.context_manager import ContextManager
from app.services.prompt_drift_detector import PromptDriftDetector
from app.config import settings

class AIGateway:
    def __init__(self, redis_client: Redis):

        self.redis = redis_client
        self.cache_manager = CacheManager(redis_client, default_ttl=3600)

        self.hallucination_detector = HallucinationDetector(ai_gateway=self)
        self.schema_manager = SchemaManager()

        print("---About to initialize cost manager")
        self.cost_manager = CostManager(settings.monthly_budget_usd)
        self.rate_limiter = RateLimiter(redis_client, settings.rate_limit_per_minute)
        self.context_manager = ContextManager(settings.max_tokens_per_request)
    
        # Initialize PromptDriftDetector with baseline prompt from settings
        baseline = settings.baseline_system_prompt
        self.prompt_drift_detector = PromptDriftDetector(baseline_prompt=baseline)


    async def process_request(self, request: AIRequest) -> AIResponse:
        start_time = time.time()
        
        print("reacched here ... 2")
        # 1. Check cache using CacheManager
        cache_key = self._get_cache_key(request)
        cached = self.cache_manager.get(cache_key)
        if cached:
            print(f"✅ Cache hit for key: {cache_key}")
            return AIResponse(**cached)
        
        print(f"❌ Cache miss for key: {cache_key}")

        #print("cahced response is: " + cached)
        if cached:
            return AIResponse.parse_raw(cached)

        # 2. Check rate limit with proper error handling
        try:
            await self.rate_limiter.check_limit(request.api_key or "default")
        except Exception as e:
            if "Rate limit exceeded" in str(e):
                # Return a proper rate limit response
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded. Please try again later."
                )
            raise

        print("reacched here ... 4")
        # 3. Check and fix prompt drift - NOW WITH ACTUAL FIX
        if self.prompt_drift_detector.detect_drift(request.prompt):
            print(f"⚠️ Prompt drift detected for: {request.prompt[:50]}...")
            original_prompt = request.prompt
            request.prompt = self.prompt_drift_detector.fix_prompt(request.prompt)
            print(f"✅ Fixed prompt: {request.prompt[:50]}...")
            
            # Optional: Log the drift for monitoring
            if self.redis:
                drift_log = {
                    "original": original_prompt,
                    "fixed": request.prompt,
                    "timestamp": time.time()
                }
                self.redis.lpush("prompt_drift_log", json.dumps(drift_log))
        
        print("reacched here ... 5")
        # 4. Handle context window
        processed_context = self.context_manager.process(request.prompt, request.context)
        
        print("reacched here ... 6")
        # 5. Make AI call with cost management
        response = await self.cost_manager.make_ai_call(
            prompt=processed_context,
            model=request.model or settings.primary_model
        )

        print("reacched here ... 7")
        # Validate and transform schema
        validated_output = self.schema_manager.validate(output)
        
        # If transformation was applied, log it
        if validated_output != output:
            print(f"🔄 Schema transformation applied")

        print("reacched here ... 8")
        # 7. Detect hallucinations
        confidence = await self.hallucination_detector.check(
            request.prompt, 
            validated,
            use_consistency=use_consistency  # Enable self-consistency check
        )

        # If confidence is very low, regenerate with lower temperature
        if confidence < 0.6 and request.max_retries > 0:
            print(f"⚠️ Low confidence ({confidence:.2f}), regenerating with lower temperature")
            retry_request = AIRequest(
                prompt=request.prompt,
                context=request.context,
                temperature=0.3,  # Lower temperature for consistency
                max_retries=request.max_retries - 1
            )
            return await self.process_request(retry_request)

        print("reacched here ... 9")
        result = AIResponse(
            output=validated,
            confidence=confidence,
            tokens_used=self.context_manager.last_tokens_used,
            model_used=settings.primary_model,
            processing_time=time.time() - start_time
        )

        print("reacched here ... 10")
        # 8. Cache if high confidence
        if confidence > 0.8:
            self.cache_manager.set(
                cache_key, 
                {
                    "output": validated,
                    "confidence": confidence,
                    "tokens_used": tokens_used,
                    "model_used": "mock-gpt-4" if self.use_mock else settings.primary_model,
                    "processing_time": time.time() - start_time,
                    "cached": True,
                    "timestamp": datetime.now().isoformat()
                },
                ttl=3600
            )

        print("reacched here ... 11")
        # Add debug logging
        print(f"🔍 Returning AIResponse object: {type(result)}")
        print(f"📦 Result content: {result}")
        
        return result
    
    def _get_cache_key(self, request: AIRequest) -> str:
        """Generate cache key from request"""
        content = f"{request.prompt}:{request.context}"
        return f"ai:response:{hashlib.md5(content.encode()).hexdigest()}"
    
    async def health_check(self) -> bool:
        """Check if AI service is healthy"""
        try:
            test_response = await self.cost_manager.make_ai_call(
                prompt="Health check",
                model=settings.primary_model,
                max_tokens=10
            )
            return bool(test_response)
        except Exception:
            return False

# def get_ai_gateway():
#     """Dependency injection for AI Gateway"""
#     from app.main import ai_gateway
#     return ai_gateway

def get_ai_gateway():
    """Dependency injection for AI Gateway"""
    try:
        from app.main import ai_gateway
        
        print(f"🔧 get_ai_gateway called")
        print(f"ai_gateway instance: {ai_gateway}")
        print(f"ai_gateway type: {type(ai_gateway)}")
        
        if ai_gateway is None:
            print("❌ ERROR: ai_gateway is None! Creating fallback...")
            from app.main import redis_client
            if redis_client is None:
                import redis
                redis_client = redis.Redis(decode_responses=True)
            return AIGateway(redis_client)
        
        return ai_gateway
    
    except Exception as e:
        print(f"❌ Error in get_ai_gateway: {e}")
        import traceback
        traceback.print_exc()
        raise