"""Insight Bridge / LLM paths must not inherit the short default request budget."""

from app.middleware.timeout import RequestTimeoutMiddleware


def test_agent_and_llm_paths_have_long_timeouts():
    mw = RequestTimeoutMiddleware(app=None)

    assert mw._get_timeout_for_path("/api/v1/agent/stream") >= 600.0
    assert mw._get_timeout_for_path("/api/v1/agent/run") >= 600.0
    assert mw._get_timeout_for_path("/api/v1/llm/generate") >= 180.0
    assert mw._get_timeout_for_path("/api/v1/chat/chat") >= 180.0
    assert mw._get_timeout_for_path("/api/v1/documents") == 15.0
