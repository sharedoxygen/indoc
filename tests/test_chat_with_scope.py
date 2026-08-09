"""
Test chat functionality with document scope and citations
"""
import pytest
import asyncio
from uuid import uuid4
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User, UserRole
from app.models.document import Document
from app.models.conversation import Conversation, Message
from app.api.v1.endpoints.chat import chat
from app.schemas.conversation import ChatRequest
from app.core.document_scope import get_effective_document_ids
from app.core.security import get_password_hash


@pytest.fixture
async def test_user(test_db: AsyncSession):
    """Create a test user"""
    user = User(
        username="test_chat_user",
        email="chat@test.com",
        role=UserRole.ANALYST,
        is_active=True,
        hashed_password=get_password_hash("testpass123")
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    yield user
    # Cleanup
    await test_db.delete(user)
    await test_db.commit()


@pytest.fixture
async def test_documents(test_db: AsyncSession, test_user):
    """Create test documents with different content"""
    docs = []
    
    # Document 1: Automotive content
    doc1 = Document(
        uuid=uuid4(),
        filename="automotive_report.pdf",
        title="Automotive Industry Analysis",
        description="Analysis of automotive trends",
        file_type="pdf",
        file_size=1024,
        status="indexed",
        uploaded_by=test_user.id,
        storage_path="test/automotive_report.pdf",
        full_text="The automotive industry is experiencing rapid transformation with electric vehicles and autonomous driving technology."
    )
    
    # Document 2: Financial content
    doc2 = Document(
        uuid=uuid4(),
        filename="financial_summary.docx",
        title="Q4 Financial Summary",
        description="Quarterly financial results",
        file_type="docx",
        file_size=2048,
        status="indexed",
        uploaded_by=test_user.id,
        storage_path="test/financial_summary.docx",
        full_text="Our financial performance showed strong growth in Q4 with revenue increasing by 15%."
    )
    
    # Document 3: Technology content
    doc3 = Document(
        uuid=uuid4(),
        filename="tech_trends.pdf",
        title="Technology Trends 2024",
        description="Emerging technology trends",
        file_type="pdf",
        file_size=3072,
        status="indexed",
        uploaded_by=test_user.id,
        storage_path="test/tech_trends.pdf",
        full_text="Artificial intelligence and machine learning continue to dominate the technology landscape."
    )
    
    docs.extend([doc1, doc2, doc3])
    for doc in docs:
        test_db.add(doc)
    
    await test_db.commit()
    for doc in docs:
        await test_db.refresh(doc)
    
    yield docs
    
    # Cleanup
    for doc in docs:
        await test_db.delete(doc)
    await test_db.commit()


class TestChatWithScope:
    """Test chat functionality with document scope"""
    
    @pytest.mark.asyncio
    async def test_chat_with_all_accessible_documents(self, test_db: AsyncSession, test_user, test_documents):
        """Test chat when no documents are selected (default to all accessible)"""
        # Create chat request
        chat_request = ChatRequest(
            message="What topics are covered in the documents?",
            document_ids=None  # No selection
        )
        
        # Mock the chat endpoint behavior
        from app.services.search_service import SearchService
        search = SearchService(test_db)
        
        # Search should return results from all accessible documents
        results = await search.hybrid_search(
            query=chat_request.message,
            limit=5,
            user=test_user,
            selected_document_ids=None
        )
        
        assert len(results) > 0
        # Verify results come from user's accessible documents
        doc_ids = [r.document_id for r in results]
        assert all(str(doc.uuid) in doc_ids for doc in test_documents[:2])  # At least some match
    
    @pytest.mark.asyncio
    async def test_chat_with_selected_documents(self, test_db: AsyncSession, test_user, test_documents):
        """Test chat when specific documents are selected"""
        # Select only automotive document
        selected_ids = [test_documents[0].uuid]
        
        chat_request = ChatRequest(
            message="What topics are covered?",
            document_ids=selected_ids
        )
        
        # Mock search with selection
        from app.services.search_service import SearchService
        search = SearchService(test_db)
        
        # Get document content for selected IDs only
        documents = await search.get_document_content_for_chat(
            [str(id) for id in selected_ids],
            max_content_length=2000
        )
        
        assert len(documents) == 1
        assert "automotive" in documents[0]["content"].lower()
    
    @pytest.mark.asyncio
    async def test_count_question_with_scope(self, test_db: AsyncSession, test_user, test_documents):
        """Test count questions respect document scope"""
        # Test 1: Count all accessible documents
        effective_ids = await get_effective_document_ids(test_db, test_user, None)
        assert len(effective_ids) == 3  # User should see all 3 documents
        
        # Test 2: Count with selection
        selected_set = {test_documents[0].id, test_documents[1].id}
        effective_ids_filtered = await get_effective_document_ids(test_db, test_user, selected_set)
        assert len(effective_ids_filtered) == 2
    
    @pytest.mark.asyncio
    async def test_keyword_summarization_intent(self, test_db: AsyncSession, test_user, test_documents):
        """Test keyword-based summarization intent detection"""
        chat_request = ChatRequest(
            message="summarize all documents containing automotive",
            document_ids=None
        )
        
        # Extract keyword from message
        import re
        normalized_q = chat_request.message.lower()
        keyword_query = None
        
        if "summarize" in normalized_q and "containing" in normalized_q:
            m = re.search(r"containing\s+([\w\- ]{3,50})", normalized_q)
            if m:
                keyword_query = m.group(1).strip()
        
        assert keyword_query == "automotive"
        
        # Search with keyword
        from app.services.search_service import SearchService
        search = SearchService(test_db)
        
        results = await search.hybrid_search(
            query=keyword_query,
            limit=25,
            user=test_user,
            selected_document_ids=None
        )
        
        # Should find the automotive document
        assert any("automotive" in r.content.lower() for r in results)
    
    @pytest.mark.asyncio
    async def test_related_documents_intent(self, test_db: AsyncSession, test_user, test_documents):
        """Test related documents question"""
        # Get user's accessible documents
        effective_ids = await get_effective_document_ids(test_db, test_user, None)
        
        # Query documents
        query = select(Document).where(Document.id.in_(effective_ids)).order_by(Document.updated_at.desc())
        result = await test_db.execute(query)
        docs = result.scalars().all()
        
        assert len(docs) == 3
        assert all(d.uploaded_by == test_user.id for d in docs)
    
    @pytest.mark.asyncio
    async def test_scope_metadata_in_response(self, test_db: AsyncSession, test_user, test_documents):
        """Test that scope metadata is properly included in responses"""
        # Create a conversation
        conv = Conversation(
            id=uuid4(),
            tenant_id=test_user.tenant_id or uuid4(),
            user_id=test_user.id,
            title="Test conversation"
        )
        test_db.add(conv)
        await test_db.commit()
        
        # Add a message with scope metadata
        msg = Message(
            id=uuid4(),
            conversation_id=conv.id,
            role="assistant",
            content="Test response",
            message_metadata={
                "scope": "all_accessible",
                "sources": [{"id": str(test_documents[0].uuid)}],
                "context_used": True
            }
        )
        test_db.add(msg)
        await test_db.commit()
        await test_db.refresh(msg)
        
        # Verify metadata
        assert msg.message_metadata["scope"] == "all_accessible"
        assert len(msg.message_metadata["sources"]) == 1
        
        # Cleanup
        await test_db.delete(msg)
        await test_db.delete(conv)
        await test_db.commit()
    
    @pytest.mark.asyncio
    async def test_hybrid_search_with_rbac(self, test_db: AsyncSession, test_user, test_documents):
        """Test hybrid search respects role-based access control"""
        # Create another user who shouldn't see our documents
        other_user = User(
            username="other_user",
            email="other@test.com",
            role=UserRole.ANALYST,
            is_active=True,
            hashed_password=get_password_hash("pass123")
        )
        test_db.add(other_user)
        await test_db.commit()
        
        # Search as other user
        from app.services.search_service import SearchService
        search = SearchService(test_db)
        
        results = await search.hybrid_search(
            query="automotive",
            limit=10,
            user=other_user,
            selected_document_ids=None
        )
        
        # Should not find any documents (not uploaded by other_user)
        assert len(results) == 0
        
        # Cleanup
        await test_db.delete(other_user)
        await test_db.commit()


class TestChatIntegration:
    """Integration tests for complete chat flow"""
    
    @pytest.mark.asyncio
    async def test_full_chat_flow_with_citations(self, test_db: AsyncSession, test_user, test_documents):
        """Test complete chat flow including context building and citations"""
        from app.core.context_manager import context_manager
        
        # Build context items
        documents = [
            {
                "id": str(test_documents[0].uuid),
                "title": test_documents[0].title,
                "content": test_documents[0].full_text,
                "file_type": test_documents[0].file_type,
                "metadata": {
                    "filename": test_documents[0].filename,
                    "created_at": datetime.utcnow().isoformat()
                }
            }
        ]
        
        context_items = context_manager.build_context_items(
            user_message="Tell me about automotive",
            documents=documents,
            conversation_history=[],
            metadata={
                "scope": "selected",
                "document_sources": [{
                    "id": str(test_documents[0].uuid),
                    "filename": test_documents[0].filename
                }]
            }
        )
        
        # Optimize context
        token_budget = 4096
        context_text, context_metadata = context_manager.optimize_context(
            context_items=context_items,
            token_budget=token_budget
        )
        
        assert "automotive" in context_text.lower()
        assert context_metadata["documents_included"] == 1
        assert len(context_metadata["sources"]) == 1
        
        # Extract sources safely
        sources = context_manager.safe_extract_sources(context_metadata)
        assert len(sources) == 1
        assert sources[0]["id"] == str(test_documents[0].uuid)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
