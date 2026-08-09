"""
Unit tests for database models
"""
import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User, UserRole
from app.models.document import Document, DocumentChunk
from app.models.audit import AuditLog
from app.core.security import get_password_hash


class TestUserModel:
    """Test User model"""
    
    async def test_create_user(self, test_db: AsyncSession):
        """Test creating a user"""
        user = User(
            email="newuser@example.com",
            username="newuser",
            full_name="New User",
            hashed_password=get_password_hash("password123"),
            role=UserRole.VIEWER
        )
        
        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)
        
        assert user.id is not None
        assert user.email == "newuser@example.com"
        assert user.username == "newuser"
        assert user.role == UserRole.VIEWER
        assert user.is_active is True
        assert user.is_verified is False
        assert user.created_at is not None
        assert user.updated_at is not None
    
    async def test_user_unique_email(self, test_db: AsyncSession):
        """Test that user emails must be unique"""
        user1 = User(
            email="duplicate@example.com",
            username="user1",
            hashed_password=get_password_hash("password123"),
            role=UserRole.VIEWER
        )
        
        user2 = User(
            email="duplicate@example.com",
            username="user2",
            hashed_password=get_password_hash("password123"),
            role=UserRole.VIEWER
        )
        
        test_db.add(user1)
        await test_db.commit()
        
        test_db.add(user2)
        
        with pytest.raises(Exception):  # Should raise integrity error
            await test_db.commit()
    
    async def test_user_unique_username(self, test_db: AsyncSession):
        """Test that usernames must be unique"""
        user1 = User(
            email="user1@example.com",
            username="duplicate",
            hashed_password=get_password_hash("password123"),
            role=UserRole.VIEWER
        )
        
        user2 = User(
            email="user2@example.com",
            username="duplicate",
            hashed_password=get_password_hash("password123"),
            role=UserRole.VIEWER
        )
        
        test_db.add(user1)
        await test_db.commit()
        
        test_db.add(user2)
        
        with pytest.raises(Exception):  # Should raise integrity error
            await test_db.commit()
    
    async def test_user_role_enum(self, test_db: AsyncSession):
        """Test user role enumeration"""
        for role in UserRole:
            user = User(
                email=f"user_{role.value.lower()}@example.com",
                username=f"user_{role.value.lower()}",
                hashed_password=get_password_hash("password123"),
                role=role
            )
            test_db.add(user)
        
        await test_db.commit()
        
        # Verify all users were created with correct roles
        result = await test_db.execute(select(User))
        users = result.scalars().all()
        
        roles_found = {user.role for user in users}
        expected_roles = set(UserRole)
        
        assert roles_found == expected_roles


class TestDocumentModel:
    """Test Document model"""
    
    async def test_create_document(self, test_db: AsyncSession, test_user: User):
        """Test creating a document"""
        document = Document(
            filename="test.pdf",
            file_type="pdf",
            file_size=2048,
            file_hash="hash123456",
            storage_path="/storage/test.pdf",
            status="pending",
            title="Test Document",
            uploaded_by=test_user.id
        )
        
        test_db.add(document)
        await test_db.commit()
        await test_db.refresh(document)
        
        assert document.id is not None
        assert document.uuid is not None
        assert document.filename == "test.pdf"
        assert document.file_type == "pdf"
        assert document.file_size == 2048
        assert document.uploaded_by == test_user.id
        assert document.status == "pending"
        assert document.created_at is not None
    
    async def test_document_user_relationship(self, test_db: AsyncSession, test_user: User):
        """Test document-user relationship"""
        document = Document(
            filename="relationship_test.pdf",
            file_type="pdf",
            file_size=1024,
            file_hash="relationship123",
            storage_path="/storage/relationship_test.pdf",
            uploaded_by=test_user.id
        )
        
        test_db.add(document)
        await test_db.commit()
        await test_db.refresh(document)
        
        # Test relationship loading
        result = await test_db.execute(
            select(Document).where(Document.id == document.id)
        )
        loaded_doc = result.scalar_one()
        
        # Load the relationship
        await test_db.refresh(loaded_doc, ["uploaded_by_user"])
        
        assert loaded_doc.uploaded_by_user.id == test_user.id
        assert loaded_doc.uploaded_by_user.email == test_user.email


class TestDocumentChunkModel:
    """Test DocumentChunk model"""
    
    async def test_create_document_chunk(self, test_db: AsyncSession, test_document: Document):
        """Test creating a document chunk"""
        chunk = DocumentChunk(
            document_id=test_document.id,
            chunk_index=0,
            content="This is a test chunk of content.",
            chunk_type="paragraph",
            page_number=1,
            start_char=0,
            end_char=32
        )
        
        test_db.add(chunk)
        await test_db.commit()
        await test_db.refresh(chunk)
        
        assert chunk.id is not None
        assert chunk.document_id == test_document.id
        assert chunk.chunk_index == 0
        assert chunk.content == "This is a test chunk of content."
        assert chunk.chunk_type == "paragraph"
        assert chunk.page_number == 1
    
    async def test_document_chunks_relationship(self, test_db: AsyncSession, test_document: Document):
        """Test document-chunks relationship"""
        chunks = []
        for i in range(3):
            chunk = DocumentChunk(
                document_id=test_document.id,
                chunk_index=i,
                content=f"Chunk {i} content",
                chunk_type="paragraph"
            )
            chunks.append(chunk)
            test_db.add(chunk)
        
        await test_db.commit()
        
        # Load document with chunks
        result = await test_db.execute(
            select(Document).where(Document.id == test_document.id)
        )
        loaded_doc = result.scalar_one()
        await test_db.refresh(loaded_doc, ["chunks"])
        
        assert len(loaded_doc.chunks) == 3
        assert all(chunk.document_id == test_document.id for chunk in loaded_doc.chunks)


class TestAuditLogModel:
    """Test AuditLog model"""
    
    async def test_create_audit_log(self, test_db: AsyncSession, test_user: User):
        """Test creating an audit log entry"""
        audit_log = AuditLog(
            user_id=test_user.id,
            user_email=test_user.email,
            user_role=test_user.role.value,
            action="create",
            resource_type="document",
            resource_id="123",
            ip_address="192.168.1.1",
            user_agent="test-agent",
            request_method="POST",
            request_path="/api/v1/files",
            response_status=201,
            response_time_ms=150
        )
        
        test_db.add(audit_log)
        await test_db.commit()
        await test_db.refresh(audit_log)
        
        assert audit_log.id is not None
        assert audit_log.user_id == test_user.id
        assert audit_log.user_email == test_user.email
        assert audit_log.action == "create"
        assert audit_log.resource_type == "document"
        assert audit_log.response_status == 201
        assert audit_log.created_at is not None
    
    async def test_audit_log_user_relationship(self, test_db: AsyncSession, test_user: User):
        """Test audit log-user relationship"""
        audit_log = AuditLog(
            user_id=test_user.id,
            user_email=test_user.email,
            user_role=test_user.role.value,
            action="read",
            resource_type="document"
        )
        
        test_db.add(audit_log)
        await test_db.commit()
        await test_db.refresh(audit_log)
        
        # Load with relationship
        result = await test_db.execute(
            select(AuditLog).where(AuditLog.id == audit_log.id)
        )
        loaded_log = result.scalar_one()
        await test_db.refresh(loaded_log, ["user"])
        
        assert loaded_log.user.id == test_user.id
        assert loaded_log.user.email == test_user.email
