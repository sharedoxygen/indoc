"""
Rate limiting middleware for API endpoints
"""
import time
import logging
from typing import Dict, Optional
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
import asyncio
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class InMemoryRateLimiter:
    """In-memory rate limiter using sliding window"""
    
    def __init__(self):
        self.clients: Dict[str, deque] = defaultdict(deque)
        self.cleanup_interval = 300  # 5 minutes
        self.last_cleanup = time.time()
    
    def is_allowed(self, client_id: str, limit: int, window: int) -> bool:
        """Check if request is allowed within rate limit"""
        now = time.time()
        
        # Cleanup old entries periodically
        if now - self.last_cleanup > self.cleanup_interval:
            self._cleanup_old_entries()
            self.last_cleanup = now
        
        client_requests = self.clients[client_id]
        
        # Remove requests outside the time window
        while client_requests and client_requests[0] <= now - window:
            client_requests.popleft()
        
        # Check if under limit
        if len(client_requests) < limit:
            client_requests.append(now)
            return True
        
        return False
    
    def _cleanup_old_entries(self):
        """Remove old client entries to prevent memory leaks"""
        now = time.time()
        clients_to_remove = []
        
        for client_id, requests in self.clients.items():
            # Remove old requests
            while requests and requests[0] <= now - 3600:  # 1 hour
                requests.popleft()
            
            # Remove clients with no recent requests
            if not requests:
                clients_to_remove.append(client_id)
        
        for client_id in clients_to_remove:
            del self.clients[client_id]
    
    def get_stats(self) -> Dict[str, int]:
        """Get rate limiter statistics"""
        return {
            "active_clients": len(self.clients),
            "total_requests_tracked": sum(len(requests) for requests in self.clients.values())
        }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware"""
    
    def __init__(self, app, limiter: Optional[InMemoryRateLimiter] = None):
        super().__init__(app)
        self.limiter = limiter or InMemoryRateLimiter()
        
        # Rate limit configurations for different endpoints
        self.rate_limits = {
            # Authentication endpoints (stricter limits)
            "/api/v1/auth/login": {"limit": 5, "window": 300},  # 5 attempts per 5 minutes
            "/api/v1/auth/register": {"limit": 3, "window": 3600},  # 3 registrations per hour
            
            # File upload endpoints
            "/api/v1/files/upload": {"limit": 10, "window": 60},  # 10 uploads per minute
            "/api/v1/files/bulk-upload": {"limit": 2, "window": 300},  # 2 bulk uploads per 5 minutes
            
            # Search endpoints
            "/api/v1/search": {"limit": 30, "window": 60},  # 30 searches per minute
            
            # General API endpoints
            "default": {"limit": 100, "window": 60},  # 100 requests per minute
            
            # Admin endpoints
            "/api/v1/admin": {"limit": 20, "window": 60},  # 20 admin actions per minute
            "/api/v1/users": {"limit": 20, "window": 60},  # 20 user management actions per minute
        }
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with rate limiting"""
        
        # Skip rate limiting for health checks and auth endpoints
        if request.url.path in ["/health", "/", "/api/v1/health", "/api/v1/auth/register", "/api/v1/auth/login"]:
            return await call_next(request)
        
        # Get client identifier
        client_id = self._get_client_id(request)
        
        # Get rate limit for this endpoint
        rate_limit = self._get_rate_limit(request.url.path)
        
        # Check rate limit
        if not self.limiter.is_allowed(
            client_id, 
            rate_limit["limit"], 
            rate_limit["window"]
        ):
            logger.warning(
                f"Rate limit exceeded for client {client_id} on {request.url.path}"
            )
            
            # Return rate limit error
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "limit": rate_limit["limit"],
                    "window": rate_limit["window"],
                    "retry_after": rate_limit["window"]
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(rate_limit["limit"])
        response.headers["X-RateLimit-Window"] = str(rate_limit["window"])
        
        return response
    
    def _get_client_id(self, request: Request) -> str:
        """Get unique client identifier"""
        # Try to get user ID from request state (if authenticated)
        if hasattr(request.state, "user") and request.state.user:
            return f"user:{request.state.user.id}"
        
        # Fall back to IP address
        client_ip = request.client.host if request.client else "unknown"
        
        # Check for forwarded headers (reverse proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            client_ip = real_ip
        
        return f"ip:{client_ip}"
    
    def _get_rate_limit(self, path: str) -> Dict[str, int]:
        """Get rate limit configuration for a path"""
        # Check for exact match
        if path in self.rate_limits:
            return self.rate_limits[path]
        
        # Check for prefix matches
        for pattern, limit in self.rate_limits.items():
            if pattern != "default" and path.startswith(pattern):
                return limit
        
        # Return default rate limit
        return self.rate_limits["default"]
    
    def get_stats(self) -> Dict[str, any]:
        """Get rate limiting statistics"""
        return {
            "rate_limiter": self.limiter.get_stats(),
            "configured_limits": len(self.rate_limits),
            "endpoints": list(self.rate_limits.keys())
        }


class RateLimitConfig:
    """Rate limit configuration helper"""
    
    @staticmethod
    def create_strict_config() -> Dict[str, Dict[str, int]]:
        """Create strict rate limiting configuration"""
        return {
            "/api/v1/auth/login": {"limit": 3, "window": 300},
            "/api/v1/auth/register": {"limit": 1, "window": 3600},
            "/api/v1/files/upload": {"limit": 5, "window": 60},
            "/api/v1/files/bulk-upload": {"limit": 1, "window": 600},
            "/api/v1/search": {"limit": 15, "window": 60},
            "default": {"limit": 50, "window": 60},
        }
    
    @staticmethod
    def create_development_config() -> Dict[str, Dict[str, int]]:
        """Create lenient rate limiting for development"""
        return {
            "/api/v1/auth/login": {"limit": 20, "window": 60},
            "/api/v1/auth/register": {"limit": 10, "window": 60},
            "/api/v1/files/upload": {"limit": 50, "window": 60},
            "/api/v1/files/bulk-upload": {"limit": 10, "window": 60},
            "/api/v1/search": {"limit": 100, "window": 60},
            "default": {"limit": 500, "window": 60},
        }


# Global rate limiter instance
rate_limiter = InMemoryRateLimiter()


def create_rate_limit_middleware(strict: bool = False) -> RateLimitMiddleware:
    """Create rate limit middleware with configuration"""
    middleware = RateLimitMiddleware(app=None, limiter=rate_limiter)
    
    if strict:
        middleware.rate_limits = RateLimitConfig.create_strict_config()
    else:
        middleware.rate_limits = RateLimitConfig.create_development_config()
    
    return middleware
