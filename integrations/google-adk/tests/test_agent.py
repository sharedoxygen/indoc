"""Agent wiring: per-user headers and the sign-in guard that runs before MCP tool discovery."""
import base64
import json
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("INDOC_MCP_URL", "http://indoc-mcp.test/mcp")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.adk.tools.mcp_tool import McpToolset  # noqa: E402

from indoc_agent.agent import (  # noqa: E402
    INDOC_TOOLS,
    SIGN_IN_MESSAGE,
    TOKEN_STATE_KEY,
    indoc_headers,
    require_indoc_session,
    root_agent,
)


def _jwt(exp_offset_seconds: float) -> str:
    def part(data):
        return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()

    return f"{part({'alg': 'HS256'})}.{part({'exp': time.time() + exp_offset_seconds})}.signature"


def _ctx(state):
    return SimpleNamespace(state=state)


def test_headers_carry_the_session_users_token():
    token = _jwt(600)
    headers = indoc_headers(_ctx({TOKEN_STATE_KEY: token}))
    assert headers["Authorization"] == f"Bearer {token}"
    assert headers["X-Indoc-Client"] == "google-adk"


def test_no_token_sends_no_authorization_header():
    assert "Authorization" not in indoc_headers(_ctx({}))


def test_guard_allows_a_fresh_token():
    assert require_indoc_session(_ctx({TOKEN_STATE_KEY: _jwt(600)})) is None


def test_guard_asks_to_sign_in_when_token_missing_expired_or_malformed():
    for state in ({}, {TOKEN_STATE_KEY: _jwt(-5)}, {TOKEN_STATE_KEY: _jwt(30)}, {TOKEN_STATE_KEY: "garbage"}):
        content = require_indoc_session(_ctx(state))
        assert content is not None
        assert content.parts[0].text == SIGN_IN_MESSAGE


def test_dev_token_fallback_only_when_env_is_local(monkeypatch):
    monkeypatch.setenv("INDOC_DEV_TOKEN", "dev-token")
    monkeypatch.setenv("ENV", "production")
    assert "Authorization" not in indoc_headers(_ctx({}))
    monkeypatch.setenv("ENV", "local")
    assert indoc_headers(_ctx({}))["Authorization"] == "Bearer dev-token"


def test_agent_exposes_only_the_read_only_inDoc_toolset():
    toolsets = [tool for tool in root_agent.tools if isinstance(tool, McpToolset)]
    assert len(toolsets) == 1 and len(root_agent.tools) == 1
    assert toolsets[0].tool_filter == INDOC_TOOLS
    assert root_agent.before_agent_callback is require_indoc_session
