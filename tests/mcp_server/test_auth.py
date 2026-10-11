"""MCP token verification (no MCP SDK needed; runs in the main env too)."""

import time
from datetime import timedelta

import pytest

from app.core.security import create_access_token, create_refresh_token
from app.mcp_server.auth import (
    MCP_READ_SCOPE,
    MCP_TOKEN_TYPE,
    MCPAuthError,
    authenticate,
)

MAX_TTL = 60


def _mcp_token(email: str, minutes: int = 30, **claims) -> str:
    data = {"sub": email, "scp": MCP_READ_SCOPE, "iat": int(time.time()), **claims}
    return create_access_token(
        data=data, expires_delta=timedelta(minutes=minutes), token_type=MCP_TOKEN_TYPE
    )


async def test_valid_token_resolves_principal(session_factory, world):
    async with session_factory() as db:
        principal = await authenticate(world.tokens["manager"], db, MAX_TTL)
    assert principal.user_id == world.manager.id
    assert principal.email == world.manager.email


@pytest.mark.parametrize(
    "make_token",
    [
        pytest.param(lambda w: "not-a-jwt", id="malformed"),
        pytest.param(lambda w: w.tokens["manager"][:-4] + "abcd", id="bad-signature"),
        pytest.param(lambda w: _mcp_token(w.manager.email, minutes=-1), id="expired"),
        pytest.param(
            lambda w: create_access_token(data={"sub": w.manager.email}),
            id="ordinary-session-token",
        ),
        pytest.param(
            lambda w: create_refresh_token(w.manager.id, "Manager"), id="refresh-token"
        ),
        pytest.param(
            lambda w: _mcp_token(w.manager.email, scp="other"), id="missing-scope"
        ),
        pytest.param(
            lambda w: _mcp_token(w.manager.email, minutes=MAX_TTL * 3),
            id="lifetime-over-cap",
        ),
        pytest.param(lambda w: _mcp_token("nobody@example.com"), id="unknown-user"),
        pytest.param(lambda w: w.tokens["inactive"], id="inactive-user"),
    ],
)
async def test_rejected_tokens(session_factory, world, make_token):
    async with session_factory() as db:
        with pytest.raises(MCPAuthError):
            await authenticate(make_token(world), db, MAX_TTL)
