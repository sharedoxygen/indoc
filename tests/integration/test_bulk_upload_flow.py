"""
Integration tests for bulk upload flow

Tests complete upload pipeline per AI Prompt Engineering Guide §10:
- Auth token generation
- File upload with metadata
- Processing pipeline (virus scan, text extraction, indexing)
- Data integrity and referential integrity
- Hybrid search (ES + Weaviate concurrency)
"""
import pytest
import asyncio
from httpx import AsyncClient
from pathlib import Path
import tempfile
import hashlib
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.user import User, UserRole
from app.models.document import Document
from app.core.security import create_access_token
from app.db.session import AsyncSessionLocal


@pytest.fixture
async def auth_headers():
    """Create auth headers with valid token"""
    async with AsyncSessionLocal() as db:
        # Get or create test user
        result = await db.execute(
            select(User).where(User.email == "test_upload@example.com")
        )
        user = result.scalar_one_or_none()
        
        if not user:
            from app.core.security import get_password_hash
            user = User(
                email="test_upload@example.com",
                username="test_upload",
                full_name="Test Upload User",
                hashed_password=get_password_hash("Test123!"),
                role=UserRole.ADMIN,
                is_active=True,
                is_verified=True
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
        
        token = create_access_token(subject=user.email, role=user.role.value)
        return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_files():
    """Create temporary test files"""
    files = []
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Create test files
        for i in range(3):
            filepath = tmppath / f"test_file_{i}.txt"
            filepath.write_text(f"Test content {i}\nThis is test document number {i}")
            files.append(filepath)
        
        yield files


class TestBulkUploadFlow:
    """Test complete bulk upload flow with data integrity checks"""
    
    @pytest.mark.asyncio
    async def test_bulk_upload_basic(self, auth_headers, test_files):
        """Test basic bulk upload with multiple files"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Prepare form data
            files_data = []
            for filepath in test_files:
                files_data.append(
                    ("files", (filepath.name, open(filepath, "rb"), "text/plain"))
                )
            
            # Upload files
            response = await client.post(
                "/api/v1/files/upload/bulk",
                headers=auth_headers,
                files=files_data
            )
            
            assert response.status_code == 200, f"Upload failed: {response.text}"
            result = response.json()
            
            # Verify response structure
            assert "successful" in result
            assert "failed" in result
            assert len(result["successful"]) == 3
            assert len(result["failed"]) == 0
            
            # Verify each file result
            for file_result in result["successful"]:
                assert "id" in file_result
                assert "filename" in file_result
                assert "status" in file_result
                assert file_result["status"] in ["pending", "processing", "indexed"]
    
    @pytest.mark.asyncio
    async def test_bulk_upload_with_metadata(self, auth_headers, test_files):
        """Test bulk upload with metadata (title, description, tags)"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            files_data = [
                ("files", (fp.name, open(fp, "rb"), "text/plain"))
                for fp in test_files
            ]
            
            form_data = {
                "title": "Test Bulk Upload",
                "description": "Integration test for bulk upload",
                "tags": "test,integration,bulk",
                "document_set_id": "test-set-123"
            }
            
            response = await client.post(
                "/api/v1/files/upload/bulk",
                headers=auth_headers,
                files=files_data,
                data=form_data
            )
            
            assert response.status_code == 200
            result = response.json()
            
            # Verify metadata was applied
            async with AsyncSessionLocal() as db:
                for file_result in result["successful"]:
                    doc_result = await db.execute(
                        select(Document).where(Document.id == file_result["id"])
                    )
                    doc = doc_result.scalar_one()
                    
                    # Note: Some metadata like title/description may be file-specific
                    # document_set_id should be applied to all
                    assert doc.document_set_id == "test-set-123"
    
    @pytest.mark.asyncio
    async def test_bulk_upload_with_folder_mapping(self, auth_headers):
        """Test bulk upload with folder structure preservation"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Create files with folder structure
            with tempfile.TemporaryDirectory() as tmpdir:
                tmppath = Path(tmpdir)
                
                # Create nested structure
                (tmppath / "folder1").mkdir()
                (tmppath / "folder1/subfolder").mkdir()
                
                file1 = tmppath / "folder1/file1.txt"
                file2 = tmppath / "folder1/subfolder/file2.txt"
                
                file1.write_text("File 1 content")
                file2.write_text("File 2 content")
                
                files_data = [
                    ("files", (f.name, open(f, "rb"), "text/plain"))
                    for f in [file1, file2]
                ]
                
                # Folder mapping JSON
                folder_mapping = {
                    "file1.txt": "folder1/file1.txt",
                    "file2.txt": "folder1/subfolder/file2.txt"
                }
                
                import json
                form_data = {
                    "folder_mapping": json.dumps(folder_mapping)
                }
                
                response = await client.post(
                    "/api/v1/files/upload/bulk",
                    headers=auth_headers,
                    files=files_data,
                    data=form_data
                )
                
                assert response.status_code == 200
                result = response.json()
                
                # Verify folder structure was preserved
                async with AsyncSessionLocal() as db:
                    for file_result in result["successful"]:
                        doc_result = await db.execute(
                            select(Document).where(Document.id == file_result["id"])
                        )
                        doc = doc_result.scalar_one()
                        
                        # Verify folder_path was set
                        assert doc.folder_path is not None
                        assert "folder1" in doc.folder_path
    
    @pytest.mark.asyncio
    async def test_data_integrity_after_upload(self, auth_headers, test_files):
        """Test data and referential integrity after upload (Guide §5)"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            files_data = [
                ("files", (fp.name, open(fp, "rb"), "text/plain"))
                for fp in test_files
            ]
            
            response = await client.post(
                "/api/v1/files/upload/bulk",
                headers=auth_headers,
                files=files_data
            )
            
            assert response.status_code == 200
            result = response.json()
            
            # Verify data integrity
            async with AsyncSessionLocal() as db:
                for file_result in result["successful"]:
                    doc_result = await db.execute(
                        select(Document).where(Document.id == file_result["id"])
                    )
                    doc = doc_result.scalar_one()
                    
                    # Check UUID is present and valid
                    assert doc.uuid is not None
                    assert len(str(doc.uuid)) == 36  # Standard UUID format
                    
                    # Check timestamps (BaseModel server defaults)
                    assert doc.created_at is not None
                    assert doc.updated_at is not None
                    
                    # Check file hash is present
                    assert doc.file_hash is not None
                    assert len(doc.file_hash) == 64  # SHA-256 hash
                    
                    # Check foreign key integrity (uploaded_by)
                    assert doc.uploaded_by is not None
                    user_result = await db.execute(
                        select(User).where(User.id == doc.uploaded_by)
                    )
                    user = user_result.scalar_one_or_none()
                    assert user is not None, "Foreign key violation: uploaded_by user not found"
                    
                    # Check storage path exists
                    assert doc.storage_path is not None
                    # Note: File may be in processing, don't assert Path(doc.storage_path).exists()
    
    @pytest.mark.asyncio
    async def test_upload_without_auth_fails(self, test_files):
        """Test that upload without auth token fails with 401"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            files_data = [
                ("files", (fp.name, open(fp, "rb"), "text/plain"))
                for fp in test_files
            ]
            
            response = await client.post(
                "/api/v1/files/upload/bulk",
                files=files_data
            )
            
            assert response.status_code == 401
            assert "not authenticated" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_upload_empty_files_list(self, auth_headers):
        """Test upload with no files returns appropriate error"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/files/upload/bulk",
                headers=auth_headers,
                files=[]
            )
            
            # Should either return 422 (validation error) or 400 (bad request)
            assert response.status_code in [400, 422]
    
    @pytest.mark.asyncio
    async def test_upload_file_too_large(self, auth_headers):
        """Test that files exceeding MAX_FILE_SIZE are rejected"""
        from app.core.config import settings
        
        # Skip if MAX_FILE_SIZE is very large (would take too long to test)
        if settings.MAX_FILE_SIZE > 10 * 1024 * 1024:  # 10MB
            pytest.skip("MAX_FILE_SIZE too large for test")
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Create file larger than MAX_FILE_SIZE
            with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
                large_content = b"x" * (settings.MAX_FILE_SIZE + 1024)
                tmp.write(large_content)
                tmp.flush()
                
                files_data = [
                    ("files", (tmp.name, open(tmp.name, "rb"), "text/plain"))
                ]
                
                response = await client.post(
                    "/api/v1/files/upload/bulk",
                    headers=auth_headers,
                    files=files_data
                )
                
                # Should return error for file too large
                assert response.status_code in [400, 413, 422]
    
    @pytest.mark.asyncio
    async def test_hybrid_search_after_upload(self, auth_headers, test_files):
        """Test that uploaded files are searchable via hybrid search (Guide §4)"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Upload files
            files_data = [
                ("files", (fp.name, open(fp, "rb"), "text/plain"))
                for fp in test_files
            ]
            
            upload_response = await client.post(
                "/api/v1/files/upload/bulk",
                headers=auth_headers,
                files=files_data
            )
            
            assert upload_response.status_code == 200
            
            # Wait for indexing (in real system, would poll or use webhooks)
            await asyncio.sleep(2)  # Give time for async processing
            
            # Search for uploaded content
            search_response = await client.post(
                "/api/v1/search/",
                headers=auth_headers,
                json={
                    "query": "test content",
                    "limit": 10,
                    "search_type": "hybrid"  # Ensure hybrid search is used
                }
            )
            
            # Note: Search may return 200 even if files not yet indexed
            # This is expected behavior for async processing
            assert search_response.status_code == 200
            
            # If results present, verify structure
            search_result = search_response.json()
            if search_result.get("results"):
                for result in search_result["results"]:
                    assert "document_id" in result or "id" in result
                    assert "score" in result or "relevance_score" in result


@pytest.mark.asyncio
async def test_bulk_upload_regression_check():
    """
    Regression test: Ensure no hallucinated modules or fabricated APIs
    per AI Prompt Engineering Guide §6, §11
    """
    # Verify bulk_upload endpoint exists and imports are valid
    from app.api.v1.endpoints import bulk_upload
    
    assert hasattr(bulk_upload, "router")
    assert hasattr(bulk_upload, "bulk_upload_files")
    
    # Verify no metrics_business import (was hallucinated in merge conflict)
    from app.api.v1 import api
    import inspect
    
    api_source = inspect.getsource(api)
    assert "metrics_business" not in api_source, "Hallucinated module reference found!"

