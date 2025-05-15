from prometheus_client import Counter, Histogram, Gauge
from typing import Optional
import time

# Counters
processed_files = Counter(
    'processed_files_total',
    'Total number of files processed',
    ['status']
)

processing_errors = Counter(
    'processing_errors_total',
    'Total number of processing errors',
    ['error_type']
)

# Histograms
processing_time = Histogram(
    'processing_time_seconds',
    'Time spent processing files',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

# Gauges
queue_size = Gauge(
    'queue_size',
    'Current size of the processing queue'
)

def track_processing_time():
    """Decorator to track processing time of functions"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                processing_time.observe(time.time() - start_time)
                return result
            except Exception as e:
                processing_time.observe(time.time() - start_time)
                raise
        return wrapper
    return decorator

def update_queue_size(size: int):
    """Update the queue size metric"""
    queue_size.set(size)

def record_processed_file(status: str = 'success'):
    """Record a processed file"""
    processed_files.labels(status=status).inc()

def record_error(error_type: str):
    """Record a processing error"""
    processing_errors.labels(error_type=error_type).inc() 