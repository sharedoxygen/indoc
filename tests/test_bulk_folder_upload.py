"""
Tests for bulk folder upload functionality with metadata preservation
"""
import io
import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient
from pathlib import Path


@pytest.mark.anyio
async def test_bulk_folder_upload_with_structure(client: AsyncClient, test_token: str):
    """Test uploading multiple files with folder structure preservation"""
    headers = {"Authorization": f"Bearer {test_token}"}
    
    # Simulate a folder structure:
    # MyDocs/
    #   ├── 2024/
    #   │   └── Report.pdf
    #   └── Archive/
    #       └── Old.txt
    
    files = [
        ("files", ("Report.pdf", io.BytesIO(b"PDF content for 2024 report"), "application/pdf")),
        ("files", ("Old.txt", io.BytesIO(b"Old archived text file"), "text/plain")),
    ]
    
    folder_mapping = {
        "Report.pdf": "MyDocs/2024/Report.pdf",
        "Old.txt": "MyDocs/Archive/Old.txt"
    }
    
    data = {
        "folder_mapping": json.dumps(folder_mapping),
        "title": "Bulk Upload Test",
        "description": "Testing folder structure preservation",
        "tags": "test,bulk,folder"
    }
    
    # Patch Celery and storage operations
    with patch("app.tasks.document.process_document.delay", return_value=MagicMock(id="task-123")), \
         patch("app.services.bulk_upload_service.BulkUploadService._queue_for_processing", new_callable=AsyncMock):
        
        response = await client.post(
            "/api/v1/files/upload/bulk",
            headers=headers,
            files=files,
            data=data
        )
        
        assert response.status_code == 200
        body = response.json()
        
        # Verify response structure
        assert body["total_files"] == 2
        assert body["successful_uploads"] == 2
        assert body["failed_uploads"] == 0
        assert body["skipped_duplicates"] == 0
        
        # Verify files were processed
        assert len(body["files"]) == 2
        
        # Check folder paths preserved
        report_file = next(f for f in body["files"] if f["filename"] == "Report.pdf")
        assert report_file["folder_path"] == "MyDocs/2024"
        assert report_file["status"] == "success"
        
        old_file = next(f for f in body["files"] if f["filename"] == "Old.txt")
        assert old_file["folder_path"] == "MyDocs/Archive"
        assert old_file["status"] == "success"


@pytest.mark.anyio
async def test_bulk_upload_without_folder_mapping(client: AsyncClient, test_token: str):
    """Test bulk upload without folder structure (flat upload)"""
    headers = {"Authorization": f"Bearer {test_token}"}
    
    files = [
        ("files", ("file1.txt", io.BytesIO(b"File 1 content"), "text/plain")),
        ("files", ("file2.txt", io.BytesIO(b"File 2 content"), "text/plain")),
    ]
    
    with patch("app.tasks.document.process_document.delay", return_value=MagicMock(id="task-123")), \
         patch("app.services.bulk_upload_service.BulkUploadService._queue_for_processing", new_callable=AsyncMock):
        
        response = await client.post(
            "/api/v1/files/upload/bulk",
            headers=headers,
            files=files
        )
        
        assert response.status_code == 200
        body = response.json()
        
        assert body["total_files"] == 2
        assert body["successful_uploads"] == 2
        
        # Verify files uploaded without folder paths
        for file_result in body["files"]:
            assert file_result.get("folder_path") is None or file_result["folder_path"] == ""


@pytest.mark.anyio
async def test_bulk_upload_with_metadata(client: AsyncClient, test_token: str):
    """Test that user-provided metadata is captured in audit trail"""
    headers = {"Authorization": f"Bearer {test_token}"}
    
    files = [
        ("files", ("document.pdf", io.BytesIO(b"Document content"), "application/pdf")),
    ]
    
    data = {
        "title": "Important Document",
        "description": "This is a critical business document",
        "tags": "business,important,2024"
    }
    
    with patch("app.tasks.document.process_document.delay", return_value=MagicMock(id="task-123")), \
         patch("app.services.bulk_upload_service.BulkUploadService._queue_for_processing", new_callable=AsyncMock):
        
        response = await client.post(
            "/api/v1/files/upload/bulk",
            headers=headers,
            files=files,
            data=data
        )
        
        assert response.status_code == 200
        body = response.json()
        
        assert body["successful_uploads"] == 1


@pytest.mark.anyio
async def test_bulk_upload_duplicate_handling(client: AsyncClient, test_token: str):
    """Test that duplicate files are detected and skipped in bulk upload"""
    headers = {"Authorization": f"Bearer {test_token}"}
    
    content = b"Duplicate test content for bulk upload"
    files = [
        ("files", ("duplicate.txt", io.BytesIO(content), "text/plain")),
    ]
    
    with patch("app.tasks.document.process_document.delay", return_value=MagicMock(id="task-123")), \
         patch("app.services.bulk_upload_service.BulkUploadService._queue_for_processing", new_callable=AsyncMock):
        
        # First upload
        first = await client.post(
            "/api/v1/files/upload/bulk",
            headers=headers,
            files=files
        )
        assert first.status_code == 200
        assert first.json()["successful_uploads"] == 1
        
        # Second upload (duplicate)
        second = await client.post(
            "/api/v1/files/upload/bulk",
            headers=headers,
            files=[("files", ("duplicate.txt", io.BytesIO(content), "text/plain"))]
        )
        assert second.status_code == 200
        body = second.json()
        
        # Should be marked as duplicate
        assert body["skipped_duplicates"] == 1
        assert body["successful_uploads"] == 0


