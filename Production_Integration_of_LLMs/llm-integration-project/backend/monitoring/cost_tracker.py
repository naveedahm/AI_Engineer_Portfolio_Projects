"""Cost tracking and budget management"""
from datetime import datetime, date, timedelta
from typing import Dict, Optional
import redis
from loguru import logger
from .metrics import record_cost

class CostTracker:
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """Initialize cost tracker with Redis storage"""
        self.redis = redis_client
        
        # Model pricing (per 1K tokens in USD)
        self.model_pricing = {
            "gpt-4": {"prompt": 0.03, "completion": 0.06},
            "gpt-4-32k": {"prompt": 0.06, "completion": 0.12},
            "gpt-3.5-turbo": {"prompt": 0.001, "completion": 0.002},
            "gpt-3.5-turbo-16k": {"prompt": 0.003, "completion": 0.004},
            "claude-2": {"prompt": 0.008, "completion": 0.024},
            "claude-instant": {"prompt": 0.00163, "completion": 0.00551}
        }
        
        # Budget configuration
        self.daily_budget = float(50.0)  # USD
        self.monthly_budget = float(1000.0)  # USD
        self.alert_threshold = 0.8  # 80% alert
    
    async def track_usage(
        self, 
        model: str, 
        prompt_tokens: int, 
        completion_tokens: int,
        user_id: str = "anonymous"
    ) -> Dict:
        """Track token usage and calculate cost"""
        
        # Calculate cost
        pricing = self.model_pricing.get(model, self.model_pricing["gpt-3.5-turbo"])
        
        prompt_cost = (prompt_tokens / 1000) * pricing["prompt"]
        completion_cost = (completion_tokens / 1000) * pricing["completion"]
        total_cost = prompt_cost + completion_cost
        
        # Record metrics
        record_cost(model, total_cost, "api_call")
        
        # Store in Redis if available
        if self.redis:
            today = date.today().isoformat()
            key = f"cost:{today}"
            
            pipe = self.redis.pipeline()
            pipe.hincrbyfloat(key, "total_cost", total_cost)
            pipe.hincrbyfloat(key, f"{model}:cost", total_cost)
            pipe.hincrby(key, f"{model}:prompt_tokens", prompt_tokens)
            pipe.hincrby(key, f"{model}:completion_tokens", completion_tokens)
            pipe.hincrby(key, f"user:{user_id}:requests", 1)
            pipe.expire(key, 86400 * 30)  # Keep for 30 days
            pipe.execute()
        
        # Check budget alerts
        await self.check_budget_alerts()
        
        logger.info(f"Cost tracked - Model: {model}, Cost: ${total_cost:.6f}, User: {user_id}")
        
        return {
            "prompt_cost": prompt_cost,
            "completion_cost": completion_cost,
            "total_cost": total_cost,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "model": model,
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_daily_cost(self, day: Optional[date] = None) -> float:
        """Get total cost for a specific day"""
        if day is None:
            day = date.today()
        
        if self.redis:
            key = f"cost:{day.isoformat()}"
            total = self.redis.hget(key, "total_cost")
            return float(total) if total else 0.0
        
        return 0.0
    
    async def get_monthly_cost(self) -> float:
        """Get total cost for current month"""
        today = date.today()
        month_start = date(today.year, today.month, 1)
        
        total = 0.0
        current = month_start
        
        while current <= today:
            total += await self.get_daily_cost(current)
            current += timedelta(days=1)
        
        return total
    
    async def check_budget_alerts(self):
        """Check if budgets are near limits and send alerts"""
        daily_cost = await self.get_daily_cost()
        monthly_cost = await self.get_monthly_cost()
        
        # Check daily budget
        if daily_cost >= self.daily_budget:
            logger.error(f"Daily budget exceeded: ${daily_cost:.2f} / ${self.daily_budget:.2f}")
            await self._send_alert("DAILY_BUDGET_EXCEEDED", daily_cost, self.daily_budget)
        elif daily_cost >= self.daily_budget * self.alert_threshold:
            logger.warning(f"Daily budget alert: ${daily_cost:.2f} / ${self.daily_budget:.2f}")
            await self._send_alert("DAILY_BUDGET_WARNING", daily_cost, self.daily_budget)
        
        # Check monthly budget
        if monthly_cost >= self.monthly_budget:
            logger.error(f"Monthly budget exceeded: ${monthly_cost:.2f} / ${self.monthly_budget:.2f}")
            await self._send_alert("MONTHLY_BUDGET_EXCEEDED", monthly_cost, self.monthly_budget)
        elif monthly_cost >= self.monthly_budget * self.alert_threshold:
            logger.warning(f"Monthly budget alert: ${monthly_cost:.2f} / ${self.monthly_budget:.2f}")
            await self._send_alert("MONTHLY_BUDGET_WARNING", monthly_cost, self.monthly_budget)
    
    async def _send_alert(self, alert_type: str, current: float, limit: float):
        """Send alert (webhook, email, etc.)"""
        # Implement your alert mechanism here
        # Example: Send to Slack, email, PagerDuty, etc.
        logger.info(f"ALERT: {alert_type} - Current: ${current:.2f}, Limit: ${limit:.2f}")
    
    async def get_detailed_report(self, days: int = 7) -> Dict:
        """Get detailed cost report for last N days"""
        report = {
            "daily_breakdown": {},
            "model_breakdown": {},
            "total_cost": 0.0,
            "total_tokens": 0
        }
        
        for i in range(days):
            day = date.today() - timedelta(days=i)
            day_cost = await self.get_daily_cost(day)
            report["daily_breakdown"][day.isoformat()] = day_cost
            report["total_cost"] += day_cost
        
        return report