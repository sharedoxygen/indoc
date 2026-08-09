"""
Main FastAPI application
"""
from fastapi import FastAPI, Request, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
from datetime import datetime
import logging
import time

from app.core.config import settings
from app.api.v1.api import api_router
from app.db.session import async_engine
from app.models.base import Base
from app.middleware.audit import AuditMiddleware
from app.middleware.telemetry import TelemetryMiddleware
from app.core.monitoring import metrics_endpoint, MonitoringRoute
# from app.api.v1.endpoints import chat, bulk_upload  # Temporarily disabled
from app.middleware.timeout import RequestTimeoutMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.rate_limiting import RateLimitMiddleware, rate_limiter
from app.core.cache import cache_service
from app.core.siem_export import init_siem_exporter, get_siem_exporter, SIEMProvider
from app.services.search.elasticsearch_service import close_elasticsearch_service
from app.services.search.qdrant_service import close_qdrant_service
from app.core.secrets_vault import init_secrets_vault, VaultProvider
from app.api.deps import get_db, get_current_user
from app.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def _validate_security_config():
    """
    Validate critical security configuration on startup
    
    FAIL-FAST if required security config is missing or insecure
    Per Review C2.1: Prevent production deployment with empty/weak secrets
    """
    errors = []
    
    # 1. JWT Secret Key validation
    if not settings.JWT_SECRET_KEY or len(settings.JWT_SECRET_KEY) < 32:
        if settings.ENVIRONMENT == "production":
            errors.append("JWT_SECRET_KEY must be at least 32 characters in production")
        elif not settings.JWT_SECRET_KEY:
            # In development, generate a random key
            import secrets
            generated_key = secrets.token_urlsafe(64)
            logger.warning(f"⚠️ No JWT_SECRET_KEY configured, generated temporary key for development")
            logger.warning(f"⚠️ Set JWT_SECRET_KEY in .env for production!")
            # Note: We can't modify settings directly as it's frozen
            # This is a warning only in dev mode
    
    # 2. Database credentials validation
    if settings.ENVIRONMENT == "production":
        if settings.POSTGRES_PASSWORD == "indoc_dev_password":
            errors.append("Production database still using development password!")
        if settings.POSTGRES_USER == "indoc_user":
            logger.warning("⚠️ Using default database username in production")
    
    # 3. Redis validation
    if "localhost" in settings.REDIS_URL and settings.ENVIRONMENT == "production":
        logger.warning("⚠️ Redis configured for localhost in production environment")
    
    # 4. Encryption key validation
    if settings.ENABLE_FIELD_ENCRYPTION and not settings.FIELD_ENCRYPTION_KEY:
        errors.append("Field encryption enabled but FIELD_ENCRYPTION_KEY not set")
    
    # Fail fast if critical errors found
    if errors:
        logger.error("🔴 CRITICAL SECURITY CONFIGURATION ERRORS:")
        for error in errors:
            logger.error(f"   - {error}")
        logger.error("")
        logger.error("Application startup ABORTED for security reasons.")
        logger.error("Fix configuration in .env or config/local.yaml and restart.")
        raise RuntimeError(f"Security configuration validation failed: {'; '.join(errors)}")
    
    logger.info("✅ Security configuration validated")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    logger.info("Starting inDoc application...")
    
    # CRITICAL SECURITY: Fail-fast JWT validation (AI Guide + Review C2.1)
    await _validate_security_config()
    
    # Ensure storage directories exist (moved from settings validator)
    try:
        settings.TEMP_REPO_PATH.mkdir(parents=True, exist_ok=True)
        settings.STORAGE_PATH.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to initialize storage directories: {e}")
        raise
    
    # Initialize cache service
    await cache_service.connect()
    
    # Initialize secrets vault
    if settings.VAULT_ENABLED:
        vault_config = {
            "vault_url": settings.VAULT_URL,
            "vault_token": settings.VAULT_TOKEN,
        }
        init_secrets_vault(provider=VaultProvider(settings.VAULT_PROVIDER), config=vault_config)
        logger.info(f"Secrets vault initialized: provider={settings.VAULT_PROVIDER}")
    
    # Initialize SIEM exporter
    if settings.SIEM_ENABLED:
        siem_config = {
            "enabled": settings.SIEM_ENABLED,
            "log_file_path": settings.SIEM_LOG_FILE_PATH,
            "syslog_host": settings.SIEM_SYSLOG_HOST,
            "syslog_port": settings.SIEM_SYSLOG_PORT,
            "splunk_hec_url": settings.SIEM_SPLUNK_HEC_URL,
            "splunk_hec_token": settings.SIEM_SPLUNK_HEC_TOKEN,
            "datadog_api_key": settings.DATADOG_API_KEY,
            "datadog_api_url": settings.SIEM_DATADOG_API_URL,
            "cloudwatch_log_group": settings.SIEM_CLOUDWATCH_LOG_GROUP,
            "cloudwatch_log_stream": settings.SIEM_CLOUDWATCH_LOG_STREAM,
            "cloudwatch_region": settings.SIEM_CLOUDWATCH_REGION,
        }
        init_siem_exporter(provider=SIEMProvider(settings.SIEM_PROVIDER), config=siem_config)
        logger.info(f"SIEM exporter initialized: provider={settings.SIEM_PROVIDER}")
    
    # Create database tables if they don't exist
    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables verified/created successfully")
    except Exception as e:
        # If tables already exist or there's a permission issue, continue anyway
        logger.warning(f"Could not create tables (may already exist): {e}")
        logger.info("Continuing with existing database schema")

    # Validate production configuration
    try:
        settings.validate_production_config()
        logger.info(f"Configuration validated for {settings.ENVIRONMENT} environment")
    except ValueError as e:
        logger.error(f"Configuration validation failed: {e}")
        if settings.ENVIRONMENT == "production":
            raise
        else:
            logger.warning("Continuing with invalid configuration in non-production environment")
    
    yield
    
    # Shutdown
    logger.info("Shutting down inDoc application...")
    siem_exporter = get_siem_exporter()
    if siem_exporter:
        await siem_exporter.aclose()
    await close_elasticsearch_service()
    close_qdrant_service()
    await cache_service.disconnect()
    await async_engine.dispose()


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
    lifespan=lifespan
)

