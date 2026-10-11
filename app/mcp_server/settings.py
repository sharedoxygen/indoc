"""
Runtime settings for the inDoc MCP server (environment prefix ``MCP_``).
"""

from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


def _split_csv(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


class MCPServerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MCP_", extra="ignore")

    SERVER_PORT: int = 8010
    # Counted per user per HTTP request; ADK issues tools/list as well as
    # tools/call, so one agent turn costs several requests.
    RATE_LIMIT_PER_MIN: int = 60
    ALLOWED_HOSTS: str = "localhost:*,127.0.0.1:*"
    ALLOWED_ORIGINS: str = ""
    TOKEN_MAX_TTL_MINUTES: int = 60

    @property
    def allowed_hosts(self) -> List[str]:
        return _split_csv(self.ALLOWED_HOSTS)

    @property
    def allowed_origins(self) -> List[str]:
        return _split_csv(self.ALLOWED_ORIGINS)
