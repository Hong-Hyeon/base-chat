"""
Prometheus metrics for embedding server monitoring
"""

from prometheus_client import Counter, Histogram, Gauge, Summary
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
import time


# Metrics definitions
EMBEDDING_REQUESTS = Counter(
    'embedding_requests_total',
    'Total number of embedding requests',
    ['model', 'status']
)

EMBEDDING_DURATION = Histogram(
    'embedding_duration_seconds',
    'Time spent creating embeddings',
    ['model']
)

SEARCH_REQUESTS = Counter(
    'search_requests_total',
    'Total number of search requests',
    ['status']
)

SEARCH_DURATION = Histogram(
    'search_duration_seconds',
    'Time spent searching embeddings'
)

BATCH_JOBS = Counter(
    'batch_jobs_total',
    'Total number of batch jobs',
    ['status']
)

BATCH_DURATION = Histogram(
    'batch_duration_seconds',
    'Time spent processing batch jobs'
)

ACTIVE_CONNECTIONS = Gauge(
    'active_database_connections',
    'Number of active database connections'
)

DOCUMENT_COUNT = Gauge(
    'total_documents',
    'Total number of documents in the database'
)

EMBEDDING_DIMENSION = Gauge(
    'embedding_dimension',
    'Dimension of embeddings'
)

# Batch processing metrics
BATCH_QUEUE_SIZE = Gauge(
    'batch_queue_size',
    'Number of items in batch processing queue'
)

BATCH_WORKERS = Gauge(
    'batch_workers_active',
    'Number of active batch processing workers'
)

# Error metrics
ERROR_COUNTER = Counter(
    'errors_total',
    'Total number of errors',
    ['service', 'error_type']
)

# Performance metrics
MEMORY_USAGE = Gauge(
    'memory_usage_bytes',
    'Memory usage in bytes'
)

CPU_USAGE = Gauge(
    'cpu_usage_percent',
    'CPU usage percentage'
)


class MetricsMiddleware:
    """Middleware for collecting metrics."""
    
    def __init__(self):
        self.start_time = None
    
    async def __call__(self, request, call_next):
        self.start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Record request metrics
        duration = time.time() - self.start_time
        
        if request.url.path.startswith('/embed'):
            EMBEDDING_REQUESTS.labels(
                model='text-embedding-3-small',
                status=response.status_code
            ).inc()
            EMBEDDING_DURATION.labels(model='text-embedding-3-small').observe(duration)
        
        elif request.url.path.startswith('/search'):
            SEARCH_REQUESTS.labels(status=response.status_code).inc()
            SEARCH_DURATION.observe(duration)
        
        elif request.url.path.startswith('/batch'):
            BATCH_JOBS.labels(status=response.status_code).inc()
            BATCH_DURATION.observe(duration)
        
        return response


def get_metrics_response():
    """Generate Prometheus metrics response."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


def update_system_metrics():
    """Update system-level metrics."""
    import psutil
    
    # Memory usage
    memory = psutil.virtual_memory()
    MEMORY_USAGE.set(memory.used)
    
    # CPU usage
    cpu_percent = psutil.cpu_percent(interval=1)
    CPU_USAGE.set(cpu_percent)


def record_error(service: str, error_type: str):
    """Record error metrics."""
    ERROR_COUNTER.labels(service=service, error_type=error_type).inc()


def update_database_metrics(stats: dict):
    """Update database-related metrics."""
    if 'total_documents' in stats:
        DOCUMENT_COUNT.set(stats['total_documents'])
    
    if 'avg_embedding_dimension' in stats:
        EMBEDDING_DIMENSION.set(stats['avg_embedding_dimension'])


def update_batch_metrics(queue_size: int, active_workers: int):
    """Update batch processing metrics."""
    BATCH_QUEUE_SIZE.set(queue_size)
    BATCH_WORKERS.set(active_workers)
