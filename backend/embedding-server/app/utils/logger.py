import logging
import sys
from typing import Optional
from app.core.config import settings


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """Get a logger instance."""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(getattr(logging, level or settings.log_level))
        
        # Create console handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(getattr(logging, level or settings.log_level))
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(handler)
    
    return logger


def log_request_info(logger: logging.Logger, method: str, path: str, status_code: int, duration: float):
    """Log request information."""
    logger.info(
        f"Request: {method} {path} - Status: {status_code} - Duration: {duration:.3f}s"
    )
