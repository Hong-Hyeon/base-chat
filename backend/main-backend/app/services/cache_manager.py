"""
Cache management system for LangGraph workflow optimization.

This module provides:
- Redis-based caching for LLM responses, MCP tools, and intent analysis
- Cache key generation strategies
- Cache invalidation logic
- Performance metrics collection
"""

import json
import hashlib
import asyncio
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
import redis.asyncio as aioredis
from app.core.config import settings
from app.utils.logger import get_logger


class CacheManager:
    """Redis-based cache manager for LangGraph workflow optimization."""
    
    def __init__(self):
        self.logger = get_logger("cache_manager")
        self.redis_client: Optional[aioredis.Redis] = None
        self._connection_lock = asyncio.Lock()
        
        # Cache configuration
        self.enabled = settings.cache_enabled
        self.default_ttl = settings.cache_default_ttl
        self.llm_ttl = settings.cache_llm_ttl
        self.mcp_ttl = settings.cache_mcp_ttl
        self.intent_ttl = settings.cache_intent_ttl
        
        # Performance metrics
        self.metrics = {
            "llm": {"hits": 0, "misses": 0},
            "mcp": {"hits": 0, "misses": 0},
            "intent": {"hits": 0, "misses": 0}
        }
    
    async def _get_redis_client(self) -> aioredis.Redis:
        """Get Redis client with connection pooling."""
        if self.redis_client is None:
            async with self._connection_lock:
                if self.redis_client is None:
                    try:
                        self.redis_client = aioredis.from_url(
                            settings.redis_url,
                            encoding="utf-8",
                            decode_responses=True,
                            max_connections=20
                        )
                        # Test connection
                        await self.redis_client.ping()
                        self.logger.info("Redis cache connection established")
                    except Exception as e:
                        self.logger.error(f"Failed to connect to Redis: {str(e)}")
                        raise
        return self.redis_client
    
    def _generate_llm_cache_key(self, messages: List[Dict], model: str, temperature: float, max_tokens: Optional[int] = None) -> str:
        """Generate cache key for LLM responses."""
        # Create a stable representation of messages
        message_content = []
        for msg in messages:
            if isinstance(msg, dict):
                content = msg.get("content", "")
                role = msg.get("role", "")
            else:
                content = getattr(msg, "content", "")
                role = getattr(msg, "role", "")
            message_content.append(f"{role}:{content}")
        
        # Create hash from message content and parameters
        content_str = "|".join(message_content)
        params_str = f"{model}:{temperature}:{max_tokens or 'default'}"
        combined = f"{content_str}|{params_str}"
        
        # Generate hash
        hash_value = hashlib.md5(combined.encode()).hexdigest()
        return f"llm:{hash_value}"
    
    def _generate_mcp_cache_key(self, tool_name: str, input_data: Dict[str, Any]) -> str:
        """Generate cache key for MCP tool calls."""
        # Create stable representation of input data
        input_str = json.dumps(input_data, sort_keys=True)
        hash_value = hashlib.md5(f"{tool_name}:{input_str}".encode()).hexdigest()
        return f"mcp:{tool_name}:{hash_value}"
    
    def _generate_intent_cache_key(self, user_content: str) -> str:
        """Generate cache key for intent analysis."""
        # Normalize user content (remove extra whitespace, lowercase)
        normalized_content = " ".join(user_content.lower().split())
        hash_value = hashlib.md5(normalized_content.encode()).hexdigest()
        return f"intent:{hash_value}"
    
    async def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get value from cache."""
        if not self.enabled:
            return None
        
        try:
            redis_client = await self._get_redis_client()
            cached_value = await redis_client.get(cache_key)
            
            if cached_value:
                self.logger.debug(f"Cache hit: {cache_key}")
                return json.loads(cached_value)
            else:
                self.logger.debug(f"Cache miss: {cache_key}")
                return None
                
        except Exception as e:
            self.logger.error(f"Cache get error for {cache_key}: {str(e)}")
            return None
    
    async def set(self, cache_key: str, value: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set value in cache with TTL."""
        if not self.enabled:
            return False
        
        try:
            redis_client = await self._get_redis_client()
            serialized_value = json.dumps(value, default=str)
            
            if ttl is None:
                ttl = self.default_ttl
            
            await redis_client.setex(cache_key, ttl, serialized_value)
            self.logger.debug(f"Cache set: {cache_key} (TTL: {ttl}s)")
            return True
            
        except Exception as e:
            self.logger.error(f"Cache set error for {cache_key}: {str(e)}")
            return False
    
    async def delete(self, cache_key: str) -> bool:
        """Delete value from cache."""
        if not self.enabled:
            return False
        
        try:
            redis_client = await self._get_redis_client()
            result = await redis_client.delete(cache_key)
            self.logger.debug(f"Cache delete: {cache_key}")
            return result > 0
            
        except Exception as e:
            self.logger.error(f"Cache delete error for {cache_key}: {str(e)}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern."""
        if not self.enabled:
            return 0
        
        try:
            redis_client = await self._get_redis_client()
            keys = await redis_client.keys(pattern)
            if keys:
                result = await redis_client.delete(*keys)
                self.logger.info(f"Cache delete pattern: {pattern} ({len(keys)} keys)")
                return result
            return 0
            
        except Exception as e:
            self.logger.error(f"Cache delete pattern error for {pattern}: {str(e)}")
            return 0
    
    async def get_llm_cache(self, messages: List[Dict], model: str, temperature: float, max_tokens: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Get LLM response from cache."""
        cache_key = self._generate_llm_cache_key(messages, model, temperature, max_tokens)
        result = await self.get(cache_key)
        
        if result:
            self.metrics["llm"]["hits"] += 1
        else:
            self.metrics["llm"]["misses"] += 1
        
        return result
    
    async def set_llm_cache(self, messages: List[Dict], model: str, temperature: float, max_tokens: Optional[int], response: Dict[str, Any]) -> bool:
        """Set LLM response in cache."""
        cache_key = self._generate_llm_cache_key(messages, model, temperature, max_tokens)
        return await self.set(cache_key, response, self.llm_ttl)
    
    async def get_mcp_cache(self, tool_name: str, input_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get MCP tool result from cache."""
        cache_key = self._generate_mcp_cache_key(tool_name, input_data)
        result = await self.get(cache_key)
        
        if result:
            self.metrics["mcp"]["hits"] += 1
        else:
            self.metrics["mcp"]["misses"] += 1
        
        return result
    
    async def set_mcp_cache(self, tool_name: str, input_data: Dict[str, Any], result: Dict[str, Any]) -> bool:
        """Set MCP tool result in cache."""
        cache_key = self._generate_mcp_cache_key(tool_name, input_data)
        return await self.set(cache_key, result, self.mcp_ttl)
    
    async def get_intent_cache(self, user_content: str) -> Optional[Dict[str, Any]]:
        """Get intent analysis result from cache."""
        cache_key = self._generate_intent_cache_key(user_content)
        result = await self.get(cache_key)
        
        if result:
            self.metrics["intent"]["hits"] += 1
        else:
            self.metrics["intent"]["misses"] += 1
        
        return result
    
    async def set_intent_cache(self, user_content: str, result: Dict[str, Any]) -> bool:
        """Set intent analysis result in cache."""
        cache_key = self._generate_intent_cache_key(user_content)
        return await self.set(cache_key, result, self.intent_ttl)
    
    async def invalidate_llm_cache(self, messages: List[Dict] = None) -> int:
        """Invalidate LLM cache based on context."""
        if messages and len(messages) > 10:
            # Long conversations are context-dependent, invalidate all LLM cache
            return await self.delete_pattern("llm:*")
        return 0
    
    async def invalidate_mcp_cache(self, tool_name: str = None) -> int:
        """Invalidate MCP tool cache."""
        if tool_name:
            return await self.delete_pattern(f"mcp:{tool_name}:*")
        else:
            return await self.delete_pattern("mcp:*")
    
    async def invalidate_intent_cache(self, user_content: str = None) -> int:
        """Invalidate intent analysis cache."""
        if user_content:
            cache_key = self._generate_intent_cache_key(user_content)
            return 1 if await self.delete(cache_key) else 0
        else:
            return await self.delete_pattern("intent:*")
    
    def get_cache_stats(self) -> Dict[str, Dict[str, Union[int, float]]]:
        """Get cache performance statistics."""
        stats = {}
        
        for cache_type, metrics in self.metrics.items():
            total = metrics["hits"] + metrics["misses"]
            hit_rate = (metrics["hits"] / total * 100) if total > 0 else 0
            
            stats[cache_type] = {
                "hits": metrics["hits"],
                "misses": metrics["misses"],
                "total": total,
                "hit_rate": round(hit_rate, 2)
            }
        
        return stats
    
    async def health_check(self) -> Dict[str, Any]:
        """Check cache system health."""
        try:
            redis_client = await self._get_redis_client()
            await redis_client.ping()
            
            # Get Redis info
            info = await redis_client.info()
            
            return {
                "status": "healthy",
                "redis_connected": True,
                "cache_enabled": self.enabled,
                "redis_memory_used": info.get("used_memory_human", "unknown"),
                "redis_keyspace": info.get("db0", {}),
                "cache_stats": self.get_cache_stats()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "redis_connected": False,
                "cache_enabled": self.enabled,
                "error": str(e)
            }
    
    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
            self.logger.info("Redis cache connection closed")


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


async def get_cache_manager() -> CacheManager:
    """Get global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager 