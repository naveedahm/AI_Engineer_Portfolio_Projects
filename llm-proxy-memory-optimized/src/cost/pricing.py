# src/cost/pricing.py
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import re
from decimal import Decimal, ROUND_HALF_UP
import asyncio
from collections import defaultdict

# ============= Pricing Data Models =============

class PricingTier(str, Enum):
    """Pricing tiers for different model classes"""
    CHEAP = "cheap"          # < $0.001 per 1K tokens
    STANDARD = "standard"     # $0.001 - $0.01 per 1K tokens
    PREMIUM = "premium"       # $0.01 - $0.1 per 1K tokens
    ENTERPRISE = "enterprise" # > $0.1 per 1K tokens

@dataclass
class ModelPricingInfo:
    """Complete pricing information for a model"""
    provider: str
    model_id: str
    prompt_price_per_1k: float
    completion_price_per_1k: float
    currency: str = "USD"
    tier: PricingTier = PricingTier.STANDARD
    effective_from: datetime = field(default_factory=datetime.utcnow)
    notes: Optional[str] = None
    
    def __post_init__(self):
        # Auto-assign tier based on price
        avg_price = (self.prompt_price_per_1k + self.completion_price_per_1k) / 2
        if avg_price < 0.001:
            self.tier = PricingTier.CHEAP
        elif avg_price < 0.01:
            self.tier = PricingTier.STANDARD
        elif avg_price < 0.1:
            self.tier = PricingTier.PREMIUM
        else:
            self.tier = PricingTier.ENTERPRISE

@dataclass
class BatchPricingInfo:
    """Pricing for batch/async operations (often 50% cheaper)"""
    provider: str
    model_id: str
    batch_discount_factor: float = 0.5  # 50% discount for batch
    min_batch_tokens: int = 1000
    
@dataclass
class VolumeDiscount:
    """Volume-based pricing discounts"""
    provider: str
    monthly_tokens_threshold: int
    discount_percentage: float
    
# ============= Main Pricing Database =============

