from pydantic_settings import BaseSettings
from typing import Optional, Literal
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""
    
    # LLM Configuration
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    OPENAI_TEMPERATURE: float = 0.7
    
    # Alternative LLM providers
    LLM_PROVIDER: Literal["openai", "ollama", "anthropic"] = "openai"
    OLLAMA_BASE_URL: Optional[str] = "http://localhost:11434"
    OLLAMA_MODEL: Optional[str] = "llama2"
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: Optional[str] = "claude-3-sonnet-20240229"
    
    # Server Configuration
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000"
    
    # Search Configuration
    SEARCH_PROVIDER: Literal["duckduckgo", "google", "bing"] = "duckduckgo"
    GOOGLE_API_KEY: Optional[str] = None
    GOOGLE_CSE_ID: Optional[str] = None
    BING_API_KEY: Optional[str] = None
    
    # Agent Configuration
    MAX_RESEARCH_LOOPS: int = 3
    MAX_SEARCH_RESULTS_PER_QUERY: int = 5
    SEARCH_RESULT_CHAR_LIMIT: int = 1000
    
    # Session Management
    SESSION_TTL: int = 3600  # Time to live in seconds
    MAX_HISTORY_LENGTH: int = 50
    SESSION_STORAGE: Literal["memory", "redis", "database"] = "memory"
    REDIS_URL: Optional[str] = None
    DATABASE_URL: Optional[str] = None
    
    # Logging
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    LOG_FILE: Optional[str] = "logs/app.log"
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = False
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60  # seconds
    
    # Feature Flags
    ENABLE_STREAMING: bool = True
    ENABLE_CACHING: bool = True
    ENABLE_METRICS: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()