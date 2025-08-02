# Import routers to register them with FastAPI
from .echo_tool import router as echo_router
from .web_search_tool import router as web_search_router
from .rag_tool import register_rag_tool

# List of all routers and tools
__all__ = ["echo_router", "web_search_router", "register_rag_tool"] 