# Enable per-route Prometheus metrics collection for all endpoints
app.router.route_class = MonitoringRoute

# Add middleware - Enhanced CORS for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "User-Agent",
        "DNT",
        "Cache-Control",
        "X-Mx-ReqToken",
        "Keep-Alive",
        "X-Requested-With",
        "If-Modified-Since",
        "X-File-Name",
        "X-File-Size",
    ],
    expose_headers=["Content-Length", "X-Process-Time"],
    max_age=86400,  # Cache preflight for 24 hours
)

# Configure trusted hosts for production security
import os
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,test,testserver").split(",")
if settings.ENVIRONMENT == "production":
    ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS if host.strip()]
else:
    # In development/testing, allow test hosts
    ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS if host.strip()] + ["*"]

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=ALLOWED_HOSTS
)

# Add custom middleware
app.add_middleware(AuditMiddleware)
if settings.ENABLE_TELEMETRY:
    app.add_middleware(TelemetryMiddleware)
app.add_middleware(RequestTimeoutMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware, limiter=rate_limiter)

# Include API router
app.include_router(api_router, prefix=settings.API_PREFIX)

# Prometheus metrics endpoint
app.add_api_route(f"{settings.API_PREFIX}/metrics", metrics_endpoint, methods=["GET"], tags=["Monitoring"])

# Include WebSocket endpoints - temporarily disabled
# app.include_router(chat.router, prefix=f"{settings.API_PREFIX}/chat", tags=["chat"])
# app.include_router(bulk_upload.router, prefix=f"{settings.API_PREFIX}/files", tags=["bulk_upload"])

# Lightweight processing websocket to support the Document Processing UI in this app variant
# For full pipeline broadcasts, the backend app provides a richer manager; here we just accept
# connections so the UI shows Connected and can still fall back to polling.
processing_clients: set[WebSocket] = set()

