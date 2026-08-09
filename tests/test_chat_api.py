import pytest
from httpx import AsyncClient
from unittest.mock import patch


@pytest.mark.anyio
async def test_chat_with_document_context(client: AsyncClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Mock LLMService.generate_response to avoid heavy Ollama call
    mock_resp = {
        "model": "gpt-oss:test",
        "role": "assistant",
        "content": "This is a mocked answer including document context."
    }
    with patch("app.services.llm_service.LLMService.generate_response", return_value=mock_resp):
        body = {
            "message": "Summarize the attached doc",
            "document_ids": [],
        }
        response = await client.post(
            "/api/v1/chat/chat",
            headers=headers,
            json=body,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["assistant_message"]["content"].startswith("This is a mocked answer")
        assert data["conversation"]["id"] is not None

