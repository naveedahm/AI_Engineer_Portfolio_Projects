# src/cost/tracker.py
from typing import Dict
from datetime import datetime
from collections import defaultdict

class BudgetTracker:
    def __init__(self, daily_budget: float = 10.0, hourly_budget: float = 2.0):
        self.daily_limit = daily_budget
        self.hourly_limit = hourly_budget
        
        self.daily_spend = defaultdict(float)
        self.hourly_spend = defaultdict(float)
    
    async def check_and_record(self, cost: float) -> bool:
        """Check if cost is within budget and record it"""
        now = datetime.utcnow()
        current_day = now.strftime("%Y-%m-%d")
        current_hour = now.strftime("%Y-%m-%d-%H")
        
        daily_total = self.daily_spend[current_day] + cost
        hourly_total = self.hourly_spend[current_hour] + cost
        
        if daily_total > self.daily_limit or hourly_total > self.hourly_limit:
            return False
        
        self.daily_spend[current_day] = daily_total
        self.hourly_spend[current_hour] = hourly_total
        
        return True
    
    def get_remaining_budget(self) -> Dict[str, float]:
        """Get remaining budget"""
        now = datetime.utcnow()
        current_day = now.strftime("%Y-%m-%d")
        current_hour = now.strftime("%Y-%m-%d-%H")
        
        return {
            "daily_remaining": max(0, self.daily_limit - self.daily_spend.get(current_day, 0)),
            "daily_used": self.daily_spend.get(current_day, 0),
            "hourly_remaining": max(0, self.hourly_limit - self.hourly_spend.get(current_hour, 0)),
            "hourly_used": self.hourly_spend.get(current_hour, 0)
        }
