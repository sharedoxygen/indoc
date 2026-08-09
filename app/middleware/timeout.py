"""
Request timeout middleware
"""
from typing import Dict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
import asyncio


class RequestTimeoutMiddleware(BaseHTTPMiddleware):
    """Abort requests that exceed configured timeouts."""

    def __init__(self, app, path_timeouts: Dict[str, float] | None = None):
        super().__init__(app)
        # Seconds per path prefix; 'default' applies if no match
        self.path_timeouts = path_timeouts or {
            # Chat requests can take longer due to search + LLM generation
            "/api/v1/chat/chat": 60.0,
            "/api/v1/llm": 30.0,
            "default": 15.0,
        }

    async def dispatch(self, request: Request, call_next) -> Response:
        timeout = self._get_timeout_for_path(str(request.url.path))
        try:
            return await asyncio.wait_for(call_next(request), timeout=timeout)
        except asyncio.TimeoutError:
            return JSONResponse(
                status_code=504,
                content={
                    "detail": "Request timed out",
                    "path": str(request.url.path),
                    "timeout_seconds": timeout,
                },
            )

    def _get_timeout_for_path(self, path: str) -> float:
        # Exact match
        if path in self.path_timeouts:
            return float(self.path_timeouts[path])
        # Prefix match
        for prefix, to in self.path_timeouts.items():
            if prefix != "default" and path.startswith(prefix):
                return float(to)
        return float(self.path_timeouts.get("default", 10.0))


