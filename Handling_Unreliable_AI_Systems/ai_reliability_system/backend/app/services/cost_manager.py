import time
import tiktoken
from typing import Optional
from openai import OpenAI, APIError, RateLimitError, APIConnectionError
from app.config import settings
import httpx

class CustomHTTPClient(httpx.Client):
    def __init__(self, *args, **kwargs):
        kwargs.pop("proxies", None) # Remove 'proxies' if present
        super().__init__(*args, **kwargs)

class CostManager:

    def __init__(self, monthly_budget: float = 100.0, redis_client=None):

        print("Cost manager constructor called ....")
        self.monthly_budget = monthly_budget
        self.redis = redis_client
        self.use_real_api = False
        
        # Initialize OpenAI client if API key exists
        if settings.openai_api_key and settings.openai_api_key != "test-key-for-development":
            try:

                # Remove any proxy-related arguments
                # The v1.x client doesn't accept 'proxies' directly
                self.client = OpenAI(http_client=CustomHTTPClient(),
                api_key=settings.openai_api_key)

                # self.client = OpenAI(
                #     api_key=settings.openai_api_key,
                #     # Do NOT include: proxies=..., proxy=..., http_proxy=..., etc.
                # )
                self.use_real_api = True
                print(f"✅ OpenAI client initialized successfully")
            except Exception as e:
                print(f"❌ Failed to initialize OpenAI client: {e}")
                self.client = None
        else:
            print("⚠️ No API key found - using mock mode")
            self.client = None

    async def make_ai_call(self, prompt: str, model: str = "gpt-3.5-turbo", **kwargs) -> str:
        """Make AI call using OpenAI API v1.x"""

        print("reached here 6.01 ....")
        if not self.use_real_api or not self.client:
            # Return mock response
            print("returning mock resposne since OpenAI Api is not initialized")
            return f"AI response to: {prompt[:100]}"
        print("reached here 6.02 ....")

        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # ✅ Correct v1.x syntax
                print("reached here 6.1 ....")
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are a helpful AI assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=kwargs.get('temperature', 0.7),
                    max_tokens=kwargs.get('max_tokens', 1000),
                    timeout=30.0
                )
                
                print("reached here 6.2 .....")
                # Extract response text
                result = response.choices[0].message.content
                
                print("reached here 6.3 .....")
                # Track cost (optional)
                await self._track_cost(prompt, result, model)
                
                return result
                
            except RateLimitError as e:
                print(f"⚠️ Rate limit hit (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    return f"Rate limit exceeded. Please try again later."
                    
            except APIConnectionError as e:
                print(f"⚠️ Connection error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                else:
                    return f"Unable to connect to AI service. Please check your internet connection."
                    
            except APIError as e:
                print(f"❌ API error: {e}")
                return f"AI service error: {str(e)}"
                
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
                if attempt == max_retries - 1:
                    return f"An unexpected error occurred: {str(e)}"
                time.sleep(1)
        
        return "Failed to get response after multiple retries."
    
    async def _track_cost(self, prompt: str, response: str, model: str):
        """Track API costs (optional implementation)"""
        try:
            encoder = tiktoken.get_encoding("cl100k_base")
            input_tokens = len(encoder.encode(prompt))
            output_tokens = len(encoder.encode(response))
            total_tokens = input_tokens + output_tokens
            
            # Optional: Store in Redis
            if self.redis:
                from datetime import date
                today = date.today().isoformat()
                self.redis.incrby(f"tokens_used:{today}", total_tokens)
                
            print(f"📊 Token usage: {total_tokens} tokens (in: {input_tokens}, out: {output_tokens})")
            
        except Exception as e:
            print(f"⚠️ Cost tracking error: {e}")