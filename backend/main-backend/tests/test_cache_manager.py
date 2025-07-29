"""
Unit tests for cache manager functionality.

This module tests:
- Cache key generation
- Cache get/set operations
- Cache invalidation
- Performance metrics
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Dict, Any

from app.services.cache_manager import CacheManager, get_cache_manager


class TestCacheManager:
    """Test cases for CacheManager class."""
    
    @pytest.fixture
    def cache_manager(self):
        """Create a test cache manager instance."""
        manager = CacheManager()
        # Mock Redis client
        manager.redis_client = AsyncMock()
        manager.redis_client.ping.return_value = True
        manager.redis_client.get.return_value = None
        manager.redis_client.setex.return_value = True
        manager.redis_client.delete.return_value = 1
        manager.redis_client.keys.return_value = []
        manager.redis_client.info.return_value = {
            "used_memory_human": "1MB",
            "db0": {"keys": 10}
        }
        return manager
    
    @pytest.fixture
    def sample_messages(self):
        """Sample messages for testing."""
        return [
            {"role": "user", "content": "Hello, how are you?"},
            {"role": "assistant", "content": "I'm doing well, thank you!"}
        ]
    
    @pytest.fixture
    def sample_llm_response(self):
        """Sample LLM response for testing."""
        return {
            "response": "I'm doing well, thank you!",
            "model": "gpt-3.5-turbo",
            "usage": {"total_tokens": 50}
        }
    
    def test_generate_llm_cache_key(self, cache_manager, sample_messages):
        """Test LLM cache key generation."""
        key1 = cache_manager._generate_llm_cache_key(
            sample_messages, "gpt-3.5-turbo", 0.7, 100
        )
        key2 = cache_manager._generate_llm_cache_key(
            sample_messages, "gpt-3.5-turbo", 0.7, 100
        )
        
        # Same input should generate same key
        assert key1 == key2
        assert key1.startswith("llm:")
        
        # Different parameters should generate different keys
        key3 = cache_manager._generate_llm_cache_key(
            sample_messages, "gpt-4", 0.7, 100
        )
        assert key1 != key3
    
    def test_generate_mcp_cache_key(self, cache_manager):
        """Test MCP cache key generation."""
        input_data1 = {"query": "test query", "limit": 10}
        input_data2 = {"query": "test query", "limit": 10}
        
        key1 = cache_manager._generate_mcp_cache_key("search_tool", input_data1)
        key2 = cache_manager._generate_mcp_cache_key("search_tool", input_data2)
        
        # Same input should generate same key
        assert key1 == key2
        assert key1.startswith("mcp:search_tool:")
        
        # Different tool should generate different key
        key3 = cache_manager._generate_mcp_cache_key("other_tool", input_data1)
        assert key1 != key3
    
    def test_generate_intent_cache_key(self, cache_manager):
        """Test intent cache key generation."""
        content1 = "Hello, how are you?"
        content2 = "Hello, how are you?"
        content3 = "Hello,   how   are   you?"  # Extra whitespace
        
        key1 = cache_manager._generate_intent_cache_key(content1)
        key2 = cache_manager._generate_intent_cache_key(content2)
        key3 = cache_manager._generate_intent_cache_key(content3)
        
        # Same content should generate same key
        assert key1 == key2
        assert key1.startswith("intent:")
        
        # Normalized content should generate same key
        assert key1 == key3
    
    @pytest.mark.asyncio
    async def test_get_set_cache(self, cache_manager):
        """Test basic cache get/set operations."""
        # Test cache miss
        result = await cache_manager.get("test_key")
        assert result is None
        
        # Test cache set
        test_data = {"test": "data"}
        success = await cache_manager.set("test_key", test_data, 3600)
        assert success is True
        
        # Mock cache hit
        cache_manager.redis_client.get.return_value = '{"test": "data"}'
        result = await cache_manager.get("test_key")
        assert result == test_data
    
    @pytest.mark.asyncio
    async def test_llm_cache_operations(self, cache_manager, sample_messages, sample_llm_response):
        """Test LLM cache operations."""
        # Test cache miss
        result = await cache_manager.get_llm_cache(
            sample_messages, "gpt-3.5-turbo", 0.7, 100
        )
        assert result is None
        assert cache_manager.metrics["llm"]["misses"] == 1
        
        # Test cache hit
        cache_manager.redis_client.get.return_value = '{"response": "cached"}'
        result = await cache_manager.get_llm_cache(
            sample_messages, "gpt-3.5-turbo", 0.7, 100
        )
        assert result == {"response": "cached"}
        assert cache_manager.metrics["llm"]["hits"] == 1
        
        # Test cache set
        success = await cache_manager.set_llm_cache(
            sample_messages, "gpt-3.5-turbo", 0.7, 100, sample_llm_response
        )
        assert success is True
    
    @pytest.mark.asyncio
    async def test_mcp_cache_operations(self, cache_manager):
        """Test MCP cache operations."""
        input_data = {"query": "test"}
        
        # Test cache miss
        result = await cache_manager.get_mcp_cache("search_tool", input_data)
        assert result is None
        assert cache_manager.metrics["mcp"]["misses"] == 1
        
        # Test cache hit
        cache_manager.redis_client.get.return_value = '{"result": "cached"}'
        result = await cache_manager.get_mcp_cache("search_tool", input_data)
        assert result == {"result": "cached"}
        assert cache_manager.metrics["mcp"]["hits"] == 1
        
        # Test cache set
        success = await cache_manager.set_mcp_cache("search_tool", input_data, {"result": "test"})
        assert success is True
    
    @pytest.mark.asyncio
    async def test_intent_cache_operations(self, cache_manager):
        """Test intent cache operations."""
        user_content = "Hello, how are you?"
        
        # Test cache miss
        result = await cache_manager.get_intent_cache(user_content)
        assert result is None
        assert cache_manager.metrics["intent"]["misses"] == 1
        
        # Test cache hit
        cache_manager.redis_client.get.return_value = '{"tools_needed": []}'
        result = await cache_manager.get_intent_cache(user_content)
        assert result == {"tools_needed": []}
        assert cache_manager.metrics["intent"]["hits"] == 1
        
        # Test cache set
        success = await cache_manager.set_intent_cache(user_content, {"tools_needed": []})
        assert success is True
    
    @pytest.mark.asyncio
    async def test_cache_invalidation(self, cache_manager):
        """Test cache invalidation operations."""
        # Mock keys for pattern deletion
        cache_manager.redis_client.keys.return_value = ["llm:key1", "llm:key2"]
        cache_manager.redis_client.delete.return_value = 2
        
        # Test LLM cache invalidation (no messages provided, should return 0)
        deleted = await cache_manager.invalidate_llm_cache()
        assert deleted == 0
        
        # Test MCP cache invalidation
        deleted = await cache_manager.invalidate_mcp_cache("search_tool")
        assert deleted == 2
        
        # Test intent cache invalidation
        deleted = await cache_manager.invalidate_intent_cache()
        assert deleted == 2
    
    def test_cache_stats(self, cache_manager):
        """Test cache statistics calculation."""
        # Set some metrics
        cache_manager.metrics["llm"]["hits"] = 8
        cache_manager.metrics["llm"]["misses"] = 2
        cache_manager.metrics["mcp"]["hits"] = 5
        cache_manager.metrics["mcp"]["misses"] = 5
        
        stats = cache_manager.get_cache_stats()
        
        assert stats["llm"]["hits"] == 8
        assert stats["llm"]["misses"] == 2
        assert stats["llm"]["total"] == 10
        assert stats["llm"]["hit_rate"] == 80.0
        
        assert stats["mcp"]["hits"] == 5
        assert stats["mcp"]["misses"] == 5
        assert stats["mcp"]["total"] == 10
        assert stats["mcp"]["hit_rate"] == 50.0
    
    @pytest.mark.asyncio
    async def test_health_check(self, cache_manager):
        """Test cache health check."""
        health = await cache_manager.health_check()
        
        assert health["status"] == "healthy"
        assert health["redis_connected"] is True
        assert health["cache_enabled"] is True
        assert "redis_memory_used" in health
        assert "cache_stats" in health
    
    @pytest.mark.asyncio
    async def test_cache_disabled(self):
        """Test cache behavior when disabled."""
        # Create a manager with cache disabled
        manager = CacheManager()
        manager.enabled = False
        
        # When cache is disabled, get should return None
        result = await manager.get("test_key")
        assert result is None
        
        # When cache is disabled, set should return False
        success = await manager.set("test_key", {"test": "data"})
        assert success is False


class TestCacheManagerIntegration:
    """Integration tests for cache manager."""
    
    @pytest.mark.asyncio
    async def test_get_cache_manager_singleton(self):
        """Test that get_cache_manager returns singleton instance."""
        manager1 = await get_cache_manager()
        manager2 = await get_cache_manager()
        
        assert manager1 is manager2
    
    @pytest.mark.asyncio
    async def test_cache_manager_close(self):
        """Test cache manager connection cleanup."""
        manager = CacheManager()
        manager.redis_client = AsyncMock()
        
        await manager.close()
        
        assert manager.redis_client is None
        # redis_client is set to None, so we can't check if close was called 