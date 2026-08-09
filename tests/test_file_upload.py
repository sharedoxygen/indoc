import io
import pytest
from unittest.mock import patch
from httpx import AsyncClient


@pytest.mark.anyio
async def test_zero_byte_upload_rejected(client: AsyncClient, test_token: str):
    headers = {"Authorization": f"Bearer {test_token}"}
    files = {
        "file": ("empty.txt", io.BytesIO(b""), "text/plain"),
    }
    response = await client.post(
        "/api/v1/files/upload", headers=headers, files=files
    )
    assert response.status_code == 200  # API always 200 with JSON body
    body = response.json()
    assert body.get("error") == "Empty file"


@pytest.mark.anyio
async def test_duplicate_upload_detected(client: AsyncClient, test_token: str, monkeypatch):
    headers = {"Authorization": f"Bearer {test_token}"}

    content = b"Hello inDoc duplicate test"
    files = {"file": ("dup.txt", io.BytesIO(content), "text/plain")}

    # Patch Celery delay to no-op for fast tests
    with patch("app.tasks.document.process_document.delay", lambda *_: None):
        first = await client.post("/api/v1/files/upload", headers=headers, files=files)
        assert first.status_code == 200
        assert first.json().get("error") is None

        # Second upload should hit duplicate logic
        second = await client.post("/api/v1/files/upload", headers=headers, files=files)
        assert second.status_code == 200
        body = second.json()
        assert body.get("error") == "Duplicate file"
        assert body["existing_document"]["filename"] == "dup.txt"

