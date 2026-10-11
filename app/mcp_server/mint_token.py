"""
Issue a short-lived inDoc MCP token for an existing active user.

    python -m app.mcp_server.mint_token --email manager.demo@example.com --ttl 60 \
        --output /path/to/token

Requires access to the platform signing key (operator-only). Without
``--output`` the token is printed to stdout.
"""

import argparse
import asyncio
import os
import sys
from typing import Optional, Sequence

from sqlalchemy import select

from app.db.session import AsyncSessionLocal, async_engine
from app.mcp_server.auth import mint_mcp_token
from app.mcp_server.settings import MCPServerSettings
from app.models.user import User


async def _mint(email: str, ttl_minutes: int) -> str:
    async with AsyncSessionLocal() as db:
        user = (
            await db.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()
    if user is None or not user.is_active:
        raise SystemExit(f"No active user with email {email!r}")
    return mint_mcp_token(user, ttl_minutes)


def _write_private(path: str, token: str) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as handle:
        handle.write(token)


def main(argv: Optional[Sequence[str]] = None) -> None:
    settings = MCPServerSettings()
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--email", required=True)
    parser.add_argument(
        "--ttl", type=int, default=settings.TOKEN_MAX_TTL_MINUTES, help="minutes"
    )
    parser.add_argument("--output", help="write the token to this file (mode 600)")
    args = parser.parse_args(argv)

    if not 1 <= args.ttl <= settings.TOKEN_MAX_TTL_MINUTES:
        parser.error(f"--ttl must be between 1 and {settings.TOKEN_MAX_TTL_MINUTES}")

    # SQL echo (DEBUG) writes to stdout and would corrupt a printed token.
    async_engine.sync_engine.echo = False
    token = asyncio.run(_mint(args.email, args.ttl))

    if args.output:
        _write_private(args.output, token)
    else:
        sys.stdout.write(token + "\n")


if __name__ == "__main__":
    main()
