"""
Monitoring and metrics collection for the application
"""
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from functools import wraps
import time
import logging
from typing import Callable, Any
from fastapi import Request, Response
from fastapi.routing import APIRoute

logger = logging.getLogger(__name__)

# Define metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

active_connections = Gauge(
    'websocket_active_connections',
    'Number of active WebSocket connections'
)

document_uploads_total = Counter(
    'document_uploads_total',
    'Total document uploads',
    ['status', 'file_type']
)

search_queries_total = Counter(
    'search_queries_total',
    'Total search queries',
    ['search_type']
)

llm_requests_total = Counter(
    'llm_requests_total',
    'Total LLM requests',
    ['model', 'status']
)

llm_tokens_used = Counter(
    'llm_tokens_used_total',
    'Total LLM tokens used',
    ['model', 'type']
)

database_queries_total = Counter(
    'database_queries_total',
    'Total database queries',
    ['operation', 'table']
)

database_query_duration_seconds = Histogram(
    'database_query_duration_seconds',
    'Database query duration in seconds',
    ['operation', 'table']
)

celery_tasks_total = Counter(
    'celery_tasks_total',
    'Total Celery tasks',
    ['task_name', 'status']
)

celery_task_duration_seconds = Histogram(
    'celery_task_duration_seconds',
    'Celery task duration in seconds',
    ['task_name']
)

# System metrics
system_memory_usage = Gauge(
    'system_memory_usage_bytes',
    'System memory usage in bytes'
)

system_cpu_usage = Gauge(
    'system_cpu_usage_percent',
    'System CPU usage percentage'
)

system_disk_usage = Gauge(
    'system_disk_usage_bytes',
    'System disk usage in bytes',
    ['path']
)

# Business Analytics Metrics
document_views_total = Counter(
    'document_views_total',
    'Total document views',
    ['file_type', 'user_role', 'classification']
)

document_downloads_total = Counter(
    'document_downloads_total',
    'Total document downloads',
    ['file_type', 'user_role']
)

user_activity_total = Counter(
    'user_activity_total',
    'Total user activity events',
    ['user_role', 'activity_type']
)

documents_by_classification = Gauge(
    'documents_by_classification_count',
    'Document count by classification',
    ['classification']
)

documents_by_type = Gauge(
    'documents_by_type_count',
    'Document count by file type',
    ['file_type']
)

users_by_role = Gauge(
    'users_by_role_count',
    'User count by role',
    ['role']
)

storage_usage_by_type = Gauge(
    'storage_usage_by_type_bytes',
    'Storage usage by file type',
    ['file_type']
)


class MonitoringRoute(APIRoute):
    """Custom route class for automatic monitoring"""
    
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()
        
        async def custom_route_handler(request: Request) -> Response:
            start_time = time.time()
            
            # Get endpoint path
            endpoint = request.url.path
            method = request.method
            
            try:
                response: Response = await original_route_handler(request)
                status = response.status_code
            except Exception as e:
                status = 500
                raise
            finally:
                # Record metrics
                duration = time.time() - start_time
                http_requests_total.labels(
                    method=method,
                    endpoint=endpoint,
                    status=status
                ).inc()
                
                http_request_duration_seconds.labels(
                    method=method,
                    endpoint=endpoint
                ).observe(duration)
            
            return response
        
        return custom_route_handler


def monitor_function(func_name: str = None):
    """Decorator to monitor function execution"""
    def decorator(func: Callable) -> Callable:
        name = func_name or f"{func.__module__}.{func.__name__}"
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                status = "success"
            except Exception as e:
                status = "error"
                logger.error(f"Error in {name}: {str(e)}")
                raise
            finally:
                duration = time.time() - start_time
                logger.info(f"{name} completed in {duration:.2f}s with status: {status}")
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                status = "success"
            except Exception as e:
                status = "error"
                logger.error(f"Error in {name}: {str(e)}")
                raise
            finally:
                duration = time.time() - start_time
                logger.info(f"{name} completed in {duration:.2f}s with status: {status}")
            
            return result
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def monitor_database_query(operation: str, table: str):
    """Context manager for monitoring database queries"""
    class DatabaseMonitor:
        def __enter__(self):
            self.start_time = time.time()
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            duration = time.time() - self.start_time
            status = "success" if exc_type is None else "error"
            
            database_queries_total.labels(
                operation=operation,
                table=table
            ).inc()
            
            database_query_duration_seconds.labels(
                operation=operation,
                table=table
            ).observe(duration)
            
            if exc_type:
                logger.error(f"Database query error ({operation} on {table}): {exc_val}")
    
    return DatabaseMonitor()


def monitor_celery_task(task_name: str):
    """Decorator for monitoring Celery tasks"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                status = "success"
            except Exception as e:
                status = "error"
                logger.error(f"Celery task {task_name} error: {str(e)}")
                raise
            finally:
                duration = time.time() - start_time
                
                celery_tasks_total.labels(
                    task_name=task_name,
                    status=status
                ).inc()
                
                celery_task_duration_seconds.labels(
                    task_name=task_name
                ).observe(duration)
            
            return result
        
        return wrapper
    
    return decorator


async def collect_system_metrics():
    """Collect system-level metrics"""
    import psutil
    
    # Memory usage
    memory = psutil.virtual_memory()
    system_memory_usage.set(memory.used)
    
    # CPU usage
    cpu_percent = psutil.cpu_percent(interval=1)
    system_cpu_usage.set(cpu_percent)
    
    # Disk usage
    for partition in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            system_disk_usage.labels(path=partition.mountpoint).set(usage.used)
        except PermissionError:
            continue


async def metrics_endpoint() -> Response:
    """Endpoint to expose Prometheus metrics"""
    # Collect system metrics before generating response
    await collect_system_metrics()
    
    metrics = generate_latest()
    return Response(content=metrics, media_type="text/plain")


# Alert rules configuration
ALERT_RULES = {}


class AlertManager:
    """Manage and send alerts"""
    
    def __init__(self):
        self.alerts_sent = {}
    
    async def check_alerts(self):
        """Check all alert conditions and send notifications"""
        for alert_name, alert_config in ALERT_RULES.items():
            try:
                if alert_config["condition"]():
                    await self.send_alert(
                        alert_name,
                        alert_config["message"],
                        alert_config["severity"]
                    )
            except Exception as e:
                logger.error(f"Error checking alert {alert_name}: {str(e)}")
    
    async def send_alert(self, alert_name: str, message: str, severity: str):
        """Send alert notification"""
        # Implement rate limiting to avoid alert spam
        import time
        current_time = time.time()
        
        if alert_name in self.alerts_sent:
            last_sent = self.alerts_sent[alert_name]
            if current_time - last_sent < 300:  # 5 minutes cooldown
                return
        
        self.alerts_sent[alert_name] = current_time
        
        # Log the alert
        logger.warning(f"ALERT [{severity}] {alert_name}: {message}")
        
        # Send to external services (implement as needed)
        # await self.send_to_slack(message, severity)
        # await self.send_to_email(message, severity)
        # await self.send_to_pagerduty(message, severity)