class PricingDatabase:
    """Central database for all model pricing"""
    
    def __init__(self):
        self.pricing: Dict[str, Dict[str, ModelPricingInfo]] = defaultdict(dict)
        self.batch_pricing: Dict[str, Dict[str, BatchPricingInfo]] = defaultdict(dict)
        self._initialize_pricing()
    
    def _initialize_pricing(self):
        """Initialize pricing for all providers and models"""
        
        # ============ Hosted APIs ============
        
        # OpenAI Pricing (as of 2025)
        openai_pricing = {
            # GPT-4 Series
            "gpt-4o": ModelPricingInfo(
                provider="openai", model_id="gpt-4o",
                prompt_price_per_1k=0.005, completion_price_per_1k=0.015
            ),
            "gpt-4o-2024-08-06": ModelPricingInfo(
                provider="openai", model_id="gpt-4o-2024-08-06",
                prompt_price_per_1k=0.005, completion_price_per_1k=0.015
            ),
            "gpt-4o-mini": ModelPricingInfo(
                provider="openai", model_id="gpt-4o-mini",
                prompt_price_per_1k=0.00015, completion_price_per_1k=0.0006,
                tier=PricingTier.CHEAP
            ),
            "gpt-4-turbo": ModelPricingInfo(
                provider="openai", model_id="gpt-4-turbo",
                prompt_price_per_1k=0.01, completion_price_per_1k=0.03,
                tier=PricingTier.PREMIUM
            ),
            "gpt-4": ModelPricingInfo(
                provider="openai", model_id="gpt-4",
                prompt_price_per_1k=0.03, completion_price_per_1k=0.06,
                tier=PricingTier.ENTERPRISE
            ),
            "gpt-3.5-turbo": ModelPricingInfo(
                provider="openai", model_id="gpt-3.5-turbo",
                prompt_price_per_1k=0.0005, completion_price_per_1k=0.0015,
                tier=PricingTier.CHEAP
            ),
        }
        
        # Anthropic Pricing
        anthropic_pricing = {
            "claude-3.5-sonnet": ModelPricingInfo(
                provider="anthropic", model_id="claude-3.5-sonnet",
                prompt_price_per_1k=0.003, completion_price_per_1k=0.015,
                tier=PricingTier.PREMIUM
            ),
            "claude-3-opus": ModelPricingInfo(
                provider="anthropic", model_id="claude-3-opus",
                prompt_price_per_1k=0.015, completion_price_per_1k=0.075,
                tier=PricingTier.ENTERPRISE
            ),
            "claude-3-sonnet": ModelPricingInfo(
                provider="anthropic", model_id="claude-3-sonnet",
                prompt_price_per_1k=0.003, completion_price_per_1k=0.015,
                tier=PricingTier.PREMIUM
            ),
            "claude-3-haiku": ModelPricingInfo(
                provider="anthropic", model_id="claude-3-haiku",
                prompt_price_per_1k=0.00025, completion_price_per_1k=0.00125,
                tier=PricingTier.CHEAP
            ),
        }
        
        # Gemini Pricing
        gemini_pricing = {
            "gemini-1.5-pro": ModelPricingInfo(
                provider="gemini", model_id="gemini-1.5-pro",
                prompt_price_per_1k=0.0035, completion_price_per_1k=0.0105,
                tier=PricingTier.PREMIUM
            ),
            "gemini-1.5-flash": ModelPricingInfo(
                provider="gemini", model_id="gemini-1.5-flash",
                prompt_price_per_1k=0.00035, completion_price_per_1k=0.00105,
                tier=PricingTier.CHEAP
            ),
            "gemini-1.0-pro": ModelPricingInfo(
                provider="gemini", model_id="gemini-1.0-pro",
                prompt_price_per_1k=0.0005, completion_price_per_1k=0.0015,
                tier=PricingTier.CHEAP
            ),
        }
        
        # ============ Inference Providers ============
        
        # Together AI Pricing
        together_pricing = {
            "meta-llama/Llama-3-70b": ModelPricingInfo(
                provider="together", model_id="meta-llama/Llama-3-70b",
                prompt_price_per_1k=0.0009, completion_price_per_1k=0.0009,
                tier=PricingTier.CHEAP
            ),
            "meta-llama/Llama-3-8b": ModelPricingInfo(
                provider="together", model_id="meta-llama/Llama-3-8b",
                prompt_price_per_1k=0.0002, completion_price_per_1k=0.0002,
                tier=PricingTier.CHEAP
            ),
            "Qwen/Qwen2.5-72B": ModelPricingInfo(
                provider="together", model_id="Qwen/Qwen2.5-72B",
                prompt_price_per_1k=0.0009, completion_price_per_1k=0.0009,
                tier=PricingTier.CHEAP
            ),
            "mistralai/Mixtral-8x7B": ModelPricingInfo(
                provider="together", model_id="mistralai/Mixtral-8x7B",
                prompt_price_per_1k=0.0006, completion_price_per_1k=0.0006,
                tier=PricingTier.CHEAP
            ),
            "deepseek-ai/deepseek-coder-33b": ModelPricingInfo(
                provider="together", model_id="deepseek-ai/deepseek-coder-33b",
                prompt_price_per_1k=0.0008, completion_price_per_1k=0.0008,
                tier=PricingTier.CHEAP
            ),
        }
        
        # Groq Pricing (ultra-fast inference)
        groq_pricing = {
            "llama3-70b-8192": ModelPricingInfo(
                provider="groq", model_id="llama3-70b-8192",
                prompt_price_per_1k=0.0007, completion_price_per_1k=0.0008,
                tier=PricingTier.CHEAP
            ),
            "llama3-8b-8192": ModelPricingInfo(
                provider="groq", model_id="llama3-8b-8192",
                prompt_price_per_1k=0.0001, completion_price_per_1k=0.0001,
                tier=PricingTier.CHEAP
            ),
            "mixtral-8x7b-32768": ModelPricingInfo(
                provider="groq", model_id="mixtral-8x7b-32768",
                prompt_price_per_1k=0.0005, completion_price_per_1k=0.0005,
                tier=PricingTier.CHEAP
            ),
            "gemma2-9b-it": ModelPricingInfo(
                provider="groq", model_id="gemma2-9b-it",
                prompt_price_per_1k=0.0001, completion_price_per_1k=0.0001,
                tier=PricingTier.CHEAP
            ),
        }
        
        # Replicate Pricing (varies by model popularity)
        replicate_pricing = {
            "meta/meta-llama-3-70b": ModelPricingInfo(
                provider="replicate", model_id="meta/meta-llama-3-70b",
                prompt_price_per_1k=0.0015, completion_price_per_1k=0.0015,
                tier=PricingTier.STANDARD
            ),
            "mistralai/mixtral-8x7b": ModelPricingInfo(
                provider="replicate", model_id="mistralai/mixtral-8x7b",
                prompt_price_per_1k=0.0012, completion_price_per_1k=0.0012,
                tier=PricingTier.STANDARD
            ),
        }
        
        # Hugging Face Inference Pricing
        huggingface_pricing = {
            "meta-llama/Llama-3-70B": ModelPricingInfo(
                provider="huggingface", model_id="meta-llama/Llama-3-70B",
                prompt_price_per_1k=0.002, completion_price_per_1k=0.002,
                tier=PricingTier.STANDARD,
                notes="Serverless endpoints pricing"
            ),
            "Qwen/Qwen2.5-72B": ModelPricingInfo(
                provider="huggingface", model_id="Qwen/Qwen2.5-72B",
                prompt_price_per_1k=0.002, completion_price_per_1k=0.002,
                tier=PricingTier.STANDARD
            ),
        }
        
        # Fireworks AI Pricing
        fireworks_pricing = {
            "llama-v3-70b": ModelPricingInfo(
                provider="fireworks", model_id="llama-v3-70b",
                prompt_price_per_1k=0.0009, completion_price_per_1k=0.0009,
                tier=PricingTier.CHEAP
            ),
            "llama-v3-8b": ModelPricingInfo(
                provider="fireworks", model_id="llama-v3-8b",
                prompt_price_per_1k=0.0001, completion_price_per_1k=0.0001,
                tier=PricingTier.CHEAP
            ),
            "mixtral-8x7b": ModelPricingInfo(
                provider="fireworks", model_id="mixtral-8x7b",
                prompt_price_per_1k=0.0005, completion_price_per_1k=0.0005,
                tier=PricingTier.CHEAP
            ),
        }
        
        # ============ Self-Hosted (Cost = 0 for local, but compute costs apply) ============
        
        # vLLM (self-hosted - free, but requires GPU)
        vllm_pricing = {
            "any-model": ModelPricingInfo(
                provider="vllm", model_id="any-model",
                prompt_price_per_1k=0.0, completion_price_per_1k=0.0,
                tier=PricingTier.CHEAP,
                notes="Self-hosted - GPU compute costs only"
            ),
        }
        
        # Ollama (self-hosted - completely free)
        ollama_pricing = {
            "llama3": ModelPricingInfo(
                provider="ollama", model_id="llama3",
                prompt_price_per_1k=0.0, completion_price_per_1k=0.0,
                tier=PricingTier.CHEAP,
                notes="Local deployment - completely free"
            ),
            "qwen2.5": ModelPricingInfo(
                provider="ollama", model_id="qwen2.5",
                prompt_price_per_1k=0.0, completion_price_per_1k=0.0,
                tier=PricingTier.CHEAP
            ),
            "mistral": ModelPricingInfo(
                provider="ollama", model_id="mistral",
                prompt_price_per_1k=0.0, completion_price_per_1k=0.0,
                tier=PricingTier.CHEAP
            ),
            "deepseek-coder": ModelPricingInfo(
                provider="ollama", model_id="deepseek-coder",
                prompt_price_per_1k=0.0, completion_price_per_1k=0.0,
                tier=PricingTier.CHEAP
            ),
        }
        
        # Register all pricing
        self._register_pricing(openai_pricing)
        self._register_pricing(anthropic_pricing)
        self._register_pricing(gemini_pricing)
        self._register_pricing(together_pricing)
        self._register_pricing(groq_pricing)
        self._register_pricing(replicate_pricing)
        self._register_pricing(huggingface_pricing)
        self._register_pricing(fireworks_pricing)
        self._register_pricing(vllm_pricing)
        self._register_pricing(ollama_pricing)
        
        # Register batch pricing for supported providers
        self.batch_pricing["openai"]["*"] = BatchPricingInfo(
            provider="openai", model_id="*", batch_discount_factor=0.5
        )
        
    def _register_pricing(self, pricing_dict: Dict[str, ModelPricingInfo]):
        """Register pricing for a provider"""
        for model_id, info in pricing_dict.items():
            self.pricing[info.provider][model_id] = info
            # Also register with wildcard for default
            if "*" not in self.pricing[info.provider]:
                self.pricing[info.provider]["*"] = info

# ============= Cost Calculator =============

class CostCalculator:
    """Calculate costs for LLM requests with various optimizations"""
    
    def __init__(self, pricing_db: PricingDatabase = None):
        self.pricing_db = pricing_db or PricingDatabase()
        self.cache: Dict[str, ModelPricingInfo] = {}
        self.volume_tracking: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    
    def calculate_cost(
        self,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        is_batch: bool = False
    ) -> Tuple[float, float, float]:
        """
        Calculate cost for a request
        Returns: (prompt_cost, completion_cost, total_cost)
        """
        pricing = self._get_pricing(provider, model)
        
        # Calculate base costs
        prompt_cost = (prompt_tokens / 1000) * pricing.prompt_price_per_1k
        completion_cost = (completion_tokens / 1000) * pricing.completion_price_per_1k
        
        # Apply batch discount if applicable
        if is_batch:
            batch_info = self.pricing_db.batch_pricing.get(provider, {}).get(model, 
                        self.pricing_db.batch_pricing.get(provider, {}).get("*"))
            if batch_info:
                discount = batch_info.batch_discount_factor
                prompt_cost *= discount
                completion_cost *= discount
        
        # Round to 6 decimal places (micro-dollar precision)
        prompt_cost = round(prompt_cost, 8)
        completion_cost = round(completion_cost, 8)
        total_cost = round(prompt_cost + completion_cost, 8)
        
        return prompt_cost, completion_cost, total_cost
    
    def calculate_cost_batch(
        self,
        requests: List[Tuple[str, str, int, int]]
    ) -> List[float]:
        """
        Calculate costs for multiple requests efficiently
        requests: list of (provider, model, prompt_tokens, completion_tokens)
        """
        costs = []
        for provider, model, prompt_tokens, completion_tokens in requests:
            _, _, total = self.calculate_cost(provider, model, prompt_tokens, completion_tokens)
            costs.append(total)
        return costs
    
    def estimate_cost_for_length(
        self,
        provider: str,
        model: str,
        estimated_prompt_tokens: int,
        estimated_completion_ratio: float = 0.5
    ) -> float:
        """
        Estimate cost before making the actual request
        """
        pricing = self._get_pricing(provider, model)
        estimated_completion_tokens = int(estimated_prompt_tokens * estimated_completion_ratio)
        
        prompt_cost = (estimated_prompt_tokens / 1000) * pricing.prompt_price_per_1k
        completion_cost = (estimated_completion_tokens / 1000) * pricing.completion_price_per_1k
        
        return round(prompt_cost + completion_cost, 6)
    
    def find_cheapest_provider(
        self,
        model_family: str,
        prompt_tokens: int,
        completion_tokens: int,
        providers: List[str] = None
    ) -> Dict[str, any]:
        """
        Find the cheapest provider for a given model family
        """
        results = []
        
        # Common model mappings
        model_mappings = {
            "gpt-4-equivalent": [
                ("openai", "gpt-4o"),
                ("anthropic", "claude-3.5-sonnet"),
                ("groq", "llama3-70b-8192"),
                ("together", "meta-llama/Llama-3-70b"),
            ],
            "fast-cheap": [
                ("groq", "llama-3.1-8b-instant"),
                ("together", "meta-llama/Llama-3-8b"),
                ("fireworks", "llama-v3-8b"),
                ("openai", "gpt-3.5-turbo"),
                ("ollama", "llama3"),
            ],
        }
        
        candidates = model_mappings.get(model_family, [])
        if providers:
            candidates = [(p, m) for p, m in candidates if p in providers]
        
        for provider, model in candidates:
            try:
                _, _, total = self.calculate_cost(provider, model, prompt_tokens, completion_tokens)
                results.append({
                    "provider": provider,
                    "model": model,
                    "cost": total,
                    "pricing": self._get_pricing(provider, model)
                })
            except PricingNotFoundError:
                continue
        
        if not results:
            return None
        
        return min(results, key=lambda x: x["cost"])
    
    def _get_pricing(self, provider: str, model: str) -> ModelPricingInfo:
        """Get pricing for a model with caching"""
        cache_key = f"{provider}:{model}"
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Try exact match
        if model in self.pricing_db.pricing.get(provider, {}):
            pricing = self.pricing_db.pricing[provider][model]
        # Try wildcard match
        elif "*" in self.pricing_db.pricing.get(provider, {}):
            pricing = self.pricing_db.pricing[provider]["*"]
            # Clone with model name
            pricing = ModelPricingInfo(
                provider=provider,
                model_id=model,
                prompt_price_per_1k=pricing.prompt_price_per_1k,
                completion_price_per_1k=pricing.completion_price_per_1k,
                tier=pricing.tier,
                notes=f"Using default pricing for {model}"
            )
        else:
            raise PricingNotFoundError(f"No pricing found for {provider}/{model}")
        
        self.cache[cache_key] = pricing
        return pricing
    
    def track_volume(self, provider: str, month: str, tokens: int):
        """Track token volume for potential discounts"""
        self.volume_tracking[provider][month] += tokens
    
    def get_volume_discount(self, provider: str, month: str) -> float:
        """Calculate volume discount based on monthly usage"""
        tokens = self.volume_tracking[provider].get(month, 0)
        
        # Volume discount tiers (example)
        if tokens >= 10_000_000:  # 10M+ tokens
            return 0.20  # 20% discount
        elif tokens >= 1_000_000:  # 1M-10M tokens
            return 0.10  # 10% discount
        elif tokens >= 100_000:  # 100K-1M tokens
            return 0.05  # 5% discount
        else:
            return 0.0

