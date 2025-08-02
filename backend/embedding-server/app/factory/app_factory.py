from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import time
from datetime import datetime
from typing import Optional

from app.core.config import Settings
from app.utils.logger import get_logger, log_request_info
from app.services.gpt_embedding_service import GPTEmbeddingService
from app.services.vector_store_service import VectorStoreService
from app.services.batch_service import BatchService


class AppFactory:
    """Factory for creating FastAPI application instances."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = get_logger("app_factory")
        self.embedding_service = None
        self.vector_store_service = None
        self.batch_service = None
    
    def create_lifespan(self):
        """Create application lifespan manager."""
        
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            """Application lifespan manager for startup and shutdown events."""
            # Startup
            self.logger.info("=== Embedding Server Starting Up ===")
            self.logger.info(f"App Name: {self.settings.app_name}")
            self.logger.info(f"Version: {self.settings.app_version}")
            self.logger.info(f"Debug Mode: {self.settings.debug}")
            self.logger.info(f"Embedding Model: {self.settings.embedding_model}")
            
            # Initialize services
            try:
                self.embedding_service = GPTEmbeddingService()
                self.vector_store_service = VectorStoreService()
                self.batch_service = BatchService()
                
                # Initialize database
                await self.vector_store_service.initialize_database()
                
                # Set global service instances in API routes
                from app.api.embedding_routes import set_services
                set_services(self.embedding_service, self.vector_store_service)
                
                from app.api.batch_routes import set_batch_service
                set_batch_service(self.batch_service)
                
                # Health checks
                embedding_health = await self.embedding_service.health_check()
                vector_store_health = await self.vector_store_service.health_check()
                
                self.logger.info(f"Embedding Service Health: {embedding_health['status']}")
                self.logger.info(f"Vector Store Health: {vector_store_health['status']}")
                
            except Exception as e:
                self.logger.error(f"Failed to initialize services: {str(e)}")
                raise
            
            yield
            
            # Shutdown
            self.logger.info("=== Embedding Server Shutting Down ===")
        
        return lifespan
    
    def create_middleware(self, app: FastAPI):
        """Add middleware to the FastAPI application."""
        
        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=self.settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Add trusted host middleware for production
        if not self.settings.debug:
            app.add_middleware(
                TrustedHostMiddleware,
                allowed_hosts=["localhost", "127.0.0.1", "0.0.0.0"]
            )
        
        # Add request logging middleware
        @app.middleware("http")
        async def logging_middleware(request: Request, call_next):
            start_time = time.time()
            
            # Log request
            self.logger.info(f"Request: {request.method} {request.url.path}")
            
            # Process request
            response = await call_next(request)
            
            # Log response
            duration = time.time() - start_time
            log_request_info(self.logger, request.method, request.url.path, response.status_code, duration)
            
            return response
    
    def create_exception_handlers(self, app: FastAPI):
        """Add exception handlers to the FastAPI application."""
        
        @app.exception_handler(Exception)
        async def global_exception_handler(request: Request, exc: Exception):
            self.logger.error(f"Unhandled exception: {str(exc)}")
            return HTTPException(status_code=500, detail="Internal server error")
    
    def create_routes(self, app: FastAPI):
        """Add routes to the FastAPI application."""
        
        # Import and include routers
        from app.api.embedding_routes import router as embedding_router
        from app.api.batch_routes import router as batch_router
        from app.api.table_routes import router as table_router, set_vector_store_service
        
        app.include_router(embedding_router)
        app.include_router(batch_router)
        app.include_router(table_router)
        
        # Set vector store service for table routes
        set_vector_store_service(self.vector_store_service)
        
        # Add monitoring endpoints
        from app.monitoring.prometheus_metrics import get_metrics_response
        
        @app.get("/metrics")
        async def metrics():
            """Prometheus metrics endpoint."""
            return get_metrics_response()
        
        # Root endpoint
        @app.get("/")
        async def root():
            return {
                "message": self.settings.app_name,
                "version": self.settings.app_version,
                "status": "running",
                "timestamp": datetime.now().isoformat()
            }
        
        # Health check endpoint
        @app.get("/health")
        async def health():
            try:
                embedding_health = await self.embedding_service.health_check()
                vector_store_health = await self.vector_store_service.health_check()
                
                # Check Celery status
                try:
                    from app.celery_app import celery_app
                    celery_health = "healthy" if celery_app.control.inspect().active() else "unhealthy"
                except:
                    celery_health = "unhealthy"
                
                return {
                    "status": "healthy" if embedding_health["status"] == "healthy" and vector_store_health["status"] == "healthy" else "unhealthy",
                    "service": "embedding-server",
                    "version": self.settings.app_version,
                    "timestamp": datetime.now().isoformat(),
                    "embedding_service": embedding_health["status"],
                    "vector_store": vector_store_health["status"],
                    "celery": celery_health
                }
            except Exception as e:
                return {
                    "status": "unhealthy",
                    "service": "embedding-server",
                    "version": self.settings.app_version,
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e)
                }
    
    def create_app(self, settings: Optional[Settings] = None) -> FastAPI:
        """Create and configure the FastAPI application."""
        
        if settings is None:
            settings = self.settings
        
        app = FastAPI(
            title=settings.app_name,
            version=settings.app_version,
            description="Embedding server for RAG applications",
            docs_url="/docs" if settings.debug else None,
            redoc_url="/redoc" if settings.debug else None,
            lifespan=self.create_lifespan()
        )
        
        # Add middleware
        self.create_middleware(app)
        
        # Add exception handlers
        self.create_exception_handlers(app)
        
        # Add routes
        self.create_routes(app)
        
        return app


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    """Factory function to create FastAPI application."""
    from app.core.config import get_settings
    
    if settings is None:
        settings = get_settings()
    
    factory = AppFactory(settings)
    return factory.create_app(settings)
