"""
API v1 router aggregation
"""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    users,
    files,
    bulk_upload,
    search,
    search_inspector,
    mcp,
    metadata,
    audit,
    settings,
    analytics,
    llm,
    chat,
    chat_stream,
    chat_history,
    compliance,
    relationships,
    mcp_tools,
    mfa,
    access,
    ownership,
    rbac,
    metrics_business,
    logs,
    reindex,
    processing_websocket,
    integrity,
    agent
)

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(mfa.router, prefix="/mfa", tags=["MFA"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(files.router, prefix="/files", tags=["Files"])
api_router.include_router(bulk_upload.router, prefix="/files", tags=["Bulk Upload"])
api_router.include_router(search.router, prefix="/search", tags=["Search"])
api_router.include_router(search_inspector.router, prefix="/search-inspector", tags=["Search Inspector"])
api_router.include_router(mcp.router, prefix="/mcp", tags=["MCP"])
api_router.include_router(metadata.router, prefix="/metadata", tags=["Metadata"])
api_router.include_router(audit.router, prefix="/audit", tags=["Audit"])
api_router.include_router(settings.router, prefix="/settings", tags=["Settings"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(llm.router, prefix="/llm", tags=["LLM"])
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
api_router.include_router(chat_stream.router, prefix="/chat", tags=["Chat Streaming"])
api_router.include_router(chat_history.router, prefix="/chat", tags=["Chat History"])
api_router.include_router(compliance.router, prefix="/compliance", tags=["Compliance"])
api_router.include_router(relationships.router, prefix="/relationships", tags=["Document Relationships"])
api_router.include_router(mcp_tools.router, prefix="/mcp", tags=["MCP Tools"])
api_router.include_router(access.router, prefix="/access", tags=["Document Access"])
api_router.include_router(ownership.router, prefix="/ownership", tags=["Document Ownership"])
api_router.include_router(rbac.router, prefix="/rbac", tags=["RBAC Management"])
api_router.include_router(metrics_business.router, prefix="/metrics", tags=["Business Metrics"])
api_router.include_router(logs.router, prefix="/logs", tags=["System Logs"])
api_router.include_router(reindex.router, prefix="/admin", tags=["Admin - Reindex"])
api_router.include_router(integrity.router, prefix="/integrity", tags=["Data Integrity"])
api_router.include_router(agent.router, prefix="/agent", tags=["Autonomous Agent"])
api_router.include_router(processing_websocket.router, tags=["WebSocket - Processing"])
