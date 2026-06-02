# src/cost/tracker.py - Simplified version
from typing import Dict
from datetime import datetime, date
from collections import defaultdict

class BudgetTracker:
    def __init__(self, daily_budget: float = 5.0, hourly_budget: float = 1.0):
        self.daily_limit = daily_budget
        self.hourly_limit = hourly_budget
        self.daily_spend = defaultdict(float)
        self.hourly_spend = defaultdict(float)
    
    async def check_and_record(self, cost: float) -> bool:
        current_date = date.today()
        current_hour = datetime.utcnow().strftime("%Y-%m-%d-%H")
        
        daily_total = self.daily_spend[current_date] + cost
        hourly_total = self.hourly_spend[current_hour] + cost
        
        if daily_total > self.daily_limit or hourly_total > self.hourly_limit:
            return False
        
        self.daily_spend[current_date] = daily_total
        self.hourly_spend[current_hour] = hourly_total
        
        return True
    
    def get_remaining_budget(self) -> Dict[str, float]:
        current_date = date.today()
        return {
            "daily_remaining": max(0, self.daily_limit - self.daily_spend[current_date]),
            "daily_used": self.daily_spend[current_date]
        }