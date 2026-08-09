"""
Application settings endpoints
"""
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.security import get_current_user
from app.core.config import settings as app_settings
from app.models.user import User

router = APIRouter()


@router.get("/")
async def get_settings(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get application settings (non-sensitive)"""
    
    # Return only non-sensitive settings
    return {
        "app_name": app_settings.APP_NAME,
        "app_version": app_settings.APP_VERSION,
        "max_upload_size": app_settings.MAX_UPLOAD_SIZE,
        "allowed_extensions": app_settings.ALLOWED_EXTENSIONS,
        "search_timeout_ms": app_settings.SEARCH_TIMEOUT_MS,
        "rerank_timeout_ms": app_settings.RERANK_TIMEOUT_MS,
        "audit_log_retention_days": app_settings.AUDIT_LOG_RETENTION_DAYS,
        "enable_telemetry": app_settings.ENABLE_TELEMETRY,
        "enable_audit_logging": app_settings.ENABLE_AUDIT_LOGGING,
        "enable_field_encryption": app_settings.ENABLE_FIELD_ENCRYPTION,
        "ollama_model": app_settings.OLLAMA_MODEL
    }


@router.get("/admin")
async def get_admin_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get admin settings (requires admin role)"""
    
    # Only admins can view admin settings
    if getattr(current_user.role, "value", current_user.role) != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view admin settings"
        )
    
    return {
        "database": {
            "host": app_settings.POSTGRES_HOST,
            "port": app_settings.POSTGRES_PORT,
            "database": app_settings.POSTGRES_DB,
            "user": app_settings.POSTGRES_USER
        },
        "elasticsearch": {
            "url": app_settings.ELASTICSEARCH_URL,
            "index": app_settings.ELASTICSEARCH_INDEX
        },
        "qdrant": {
            "url": app_settings.WEAVIATE_URL,
            "class": app_settings.WEAVIATE_CLASS
        },
        "redis": {
            "url": app_settings.REDIS_URL
        },
        "ollama": {
            "base_url": app_settings.OLLAMA_BASE_URL,
            "model": app_settings.OLLAMA_MODEL,
            "timeout": app_settings.LLM_TIMEOUT_S
        },
        "storage": {
            "temp_path": str(app_settings.TEMP_REPO_PATH),
            "storage_path": str(app_settings.STORAGE_PATH)
        }
    }


@router.put("/admin")
async def update_admin_settings(
    settings_update: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Update admin settings (requires admin role)"""
    
    # Only admins can update settings
    if getattr(current_user.role, "value", current_user.role) != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can update settings"
        )
    
    # In a real implementation, this would update configuration
    # For now, return a success message
    return {
        "status": "success",
        "message": "Settings update is not implemented in this version",
        "note": "Settings are currently managed through environment variables"
    }


@router.get("/features")
async def get_feature_flags(
    current_user: User = Depends(get_current_user)
) -> Dict[str, bool]:
    """Get feature flags"""
    
    return {
        "telemetry_enabled": app_settings.ENABLE_TELEMETRY,
        "audit_logging_enabled": app_settings.ENABLE_AUDIT_LOGGING,
        "field_encryption_enabled": app_settings.ENABLE_FIELD_ENCRYPTION,
        "email_ingestion_enabled": bool(app_settings.EMAIL_IMAP_SERVER),
        "mcp_enabled": True,
        "bulk_upload_enabled": True,
        "advanced_search_enabled": True
    }


@router.get("/health/dependencies")
async def check_dependencies_health(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Check health of all dependencies"""
    
    health_status = {
        "database": "unknown",
        "elasticsearch": "unknown",
        "qdrant": "unknown",
        "redis": "unknown",
        "ollama": "unknown"
    }
    
    # Check database
    try:
        from app.db.session import async_engine
        async with async_engine.connect() as conn:
            await conn.execute("SELECT 1")
        health_status["database"] = "healthy"
    except Exception as e:
        health_status["database"] = f"unhealthy: {str(e)}"
    
    # Check Elasticsearch
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{app_settings.ELASTICSEARCH_URL}/_cluster/health")
            if response.status_code == 200:
                health_status["elasticsearch"] = "healthy"
            else:
                health_status["elasticsearch"] = f"unhealthy: status {response.status_code}"
    except Exception as e:
        health_status["elasticsearch"] = f"unhealthy: {str(e)}"
    
    # Check Weaviate
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{app_settings.WEAVIATE_URL}/v1/.well-known/ready")
            if response.status_code == 200:
                health_status["qdrant"] = "healthy"
            else:
                health_status["qdrant"] = f"unhealthy: status {response.status_code}"
    except Exception as e:
        health_status["qdrant"] = f"unhealthy: {str(e)}"
    
    # Check Redis
    try:
        import redis.asyncio as redis
        r = redis.from_url(app_settings.REDIS_URL)
        await r.ping()
        health_status["redis"] = "healthy"
        await r.close()
    except Exception as e:
        health_status["redis"] = f"unhealthy: {str(e)}"
    
    # Check Ollama
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{app_settings.OLLAMA_BASE_URL}/api/tags")
            if response.status_code == 200:
                health_status["ollama"] = "healthy"
            else:
                health_status["ollama"] = f"unhealthy: status {response.status_code}"
    except Exception as e:
        health_status["ollama"] = f"unhealthy: {str(e)}"
    
    # Calculate overall health
    all_healthy = all(status == "healthy" for status in health_status.values())
    
    return {
        "overall": "healthy" if all_healthy else "degraded",
        "dependencies": health_status
    }