"""
Token issuance and verification for the inDoc MCP server.

MCP tokens are inDoc JWTs signed with the platform key, with their own token
type and scope so the MCP server rejects ordinary session tokens, and with a
hard lifetime cap because agent platforms persist them in session state.
"""

import time
from dataclasses import dataclass
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.security import create_access_token, decode_token
from app.models.user import User

MCP_TOKEN_TYPE = "mcp"
MCP_READ_SCOPE = "mcp:read"
CLOCK_SKEW_SECONDS = 5


class MCPAuthError(Exception):
    """Raised when a bearer token cannot be accepted by the MCP server."""


@dataclass(frozen=True)
class MCPPrincipal:
    """Authenticated caller identity carried from the HTTP layer to tools."""

    user_id: int
    email: str


def mint_mcp_token(user: User, ttl_minutes: int) -> str:
    """Issue a read-scoped MCP token for ``user`` valid for ``ttl_minutes``."""
    return create_access_token(
        data={
            "sub": user.email,
            "role": getattr(user.role, "value", user.role),
            "scp": MCP_READ_SCOPE,
            "iat": int(time.time()),
        },
        expires_delta=timedelta(minutes=ttl_minutes),
        token_type=MCP_TOKEN_TYPE,
    )


async def authenticate(
    token: str, db: AsyncSession, max_ttl_minutes: int
) -> MCPPrincipal:
    """
    Validate an MCP bearer token and resolve the active inDoc user it names.

    Signature, expiry, and user lookup reuse the platform's own token handling;
    this layer adds the MCP-specific type, scope, lifetime, and active checks.
    """
    try:
        payload = decode_token(token)
    except HTTPException as exc:
        raise MCPAuthError("invalid token") from exc

    if payload.get("type") != MCP_TOKEN_TYPE:
        raise MCPAuthError("wrong token type")
    if MCP_READ_SCOPE not in str(payload.get("scp", "")).split():
        raise MCPAuthError("missing scope")

    issued_at, expires_at = payload.get("iat"), payload.get("exp")
    if not isinstance(issued_at, (int, float)) or not isinstance(
        expires_at, (int, float)
    ):
        raise MCPAuthError("missing lifetime claims")
    if expires_at - issued_at > max_ttl_minutes * 60 + CLOCK_SKEW_SECONDS:
        raise MCPAuthError("lifetime exceeds cap")

    try:
        user = await get_current_user(token=token, db=db)
    except HTTPException as exc:
        raise MCPAuthError("unknown user") from exc
    if not user.is_active:
        raise MCPAuthError("inactive user")

    return MCPPrincipal(user_id=user.id, email=user.email)
