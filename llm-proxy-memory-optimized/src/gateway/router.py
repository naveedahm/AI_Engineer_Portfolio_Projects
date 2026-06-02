# src/gateway/router.py - Complete working version
from typing import List, Dict, Any, Optional
import asyncio
import os
import gc
from datetime import datetime
from src.resilience.circuit_breaker import CircuitBreaker
from src.resilience.retry import LLMRetry
from src.cost.tracker import BudgetTracker
from src.gateway.providers import GroqClient, OpenAIClient, TogetherClient
from dotenv import load_dotenv
import os

load_dotenv()  # Loads variables from .env into environment
# TODO : Remove this line
print(os.getenv("GROQ_API_KEY"))


class LLMRouter:
    def __init__(self, config: Dict[str, Any]):
        self.providers = {}
        self.fallback_chains = {}
        self.circuit_breakers = {}
        self.retry_handler = LLMRetry()
        self.budget_tracker = BudgetTracker()
        
        # Cleanup tracking
        self._cleanup_task = None
        self._last_cleanup = 0
        
        # Initialize providers
        self._initialize_providers(config)
        self._setup_fallback_chains(config)
        
        # Start cleanup task
        self.start_cleanup_task()
    
    def _initialize_providers(self, config: Dict[str, Any]):
        """Initialize provider clients"""
        provider_configs = config.get('providers', {})
        
        # Map provider names to their classes
        provider_classes = {
            'groq': GroqClient,
            'openai': OpenAIClient,
            'together': TogetherClient,
        }
        
        print("\n📡 Initializing providers...")
        
        for provider_name, provider_cfg in provider_configs.items():
            # Check if provider is enabled (default to True)
            if not provider_cfg.get('enabled', True):
                print(f"  ⚠️  Provider {provider_name} is disabled, skipping...")
                continue
            
            # Get provider class
            provider_class = provider_classes.get(provider_name)
            if not provider_class:
                print(f"  ❌ Unknown provider: {provider_name}")
                continue
            
            try:
                # Initialize provider with only the parameters it expects
                if provider_name == 'groq':
                    api_key = os.getenv('GROQ_API_KEY')
                    if api_key and api_key != 'your-groq-key-here':
                        self.providers[provider_name] = provider_class(
                            api_key=api_key,
                            timeout=provider_cfg.get('timeout', 30)
                        )
                        print(f"  ✅ Initialized {provider_name} provider")
                    else:
                        print(f"  ⚠️  GROQ_API_KEY not found or invalid, skipping...")
                
                elif provider_name == 'openai':
                    api_key = os.getenv('OPENAI_API_KEY')
                    if api_key and api_key != 'your-openai-key-here':
                        self.providers[provider_name] = provider_class(
                            api_key=api_key,
                            timeout=provider_cfg.get('timeout', 30)
                        )
                        print(f"  ✅ Initialized {provider_name} provider")
                    else:
                        print(f"  ⚠️  OPENAI_API_KEY not found or invalid, skipping...")
                
                elif provider_name == 'together':
                    api_key = os.getenv('TOGETHER_API_KEY')
                    if api_key and api_key != 'your-together-key-here':
                        self.providers[provider_name] = provider_class(
                            api_key=api_key,
                            timeout=provider_cfg.get('timeout', 30)
                        )
                        print(f"  ✅ Initialized {provider_name} provider")
                    else:
                        print(f"  ⚠️  TOGETHER_API_KEY not found or invalid, skipping...")
                
                # Initialize circuit breaker for this provider
                if provider_name in self.providers:
                    self.circuit_breakers[provider_name] = CircuitBreaker(
                        name=provider_name,
                        failure_threshold=3,
                        recovery_timeout=30,
                        success_threshold=2
                    )
                
            except Exception as e:
                print(f"  ❌ Failed to initialize {provider_name}: {e}")
        
        if not self.providers:
            print("\n⚠️  WARNING: No providers initialized!")
            print("   Please check your API keys in the .env file")
            print("   Get a free Groq API key from: https://console.groq.com")
    
    def _setup_fallback_chains(self, config: Dict[str, Any]):
        """Configure fallback chains"""

        print("Setup fallback chains method has been called")

        models_config = config.get('models', {})
        
        if models_config:
            for chain_name, chain_config in models_config.items():
                chain = []
                
                # Add primary provider
                primary = chain_config.get('primary')
                if primary and primary.get('provider') in self.providers:
                    chain.append(primary)
                
                # Add fallbacks
                fallbacks = chain_config.get('fallbacks', [])
                for fb in fallbacks:
                    if fb.get('provider') in self.providers:
                        chain.append(fb)
                
                if chain:
                    self.fallback_chains[chain_name] = chain
        else:
            # Default fallback chain using only initialized providers
            default_chain = []
            if 'groq' in self.providers:
                default_chain.append({"provider": "groq", "model": "llama-3.1-8b-instant"})
            if 'openai' in self.providers:
                default_chain.append({"provider": "openai", "model": "gpt-3.5-turbo"})
            if 'together' in self.providers:
                default_chain.append({"provider": "together", "model": "meta-llama/Llama-3-8b"})
            
            if default_chain:
                self.fallback_chains["default"] = default_chain
        
        print(f"\n📋 Fallback chains configured: {list(self.fallback_chains.keys())}")
        for chain_name, chain in self.fallback_chains.items():
            print(f"  - {chain_name}: {[p['provider'] for p in chain]}")
    
    def start_cleanup_task(self):
        """Start background cleanup task"""
        async def cleanup_loop():
            while True:
                await asyncio.sleep(60)  # Clean every minute
                self._cleanup()
        
        # Run cleanup in background
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                self._cleanup_task = asyncio.create_task(cleanup_loop())
            else:
                # If no loop running, we'll clean synchronously
                pass
        except RuntimeError:
            # No event loop, skip background task
            pass
    
    def _cleanup(self):
        """Perform cleanup operations"""
        # Force garbage collection
        gc.collect()
        
        # Update last cleanup time
        import time
        self._last_cleanup = time.time()
    
    async def route(
        self,
        messages: List[Dict],
        model_family: str = "default",
        **kwargs
    ) -> Dict[str, Any]:
        """Route request through fallback providers"""
        print("Inside the route method")

        # Get the chain
        chain = self.fallback_chains.get(model_family)
        if not chain:
            chain = self.fallback_chains.get("default", [])
            print("Default chain has been rertrieved")


        if not chain:
            return {"error": "No fallback chain configured and no providers available"}
        
        print(f"\n🔄 Routing request with chain: {model_family}")
        
        # Try each provider in the chain
        for idx, provider_config in enumerate(chain):
            provider_name = provider_config["provider"]
            model = provider_config["model"]
            
            print(f"  Attempt {idx + 1}: {provider_name}/{model}")
            
            # Check if provider is initialized
            if provider_name not in self.providers:
                print(f"    ⚠️  Provider {provider_name} not initialized, skipping...")
                continue
            
            # Check circuit breaker
            circuit_breaker = self.circuit_breakers.get(provider_name)
            if circuit_breaker:
                try:
                    # Check if circuit is open without calling
                    if hasattr(circuit_breaker, 'state') and circuit_breaker.state == "OPEN":
                        print(f"    ⚠️  Circuit breaker is OPEN for {provider_name}, skipping...")
                        continue
                except:
                    pass
            
            try:
                # Get provider instance
                provider = self.providers[provider_name]
                
                # Make request with retry
                response = await self._make_request(
                    provider, messages, model, **kwargs
                )
                
                # Check budget
                if not await self.budget_tracker.check_and_record(response.cost):
                    print(f"    ❌ Budget limit exceeded")
                    return {
                        "error": "Budget limit exceeded",
                        "cost": response.cost
                    }
                
                # Success!
                print(f"    ✅ Success! Response from {provider_name}")
                
                return {
                    "response": response.text,
                    "provider": response.provider,
                    "model": response.model,
                    "latency_ms": response.latency_ms,
                    "cost": response.cost,
                    "tokens": {
                        "prompt": response.tokens_prompt,
                        "completion": response.tokens_completion
                    }
                }
                
            except Exception as e:
                error_msg = str(e)[:100]
                print(f"    ❌ Failed: {error_msg}")
                
                # Record failure for circuit breaker
                if circuit_breaker and hasattr(circuit_breaker, '_record_failure'):
                    try:
                        await circuit_breaker._record_failure()
                    except:
                        pass
                
                continue  # Try next provider
        
        return {"error": "All providers failed. Please check your API keys and network connection."}
    
    async def _make_request(self, provider, messages, model, **kwargs):
        """Execute request with retry logic"""
        return await self.retry_handler.execute(
            provider.chat_completion,
            messages,
            model,
            **kwargs
        )
    
    async def close(self):
        """Close all provider connections"""
        for provider in self.providers.values():
            if hasattr(provider, 'close'):
                await provider.close()
        
        if self._cleanup_task:
            self._cleanup_task.cancel()