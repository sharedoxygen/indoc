import pytest
from httpx import AsyncClient

@pytest.mark.anyio
async def test_create_conversation(client: AsyncClient, test_token: str):
    headers = {"Authorization": f"Bearer {test_token}"}
    data = {"title": "Test Conversation", "document_id": None}
    response = await client.post("/api/v1/chat/conversations", json=data, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert "id" in body
    assert body["title"] == "Test Conversation"

@pytest.mark.anyio
async def test_chat_send_message_and_receive_response(client: AsyncClient, test_token: str):
    headers = {"Authorization": f"Bearer {test_token}"}
    # Create a new conversation
    conv_data = {"title": "Chat Test", "document_id": None}
    conv_resp = await client.post("/api/v1/chat/conversations", json=conv_data, headers=headers)
    conv_id = conv_resp.json()["id"]

    # Send a chat message
    chat_data = {"conversation_id": conv_id, "message": "Hello"}
    chat_resp = await client.post("/api/v1/chat/chat", json=chat_data, headers=headers)
    assert chat_resp.status_code == 200
    body = chat_resp.json()
    assert body["conversation_id"] == conv_id
    assert "message" in body
    assert "response" in body

@pytest.mark.anyio
async def test_chat_with_document_attachment(client: AsyncClient, test_token: str, test_document):
    headers = {"Authorization": f"Bearer {test_token}"}
    # Create a conversation attached to a document
    conv_data = {"title": "Doc Chat Test", "document_id": test_document.id}
    conv_resp = await client.post("/api/v1/chat/conversations", json=conv_data, headers=headers)
    conv_id = conv_resp.json()["id"]

    # Send a chat message with document_ids in context
    chat_data = {"conversation_id": conv_id, "message": "Summarize document", "document_ids": [str(test_document.uuid)]}
    chat_resp = await client.post("/api/v1/chat/chat", json=chat_data, headers=headers)
    assert chat_resp.status_code == 200
    body = chat_resp.json()
    # Ensure document_ids metadata is included
    metadata = body["message"]["metadata"]
    assert metadata.get("document_ids") == [str(test_document.uuid)]
    assert "response" in body

@pytest.mark.anyio
async def test_get_conversation_history(client: AsyncClient, test_token: str):
    headers = {"Authorization": f"Bearer {test_token}"}
    # Create a conversation and send two messages
    conv_resp = await client.post("/api/v1/chat/conversations", json={"title": "History Test", "document_id": None}, headers=headers)
    conv_id = conv_resp.json()["id"]
    await client.post("/api/v1/chat/chat", json={"conversation_id": conv_id, "message": "First message"}, headers=headers)
    await client.post("/api/v1/chat/chat", json={"conversation_id": conv_id, "message": "Second message"}, headers=headers)

    # Retrieve conversation history
    get_resp = await client.get(f"/api/v1/chat/conversations/{conv_id}", headers=headers)
    assert get_resp.status_code == 200
    body = get_resp.json()
    assert body["id"] == conv_id
    assert len(body["messages"]) >= 2