@app.websocket("/ws/processing")
async def processing_ws(websocket: WebSocket, token: str | None = None):
    try:
        await websocket.accept()
        processing_clients.add(websocket)
        while True:
            data = await websocket.receive_text()
            # Minimal protocol: respond to ping with pong
            if data and 'ping' in data:
                await websocket.send_text('{"type":"pong"}')
    except WebSocketDisconnect:
        pass
    except Exception:
        # Swallow errors to keep server healthy
        logger.exception("Processing WS error")
    finally:
        if websocket in processing_clients:
            processing_clients.remove(websocket)

# Root endpoint
@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "api_docs": f"{settings.API_PREFIX}/docs"
    }

# Enhanced health check for production monitoring
@app.get("/health")
async def health_check():
    """Basic health check"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health/detailed")
async def detailed_health_check(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Detailed health check for monitoring systems"""
    import time
    start_time = time.time()

    health_status = {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.utcnow().isoformat(),
        "services": {}
    }

    # Database health check
    try:
        result = await db.execute("SELECT 1")
        result.scalar_one()
        health_status["services"]["database"] = {"status": "healthy", "response_time": time.time() - start_time}
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["services"]["database"] = {"status": "unhealthy", "error": str(e)}

    # Cache health check
    try:
        await cache_service.ping()
        health_status["services"]["cache"] = {"status": "healthy"}
    except Exception as e:
        health_status["services"]["cache"] = {"status": "unhealthy", "error": str(e)}

    # Search services health check
    try:
        # Add Elasticsearch/Weaviate health checks when implemented
        health_status["services"]["search"] = {"status": "not_implemented"}
    except Exception as e:
        health_status["services"]["search"] = {"status": "unhealthy", "error": str(e)}

    return health_status

# Test endpoint
@app.get("/test-auth")
async def test_auth():
    return {"message": "Test endpoint working", "status": "ok"}


# Enhanced global exception handlers for production
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Enhanced HTTP exception handler with structured logging"""
    error_id = f"err_{int(time.time()*1000)}"

    logger.error(
        f"HTTP Exception | ID: {error_id} | Status: {exc.status_code} | "
        f"Method: {request.method} | Path: {request.url.path} | "
        f"Detail: {exc.detail} | User-Agent: {request.headers.get('user-agent', 'unknown')}"
    )

    # Don't expose internal details in production
    error_detail = exc.detail if settings.ENVIRONMENT != "production" else "Request failed"

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": error_detail,
            "status_code": exc.status_code,
            "path": request.url.path,
            "error_id": error_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Enhanced validation error handler with detailed logging"""
    error_id = f"val_{int(time.time()*1000)}"

    # Log validation errors for debugging
    logger.warning(
        f"Validation Error | ID: {error_id} | Path: {request.url.path} | "
        f"Errors: {[{'loc': err.get('loc'), 'msg': err.get('msg')} for err in exc.errors()]}"
    )

    # Serialize validation errors without non-serializable data
    serialized_errors = []
    for err in exc.errors():
        serialized_errors.append({
            "loc": err.get("loc"),
            "msg": err.get("msg"),
            "type": err.get("type")
        })

    return JSONResponse(
        status_code=422,
        content={
            "detail": serialized_errors,
            "path": request.url.path,
            "error_id": error_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Enhanced unhandled exception handler for production"""
    error_id = f"exc_{int(time.time()*1000)}"

    # Log full exception details for debugging (but not in response)
    logger.exception(
        f"Unhandled Exception | ID: {error_id} | Method: {request.method} | "
        f"Path: {request.url.path} | Exception: {str(exc)}"
    )

    # In production, don't expose internal error details
    error_message = "Internal Server Error"
    if settings.ENVIRONMENT != "production":
        error_message = f"Unhandled error: {str(exc)}"

    return JSONResponse(
        status_code=500,
        content={
            "detail": error_message,
            "path": request.url.path,
            "error_id": error_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    )