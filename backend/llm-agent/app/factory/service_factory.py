from typing import Optional
from app.core.config import Settings
from app.services.base_llm_service import BaseLLMService
from app.services.llm_factory import get_llm_service


class ServiceFactory:
    """Factory for creating and managing service dependencies."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self._llm_service: Optional[BaseLLMService] = None
    
    @property
    def llm_service(self) -> BaseLLMService:
        """Get or create LLM service instance."""
        if self._llm_service is None:
            self._llm_service = get_llm_service(self.settings.llm_type)
        return self._llm_service
    
    @property
    def openai_service(self) -> BaseLLMService:
        """Get OpenAI service instance (for backward compatibility)."""
        return self.llm_service
    
    def reset(self):
        """Reset all service instances (useful for testing)."""
        self._llm_service = None


# Global service factory instance
def get_service_factory(settings: Optional[Settings] = None) -> ServiceFactory:
    """Get service factory instance."""
    from app.core.config import get_settings
    
    if settings is None:
        settings = get_settings()
    
    return ServiceFactory(settings) 