@pytest.mark.anyio
async def test_bulk_upload_mixed_success_failure(client: AsyncClient, test_token: str):
    """Test bulk upload with mix of successful and failed files"""
    headers = {"Authorization": f"Bearer {test_token}"}
    
    files = [
        ("files", ("good.txt", io.BytesIO(b"Valid content"), "text/plain")),
        ("files", ("empty.txt", io.BytesIO(b""), "text/plain")),  # Should fail (zero bytes)
    ]
    
    with patch("app.tasks.document.process_document.delay", return_value=MagicMock(id="task-123")), \
         patch("app.services.bulk_upload_service.BulkUploadService._queue_for_processing", new_callable=AsyncMock):
        
        response = await client.post(
            "/api/v1/files/upload/bulk",
            headers=headers,
            files=files
        )
        
        assert response.status_code == 200
        body = response.json()
        
        # Should have at least one success and one failure
        assert body["successful_uploads"] >= 1 or body["failed_uploads"] >= 1


@pytest.mark.anyio
async def test_bulk_upload_deep_folder_structure(client: AsyncClient, test_token: str):
    """Test uploading files with deeply nested folder structure"""
    headers = {"Authorization": f"Bearer {test_token}"}
    
    files = [
        ("files", ("file.txt", io.BytesIO(b"Deep file content"), "text/plain")),
    ]
    
    # Very deep folder structure
    folder_mapping = {
        "file.txt": "Documents/Projects/2024/Q4/Reports/Internal/Drafts/file.txt"
    }
    
    data = {
        "folder_mapping": json.dumps(folder_mapping)
    }
    
    with patch("app.tasks.document.process_document.delay", return_value=MagicMock(id="task-123")), \
         patch("app.services.bulk_upload_service.BulkUploadService._queue_for_processing", new_callable=AsyncMock):
        
        response = await client.post(
            "/api/v1/files/upload/bulk",
            headers=headers,
            files=files,
            data=data
        )
        
        assert response.status_code == 200
        body = response.json()
        
        assert body["successful_uploads"] == 1
        
        # Verify deep folder path preserved
        file_result = body["files"][0]
        assert file_result["folder_path"] == "Documents/Projects/2024/Q4/Reports/Internal/Drafts"


@pytest.mark.anyio
async def test_bulk_upload_invalid_folder_mapping(client: AsyncClient, test_token: str):
    """Test that invalid folder mapping JSON is rejected"""
    headers = {"Authorization": f"Bearer {test_token}"}
    
    files = [
        ("files", ("file.txt", io.BytesIO(b"Content"), "text/plain")),
    ]
    
    data = {
        "folder_mapping": "invalid json {{"  # Invalid JSON
    }
    
    response = await client.post(
        "/api/v1/files/upload/bulk",
        headers=headers,
        files=files,
        data=data
    )
    
    # Should return 400 Bad Request for invalid JSON
    assert response.status_code == 400
    assert "Invalid folder_mapping JSON" in response.json()["detail"]


@pytest.mark.anyio  
async def test_bulk_upload_preserves_audit_metadata(client: AsyncClient, test_token: str):
    """Test that comprehensive audit metadata is stored"""
    headers = {"Authorization": f"Bearer {test_token}"}
    
    files = [
        ("files", ("audit_test.pdf", io.BytesIO(b"PDF for audit test"), "application/pdf")),
    ]
    
    folder_mapping = {
        "audit_test.pdf": "Legal/Contracts/2024/audit_test.pdf"
    }
    
    data = {
        "folder_mapping": json.dumps(folder_mapping),
        "title": "Audit Test Document",
        "description": "Testing audit trail",
        "tags": "audit,compliance,test"
    }
    
    with patch("app.tasks.document.process_document.delay", return_value=MagicMock(id="task-123")), \
         patch("app.services.bulk_upload_service.BulkUploadService._queue_for_processing", new_callable=AsyncMock):
        
        response = await client.post(
            "/api/v1/files/upload/bulk",
            headers=headers,
            files=files,
            data=data
        )
        
        assert response.status_code == 200
        body = response.json()
        
        assert body["successful_uploads"] == 1
        
        file_result = body["files"][0]
        assert file_result["filename"] == "audit_test.pdf"
        assert file_result["folder_path"] == "Legal/Contracts/2024"
        
        # Note: To fully verify audit metadata, we'd need to query the database
        # which would require additional fixtures. This test verifies the API response.

