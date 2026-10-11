"""
inDoc MCP server (Streamable HTTP, stateless, JSON responses).

Exposes three read-only tools backed by ``AgentTools``, so every result is
filtered by the caller's RBAC/ABAC scope exactly as inside inDoc. Every HTTP
request is host-checked, authenticated with an MCP bearer token, and rate
limited per user before it reaches the MCP protocol layer.

    uvicorn --factory app.mcp_server.server:create_app --host 0.0.0.0 --port 8010
"""

import logging
import time
import uuid
from typing import Annotated, Any, Dict, Optional, Tuple

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.server.transport_security import (
    TransportSecurityMiddleware,
    TransportSecuritySettings,
)
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send

from app.db.session import AsyncSessionLocal
from app.mcp_server.audit import AuditActor, build_tool_audit
from app.mcp_server.auth import MCPAuthError, MCPPrincipal, authenticate
from app.mcp_server.settings import MCPServerSettings
from app.middleware.rate_limiting import InMemoryRateLimiter
from app.models.user import User
from app.services.agent.tools import AgentTools
from app.services.agent.tools import ToolError as AgentToolError

logger = logging.getLogger(__name__)

MCP_PATH = "/mcp"
HEALTH_PATH = "/healthz"
PRINCIPAL_STATE_KEY = "indoc_mcp_principal"
EXPOSED_TOOLS = ("search_documents", "read_document", "list_documents")
NOT_AVAILABLE_MARKER = "is not available to you"
INTERNAL_ERROR = "internal error"

# describe() reads no instance state, so it can be called without a db/user.
_DESCRIPTIONS = {
    tool["name"]: tool["description"] for tool in AgentTools.describe(None)
}

SERVER_INSTRUCTIONS = (
    "Read-only access to the caller's authorized inDoc documents. Results are "
    "already filtered to what the caller may see. Search first, read at most a "
    "few top hits, and cite document titles and ids."
)


def classify_result(tool: str, text: str) -> Tuple[str, int]:
    """Map an AgentTools observation to an audit outcome and HTTP-style status."""
    first_line = text.split("\n", 1)[0]
    if (
        tool == "read_document"
        and first_line.startswith("Document ")
        and NOT_AVAILABLE_MARKER in first_line
    ):
        return "not_available", 404
    if tool == "search_documents" and first_line.startswith("No documents matched"):
        return "no_results", 200
    if tool == "list_documents" and first_line.startswith(
        "No documents are accessible"
    ):
        return "empty", 200
    return "ok", 200


def _validate_arguments(tool: str, arguments: Dict[str, Any]) -> None:
    if tool == "read_document":
        try:
            uuid.UUID(str(arguments.get("document_id", "")))
        except ValueError as exc:
            raise AgentToolError("read_document requires a document uuid.") from exc


def _principal_from(ctx: Context) -> Optional[MCPPrincipal]:
    request = ctx.request_context.request
    if request is None:
        return None
    return getattr(request.state, PRINCIPAL_STATE_KEY, None)


