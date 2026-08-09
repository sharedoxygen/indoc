"""
Telemetry middleware for monitoring and observability
"""
import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

logger = logging.getLogger(__name__)


class TelemetryMiddleware(BaseHTTPMiddleware):
    """Middleware for telemetry and monitoring"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and collect telemetry data"""
        
        # Skip if telemetry is disabled
        if not settings.ENABLE_TELEMETRY:
            return await call_next(request)
        
        start_time = time.time()
        
        # Add request ID for tracing
        request_id = request.headers.get("X-Request-ID", str(time.time()))
        
        # Log request start
        logger.info(f"Request started: {request.method} {request.url.path} [ID: {request_id}]")
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Add telemetry headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = str(round(duration * 1000, 2))
            
            # Log request completion
            logger.info(
                f"Request completed: {request.method} {request.url.path} "
                f"[ID: {request_id}] [Status: {response.status_code}] "
                f"[Duration: {round(duration * 1000, 2)}ms]"
            )
            
            # Send metrics to monitoring service (if configured)
            await self._send_metrics(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration=duration,
                request_id=request_id
            )
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            
            # Log error
            logger.error(
                f"Request failed: {request.method} {request.url.path} "
                f"[ID: {request_id}] [Error: {str(e)}] "
                f"[Duration: {round(duration * 1000, 2)}ms]"
            )
            
            # Send error metrics
            await self._send_metrics(
                method=request.method,
                path=request.url.path,
                status_code=500,
                duration=duration,
                request_id=request_id,
                error=str(e)
            )
            
            raise
    
    async def _send_metrics(
        self,
        method: str,
        path: str,
        status_code: int,
        duration: float,
        request_id: str,
        error: str = None
    ):
        """Send metrics to monitoring service"""
        
        # This is a placeholder for actual metrics sending
        # In production, this would send to Datadog, Grafana, etc.
        
        metrics = {
            "timestamp": time.time(),
            "request_id": request_id,
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": round(duration * 1000, 2),
            "error": error
        }
        
        # Log metrics for now
        if error:
            logger.debug(f"Error metrics: {metrics}")
        else:
            logger.debug(f"Request metrics: {metrics}")
        
        # TODO: Implement actual metrics sending
        # Example integrations:
        # - OpenTelemetry
        # - Datadog
        # - Prometheus
        # - Grafana Cloud