from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, Any, Optional
from app.models.requests import Message, StreamChunk


class BaseLLMService(ABC):
    """Base class for LLM services."""
    
    def __init__(self):
        self.logger = None  # Will be set by subclasses
    
    @abstractmethod
    async def generate_text(
        self, 
        messages: list[Message], 
        model: str = None,
        temperature: float = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """Generate text using the LLM service."""
        pass
    
    @abstractmethod
    async def stream_text(
        self, 
        messages: list[Message], 
        model: str = None,
        temperature: float = None,
        max_tokens: Optional[int] = None
    ) -> AsyncGenerator[StreamChunk, None]:
        """Stream text generation using the LLM service."""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the LLM service."""
        pass
    
    def _convert_messages(self, messages: list[Message]) -> list[Dict[str, str]]:
        """Convert Pydantic messages to standard format."""
        standard_messages = []
        for msg in messages:
            standard_messages.append({
                "role": msg.role.value,
                "content": msg.content
            })
        return standard_messages 