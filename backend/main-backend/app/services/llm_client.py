import httpx
import asyncio
from typing import Dict, Any, Optional, AsyncGenerator
from app.core.config import settings
from app.utils.logger import get_logger, log_performance
from app.models.chat import ChatRequest, StreamChunk
from app.services.cache_manager import get_cache_manager
import json


class LLMClient:
    """HTTP client for communicating with the LLM Agent service with caching support."""
    
    def __init__(self, base_url: Optional[str] = None, timeout: Optional[int] = None):
        self.base_url = base_url or settings.llm_agent_url
        self.timeout = timeout or settings.llm_agent_timeout
        self.logger = get_logger("llm_client")
        
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        stream: bool = False
    ) -> httpx.Response:
        """Make HTTP request to LLM agent service."""
        url = f"{self.base_url}{endpoint}"
        
        with log_performance(self.logger, f"LLM Agent {method} {endpoint}"):
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if stream:
                    return await client.stream(method, url, json=data)
                else:
                    return await client.request(method, url, json=data)
    
    def _convert_chat_to_generate_request(self, chat_request: ChatRequest) -> Dict[str, Any]:
        """Convert ChatRequest to GenerateRequest format for LLM agent."""
        # Convert messages and handle datetime serialization
        messages = []
        for msg in chat_request.messages:
            msg_dict = msg.model_dump()
            # Convert datetime to ISO string if present
            if msg_dict.get("timestamp") and hasattr(msg_dict["timestamp"], "isoformat"):
                msg_dict["timestamp"] = msg_dict["timestamp"].isoformat()
            messages.append(msg_dict)
        
        # Wrap in request field as expected by LLM agent
        return {
            "request": {
                "messages": messages,
                "stream": chat_request.stream,
                "temperature": chat_request.temperature,
                "max_tokens": chat_request.max_tokens,
                "model": chat_request.model
            }
        }
    
    async def generate_text(self, request: ChatRequest) -> Dict[str, Any]:
        """Generate text using the LLM agent service with caching."""
        try:
            # Get cache manager
            cache_manager = await get_cache_manager()
            
            # Convert messages to dict format for cache key generation
            messages_dict = []
            for msg in request.messages:
                msg_dict = msg.model_dump()
                if msg_dict.get("timestamp") and hasattr(msg_dict["timestamp"], "isoformat"):
                    msg_dict["timestamp"] = msg_dict["timestamp"].isoformat()
                messages_dict.append(msg_dict)
            
            # Check cache first
            cached_response = await cache_manager.get_llm_cache(
                messages=messages_dict,
                model=request.model,
                temperature=request.temperature,
                max_tokens=request.max_tokens
            )
            
            if cached_response:
                self.logger.info("LLM response retrieved from cache")
                return cached_response
            
            # Cache miss - call LLM agent
            self.logger.info("LLM cache miss - calling LLM agent")
            
            # Convert ChatRequest to GenerateRequest format
            generate_data = self._convert_chat_to_generate_request(request)
            
            response = await self._make_request(
                "POST", 
                "/generate/", 
                data=generate_data
            )
            response.raise_for_status()
            response_data = response.json()
            
            # Cache the response
            await cache_manager.set_llm_cache(
                messages=messages_dict,
                model=request.model,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                response=response_data
            )
            
            return response_data
            
        except httpx.HTTPStatusError as e:
            self.logger.error(f"LLM Agent HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            self.logger.error(f"LLM Agent request failed: {str(e)}")
            raise
    
    async def stream_text(self, request: ChatRequest) -> AsyncGenerator[StreamChunk, None]:
        """Stream text generation from the LLM agent service."""
        try:
            # Convert ChatRequest to GenerateRequest format
            generate_data = self._convert_chat_to_generate_request(request)
            
            url = f"{self.base_url}/generate/stream"
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST", url, json=generate_data) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        if line.strip():
                            # Handle Server-Sent Events format
                            if line.startswith("data: "):
                                data_content = line[6:]  # Remove "data: " prefix
                                if data_content.strip() == "[DONE]":
                                    break
                                try:
                                    chunk_data = json.loads(data_content)
                                    yield StreamChunk(**chunk_data)
                                except json.JSONDecodeError:
                                    self.logger.warning(f"Invalid JSON in stream: {data_content}")
                                    continue
                            else:
                                # Try to parse as regular JSON (fallback)
                                try:
                                    chunk_data = json.loads(line)
                                    yield StreamChunk(**chunk_data)
                                except json.JSONDecodeError:
                                    self.logger.warning(f"Invalid JSON in stream: {line}")
                                    continue
                                
        except httpx.HTTPStatusError as e:
            self.logger.error(f"LLM Agent stream HTTP error: {e.response.status_code}")
            raise
        except Exception as e:
            self.logger.error(f"LLM Agent stream failed: {str(e)}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of the LLM agent service."""
        try:
            response = await self._make_request("GET", "/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"LLM Agent health check failed: {str(e)}")
            return {"status": "unhealthy", "error": str(e)}


# Global LLM client instance (for backward compatibility)
llm_client = LLMClient() 