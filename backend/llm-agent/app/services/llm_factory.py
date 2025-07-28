from typing import Optional
from app.core.config import settings
from app.services.base_llm_service import BaseLLMService
from app.services.openai_service import OpenAIService
from app.services.vllm_service import VLLMService
from app.utils.logger import get_logger


class LLMFactory:
    """Factory for creating LLM service instances."""
    
    def __init__(self):
        self.logger = get_logger("llm_factory")
        self._llm_service: Optional[BaseLLMService] = None
    
    def create_llm_service(self, llm_type: Optional[str] = None) -> BaseLLMService:
        """Create LLM service based on type."""
        llm_type = llm_type or settings.llm_type or "openai"
        
        if llm_type.lower() == "openai":
            self.logger.info("Creating OpenAI service")
            return OpenAIService()
        elif llm_type.lower() == "vllm":
            self.logger.info("Creating vLLM service")
            return VLLMService()
        else:
            self.logger.warning(f"Unknown LLM type: {llm_type}. Falling back to OpenAI.")
            return OpenAIService()
    
    def get_llm_service(self, llm_type: Optional[str] = None) -> BaseLLMService:
        """Get or create LLM service instance (singleton pattern)."""
        if self._llm_service is None:
            self._llm_service = self.create_llm_service(llm_type)
        return self._llm_service
    
    def reset(self):
        """Reset LLM service instance (useful for testing)."""
        self._llm_service = None


# Global LLM factory instance
_llm_factory: Optional[LLMFactory] = None


def get_llm_factory() -> LLMFactory:
    """Get global LLM factory instance."""
    global _llm_factory
    if _llm_factory is None:
        _llm_factory = LLMFactory()
    return _llm_factory


def get_llm_service(llm_type: Optional[str] = None) -> BaseLLMService:
    """Get LLM service instance."""
    return get_llm_factory().get_llm_service(llm_type) 