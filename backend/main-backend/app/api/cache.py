"""
Cache monitoring and management API endpoints.

This module provides:
- Cache health check endpoints
- Cache performance statistics
- Cache invalidation endpoints
- Cache configuration management
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
from app.services.cache_manager import get_cache_manager, CacheManager
from app.utils.logger import get_logger

router = APIRouter(prefix="/cache", tags=["cache"])
logger = get_logger("cache_api")


@router.get("/health")
async def cache_health_check(cache_manager: CacheManager = Depends(get_cache_manager)) -> Dict[str, Any]:
    """Check cache system health."""
    try:
        health_info = await cache_manager.health_check()
        return health_info
    except Exception as e:
        logger.error(f"Cache health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cache health check failed: {str(e)}")


@router.get("/stats")
async def get_cache_stats(cache_manager: CacheManager = Depends(get_cache_manager)) -> Dict[str, Any]:
    """Get cache performance statistics."""
    try:
        stats = cache_manager.get_cache_stats()
        return {
            "cache_stats": stats,
            "summary": {
                "total_hits": sum(stat["hits"] for stat in stats.values()),
                "total_misses": sum(stat["misses"] for stat in stats.values()),
                "overall_hit_rate": round(
                    sum(stat["hits"] for stat in stats.values()) / 
                    max(sum(stat["total"] for stat in stats.values()), 1) * 100, 2
                )
            }
        }
    except Exception as e:
        logger.error(f"Failed to get cache stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get cache stats: {str(e)}")


@router.delete("/invalidate/llm")
async def invalidate_llm_cache(
    cache_manager: CacheManager = Depends(get_cache_manager)
) -> Dict[str, Any]:
    """Invalidate all LLM cache entries."""
    try:
        deleted_count = await cache_manager.invalidate_llm_cache()
        logger.info(f"Invalidated {deleted_count} LLM cache entries")
        return {
            "message": f"Invalidated {deleted_count} LLM cache entries",
            "deleted_count": deleted_count
        }
    except Exception as e:
        logger.error(f"Failed to invalidate LLM cache: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to invalidate LLM cache: {str(e)}")


@router.delete("/invalidate/mcp")
async def invalidate_mcp_cache(
    tool_name: str = None,
    cache_manager: CacheManager = Depends(get_cache_manager)
) -> Dict[str, Any]:
    """Invalidate MCP tool cache entries."""
    try:
        deleted_count = await cache_manager.invalidate_mcp_cache(tool_name)
        logger.info(f"Invalidated {deleted_count} MCP cache entries")
        return {
            "message": f"Invalidated {deleted_count} MCP cache entries",
            "deleted_count": deleted_count,
            "tool_name": tool_name
        }
    except Exception as e:
        logger.error(f"Failed to invalidate MCP cache: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to invalidate MCP cache: {str(e)}")


@router.delete("/invalidate/intent")
async def invalidate_intent_cache(
    cache_manager: CacheManager = Depends(get_cache_manager)
) -> Dict[str, Any]:
    """Invalidate intent analysis cache entries."""
    try:
        deleted_count = await cache_manager.invalidate_intent_cache()
        logger.info(f"Invalidated {deleted_count} intent cache entries")
        return {
            "message": f"Invalidated {deleted_count} intent cache entries",
            "deleted_count": deleted_count
        }
    except Exception as e:
        logger.error(f"Failed to invalidate intent cache: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to invalidate intent cache: {str(e)}")


@router.delete("/invalidate/all")
async def invalidate_all_cache(
    cache_manager: CacheManager = Depends(get_cache_manager)
) -> Dict[str, Any]:
    """Invalidate all cache entries."""
    try:
        llm_count = await cache_manager.invalidate_llm_cache()
        mcp_count = await cache_manager.invalidate_mcp_cache()
        intent_count = await cache_manager.invalidate_intent_cache()
        
        total_count = llm_count + mcp_count + intent_count
        
        logger.info(f"Invalidated all cache entries: {total_count} total")
        return {
            "message": "Invalidated all cache entries",
            "deleted_counts": {
                "llm": llm_count,
                "mcp": mcp_count,
                "intent": intent_count,
                "total": total_count
            }
        }
    except Exception as e:
        logger.error(f"Failed to invalidate all cache: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to invalidate all cache: {str(e)}")


@router.get("/keys")
async def list_cache_keys(
    pattern: str = "*",
    limit: int = 100,
    cache_manager: CacheManager = Depends(get_cache_manager)
) -> Dict[str, Any]:
    """List cache keys matching pattern."""
    try:
        redis_client = await cache_manager._get_redis_client()
        keys = await redis_client.keys(pattern)
        
        # Limit results
        keys = keys[:limit]
        
        # Get TTL for each key
        key_info = []
        for key in keys:
            ttl = await redis_client.ttl(key)
            key_info.append({
                "key": key,
                "ttl": ttl if ttl > 0 else "expired"
            })
        
        return {
            "pattern": pattern,
            "keys": key_info,
            "total_found": len(keys),
            "limit": limit
        }
    except Exception as e:
        logger.error(f"Failed to list cache keys: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list cache keys: {str(e)}") 