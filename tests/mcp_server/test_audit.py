"""Every executed MCP tool call writes exactly one audit row, without tokens or document text."""

import json

import pytest

pytest.importorskip("mcp")

import httpx  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.mcp_server.server import classify_result  # noqa: E402
from app.models.audit import AuditLog  # noqa: E402

from .helpers import VENDOR_CONTRACT_TEXT, call_tool  # noqa: E402


async def _audit_rows(session_factory):
    async with session_factory() as db:
        return (
            (await db.execute(select(AuditLog).order_by(AuditLog.id))).scalars().all()
        )


async def test_one_row_per_call_with_user_tool_and_outcome(
    mcp_url, session_factory, world
):
    vendor_id = world.finance_doc_ids["vendor_contract"]
    await call_tool(
        mcp_url,
        world.tokens["manager"],
        "read_document",
        {"document_id": vendor_id},
        client_name="google-adk",
    )
    await call_tool(
        mcp_url, world.tokens["analyst"], "read_document", {"document_id": vendor_id}
    )
    await call_tool(
        mcp_url,
        world.tokens["analyst"],
        "search_documents",
        {"query": "termination", "limit": 5},
    )
    await call_tool(
        mcp_url, world.tokens["analyst"], "read_document", {"document_id": "not-a-uuid"}
    )

    rows = await _audit_rows(session_factory)
    assert len(rows) == 4
    summary = [
        (r.user_email, r.resource_id, r.details["outcome"], r.response_status)
        for r in rows
    ]
    assert summary == [
        (world.manager.email, "read_document", "ok", 200),
        (world.analyst.email, "read_document", "not_available", 404),
        (world.analyst.email, "search_documents", "no_results", 200),
        (world.analyst.email, "read_document", "invalid_input", 400),
    ]
    for row in rows:
        assert row.action == "mcp_tool_call"
        assert row.resource_type == "mcp_tool"
        assert row.request_path == "/mcp"
        assert row.response_time_ms is not None
    assert rows[0].details["client"] == "google-adk"
    assert rows[0].details["document_id"] == vendor_id
    assert rows[0].details["result_chars"] > 0
    assert rows[1].manager_id == world.manager.id
    assert rows[2].details["query"] == "termination"


async def test_audit_never_stores_token_or_document_text(
    mcp_url, session_factory, world
):
    token = world.tokens["manager"]
    await call_tool(
        mcp_url,
        token,
        "read_document",
        {"document_id": world.finance_doc_ids["vendor_contract"]},
    )
    await call_tool(mcp_url, token, "search_documents", {"query": "termination"})

    for row in await _audit_rows(session_factory):
        serialized = json.dumps(
            {
                column.name: str(getattr(row, column.name))
                for column in AuditLog.__table__.columns
            }
        )
        assert token not in serialized
        assert token.split(".")[2] not in serialized
        assert VENDOR_CONTRACT_TEXT not in serialized
        assert "ninety (90) days" not in serialized


async def test_rejected_requests_execute_nothing(mcp_url, session_factory, world):
    call = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "list_documents", "arguments": {}},
    }
    async with httpx.AsyncClient(timeout=10) as http:
        response = await http.post(
            f"{mcp_url}/mcp",
            json=call,
            headers={
                "Authorization": "Bearer not-a-jwt",
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
        )
    assert response.status_code == 401
    assert await _audit_rows(session_factory) == []


@pytest.mark.parametrize(
    "tool,text,expected",
    [
        (
            "read_document",
            "Document abc is not available to you (either ...).",
            ("not_available", 404),
        ),
        (
            "read_document",
            "Content of 'X':\nThis line says is not available to you.",
            ("ok", 200),
        ),
        (
            "search_documents",
            "No documents matched the query: 'x'.",
            ("no_results", 200),
        ),
        ("list_documents", "No documents are accessible to you.", ("empty", 200)),
        ("search_documents", "Top 1 result(s) for 'x':", ("ok", 200)),
    ],
)
def test_outcome_classification_tracks_agent_tool_messages(tool, text, expected):
    assert classify_result(tool, text) == expected
