"""Local-first LLM fallback: retry primary, then another local model, then cloud."""

import pytest

from app.services.llm_service import LLMService


class _NoCache:
    async def get_cached_llm_response(self, *a, **k):
        return None

    async def cache_llm_response(self, *a, **k):
        return None


@pytest.mark.asyncio
async def test_ollama_timeout_retries_before_openai(monkeypatch):
    llm = LLMService()
    llm.openai_api_key = "sk-test"
    calls = {"ollama": 0, "openai": 0}

    async def fake_ollama(*_args, **_kwargs):
        calls["ollama"] += 1
        if calls["ollama"] == 1:
            raise TimeoutError("ReadTimeout")
        return '{"action":"list_documents","action_input":{},"thought":"ok"}'

    async def fake_openai(*_args, **_kwargs):
        calls["openai"] += 1
        return "should-not-be-used"

    monkeypatch.setattr(llm, "_ollama_generate", fake_ollama)
    monkeypatch.setattr(llm, "_openai_generate", fake_openai)
    monkeypatch.setattr("app.services.llm_service.cache_service", _NoCache())

    text = await llm.generate_response(prompt="plan", max_tokens=50, temperature=0.1, raw=True)

    assert calls["ollama"] == 2
    assert calls["openai"] == 0
    assert "list_documents" in text


@pytest.mark.asyncio
async def test_primary_failure_uses_local_fallback_before_openai(monkeypatch):
    llm = LLMService()
    llm.openai_api_key = "sk-test"
    llm.ollama_fallback_models = ["glm-4.7-flash:latest"]
    models_tried = []

    async def fake_ollama(prompt, context, max_tokens, temperature, model, *, raw=False):
        models_tried.append(model)
        if model in (None, "qwen3:32b"):
            raise RuntimeError("primary down")
        if model == "glm-4.7-flash:latest":
            return '{"action":"finish","action_input":{"answer":"local-ok"},"thought":"fb"}'
        raise RuntimeError(f"unexpected model {model}")

    async def fake_openai(*_args, **_kwargs):
        raise AssertionError("OpenAI must not be called when a local fallback works")

    async def fake_iter(primary=None):
        return ["glm-4.7-flash:latest"]

    monkeypatch.setattr(llm, "_ollama_generate", fake_ollama)
    monkeypatch.setattr(llm, "_openai_generate", fake_openai)
    monkeypatch.setattr(llm, "_iter_local_fallback_models", fake_iter)
    monkeypatch.setattr("app.services.llm_service.cache_service", _NoCache())

    text = await llm.generate_response(
        prompt="plan",
        max_tokens=50,
        temperature=0.1,
        model="qwen3:32b",
        raw=True,
    )

    assert "local-ok" in text
    assert "glm-4.7-flash:latest" in models_tried
    assert models_tried[0] == "qwen3:32b"


@pytest.mark.asyncio
async def test_iter_local_fallback_skips_primary_and_embeddings(monkeypatch):
    llm = LLMService()
    llm.ollama_fallback_models = [
        "qwen3:32b",
        "nomic-embed-text:latest",
        "glm-4.7-flash:latest",
        "missing-model:1",
    ]

    async def fake_list():
        return [
            "qwen3:32b",
            "nomic-embed-text:latest",
            "glm-4.7-flash:latest",
            "qwen3.6:27b",
        ]

    monkeypatch.setattr(llm, "list_available_models", fake_list)

    models = await llm._iter_local_fallback_models(primary="qwen3:32b")
    assert models == ["glm-4.7-flash:latest"]
