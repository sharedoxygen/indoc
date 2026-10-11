"""HTTP gateway: authentication before discovery, host checks, rate limits, tool catalog."""

import pytest

pytest.importorskip("mcp")

import httpx  # noqa: E402

from app.core.security import create_access_token  # noqa: E402

from .helpers import EXPECTED_TOOLS, mcp_session, running_server  # noqa: E402

LIST_TOOLS = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
JSONRPC_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


async def _post(url: str, headers=None, **kwargs) -> httpx.Response:
    async with httpx.AsyncClient(timeout=10) as http:
        return await http.post(
            f"{url}/mcp",
            json=LIST_TOOLS,
            headers={**JSONRPC_HEADERS, **(headers or {})},
            **kwargs,
        )


async def test_missing_token_gets_401_before_discovery(mcp_url):
    response = await _post(mcp_url)
    assert response.status_code == 401
    assert response.headers["www-authenticate"].startswith("Bearer")
    assert "search_documents" not in response.text


@pytest.mark.parametrize(
    "authorization", ["Bearer not-a-jwt", "Basic dXNlcjpwYXNz", "Bearer"]
)
async def test_invalid_credentials_get_401(mcp_url, authorization):
    response = await _post(mcp_url, headers={"Authorization": authorization})
    assert response.status_code == 401


async def test_ordinary_session_token_is_rejected(mcp_url, world):
    session_token = create_access_token(data={"sub": world.manager.email})
    response = await _post(
        mcp_url, headers={"Authorization": f"Bearer {session_token}"}
    )
    assert response.status_code == 401


async def test_unlisted_host_is_rejected(mcp_url, world):
    response = await _post(
        mcp_url,
        headers={
            "Authorization": f"Bearer {world.tokens['manager']}",
            "Host": "evil.example.com",
        },
    )
    assert response.status_code == 421


async def test_health_needs_no_token(mcp_url):
    async with httpx.AsyncClient(timeout=10) as http:
        response = await http.get(f"{mcp_url}/healthz")
    assert response.status_code == 200


async def test_tools_list_returns_exactly_three_read_only_tools(mcp_url, world):
    async with mcp_session(mcp_url, world.tokens["analyst"]) as session:
        tools = (await session.list_tools()).tools

    assert sorted(tool.name for tool in tools) == EXPECTED_TOOLS
    schemas = {tool.name: tool.inputSchema for tool in tools}
    assert schemas["search_documents"]["required"] == ["query"]
    assert schemas["search_documents"]["properties"]["limit"]["maximum"] == 15
    assert schemas["read_document"]["required"] == ["document_id"]
    assert schemas["list_documents"].get("properties", {}) == {}
    assert all(tool.description for tool in tools)


async def test_rate_limit_returns_429(session_factory, world):
    async with running_server(session_factory, RATE_LIMIT_PER_MIN=2) as url:
        auth = {"Authorization": f"Bearer {world.tokens['manager']}"}
        statuses = [(await _post(url, headers=auth)).status_code for _ in range(3)]
    assert 429 not in statuses[:2]
    assert statuses[2] == 429
