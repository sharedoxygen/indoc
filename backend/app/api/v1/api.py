"""
API v1 router aggregation
"""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    users,
    files,
    search,
    mcp,
    metadata,
    audit,
    settings,
    analytics,
    llm,
    chat
)

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(files.router, prefix="/files", tags=["Files"])
api_router.include_router(search.router, prefix="/search", tags=["Search"])
api_router.include_router(mcp.router, prefix="/mcp", tags=["MCP"])
api_router.include_router(metadata.router, prefix="/metadata", tags=["Metadata"])
api_router.include_router(audit.router, prefix="/audit", tags=["Audit"])
api_router.include_router(settings.router, prefix="/settings", tags=["Settings"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(llm.router, prefix="/llm", tags=["LLM"])
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])