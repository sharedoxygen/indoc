"""Shared helpers for MCP server tests: a real uvicorn server and an SDK client."""

import asyncio
import socket
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, Optional

EXPECTED_TOOLS = ["list_documents", "read_document", "search_documents"]

VENDOR_CONTRACT_TEXT = (
    "Master Services Agreement between Acme Corp and Halvorsen Freight. "
    "Termination: either party may terminate for convenience on ninety (90) days "
    "written notice. Termination for cause requires a thirty (30) day cure period."
)


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@asynccontextmanager
async def running_server(session_factory, **settings_overrides) -> AsyncIterator[str]:
    """Serve the real MCP app with uvicorn in this event loop; yields the base URL."""
    import uvicorn

    from app.mcp_server.server import create_app
    from app.mcp_server.settings import MCPServerSettings

    settings = MCPServerSettings(
        **{"ALLOWED_HOSTS": "127.0.0.1:*,localhost:*", **settings_overrides}
    )
    port = _free_port()
    server = uvicorn.Server(
        uvicorn.Config(
            create_app(session_factory=session_factory, settings=settings),
            host="127.0.0.1",
            port=port,
            log_level="warning",
            lifespan="on",
        )
    )
    task = asyncio.create_task(server.serve())
    try:
        for _ in range(200):
            if server.started:
                break
            await asyncio.sleep(0.05)
        assert server.started, "MCP test server did not start"
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        await task


@asynccontextmanager
async def mcp_session(base_url: str, token: str, client_name: Optional[str] = None):
    """Official MCP SDK client session over Streamable HTTP."""
    import httpx
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    headers = {"Authorization": f"Bearer {token}"}
    if client_name:
        headers["X-Indoc-Client"] = client_name
    async with httpx.AsyncClient(headers=headers, timeout=30) as http:
        async with streamable_http_client(f"{base_url}/mcp", http_client=http) as (
            read,
            write,
            _,
        ):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session


async def call_tool(
    base_url: str, token: str, name: str, arguments: Dict[str, Any], **kwargs
):
    async with mcp_session(base_url, token, **kwargs) as session:
        return await session.call_tool(name, arguments)


def result_text(result) -> str:
    return "\n".join(
        block.text for block in result.content if getattr(block, "type", "") == "text"
    )
