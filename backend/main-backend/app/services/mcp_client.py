import httpx
from typing import Dict, Any, Optional
from app.utils.logger import get_logger
from app.core.config import get_settings
from app.services.cache_manager import get_cache_manager


class MCPClient:
    """Client for calling MCP tools from the main backend using HTTP API with caching support."""
    
    def __init__(self, base_url: str = None):
        self.settings = get_settings()
        # Use the MCP server URL from environment or default to localhost:8002
        self.base_url = base_url or getattr(self.settings, 'mcp_server_url', 'http://mcp-server:8002')
        self.logger = get_logger("mcp_client")
    
    async def call_tool(self, tool_name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call an MCP tool by name with input data using HTTP API with caching.
        
        Args:
            tool_name: Name of the MCP tool to call
            input_data: Input data for the tool
            
        Returns:
            Tool response data
        """
        try:
            # Get cache manager
            cache_manager = await get_cache_manager()
            
            # Check cache first
            cached_result = await cache_manager.get_mcp_cache(tool_name, input_data)
            
            if cached_result:
                self.logger.info(f"MCP tool {tool_name} result retrieved from cache")
                return cached_result
            
            # Cache miss - call MCP tool
            self.logger.info(f"MCP cache miss - calling tool {tool_name}")
            
            # Use the direct HTTP endpoint for the tool
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/{tool_name}",
                    json=input_data,
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()
                
                # Cache the result
                await cache_manager.set_mcp_cache(tool_name, input_data, result)
                
                return result
                
        except httpx.HTTPStatusError as e:
            self.logger.error(f"HTTP error calling tool {tool_name}: {e.response.status_code}")
            raise
        except Exception as e:
            self.logger.error(f"Error calling tool {tool_name}: {str(e)}")
            raise
    
    async def list_tools(self) -> Dict[str, Any]:
        """
        Get list of available MCP tools using OpenAPI schema.
        
        Returns:
            List of available tools
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/openapi.json",
                    timeout=10.0
                )
                response.raise_for_status()
                openapi_schema = response.json()
                
                # Extract tools from OpenAPI schema
                tools = []
                for path, methods in openapi_schema.get("paths", {}).items():
                    for method, operation in methods.items():
                        if method.lower() == "post" and "operationId" in operation:
                            operation_id = operation["operationId"]
                            if operation_id.endswith("_tool"):
                                tool_name = operation_id.replace("_tool", "")
                                tools.append({
                                    "name": tool_name,
                                    "description": operation.get("description", ""),
                                    "input_schema": operation.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema", {}),
                                    "output_schema": operation.get("responses", {}).get("200", {}).get("content", {}).get("application/json", {}).get("schema", {})
                                })
                
                return {"tools": tools}
                
        except httpx.HTTPStatusError as e:
            self.logger.error(f"HTTP error listing tools: {e.response.status_code}")
            raise
        except Exception as e:
            self.logger.error(f"Error listing tools: {str(e)}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check MCP server health.
        
        Returns:
            Health status
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/health",
                    timeout=5.0
                )
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            self.logger.error(f"HTTP error checking MCP health: {e.response.status_code}")
            return {"status": "unhealthy", "error": f"HTTP {e.response.status_code}"}
        except Exception as e:
            self.logger.error(f"Error checking MCP health: {str(e)}")
            return {"status": "unhealthy", "error": str(e)} 