# src/gateway/router.py - Updated to record costs in all paths
from typing import List, Dict, Any, Optional
import asyncio
import gc
import time
from src.resilience.circuit_breaker import CircuitBreaker
from src.resilience.retry import LLMRetry
from src.cost.tracker import BudgetTracker
from src.cost.cost_tracker import cost_tracker
from dotenv import load_dotenv
import os

# Load variables from the .env file
load_dotenv()

class LLMRouter:

    def __init__(self, config: Dict[str, Any]):
        print("=" * 50)
        print("Initializing LLM Router...")
        print("=" * 50)
        
        self.providers = {}
        self.fallback_chains = {}
        self.circuit_breakers = {}
        self.retry_handler = LLMRetry()
        self.budget_tracker = BudgetTracker()
        
        # Store provider configs
        self._provider_configs = config.get('providers', {})
        self._provider_instances = {}
        
        # DEBUG: Print all provider configs
        print(f"📋 Provider configs found: {list(self._provider_configs.keys())}")
        for name, cfg in self._provider_configs.items():
            print(f"   - {name}: enabled={cfg.get('enabled', True)}")
        
        # Setup fallback chains
        self._setup_fallback_chains(config)
        
        # Initialize circuit breakers
        self._init_circuit_breakers()
        
        # DEBUG: Print available chains
        print(f"📋 Available chains: {list(self.fallback_chains.keys())}")
        
        print("=" * 50)

    
    def _setup_fallback_chains(self, config: Dict[str, Any]):
        """Setup fallback chains from config"""
        models_config = config.get('models', {})
        
        if models_config:
            for chain_name, chain_config in models_config.items():
                chain = []
                if 'primary' in chain_config:
                    chain.append(chain_config['primary'])
                if 'fallbacks' in chain_config:
                    chain.extend(chain_config['fallbacks'])
                self.fallback_chains[chain_name] = chain
        else:
            self.fallback_chains = {
                "default": [
                    {"provider": "groq", "model": "llama-3.1-8b-instant"},
                    {"provider": "openai", "model": "gpt-3.5-turbo"}
                ],
                "premium": [
                    {"provider": "groq", "model": "llama-3.3-70b-versatile"},
                    {"provider": "openai", "model": "gpt-4o-mini"},
                    {"provider": "openai", "model": "gpt-3.5-turbo"}
                ]
            }
    
    def _init_circuit_breakers(self):
        """Initialize circuit breakers for providers"""
        for provider_name in self._provider_configs.keys():
            self.circuit_breakers[provider_name] = CircuitBreaker(
                name=provider_name,
                failure_threshold=3,
                recovery_timeout=30
            )
    
    # src/gateway/router.py - Update the provider initialization

    async def _get_provider(self, provider_name: str):
        """Lazy load provider on first use"""
        if provider_name not in self._provider_instances:
            config = self._provider_configs.get(provider_name, {})
            
            # Check if provider is enabled
            if config.get('enabled') is False:
                print(f"  ⏭️  Provider {provider_name} is disabled")
                return None
            
            # Dynamically import provider classes
            try:
                from src.gateway.providers import OpenAIClient, GroqClient, TogetherClient, OllamaClient, HuggingFaceClient
                
                provider_map = {
                    'openai': OpenAIClient,
                    'groq': GroqClient,
                    'together': TogetherClient,
                    'ollama': OllamaClient,  # Make sure this is here
                    'huggingface': HuggingFaceClient,  # Add this line
                }
                
                provider_class = provider_map.get(provider_name)
                if not provider_class:
                    print(f"  ❌ Unknown provider: {provider_name}")
                    return None
                
                # Extract parameters for the provider
                valid_params = {}
                if 'timeout' in config:
                    valid_params['timeout'] = config['timeout']
                if 'api_key' in config and config['api_key']:
                    valid_params['api_key'] = config['api_key']
                if 'base_url' in config:
                    valid_params['base_url'] = config['base_url']
                
                # Initialize the provider
                self._provider_instances[provider_name] = provider_class(**valid_params)
                print(f"  ✅ Initialized {provider_name} provider")
                
            except Exception as e:
                print(f"  ❌ Failed to initialize {provider_name}: {e}")
                return None
        
        return self._provider_instances.get(provider_name)
    
    async def route(
        self,
        messages: List[Dict],
        model_family: str = "default",
        provider: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Route request with model family support and cost tracking"""
        
        # Priority 1: Direct provider/model specified
        if provider and model:
            result = await self._route_to_provider(provider, model, messages, **kwargs)
            # Record cost for direct call
            if "error" not in result:
                cost_tracker.record_cost(
                    provider=result.get('provider', provider),
                    model=result.get('model', model),
                    cost=result.get('cost', 0),
                    tokens_prompt=result.get('tokens', {}).get('prompt', 0),
                    tokens_completion=result.get('tokens', {}).get('completion', 0),
                    metadata={"model_family": "direct", "request_type": "direct_provider"}
                )
            return result
        
        # Priority 2: Use model family chain
        chain = self.fallback_chains.get(model_family, self.fallback_chains.get("default", []))
        
        if not chain:
            return {"error": f"No chain found for model family: {model_family}"}
        
        print(f"\n🔄 Routing request with chain: {model_family}")
        
        for idx, provider_config in enumerate(chain, 1):
            provider_name = provider_config["provider"]
            model_name = provider_config["model"]
            
            print(f"  Attempt {idx}: {provider_name}/{model_name}")
            
            try:
                provider_client = await self._get_provider(provider_name)
                if not provider_client:
                    print(f"    ⏭️  Provider not available")
                    continue
                
                response = await self._make_request(
                    provider_client, messages, model_name, **kwargs
                )
                
                if not await self.budget_tracker.check_and_record(response.cost):
                    return {
                        "error": "Budget limit exceeded",
                        "cost": response.cost
                    }
                
                # Record cost for successful response
                cost_tracker.record_cost(
                    provider=response.provider,
                    model=response.model,
                    cost=response.cost,
                    tokens_prompt=response.tokens_prompt,
                    tokens_completion=response.tokens_completion,
                    metadata={"model_family": model_family, "attempt": idx}
                )
                
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
                print(f"    ❌ Failed: {str(e)[:100]}")
                continue
        
        return {"error": "All providers in chain failed"}
    
    async def _route_to_provider(
        self, 
        provider_name: str, 
        model_name: str, 
        messages: List[Dict], 
        **kwargs
    ) -> Dict[str, Any]:
        """Route directly to specific provider"""
        print(f"\n🎯 Direct routing to {provider_name}/{model_name}")
        
        provider_client = await self._get_provider(provider_name)
        if not provider_client:
            return {"error": f"Provider {provider_name} not available"}
        
        response = await self._make_request(
            provider_client, messages, model_name, **kwargs
        )
        
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
    
    async def _make_request(self, provider, messages, model, **kwargs):
        """Execute request with retry logic"""
        return await self.retry_handler.execute(
            provider.chat_completion,
            messages,
            model,
            **kwargs
        )