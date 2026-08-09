"""
Security headers middleware with strict CSP and modern security policies
"""
import logging
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class SecurityHeadersConfig:
    """Configuration for security headers"""
    
    def __init__(
        self,
        csp_report_only: bool = False,
        csp_report_uri: Optional[str] = None,
        hsts_enabled: bool = True,
        hsts_max_age: int = 31536000,  # 1 year
        permissions_policy_enabled: bool = True
    ):
        self.csp_report_only = csp_report_only
        self.csp_report_uri = csp_report_uri
        self.hsts_enabled = hsts_enabled
        self.hsts_max_age = hsts_max_age
        self.permissions_policy_enabled = permissions_policy_enabled
    
    def get_csp_header(self, is_production: bool = False) -> str:
        """
        Generate Content-Security-Policy header
        
        Production CSP is stricter (no unsafe-inline, no localhost)
        Development CSP allows localhost for local testing
        """
        if is_production:
            # Strict CSP for production
            csp_directives = [
                "default-src 'self'",
                "script-src 'self' 'strict-dynamic'",  # No unsafe-inline in production
                "style-src 'self' 'unsafe-hashes'",  # Allow hashed inline styles only
                "img-src 'self' data: blob: https:",
                "font-src 'self' data:",
                "connect-src 'self' wss: https:",
                "frame-ancestors 'none'",
                "base-uri 'self'",
                "form-action 'self'",
                "object-src 'none'",
                "upgrade-insecure-requests"
            ]
        else:
            # Development CSP (more permissive for local dev)
            csp_directives = [
                "default-src 'self'",
                "script-src 'self' 'strict-dynamic' 'unsafe-inline'",  # Allow inline for dev
                "style-src 'self' 'unsafe-inline'",
                "img-src 'self' data: blob: http: https:",
                "font-src 'self' data:",
                "connect-src 'self' http://localhost:* ws://localhost:* wss: https:",
                "frame-ancestors 'none'",
                "base-uri 'self'",
                "form-action 'self'",
                "object-src 'none'"
            ]
        
        # Add report URI if configured
        if self.csp_report_uri:
            csp_directives.append(f"report-uri {self.csp_report_uri}")
        
        return "; ".join(csp_directives)
    
    def get_permissions_policy(self) -> str:
        """
        Generate Permissions-Policy header
        
        Restricts browser features to prevent misuse
        """
        policies = [
            "geolocation=()",  # No geolocation
            "microphone=()",  # No microphone access
            "camera=()",  # No camera access
            "payment=()",  # No payment API
            "usb=()",  # No USB access
            "magnetometer=()",  # No magnetometer
            "gyroscope=()",  # No gyroscope
            "accelerometer=()",  # No accelerometer
            "interest-cohort=()"  # Opt out of FLoC
        ]
        return ", ".join(policies)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Enhanced security headers middleware
    
    Features:
    - Content Security Policy (CSP) with report-only mode
    - HTTP Strict Transport Security (HSTS)
    - Permissions Policy
    - X-Frame-Options, X-Content-Type-Options, etc.
    - Referrer-Policy
    """
    
    def __init__(
        self,
        app,
        config: Optional[SecurityHeadersConfig] = None,
        is_production: bool = False
    ):
        super().__init__(app)
        self.config = config or SecurityHeadersConfig()
        self.is_production = is_production
        self.csp_header_name = (
            "Content-Security-Policy-Report-Only" 
            if self.config.csp_report_only 
            else "Content-Security-Policy"
        )
        
        logger.info(
            f"SecurityHeadersMiddleware initialized. "
            f"CSP report-only: {self.config.csp_report_only}, "
            f"Production mode: {self.is_production}"
        )

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        
        # Cache control for API responses - prevent stale data issues
        if request.url.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        
        # Basic hardening headers
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'DENY')
        response.headers.setdefault('X-XSS-Protection', '0')  # Disable legacy XSS filter (CSP is better)
        
        # Referrer Policy - don't leak URLs
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        
        # Content Security Policy
        csp = self.config.get_csp_header(self.is_production)
        response.headers.setdefault(self.csp_header_name, csp)
        
        # Permissions Policy (formerly Feature-Policy)
        if self.config.permissions_policy_enabled:
            permissions_policy = self.config.get_permissions_policy()
            response.headers.setdefault('Permissions-Policy', permissions_policy)
        
        # HTTP Strict Transport Security (only in production with HTTPS)
        if self.config.hsts_enabled and self.is_production:
            hsts_value = f"max-age={self.config.hsts_max_age}; includeSubDomains; preload"
            response.headers.setdefault('Strict-Transport-Security', hsts_value)
        
        # Cross-Origin policies
        response.headers.setdefault('Cross-Origin-Opener-Policy', 'same-origin')
        response.headers.setdefault('Cross-Origin-Embedder-Policy', 'require-corp')
        response.headers.setdefault('Cross-Origin-Resource-Policy', 'same-origin')
        
        return response
