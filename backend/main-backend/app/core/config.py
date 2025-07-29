from pydantic_settings import BaseSettings
from typing import Optional, List
import os
from pathlib import Path


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application settings
    app_name: str = "BaseChat Main Backend"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    
    # LLM Agent service settings
    llm_agent_url: str = os.getenv("LLM_AGENT_URL")
    llm_agent_timeout: int = 30
    
    # MCP Server settings
    mcp_server_url: str = os.getenv("MCP_SERVER_URL")
    
    # OpenAI settings (for direct fallback)
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    
    # Database settings (optional)
    database_url: Optional[str] = os.getenv("DATABASE_URL")
    
    # Redis Cache settings
    redis_url: str = os.getenv("REDIS_URL", "redis://basechat_redis:6379/0")
    redis_host: str = os.getenv("REDIS_HOST", "basechat_redis")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_db: int = int(os.getenv("REDIS_DB", "0"))
    redis_password: Optional[str] = os.getenv("REDIS_PASSWORD")
    
    # Cache configuration
    cache_enabled: bool = True
    cache_default_ttl: int = 3600  # 1 hour
    cache_max_size: str = "1GB"
    cache_eviction_policy: str = "lru"
    
    # Cache TTL settings (in seconds)
    cache_llm_ttl: int = 3600      # LLM responses: 1 hour
    cache_mcp_ttl: int = 1800      # MCP tools: 30 minutes
    cache_intent_ttl: int = 7200   # Intent analysis: 2 hours
    
    # Security settings
    secret_key: str = os.getenv("SECRET_KEY")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Logging settings
    log_level: str = "INFO"
    log_format: str = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"
    
    # CORS settings - Updated for frontend integration
    cors_origins: List[str] = [
        "http://localhost:3000", 
        "http://localhost:3001",
        "http://frontend:3000",  # Docker container name
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001"
    ]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


def get_settings() -> Settings:
    """Get application settings with proper .env loading."""
    # Load .env file from the project root
    env_path = Path(__file__).parent.parent.parent.parent / ".env"
    if env_path.exists():
        from dotenv import load_dotenv
        load_dotenv(env_path)
    
    return Settings()


# Global settings instance
settings = get_settings() 