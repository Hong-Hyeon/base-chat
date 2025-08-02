from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    app_name: str = "Embedding Server"
    app_version: str = "1.0.0"
    debug: bool = True
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8003
    
    # Database
    embedding_database_url: str = "postgresql://embedding_user:embedding_password@basechat_embedding_postgres:5432/embeddings"
    
    # Redis
    redis_url: str = "redis://basechat_redis:6379/1"  # DB 1 for Celery
    
    # OpenAI
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    embedding_model: str = "text-embedding-3-small"
    
    # CORS
    cors_origins: List[str] = ["*"]
    
    # Logging
    log_level: str = "INFO"
    
    # Batch Processing
    batch_size: int = 100
    max_workers: int = 4
    
    class Config:
        env_file = ".env"
        case_sensitive = False


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()


# Global settings instance
settings = get_settings()
