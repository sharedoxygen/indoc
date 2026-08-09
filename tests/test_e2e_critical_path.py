"""
End-to-end test for the critical user journey.
"""
import pytest
from httpx import AsyncClient
import asyncio
from uuid import uuid4
import io
from unittest.mock import patch

# A simple text file content for uploads
TEST_FILE_CONTENT = b"This is the content of the test document for the critical user journey."


@pytest.mark.anyio
async def test_critical_path_user_journey(client: AsyncClient, test_db):
    # --- 1. Register & Login ---
    unique_email = f"testuser_{uuid4()}@example.com"
    unique_username = f"testuser_{uuid4()}"
    register_data = {
        "email": unique_email,
        "username": unique_username,
        "password": "password123",
        "role": "Uploader"
    }
    register_resp = await client.post("/api/v1/auth/register", json=register_data)
    assert register_resp.status_code == 201, f"Registration failed: {register_resp.text}"

    login_data = {"username": unique_email, "password": "password123"}
    login_resp = await client.post(
        "/api/v1/auth/login",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # --- 2. Upload ---
    files = {
        "file": ("e2e_test_doc.txt", io.BytesIO(TEST_FILE_CONTENT), "text/plain"),
    }
    # Patch Celery to avoid actual async processing and allow us to simulate it
    with patch("app.tasks.document.process_document.delay") as mock_process_document:
        upload_resp = await client.post(
            "/api/v1/files/upload", headers=headers, files=files
        )
        assert upload_resp.status_code == 200, f"Upload failed: {upload_resp.text}"
        upload_data = upload_resp.json()
        document_uuid = upload_data["uuid"]
        assert document_uuid is not None
        # Verify that our mock was called, meaning the file was accepted
        mock_process_document.assert_called_once_with(document_uuid)

    # --- 3. Process (Simulated) ---
    # In a real test against a live Celery, we would poll.
    # Here, we will manually update the document to 'indexed' to simulate success.
    from app.models.document import Document
    from sqlalchemy import update

    # Manually add the text content and set status, as the task is mocked
    await test_db.execute(
        update(Document)
        .where(Document.uuid == document_uuid)
        .values(status="indexed", full_text=TEST_FILE_CONTENT.decode())
    )
    await test_db.commit()

    # Verify the status is updated
    status_resp = await client.get(f"/api/v1/files/{document_uuid}", headers=headers)
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "indexed"
    assert status_resp.json()["full_text"] is not None

    # --- 4. Chat ---
    # Mock the LLM to control the response and confirm context was used
    mock_llm_response = "Response based on document content."
    with patch(
        "app.services.llm_service.LLMService.generate_response",
        return_value=mock_llm_response,
    ) as mock_generate_response:
        chat_data = {
            "message": "What is in the document?",
            "document_ids": [document_uuid],
        }
        chat_resp = await client.post(
            "/api/v1/chat/chat", headers=headers, json=chat_data
        )

    # --- 5. Assert ---
    assert chat_resp.status_code == 200, f"Chat failed: {chat_resp.text}"
    chat_data = chat_resp.json()

    # Assert that the LLM was called with context
    call_args, call_kwargs = mock_generate_response.call_args
    context_text = call_kwargs.get("context", "")
    assert (
        "This is the content of the test document" in context_text
    ), "Document content was not found in the LLM context"

    # Assert that the chat response indicates context was used
    assistant_message = chat_data.get("response", {})
    assert assistant_message.get("content") == mock_llm_response
    assert (
        assistant_message.get("metadata", {}).get("context_used") is True
    ), "Response metadata does not indicate context was used"

    print("\\n✅ Critical path test passed successfully! ✅\\n")
