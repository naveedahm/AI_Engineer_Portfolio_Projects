from pydantic_settings import BaseSettings
from typing import Optional, List
import os

class Settings(BaseSettings):
    # OpenAI
    openai_api_key: str = "test-key-for-development"
    openai_org_id: Optional[str] = None
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    redis_password: Optional[str] = None
    
    # Database
    database_url: str = "postgresql://user:password@localhost:5432/ai_monitoring"
    
    # API
    api_port: int = 8000
    api_workers: int = 4
    rate_limit_per_minute: int = 60
    max_tokens_per_request: int = 4000
    
    # Hallucination detection settings
    enable_self_consistency: bool = True
    consistency_checks_per_request: int = 3
    consistency_confidence_threshold: float = 0.7

    # Prompt drift configuration
    baseline_system_prompt: str = "You are a helpful AI assistant that provides accurate, concise, and well-structured responses."
    prompt_drift_threshold: float = 0.15
    auto_fix_prompts: bool = True

    # Cost Management
    monthly_budget_usd: float = 100.0
    cost_alert_threshold: float = 0.9
    
    # Model Configuration
    primary_model: str = "gpt-4"
    fallback_model: str = "gpt-3.5-turbo"
    
    # Circuit Breaker
    circuit_breaker_timeout: int = 30000
    circuit_breaker_error_threshold: int = 50
    circuit_breaker_reset_timeout: int = 60000
    
    # Monitoring
    enable_metrics: bool = True
    prometheus_port: int = 9090
    grafana_port: int = 3000  # ADD THIS LINE
    loki_port: int = 3100     # Optional: add if needed
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Change from 'forbid' to 'ignore' to allow extra fields

# Create settings instance
settings = Settings()

# Debug: Print API key status (remove in production)
if settings.openai_api_key == "test-key-for-development":
    print("⚠️ WARNING: Using mock AI service (no API key found in .env)")
    print("   Please check that:")
    print("   1. .env file exists in the backend/ directory")
    print("   2. OPENAI_API_KEY is set correctly")
    print(f"   Current .env path: {os.path.join(os.getcwd(), '.env')}")
else:
    print(f"✅ OpenAI API key loaded (starts with: {settings.openai_api_key[:10]}...)")
    print(f"   Using model: {settings.primary_model}")