# ============= Budget Manager =============

class BudgetManager:
    """Manage and enforce budget limits across providers"""
    
    def __init__(
        self,
        daily_limit_usd: float = 10.0,
        hourly_limit_usd: float = 2.0,
        monthly_limit_usd: float = 100.0
    ):
        self.daily_limit = daily_limit_usd
        self.hourly_limit = hourly_limit_usd
        self.monthly_limit = monthly_limit_usd
        
        self.daily_spend: Dict[str, float] = defaultdict(float)
        self.hourly_spend: Dict[str, float] = defaultdict(float)
        self.monthly_spend: Dict[str, float] = defaultdict(float)
        
        self.last_reset = datetime.utcnow()
        self._lock = asyncio.Lock()
    
    async def check_budget(self, cost: float) -> bool:
        """Check if request is within budget"""
        async with self._lock:
            await self._reset_if_needed()
            
            now = datetime.utcnow()
            current_hour = now.strftime("%Y-%m-%d-%H")
            current_day = now.strftime("%Y-%m-%d")
            current_month = now.strftime("%Y-%m")
            
            # Check all limits
            if self.hourly_spend[current_hour] + cost > self.hourly_limit:
                return False
            if self.daily_spend[current_day] + cost > self.daily_limit:
                return False
            if self.monthly_spend[current_month] + cost > self.monthly_limit:
                return False
            
            # Record the spend
            self.hourly_spend[current_hour] += cost
            self.daily_spend[current_day] += cost
            self.monthly_spend[current_month] += cost
            
            return True
    
    async def _reset_if_needed(self):
        """Reset counters based on time periods"""
        now = datetime.utcnow()
        
        # Reset hourly (if new hour)
        current_hour = now.strftime("%Y-%m-%d-%H")
        if not any(k.endswith(current_hour.split("-")[-1]) for k in self.hourly_spend.keys()):
            # Keep only current hour
            self.hourly_spend = {current_hour: self.hourly_spend.get(current_hour, 0)}
        
        # Reset daily (if new day)
        current_day = now.strftime("%Y-%m-%d")
        if not any(k == current_day for k in self.daily_spend.keys()):
            # Keep only current day
            self.daily_spend = {current_day: self.daily_spend.get(current_day, 0)}
        
        # Reset monthly (if new month)
        current_month = now.strftime("%Y-%m")
        if not any(k == current_month for k in self.monthly_spend.keys()):
            self.monthly_spend = {current_month: self.monthly_spend.get(current_month, 0)}
    
    def get_remaining_budget(self) -> Dict[str, float]:
        """Get remaining budget for all periods"""
        now = datetime.utcnow()
        current_hour = now.strftime("%Y-%m-%d-%H")
        current_day = now.strftime("%Y-%m-%d")
        current_month = now.strftime("%Y-%m")
        
        return {
            "hourly_remaining": max(0, self.hourly_limit - self.hourly_spend.get(current_hour, 0)),
            "daily_remaining": max(0, self.daily_limit - self.daily_spend.get(current_day, 0)),
            "monthly_remaining": max(0, self.monthly_limit - self.monthly_spend.get(current_month, 0)),
            "hourly_used": self.hourly_spend.get(current_hour, 0),
            "daily_used": self.daily_spend.get(current_day, 0),
            "monthly_used": self.monthly_spend.get(current_month, 0),
        }
    
    def reset_budget(self, period: str = "daily"):
        """Reset budget for a specific period"""
        if period == "hourly":
            self.hourly_spend.clear()
        elif period == "daily":
            self.daily_spend.clear()
        elif period == "monthly":
            self.monthly_spend.clear()
        elif period == "all":
            self.hourly_spend.clear()
            self.daily_spend.clear()
            self.monthly_spend.clear()

