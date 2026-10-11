"""
Audit records for MCP tool calls.

Each executed tool call produces one ``AuditLog`` row. Tokens and document
text are never recorded; only the tool, its identifying inputs, the outcome,
and the size of what was returned to the agent.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from starlette.requests import Request

from app.models.audit import AuditLog
from app.models.user import User

MAX_QUERY_CHARS = 500
CLIENT_HEADER = "x-indoc-client"


@dataclass(frozen=True)
class AuditActor:
    """Snapshot of the caller, taken before the tool runs so a rollback cannot expire it."""

    user_id: int
    email: str
    role: str
    manager_id: Optional[int]

    @classmethod
    def from_user(cls, user: User) -> "AuditActor":
        return cls(
            user_id=user.id,
            email=user.email,
            role=getattr(user.role, "value", user.role),
            manager_id=user.manager_id,
        )


def client_ip(request: Request) -> Optional[str]:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()[:45]
    return request.client.host if request.client else None


def build_tool_audit(
    *,
    actor: AuditActor,
    request: Request,
    tool: str,
    arguments: Dict[str, Any],
    outcome: str,
    status: int,
    result_chars: int,
    elapsed_ms: int,
) -> AuditLog:
    details: Dict[str, Any] = {
        "tool": tool,
        "outcome": outcome,
        "result_chars": result_chars,
        "client": request.headers.get(CLIENT_HEADER, "unknown")[:100],
    }
    if "query" in arguments:
        details["query"] = str(arguments["query"])[:MAX_QUERY_CHARS]
    if "limit" in arguments:
        details["limit"] = arguments["limit"]
    if "document_id" in arguments:
        details["document_id"] = str(arguments["document_id"])[:100]

    return AuditLog(
        user_id=actor.user_id,
        user_email=actor.email,
        user_role=actor.role,
        manager_id=actor.manager_id,
        action="mcp_tool_call",
        resource_type="mcp_tool",
        resource_id=tool,
        ip_address=client_ip(request),
        user_agent=(request.headers.get("user-agent") or "")[:500],
        request_method=request.method,
        request_path=request.url.path,
        response_status=status,
        response_time_ms=elapsed_ms,
        details=details,
    )
