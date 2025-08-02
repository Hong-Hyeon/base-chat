from openai import OpenAI
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.utils.logger import get_logger


class GPTEmbeddingService:
    """Service for creating embeddings using OpenAI GPT models."""
    
    def __init__(self):
        self.logger = get_logger("gpt_embedding_service")
        self.model = settings.embedding_model
        
        # Configure OpenAI client
        if settings.openai_api_key:
            self.client = OpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url
            )
        else:
            self.logger.warning("OpenAI API key not provided")
            self.client = None
    
    async def create_embedding(self, text: str) -> List[float]:
        """Create embedding for a single text."""
        try:
            if not self.client:
                raise Exception("OpenAI client not initialized - API key required")
                
            self.logger.info(f"Creating embedding for text: {text[:50]}...")
            
            response = self.client.embeddings.create(
                model=self.model,
                input=text
            )
            
            embedding = response.data[0].embedding
            self.logger.info(f"Embedding created successfully, dimension: {len(embedding)}")
            
            return embedding
            
        except Exception as e:
            self.logger.error(f"Error creating embedding: {str(e)}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Check OpenAI API health."""
        try:
            if not self.client:
                return {
                    "status": "unhealthy",
                    "error": "OpenAI API key not provided",
                    "model": self.model
                }
            
            # Try to create a simple embedding
            test_embedding = await self.create_embedding("test")
            return {
                "status": "healthy",
                "model": self.model,
                "embedding_dimension": len(test_embedding)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "model": self.model
            }