# ============= Price Alerts =============

class PriceAlert:
    """Generate alerts for unusual spending patterns"""
    
    def __init__(self, budget_manager: BudgetManager):
        self.budget_manager = budget_manager
        self.alert_history: List[Dict] = []
    
    def check_alerts(self) -> List[Dict]:
        """Check for budget-related alerts"""
        alerts = []
        remaining = self.budget_manager.get_remaining_budget()
        
        # Check hourly threshold (80% used)
        hourly_used_pct = remaining["hourly_used"] / self.budget_manager.hourly_limit
        if hourly_used_pct > 0.8:
            alerts.append({
                "type": "hourly_threshold",
                "message": f"Hourly budget at {hourly_used_pct*100:.1f}%",
                "severity": "warning",
                "remaining": remaining["hourly_remaining"]
            })
        
        # Check daily threshold (80% used)
        daily_used_pct = remaining["daily_used"] / self.budget_manager.daily_limit
        if daily_used_pct > 0.8:
            alerts.append({
                "type": "daily_threshold",
                "message": f"Daily budget at {daily_used_pct*100:.1f}%",
                "severity": "critical",
                "remaining": remaining["daily_remaining"]
            })
        
        # Monthly projection alert
        days_in_month = 30
        current_day = datetime.utcnow().day
        projected_monthly = (remaining["daily_used"] / current_day) * days_in_month
        if projected_monthly > self.budget_manager.monthly_limit:
            alerts.append({
                "type": "monthly_projection",
                "message": f"Projected monthly cost ${projected_monthly:.2f} exceeds limit",
                "severity": "warning",
                "projected": projected_monthly,
                "limit": self.budget_manager.monthly_limit
            })
        
        self.alert_history.extend(alerts)
        return alerts

