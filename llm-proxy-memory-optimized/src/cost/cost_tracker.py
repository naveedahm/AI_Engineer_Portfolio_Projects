# src/cost/cost_tracker.py - Complete cost tracking system
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Optional
import json
import os
from threading import Lock

class CostTracker:
    """Thread-safe cost tracking system"""
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize cost tracking"""
        self.by_provider: Dict[str, float] = defaultdict(float)
        self.by_model: Dict[str, float] = defaultdict(float)
        self.by_provider_model: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self.request_counts: Dict[str, int] = defaultdict(int)
        self.cost_history: List[Dict] = []
        self.daily_costs: Dict[str, Dict] = defaultdict(lambda: defaultdict(float))
        self.hourly_costs: Dict[str, Dict] = defaultdict(lambda: defaultdict(float))
        
        # Load saved costs if exists
        self._load_costs()
        
        # Start periodic save
        self._last_save = datetime.now()
    
    def record_cost(self, provider: str, model: str, cost: float, tokens_prompt: int, tokens_completion: int, metadata: Dict = None):
        """Record a cost entry"""
        with self._lock:
            # Update aggregations
            self.by_provider[provider] += cost
            self.by_model[f"{provider}/{model}"] += cost
            self.by_provider_model[provider][model] += cost
            self.request_counts[f"{provider}/{model}"] += 1
            
            # Store in history
            now = datetime.now()
            cost_entry = {
                "timestamp": now.isoformat(),
                "provider": provider,
                "model": model,
                "cost": cost,
                "tokens_prompt": tokens_prompt,
                "tokens_completion": tokens_completion,
                "total_tokens": tokens_prompt + tokens_completion,
                "metadata": metadata or {}
            }
            self.cost_history.append(cost_entry)
            
            # Daily aggregation
            day_key = now.strftime("%Y-%m-%d")
            self.daily_costs[day_key][f"{provider}/{model}"] += cost
            
            # Hourly aggregation
            hour_key = now.strftime("%Y-%m-%d %H:00")
            self.hourly_costs[hour_key][f"{provider}/{model}"] += cost
            
            # Auto-save every 10 entries or 5 minutes
            if len(self.cost_history) % 10 == 0 or (datetime.now() - self._last_save).seconds > 300:
                self._save_costs()
    
    def get_breakdown(self, period: str = "all", limit: int = 100) -> Dict:
        """Get cost breakdown by various dimensions"""
        with self._lock:
            if period == "today":
                today = datetime.now().strftime("%Y-%m-%d")
                costs = self.daily_costs.get(today, {})
                history = [h for h in self.cost_history if h["timestamp"].startswith(today)]
            elif period == "hour":
                hour = datetime.now().strftime("%Y-%m-%d %H:00")
                costs = self.hourly_costs.get(hour, {})
                history = [h for h in self.cost_history if h["timestamp"].startswith(hour[:13])]
            else:
                costs = self.by_provider_model
                history = self.cost_history[-limit:]
            
            # Build breakdown by provider
            provider_breakdown = {}
            for provider in set([k.split('/')[0] for k in costs.keys()]):
                provider_models = {k.split('/')[1]: v for k, v in costs.items() if k.startswith(provider)}
                provider_total = sum(provider_models.values())
                provider_breakdown[provider] = {
                    "total_cost": provider_total,
                    "percentage": 0,  # Will calculate after total
                    "models": provider_models,
                    "request_count": sum(self.request_counts.get(f"{provider}/{m}", 0) for m in provider_models.keys())
                }
            
            # Calculate percentages
            total_cost = sum(p["total_cost"] for p in provider_breakdown.values())
            for provider in provider_breakdown:
                if total_cost > 0:
                    provider_breakdown[provider]["percentage"] = (provider_breakdown[provider]["total_cost"] / total_cost) * 100
            
            # Recent requests
            recent_requests = []
            for entry in history[-20:]:  # Last 20 requests
                recent_requests.append({
                    "timestamp": entry["timestamp"],
                    "provider": entry["provider"],
                    "model": entry["model"],
                    "cost": entry["cost"],
                    "tokens": entry["total_tokens"]
                })
            
            return {
                "summary": {
                    "total_cost": total_cost,
                    "total_requests": sum(self.request_counts.values()),
                    "unique_models": len(self.by_model),
                    "period": period
                },
                "by_provider": provider_breakdown,
                "by_model": dict(sorted(self.by_model.items(), key=lambda x: x[1], reverse=True)[:20]),
                "recent_requests": recent_requests,
                "cost_history": history[-limit:]
            }
    
    def get_model_costs(self) -> Dict:
        """Get detailed costs by model"""
        with self._lock:
            model_details = {}
            for model_key, total_cost in self.by_model.items():
                provider, model = model_key.split('/', 1)
                request_count = self.request_counts.get(model_key, 0)
                avg_cost = total_cost / request_count if request_count > 0 else 0
                
                # Get average tokens
                model_history = [h for h in self.cost_history if h["provider"] == provider and h["model"] == model]
                avg_tokens = sum(h["total_tokens"] for h in model_history) / len(model_history) if model_history else 0
                
                model_details[model_key] = {
                    "provider": provider,
                    "model": model,
                    "total_cost": total_cost,
                    "request_count": request_count,
                    "average_cost_per_request": avg_cost,
                    "average_tokens_per_request": avg_tokens,
                    "estimated_cost_per_1k_tokens": (avg_cost / avg_tokens) * 1000 if avg_tokens > 0 else 0
                }
            
            return model_details
    
    def _save_costs(self):
        """Save costs to file for persistence"""
        try:
            os.makedirs("data", exist_ok=True)
            data = {
                "by_provider": dict(self.by_provider),
                "by_model": dict(self.by_model),
                "request_counts": dict(self.request_counts),
                "cost_history": self.cost_history[-1000:],  # Keep last 1000
                "last_updated": datetime.now().isoformat()
            }
            with open("data/cost_tracking.json", "w") as f:
                json.dump(data, f, indent=2)
            self._last_save = datetime.now()
        except Exception as e:
            print(f"Error saving costs: {e}")
    
    def _load_costs(self):
        """Load costs from file"""
        try:
            if os.path.exists("data/cost_tracking.json"):
                with open("data/cost_tracking.json", "r") as f:
                    data = json.load(f)
                
                self.by_provider.update(data.get("by_provider", {}))
                self.by_model.update(data.get("by_model", {}))
                self.request_counts.update(data.get("request_counts", {}))
                self.cost_history = data.get("cost_history", [])
        except Exception as e:
            print(f"Error loading costs: {e}")
    
    def reset_costs(self, confirm: bool = False):
        """Reset all cost tracking (use with caution)"""
        if confirm:
            with self._lock:
                self.by_provider.clear()
                self.by_model.clear()
                self.by_provider_model.clear()
                self.request_counts.clear()
                self.cost_history.clear()
                self.daily_costs.clear()
                self.hourly_costs.clear()
                self._save_costs()
                return {"message": "Cost tracking reset successfully"}
        return {"message": "Reset not confirmed. Set confirm=True to reset"}

# Global instance
cost_tracker = CostTracker()    