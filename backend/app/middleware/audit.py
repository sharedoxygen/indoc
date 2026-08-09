"""
Audit logging middleware
"""
import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.audit import AuditLog
from app.core.config import settings

logger = logging.getLogger(__name__)


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware for audit logging of API requests"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log audit information"""
        
        # Skip audit logging if disabled
        if not settings.ENABLE_AUDIT_LOGGING:
            return await call_next(request)
        
        # Skip health check endpoints
        if request.url.path in ["/health", "/", "/api/v1/health"]:
            return await call_next(request)
        
        start_time = time.time()
        
        # Get request details
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Process request
        response = await call_next(request)
        
        # Calculate request duration
        duration = time.time() - start_time
        
        # Log audit information for important endpoints
        if request.url.path.startswith("/api/v1/") and request.method in ["POST", "PUT", "DELETE"]:
            try:
                # Extract user information from request if available
                user_id = None
                user_email = None
                user_role = None
                
                # Try to get user from request state (set by auth middleware)
                if hasattr(request.state, "user"):
                    user = request.state.user
                    user_id = user.id
                    user_email = user.email
                    user_role = user.role
                
                # Determine action from endpoint
                action = self._determine_action(request.method, request.url.path)
                resource_type = self._determine_resource_type(request.url.path)
                
                # Create audit log entry only for authenticated requests
                if user_id is not None:  # Only log for authenticated users
                    async with AsyncSessionLocal() as db:
                        # Ensure enum values are coerced to strings
                        coerced_role = getattr(user_role, "value", user_role) if user_role is not None else "anonymous"
                        audit_log = AuditLog(
                            user_id=user_id,
                            user_email=user_email or "anonymous",
                            user_role=coerced_role,
                            action=action,
                            resource_type=resource_type,
                            resource_id=None,  # Could be extracted from path
                            details={
                                "method": request.method,
                                "path": request.url.path,
                                "status_code": response.status_code,
                                "duration_ms": round(duration * 1000, 2)
                            },
                            ip_address=client_ip,
                            user_agent=user_agent
                        )
                        db.add(audit_log)
                        await db.commit()
                    
            except Exception as e:
                logger.error(f"Failed to create audit log: {e}")
        
        return response
    
    def _determine_action(self, method: str, path: str) -> str:
        """Determine action from HTTP method and path"""
        if "login" in path:
            return "login"
        elif "logout" in path:
            return "logout"
        elif "register" in path:
            return "register"
        elif method == "POST":
            if "upload" in path:
                return "upload"
            elif "search" in path:
                return "search"
            return "create"
        elif method == "PUT":
            return "update"
        elif method == "DELETE":
            return "delete"
        elif method == "GET":
            return "read"
        return "unknown"
    
    def _determine_resource_type(self, path: str) -> str:
        """Determine resource type from path"""
        path_parts = path.split("/")
        
        if "auth" in path:
            return "auth"
        elif "users" in path:
            return "user"
        elif "files" in path or "documents" in path:
            return "document"
        elif "search" in path:
            return "search"
        elif "settings" in path:
            return "settings"
        elif "audit" in path:
            return "audit"
        
        # Try to extract from path
        if len(path_parts) > 3:
            return path_parts[3]  # Assuming /api/v1/resource_type/...
        
        return "unknown"