# ============= Exceptions =============

class PricingNotFoundError(Exception):
    """Raised when pricing information is not found"""
    pass

class BudgetExceededError(Exception):
    """Raised when budget limits are exceeded"""
    pass

# ============= Example Usage =============

if __name__ == "__main__":

    # Initialize pricing system
    pricing_db = PricingDatabase()
    calculator = CostCalculator(pricing_db)
    budget_manager = BudgetManager(daily_limit_usd=5.0, hourly_limit_usd=1.0)

    # Example 1: Calculate cost for GPT-4
    prompt_cost, completion_cost, total = calculator.calculate_cost(
        provider="openai",
        model="gpt-4o",
        prompt_tokens=1500,
        completion_tokens=500
    )
    print(f"GPT-4o Cost: ${total:.6f}")
    
    # Example 2: Find cheapest provider for a task
    cheapest = calculator.find_cheapest_provider(
        model_family="fast-cheap",
        prompt_tokens=1000,
        completion_tokens=200
    )
    if cheapest:
        print(f"Cheapest: {cheapest['provider']}/{cheapest['model']} at ${cheapest['cost']:.6f}")
    
    # Example 3: Batch cost calculation
    requests = [
        ("groq", "llama-3.1-8b-instant", 1000, 200),
        ("together", "meta-llama/Llama-3-8b", 1000, 200),
        ("ollama", "llama3", 1000, 200),
    ]
    costs = calculator.calculate_cost_batch(requests)
    for (provider, model, _, _), cost in zip(requests, costs):
        print(f"{provider}/{model}: ${cost:.6f}")
    
    # Example 4: Budget checking
    import asyncio
    
    async def test_budget():
        for cost in [0.5, 0.6, 0.4]:
            if await budget_manager.check_budget(cost):
                print(f"✅ Budget approved for ${cost}")
            else:
                print(f"❌ Budget exceeded for ${cost}")
        
        remaining = budget_manager.get_remaining_budget()
        print(f"Remaining budget: ${remaining['daily_remaining']:.2f}")
    
    asyncio.run(test_budget())