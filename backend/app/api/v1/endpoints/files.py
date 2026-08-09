"""
File management endpoints
"""
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, String
import hashlib
import logging
from pathlib import Path
import aiofiles
import uuid

logger = logging.getLogger(__name__)

from app.core.config import settings
from app.core.security import get_current_user, require_uploader, require_admin
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.document import Document
from app.models.audit import AuditLog
from app.schemas.document import DocumentResponse, DocumentUpdate, DocumentList
from app.services.document_processor import DocumentProcessor
from app.services.virus_scanner import VirusScanner

router = APIRouter()

document_processor = DocumentProcessor()
virus_scanner = VirusScanner()




@router.get("/list")
async def list_documents(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    file_type: Optional[str] = None,
    status: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """List documents accessible to current user with search and filtering"""
    
    # Build query based on user role and tenant
    query = select(Document)
    # Always scope by tenant if available
    # TODO: Re-enable when Document model has tenant_id
    # if getattr(current_user, 'tenant_id', None):
    #     query = query.where(Document.tenant_id == current_user.tenant_id)
    if current_user.role not in [UserRole.ADMIN, UserRole.REVIEWER]:
        query = query.where(Document.uploaded_by == current_user.id)
    
    # Add search filter - use hybrid search (Elasticsearch + Weaviate)
    if search:
        try:
            # Use hybrid search combining keyword and semantic search
            from app.services.search.elasticsearch_service import ElasticsearchService
            from app.services.search.weaviate_service import WeaviateService
            import asyncio
            
            es_service = ElasticsearchService()
            weaviate_service = WeaviateService()
            
            # Execute both searches in parallel for better performance
            search_tasks = [
                es_service.search(search, 500),  # Keyword search
                weaviate_service.vector_search(search, 500)  # Semantic search
            ]
            
            try:
                es_results, weaviate_results = await asyncio.gather(*search_tasks, return_exceptions=True)
            except Exception as e:
                logger.warning(f"Parallel search failed, trying sequential: {e}")
                es_results = await es_service.search(search, 500)
                try:
                    weaviate_results = await weaviate_service.vector_search(search, 500)
                except Exception:
                    logger.warning("Weaviate search failed, using ES only")
                    weaviate_results = []
            
            # Combine and deduplicate results
            combined_doc_ids = set()
            
            # Add Elasticsearch results
            if isinstance(es_results, list):
                combined_doc_ids.update(result["id"] for result in es_results)
            
            # Add Weaviate results
            if isinstance(weaviate_results, list):
                combined_doc_ids.update(result.get("document_id") for result in weaviate_results if result.get("document_id"))
            
            if combined_doc_ids:
                # Convert string UUIDs to UUID objects for the query
                from uuid import UUID
                uuid_list = [UUID(doc_id) for doc_id in combined_doc_ids if doc_id]
                query = query.where(Document.uuid.in_(uuid_list))
            else:
                # No search results found, return empty
                query = query.where(Document.uuid == "00000000-0000-0000-0000-000000000000")  # Non-existent ID
                
        except Exception as e:
            logger.error(f"Hybrid search error, falling back to database search: {e}")
            # Fallback to database search - use PostgreSQL full-text search for better performance
            from sqlalchemy import text
            
            # Use PostgreSQL's full-text search with ts_vector for better performance
            search_vector = func.to_tsvector('english', 
                func.coalesce(Document.filename, '') + ' ' +
                func.coalesce(Document.title, '') + ' ' +
                func.coalesce(Document.description, '') + ' ' +
                func.coalesce(Document.full_text, '')
            )
            search_query = func.plainto_tsquery('english', search)
            
            # Add both full-text search and trigram similarity for best results
            query = query.where(
                search_vector.op('@@')(search_query) |
                func.similarity(Document.filename, search) > 0.1 |
                func.similarity(Document.title, search) > 0.1
            ).order_by(
                func.ts_rank(search_vector, search_query).desc(),
                func.similarity(Document.filename, search).desc()
            )
    
    # Add file type filter (case-insensitive)
    if file_type and file_type != "all":
        query = query.where(func.lower(Document.file_type) == func.lower(file_type))

    # Add status filter if provided (e.g., indexed)
    if status and status != "all":
        query = query.where(func.lower(Document.status) == func.lower(status))
    
    # Add sorting
    if sort_by == "filename":
        order_col = func.lower(Document.filename)
    elif sort_by == "file_type":
        order_col = func.lower(Document.file_type)
    elif sort_by == "file_size":
        order_col = Document.file_size
    elif sort_by == "updated_at":
        order_col = Document.updated_at
    else:  # default to created_at
        order_col = Document.created_at
    
    if sort_order == "asc":
        query = query.order_by(order_col.asc())
    else:
        query = query.order_by(order_col.desc())
    
    # Get total count
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar()
    
    # Get documents
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    documents = result.scalars().all()
    
    # Convert to simple response format (avoiding Pydantic models for now)
    doc_responses = []
    for doc in documents:
        doc_responses.append({
            "id": doc.id,
            "uuid": str(doc.uuid),
            "filename": doc.filename,
            "file_type": doc.file_type,
            "file_size": doc.file_size,
            "status": doc.status,
            "error_message": doc.error_message,
            "virus_scan_status": doc.virus_scan_status,
            "title": doc.title,
            "description": doc.description,
            "tags": doc.tags,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "updated_at": doc.updated_at.isoformat() if doc.updated_at else None
        })
    
    return {
        "total": total,
        "documents": doc_responses
    }


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    folder_path: Optional[str] = Form(None),
    current_user: User = Depends(require_uploader),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Upload a new document"""
    
    print(f"🔍 Upload successful for user: {current_user.email}")
    
    try:
        # Basic validation
        file_ext = Path(file.filename).suffix.lower().strip('.')
        if not file_ext:
            return {"error": "File must have an extension"}
        
        # Read file content
        content = await file.read()
        file_hash = hashlib.sha256(content).hexdigest()
        
        # Check for duplicates by hash
        existing_result = await db.execute(
            select(Document).where(Document.file_hash == file_hash)
        )
        existing_doc = existing_result.scalar_one_or_none()
        
        if existing_doc:
            return {
                "error": "Duplicate file",
                "message": f"File already exists: {existing_doc.filename}",
                "existing_document": {
                    "id": existing_doc.id,
                    "uuid": str(existing_doc.uuid),
                    "filename": existing_doc.filename,
                    "uploaded_at": existing_doc.created_at.isoformat()
                }
            }
        
        # Create a basic document record
        document = Document(
            filename=file.filename,
            file_type=file_ext,
            file_size=len(content),
            file_hash=file_hash,
            storage_path=f"backend/data/storage/{file_hash}.{file_ext}",
            temp_path=f"backend/data/temp/{file_hash}.{file_ext}",
            status="pending",
            title=title or file.filename,
            description=description,
            uploaded_by=current_user.id
        )
        
        db.add(document)
        await db.commit()
        await db.refresh(document)

        # Ensure storage directory exists and save file content
        storage_path = Path(document.storage_path)
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(storage_path, 'wb') as out:
            await out.write(content)
        
        # S3 dual-write (if configured)
        try:
            from app.services.storage.factory import get_secondary_storage, build_object_key
            secondary = get_secondary_storage()
            if secondary:
                object_key = build_object_key(
                    tenant_id=str(getattr(current_user, 'tenant_id', None)) if getattr(current_user, 'tenant_id', None) else "public",
                    file_hash=file_hash,
                    file_ext=file_ext,
                    prefix=settings.S3_PREFIX
                )
                secondary.put_bytes(object_key, content, content_type=file.content_type)
                # Save object key for later retrieval
                if not document.custom_metadata:
                    document.custom_metadata = {}
                document.custom_metadata["object_storage_key"] = object_key
                await db.commit()
                logger.info(f"☁️  Uploaded to S3: {object_key}")
        except Exception as e:
            logger.warning(f"S3 dual-write failed (non-fatal): {e}")
        
        # Trigger automatic document processing
        from app.tasks.document import process_document
        process_document.delay(str(document.uuid))  # Use UUID, not ID
        
        logger.info(f"🚀 Triggered processing for document: {document.filename}")
        
        return {
            "id": document.id,
            "uuid": str(document.uuid),
            "filename": document.filename,
            "status": document.status,
            "virus_scan_status": document.virus_scan_status,
            "tenant_id": str(getattr(current_user, 'tenant_id', '')),
            "message": "File uploaded successfully and processing started"
        }
        
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Get document by ID"""
    
    # Get document
    result = await db.execute(
        select(Document).where(Document.uuid == document_id)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Check access
    if getattr(current_user.role, "value", current_user.role) not in ["Admin", "Reviewer"] and document.uploaded_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Log access
    audit_log = AuditLog(
        user_id=current_user.id,
        user_email=current_user.email,
        user_role=getattr(current_user.role, "value", current_user.role),
        action="read",
        resource_type="document",
        resource_id=str(document.uuid)
    )
    db.add(audit_log)
    await db.commit()
    
    return DocumentResponse.from_orm(document)


@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: str,
    update_data: DocumentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Update document metadata"""
    
    # Get document
    result = await db.execute(
        select(Document).where(Document.uuid == document_id)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Check access
    if getattr(current_user.role, "value", current_user.role) not in ["Admin", "Reviewer"] and document.uploaded_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Update fields
    update_dict = update_data.dict(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(document, field, value)
    
    await db.commit()
    await db.refresh(document)
    
    # Log update
    audit_log = AuditLog(
        user_id=current_user.id,
        user_email=current_user.email,
        user_role=getattr(current_user.role, "value", current_user.role),
        action="update",
        resource_type="document",
        resource_id=str(document.uuid),
        details={"updated_fields": list(update_dict.keys())}
    )
    db.add(audit_log)
    await db.commit()
    
    return DocumentResponse.from_orm(document)


@router.get("/download/{document_id}")
async def download_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> FileResponse:
    """Download a document - serves from local storage with S3 fallback"""
    
    # Get document
    result = await db.execute(
        select(Document).where(Document.uuid == document_id)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Check access
    if getattr(current_user.role, "value", current_user.role) not in ["Admin", "Reviewer"] and document.uploaded_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Priority 1: Serve from local filesystem if exists
    file_path = Path(document.storage_path)
    if file_path.exists():
        logger.info(f"📁 Serving document from local storage: {document.filename}")
        
        # Determine media type
        if document.file_type in ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp']:
            media_type = f"image/{document.file_type}"
        elif document.file_type == 'pdf':
            media_type = "application/pdf"
        else:
            media_type = "application/octet-stream"
        
        return FileResponse(
            path=file_path,
            filename=document.filename,
            media_type=media_type
        )
    
    # Priority 2: Redirect to S3 presigned URL if local file missing
    logger.info(f"📁 Local file not found, checking S3: {document.filename}")
    meta = document.custom_metadata or {}
    object_key = meta.get('object_storage_key')
    
    if object_key:
        try:
            from app.services.storage.factory import get_secondary_storage
            secondary = get_secondary_storage()
            if secondary and secondary.exists(object_key):
                presigned_url = secondary.get_presigned_url(object_key, expires_in=settings.S3_PRESIGN_TTL_S)
                logger.info(f"☁️  Redirecting to S3 for: {document.filename}")
                return RedirectResponse(url=presigned_url, status_code=status.HTTP_302_FOUND)
        except Exception as e:
            logger.error(f"Failed to generate S3 presigned URL: {e}")
    
    # File not found in any storage
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="File not found in local or cloud storage"
    )


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Delete a document (Admin only) - removes from both local and S3 storage"""
    
    # Get document
    result = await db.execute(
        select(Document).where(Document.uuid == document_id)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Delete from local filesystem
    file_path = Path(document.storage_path)
    if file_path.exists():
        file_path.unlink()
        logger.info(f"🗑️  Deleted local file: {file_path}")
    
    # Delete temp file if exists
    if document.temp_path:
        temp_path = Path(document.temp_path)
        if temp_path.exists():
            temp_path.unlink()
    
    # Delete from S3 (if object key exists)
    try:
        meta = document.custom_metadata or {}
        object_key = meta.get('object_storage_key')
        if object_key:
            from app.services.storage.factory import get_secondary_storage
            secondary = get_secondary_storage()
            if secondary:
                secondary.delete(object_key)
                logger.info(f"☁️  Deleted from S3: {object_key}")
    except Exception as e:
        logger.warning(f"Failed to delete from S3 (non-fatal): {e}")
    
    # Log deletion before removing
    audit_log = AuditLog(
        user_id=current_user.id,
        user_email=current_user.email,
        user_role=getattr(current_user.role, "value", current_user.role),
        action="delete",
        resource_type="document",
        resource_id=str(document.uuid),
        details={"filename": document.filename}
    )
    db.add(audit_log)
    
    # Delete from database
    await db.delete(document)
    await db.commit()
    
    return {"message": "Document deleted successfully from all storage locations"}


@router.post("/retry/{document_id}")
async def retry_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Retry processing for a specific document by re-queuing the task.

    Authorization: Admin/Reviewer can retry any document; other users can only retry their own.
    """
    # Fetch document by UUID
    result = await db.execute(select(Document).where(Document.uuid == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Access control
    user_role_value = getattr(current_user.role, "value", current_user.role)
    if user_role_value not in ["Admin", "Reviewer"] and document.uploaded_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Reset minimal fields and enqueue processing
    try:
        # Keep original paths and metadata; just reset status and clear any previous error indicators
        document.status = "uploaded"
        await db.commit()

        from app.tasks.document import process_document
        process_document.delay(str(document.uuid))

        # Audit log
        audit_log = AuditLog(
            user_id=current_user.id,
            user_email=current_user.email,
            user_role=user_role_value,
            action="retry",
            resource_type="document",
            resource_id=str(document.uuid)
        )
        db.add(audit_log)
        await db.commit()

        return {"ok": True, "message": "Document re-queued for processing"}
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error retrying document {document_id} by user {current_user.id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))