def build_mcp(
    session_factory: async_sessionmaker[AsyncSession], settings: MCPServerSettings
) -> FastMCP:
    mcp = FastMCP(
        name="indoc",
        instructions=SERVER_INSTRUCTIONS,
        streamable_http_path=MCP_PATH,
        stateless_http=True,
        json_response=True,
        transport_security=transport_security_settings(settings),
    )

    async def run_tool(ctx: Context, tool: str, arguments: Dict[str, Any]) -> str:
        principal = _principal_from(ctx)
        if principal is None:
            raise ToolError("unauthorized")
        request: Request = ctx.request_context.request
        started = time.perf_counter()

        async with session_factory() as db:
            user = await db.get(User, principal.user_id)
            if user is None or not user.is_active:
                raise ToolError("unauthorized")
            actor = AuditActor.from_user(user)

            text = ""
            try:
                _validate_arguments(tool, arguments)
                text = await AgentTools(db, user).execute(tool, arguments)
                outcome, status = classify_result(tool, text)
            except AgentToolError as exc:
                text, outcome, status = str(exc), "invalid_input", 400
            except Exception:
                logger.exception(
                    "MCP tool %s failed for user_id=%s", tool, actor.user_id
                )
                await db.rollback()
                text, outcome, status = "", "error", 500

            db.add(
                build_tool_audit(
                    actor=actor,
                    request=request,
                    tool=tool,
                    arguments=arguments,
                    outcome=outcome,
                    status=status,
                    result_chars=len(text) if outcome != "invalid_input" else 0,
                    elapsed_ms=int((time.perf_counter() - started) * 1000),
                )
            )
            try:
                await db.commit()
            except Exception:
                # Fail closed: no tool output leaves without its audit record.
                logger.exception(
                    "MCP audit write failed for user_id=%s tool=%s", actor.user_id, tool
                )
                raise ToolError(INTERNAL_ERROR)

        if outcome == "invalid_input":
            raise ToolError(text)
        if outcome == "error":
            raise ToolError(INTERNAL_ERROR)
        return text

    @mcp.tool(
        name="search_documents",
        description=_DESCRIPTIONS["search_documents"],
        structured_output=False,
    )
    async def search_documents(
        query: Annotated[
            str, Field(min_length=1, max_length=500, description="What to search for")
        ],
        ctx: Context,
        limit: Annotated[
            int, Field(ge=1, le=15, description="Maximum number of results")
        ] = 8,
    ) -> str:
        return await run_tool(ctx, "search_documents", {"query": query, "limit": limit})

    @mcp.tool(
        name="read_document",
        description=_DESCRIPTIONS["read_document"],
        structured_output=False,
    )
    async def read_document(
        document_id: Annotated[
            str,
            Field(description="Document uuid from search_documents or list_documents"),
        ],
        ctx: Context,
    ) -> str:
        return await run_tool(
            ctx, "read_document", {"document_id": document_id.strip()[:100]}
        )

    @mcp.tool(
        name="list_documents",
        description=_DESCRIPTIONS["list_documents"],
        structured_output=False,
    )
    async def list_documents(ctx: Context) -> str:
        return await run_tool(ctx, "list_documents", {})

    @mcp.custom_route(HEALTH_PATH, methods=["GET"])
    async def health(_: Request) -> Response:
        return PlainTextResponse("ok")

    return mcp


def transport_security_settings(
    settings: MCPServerSettings,
) -> TransportSecuritySettings:
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=settings.allowed_hosts,
        allowed_origins=settings.allowed_origins,
    )


def _bearer_token(header: Optional[str]) -> Optional[str]:
    if not header:
        return None
    scheme, _, value = header.partition(" ")
    if scheme.lower() != "bearer" or not value.strip():
        return None
    return value.strip()


def _unauthorized() -> Response:
    return JSONResponse(
        {"error": "unauthorized"},
        status_code=401,
        headers={"WWW-Authenticate": 'Bearer realm="indoc-mcp"'},
    )


class MCPGatewayMiddleware:
    """Host check, bearer authentication, and per-user rate limiting for every HTTP request."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        settings: MCPServerSettings,
        limiter: InMemoryRateLimiter,
    ):
        self.app = app
        self.session_factory = session_factory
        self.settings = settings
        self.limiter = limiter
        self.security = TransportSecurityMiddleware(
            transport_security_settings(settings)
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        rejection = await self.security.validate_request(request, is_post=False)
        if rejection is not None:
            await rejection(scope, receive, send)
            return

        if request.url.path == HEALTH_PATH:
            await self.app(scope, receive, send)
            return

        token = _bearer_token(request.headers.get("authorization"))
        if token is None:
            await _unauthorized()(scope, receive, send)
            return

        try:
            async with self.session_factory() as db:
                principal = await authenticate(
                    token, db, self.settings.TOKEN_MAX_TTL_MINUTES
                )
        except MCPAuthError as exc:
            logger.info("MCP request rejected: %s", exc)
            await _unauthorized()(scope, receive, send)
            return
        except Exception:
            logger.exception("MCP authentication backend failure")
            await JSONResponse({"error": "unavailable"}, status_code=503)(
                scope, receive, send
            )
            return

        if not self.limiter.is_allowed(
            f"mcp:{principal.user_id}", self.settings.RATE_LIMIT_PER_MIN, 60
        ):
            logger.warning("MCP rate limit exceeded for user_id=%s", principal.user_id)
            await JSONResponse(
                {"error": "rate_limited"},
                status_code=429,
                headers={"Retry-After": "60"},
            )(scope, receive, send)
            return

        scope.setdefault("state", {})[PRINCIPAL_STATE_KEY] = principal
        await self.app(scope, receive, send)


def create_app(
    session_factory: Optional[async_sessionmaker[AsyncSession]] = None,
    settings: Optional[MCPServerSettings] = None,
) -> ASGIApp:
    settings = settings or MCPServerSettings()
    session_factory = session_factory or AsyncSessionLocal
    mcp = build_mcp(session_factory, settings)
    return MCPGatewayMiddleware(
        mcp.streamable_http_app(),
        session_factory=session_factory,
        settings=settings,
        limiter=InMemoryRateLimiter(),
    )
