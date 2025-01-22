import time
import psutil
import functools
import logging
import asyncio
import tracemalloc

from prometheus_client import Counter, Histogram, Gauge


# Prometheus metrics
OPERATION_LATENCY = Histogram(
    'operation_latency_seconds',
    'Time spent processing operation',
    ['operation_name']
)

OPERATION_ERRORS = Counter(
    'operation_errors_total',
    'Number of errors per operation',
    ['operation_name', 'error_type']
)

CPU_USAGE = Gauge(
    'cpu_usage_percent',
    'CPU usage percentage',
    ['operation_name']
)

MEMORY_USAGE = Gauge(
    'memory_usage_bytes',
    'Memory usage in bytes',
    ['operation_name']
)

DATA_LOSS_COUNTER = Counter(
    'data_loss_total',
    'Number of data loss events',
    ['operation_name']
)

def monitor_operation(operation_name):
    """
    Decorator to monitor operation performance and resource usage
    """
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Start monitoring
            start_time = time.time()
            tracemalloc.start()
            initial_cpu_percent = psutil.cpu_percent()
            
            try:
                # Execute the operation
                result = await func(*args, **kwargs)
                
                # Record metrics
                duration = time.time() - start_time
                current, peak = tracemalloc.get_traced_memory()
                cpu_percent = psutil.cpu_percent() - initial_cpu_percent
                
                # Update Prometheus metrics
                OPERATION_LATENCY.labels(operation_name=operation_name).observe(duration)
                CPU_USAGE.labels(operation_name=operation_name).set(cpu_percent)
                MEMORY_USAGE.labels(operation_name=operation_name).set(current)

                # Logging metrics
                # logging.info(f"""
                # Operation: {operation_name}
                # Duration: {duration:.4f}s
                # CPU Usage: {cpu_percent:.2f}%
                # Memory Usage: {current / 1024 / 1024:.2f}MB
                # Peak Memory: {peak / 1024 / 1024:.2f}MB
                # """)
                return result
                
            except Exception as e:
                # Record error metrics
                OPERATION_ERRORS.labels(
                    operation_name=operation_name,
                    error_type=type(e).__name__
                ).inc()
                
                if isinstance(e, (ConnectionError, TimeoutError)):
                    DATA_LOSS_COUNTER.labels(operation_name=operation_name).inc()
                
                logging.error(f"Error in {operation_name}: {str(e)}")
                raise
                
            finally:
                tracemalloc.stop()
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            tracemalloc.start()
            initial_cpu_percent = psutil.cpu_percent()
            
            try:
                result = func(*args, **kwargs)
                
                duration = time.time() - start_time
                current, peak = tracemalloc.get_traced_memory()
                cpu_percent = psutil.cpu_percent() - initial_cpu_percent
                
                OPERATION_LATENCY.labels(operation_name=operation_name).observe(duration)
                CPU_USAGE.labels(operation_name=operation_name).set(cpu_percent)
                MEMORY_USAGE.labels(operation_name=operation_name).set(current)
                
                # Log metrics
                # logging.info(f"""
                # Operation: {operation_name}
                # Duration: {duration:.4f}s
                # CPU Usage: {cpu_percent:.2f}%
                # Memory Usage: {current / 1024 / 1024:.2f}MB
                # Peak Memory: {peak / 1024 / 1024:.2f}MB
                # """)
                
                return result
                
            except Exception as e:
                OPERATION_ERRORS.labels(
                    operation_name=operation_name,
                    error_type=type(e).__name__
                ).inc()
                
                if isinstance(e, (ConnectionError, TimeoutError)):
                    DATA_LOSS_COUNTER.labels(operation_name=operation_name).inc()
                
                logging.error(f"Error in {operation_name}: {str(e)}")
                raise
                
            finally:
                tracemalloc.stop()
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator 