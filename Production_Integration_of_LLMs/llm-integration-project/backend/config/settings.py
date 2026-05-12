from pydantic_settings import BaseSettings
from typing import Optional
from enum import Enum

class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

class Settings(BaseSettings):
    # Environment
    ENVIRONMENT: Environment = Environment.DEVELOPMENT
    
    # API Keys
    OPENAI_API_KEY: str
    ANTHROPIC_API_KEY: Optional[str] = None
    
    # LLM Configuration
    DEFAULT_MODEL: str = "gpt-3.5-turbo"
    FALLBACK_MODEL: str = "gpt-3.5-turbo"
    MAX_TOKENS: int = 2000
    TEMPERATURE: float = 0.7
    
    # Timeouts
    LLM_TIMEOUT_SECONDS: int = 30
    REQUEST_TIMEOUT_SECONDS: int = 60
    
    # Retry Configuration
    MAX_RETRIES: int = 3
    RETRY_BASE_DELAY: float = 1.0
    
    # Rate Limiting
    REDIS_URL: str = "redis://localhost:6379"
    RATE_LIMIT_PER_MINUTE: int = 100
    RATE_LIMIT_PER_HOUR: int = 1000
    
    # Cost Management
    DAILY_BUDGET_USD: float = 50.0
    BUDGET_ALERT_THRESHOLD: float = 0.8
    
    # Monitoring
    PROMETHEUS_ENABLED: bool = True
    METRICS_PORT: int = 9090
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()