"""
File management endpoints
"""
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, String
import hashlib
import logging
from pathlib import Path
import aiofiles
import uuid

logger = logging.getLogger(__name__)

from app.core.config import settings
from app.core.security import get_current_user, require_uploader, require_admin, require_manager
from app.core.document_scope import get_effective_document_ids
from app.core.dlp import DLPPolicy, Watermarker, ExportAction, export_limiter
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.document import Document
from app.models.audit import AuditLog
from app.schemas.document import DocumentResponse, DocumentUpdate, DocumentList
from app.services.document_processor import DocumentProcessor
from app.services.virus_scanner import VirusScanner
from app.services.storage.factory import get_primary_storage, get_secondary_storage
from app.services.storage.base import build_object_key

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
    """List documents accessible to current user with search and filtering.

    Performance tuning goals:
    - Keep responses fast (<400ms) by avoiding large payloads and excessive counts.
    - Default to smaller page sizes and allow the client to paginate.
    """
    import time
    start_time = time.time()
    
    # Build base query - only select needed columns for performance
    from sqlalchemy.orm import load_only, joinedload
    query = select(Document).options(
        load_only(
            Document.id,
            Document.uuid,
            Document.filename,
            Document.file_type,
            Document.file_size,
            Document.status,
            Document.error_message,
            Document.virus_scan_status,
            Document.title,
            Document.description,
            Document.tags,
            Document.created_at,
            Document.updated_at,
            Document.uploaded_by,
            Document.tenant_id
        ),
        joinedload(Document.uploaded_by_user)
    )
    
    # Build WHERE conditions for filtering
    where_conditions = []
    
    # Tenant isolation - EXCEPT for Admin who sees ALL documents across ALL tenants
    if current_user.role not in [UserRole.ADMIN]:
        # Non-admin users: enforce tenant isolation
        if getattr(current_user, 'tenant_id', None):
            where_conditions.append(
                (Document.tenant_id == current_user.tenant_id) | (Document.tenant_id.is_(None))
            )
    
    # Role-based access control using hierarchy-aware scope enforcement
    # Admin sees all documents; Manager sees their own + analysts' docs; Analyst sees only their own
    if current_user.role not in [UserRole.ADMIN]:
        # Use hierarchy-aware filtering for non-Admin users
        effective_ids = await get_effective_document_ids(
            db, 
            current_user, 
            selected_ids=None,
            enforce_classification=True
        )
        if effective_ids:
            where_conditions.append(Document.id.in_(effective_ids))
        else:
            # User has no access to any documents - return empty result set
            where_conditions.append(Document.id == -1)
    
    # Add search filter - prefer Elasticsearch, with DB fallback
    if search:
        try:
            from app.services.search.elasticsearch_service import get_elasticsearch_service
            es_service = get_elasticsearch_service()
            
            # Search in Elasticsearch (no extra filters for now)
            search_results = await es_service.search(search, 1000)
            search_doc_ids = [result["id"] for result in search_results]
            
            if search_doc_ids:
                # Convert string UUIDs to UUID objects for the query
                from uuid import UUID
                uuid_list = [UUID(doc_id) for doc_id in search_doc_ids]
                where_conditions.append(Document.uuid.in_(uuid_list))
            else:
                # ES returned no hits – fall back to DB fuzzy search
                raise RuntimeError("ES returned no results; using DB fallback")
                
        except Exception as e:
            logger.error(f"Elasticsearch search error, falling back to database search: {e}")
            # Fallback to database search (indexed columns only for performance)
            search_term = f"%{search.lower()}%"
            where_conditions.append(
                func.lower(Document.filename).like(search_term) |
                func.lower(Document.title).like(search_term)
            )
    
    # File type filter
    if file_type and file_type != "all":
        where_conditions.append(func.lower(Document.file_type) == func.lower(file_type))

    # Status filter
    if status and status != "all":
        where_conditions.append(func.lower(Document.status) == func.lower(status))
    
    # Apply all WHERE conditions
    if where_conditions:
        query = query.where(*where_conditions)
    
    # Optimized count query – only when small result sets or explicitly requested by client
    total: Optional[int] = None
    if limit <= 200:
        count_query = select(func.count(Document.id))
        if where_conditions:
            count_query = count_query.where(*where_conditions)
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0
    
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
    
    # Get documents with pagination
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
            "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
            # CRITICAL: Include uploaded_by and tenant_id for RBAC visibility
            "uploaded_by": doc.uploaded_by,
            "uploaded_by_email": doc.uploaded_by_user.email if doc.uploaded_by_user else None,
            "tenant_id": str(doc.tenant_id) if doc.tenant_id else None
        })
    
    elapsed_ms = (time.time() - start_time) * 1000
    logger.info(f"📊 Document list query completed in {elapsed_ms:.2f}ms - {len(doc_responses)} documents returned (total: {total})")
    
    response: dict[str, Any] = {"documents": doc_responses}
    if total is not None:
        response["total"] = total
    return response


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    folder_path: Optional[str] = Form(None),
    document_set_id: Optional[str] = Form(None),
    current_user: User = Depends(require_uploader),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Upload a new document with comprehensive error reporting"""
    
    logger.info(f"🔍 Starting upload for user: {current_user.email}, file: {file.filename}")
    
    try:
        # Basic validation
        if not file.filename:
            logger.error("Upload failed: No filename provided")
            return {
                "error": "Invalid file",
                "message": "No filename provided",
                "details": "Please select a valid file to upload"
            }
            
        file_ext = Path(file.filename).suffix.lower().strip('.')
        if not file_ext:
            logger.error(f"Upload failed: File {file.filename} has no extension")
            return {
                "error": "Invalid file type",
                "message": f"File '{file.filename}' must have an extension",
                "details": "Supported formats: PDF, DOCX, XLSX, PPTX, TXT, HTML, XML, JSON, EML, PNG, JPG, TIFF"
            }

        allowed = {ext.lower() for ext in settings.ALLOWED_EXTENSIONS}
        if file_ext not in allowed:
            logger.error(f"Upload failed: unsupported type .{file_ext} for {file.filename}")
            return {
                "error": "Unsupported file type",
                "message": f"'{file.filename}' is not an indexable document type",
                "details": (
                    f".{file_ext} files are skipped. Upload PDF/Office/text/HTML/XML/JSON/email/images. "
                    "Use the ZIP upload path only when you want an archive expanded first."
                ),
            }
        
        # Read file content
        try:
            logger.info(f"📖 Reading file content: {file.filename}")
            content = await file.read()
            logger.info(f"✅ File read successfully: {len(content)} bytes")
        except Exception as e:
            logger.error(f"❌ Upload read error for {file.filename}: {e}")
            return {
                "error": "File read failed",
                "message": f"Failed to read uploaded file: {file.filename}",
                "details": str(e)
            }
            
        if len(content) == 0:
            logger.error(f"❌ Upload failed: Empty file {file.filename}")
            return {
                "error": "Empty file",
                "message": f"File '{file.filename}' is zero bytes",
                "details": "Please upload a file with content"
            }

        # Generate file hash for duplicate detection
        logger.info(f"🔐 Generating hash for {file.filename}")
        file_hash = hashlib.sha256(content).hexdigest()
        logger.info(f"✅ File hash: {file_hash[:16]}...")

        # Check for duplicates by hash
        logger.info(f"🔍 Checking for duplicate files...")
        existing_result = await db.execute(
            select(Document).where(Document.file_hash == file_hash)
        )
        existing_doc = existing_result.scalar_one_or_none()

        if existing_doc:
            logger.warning(f"⚠️ Duplicate file detected: {file.filename} (matches {existing_doc.filename})")
            return {
                "error": "Duplicate file",
                "message": f"File '{file.filename}' already exists",
                "details": f"This file was previously uploaded as '{existing_doc.filename}' on {existing_doc.created_at.strftime('%Y-%m-%d %H:%M')}",
                "existing_document": {
                    "id": existing_doc.id,
                    "uuid": str(existing_doc.uuid),
                    "filename": existing_doc.filename,
                    "uploaded_at": existing_doc.created_at.isoformat()
                }
            }

        # Robust, absolute storage locations using configured paths
        from app.core.config import settings
        logger.info(f"📁 Setting up storage paths...")
        storage_abs_path = (settings.STORAGE_PATH / f"{file_hash}.{file_ext}").resolve()
        temp_abs_path = (settings.TEMP_REPO_PATH / f"{file_hash}.{file_ext}").resolve()
        logger.info(f"✅ Storage path: {storage_abs_path}")
        logger.info(f"✅ Temp path: {temp_abs_path}")

        # Create a basic document record
        logger.info(f"💾 Creating database record for {file.filename}")
        document = Document(
            filename=file.filename,
            file_type=file_ext,
            file_size=len(content),
            file_hash=file_hash,
            storage_path=str(storage_abs_path),
            temp_path=str(temp_abs_path),
            folder_path=folder_path,  # Save folder hierarchy
            document_set_id=document_set_id,  # Link to document set
            status="uploaded",
            title=title or file.filename,
            description=description,
            uploaded_by=current_user.id
        )
        
        db.add(document)
        await db.flush()  # Flush to get UUID without committing yet
        logger.info(f"✅ Database record staged: {document.uuid}")

        # Save file to local filesystem and optional object storage (dual-write)
        storage_path = Path(document.storage_path)
        primary_ok = False
        try:
            logger.info(f"💿 Writing file to storage: {storage_path}")
            storage_path.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(storage_path, 'wb') as out:
                await out.write(content)
            logger.info(f"✅ File written successfully: {len(content)} bytes")
            primary_ok = True
        except Exception as e:
            logger.error(f"❌ Failed to write file to storage: {e}")

        # Object storage key and dual write
        object_key = build_object_key(
            getattr(current_user, 'tenant_id', None),
            file_hash,
            file_ext,
            prefix=getattr(settings, 'S3_PREFIX', 'uploads')
        )
        object_ok = False
        try:
            s_primary = get_primary_storage()
            if s_primary:
                s_primary.put_bytes(object_key, content, content_type=file.content_type)
                object_ok = True
                logger.info(f"☁️  Uploaded to primary object storage: key={object_key}")
        except Exception as e:
            logger.warning(f"Object storage primary write failed: {e}")
        try:
            s_secondary = get_secondary_storage()
            if s_secondary:
                s_secondary.put_bytes(object_key, content, content_type=file.content_type)
                logger.info(f"☁️  Uploaded to secondary object storage: key={object_key}")
        except Exception as e:
            logger.warning(f"Object storage secondary write failed: {e}")

        # If both backends failed, abort and roll back DB record
        if not primary_ok and not object_ok:
            await db.rollback()  # Rollback the transaction instead of deleting and committing
            return {
                "error": "Storage failed",
                "message": f"Failed to persist file '{file.filename}' to any storage backend",
                "details": "Local filesystem and object storage both failed"
            }

        # Persist object key for future downloads
        try:
            meta = document.custom_metadata or {}
            meta['object_storage_key'] = object_key
            document.custom_metadata = meta
            # Will be committed by get_db dependency
        except Exception:
            pass
        
        # Trigger automatic document processing
        logger.info(f"🚀 Triggering processing for document: {document.filename}")
        try:
            from app.tasks.document import process_document
            async_result = process_document.delay(str(document.uuid))  # Use UUID, not ID
            logger.info(f"✅ Processing task queued: {async_result.id}")
        except Exception as e:
            logger.error(f"❌ Failed to queue processing task: {e}")
            return {
                "error": "Processing queue failed",
                "message": f"File uploaded but processing could not be started",
                "details": f"Task queue error: {str(e)}",
                "document_id": str(document.uuid),
                "status": "uploaded"
            }
        
        logger.info(f"🎉 Upload completed successfully: {document.filename}")
        
        return {
            "id": document.id,
            "uuid": str(document.uuid),
            "filename": document.filename,
            "status": document.status,
            "virus_scan_status": document.virus_scan_status,
            "tenant_id": str(getattr(current_user, 'tenant_id', '')),
            "message": f"File '{document.filename}' uploaded successfully and processing started",
            "details": f"Processing task queued with ID: {async_result.id}",
            "task_id": async_result.id,
            "queue": "document_processing",
            "file_size": len(content),
            "file_hash": file_hash[:16] + "..."
        }
        
    except Exception as e:
        import traceback
        logger.error(f"❌ Upload failed with unexpected error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "error": "Upload failed",
            "message": f"Unexpected error during upload: {str(e)}",
            "details": "Please try again or contact support if the problem persists",
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
    # Will be committed by get_db dependency
    
    return DocumentResponse.from_orm(document)


@router.post("/scan_all", summary="Trigger virus scan for all documents")
async def scan_all_documents(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Enqueue virus scan Celery tasks for every document not yet marked clean."""
    # Find all documents pending or errored for virus scanning
    result = await db.execute(
        select(Document).where(Document.virus_scan_status != "clean")
    )
    docs = result.scalars().all()
    from app.tasks.document import process_document

    count = 0
    for doc in docs:
        process_document.delay(str(doc.uuid))
        count += 1

    return {"enqueued": count, "total": len(docs)}


@router.post("/scan_virus/{document_id}")
async def manual_virus_scan(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Manually trigger virus scan for a specific document"""
    result = await db.execute(select(Document).where(Document.uuid == document_id))
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    
    user_role_value = getattr(current_user.role, "value", current_user.role)
    if user_role_value not in ["Admin", "Reviewer"] and document.uploaded_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    # Check if file exists
    storage_path = Path(document.storage_path)
    if not storage_path.exists():
        # Try alternative path
        alt_path = Path(f"data/storage/{storage_path.name}")
        if alt_path.exists():
            document.storage_path = str(alt_path)
            # Will be committed by get_db dependency
            storage_path = alt_path
        else:
            document.virus_scan_status = "error"
            document.error_message = f"File not found: {document.storage_path}"
            # Will be committed by get_db dependency when exception is raised
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File not found on disk")
    
    # Run virus scan
    try:
        scanner = VirusScanner()
        scan_result = scanner.scan_file_sync(storage_path)
        document.virus_scan_status = scan_result.get("status", "error")
        # Will be committed by get_db dependency
        
        return {"ok": True, "scan_result": scan_result, "virus_status": document.virus_scan_status}
    except Exception as e:
        document.virus_scan_status = "error"
        document.error_message = f"Virus scan failed: {str(e)}"
        # Will be committed by get_db dependency when exception is raised
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


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
    
    # Will be committed by get_db dependency
    
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
    # Will be committed by get_db dependency
    
    # If searchable fields changed, trigger reindex in background
    if any(field in update_dict for field in ["title", "description", "tags", "full_text"]):
        try:
            from app.tasks.document import reindex_document
            # Task expects DB id
            reindex_document.delay(str(document.id))
            logger.info(f"Queued reindex for document {document.filename} ({document.uuid})")
        except Exception as e:
            logger.warning(f"Failed to queue reindex for {document.uuid}: {e}")

    return DocumentResponse.from_orm(document)


@router.post("/folder/delete")
async def delete_folder_from_indoc(
    folder_path: str = Form(...),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Remove every inDoc document under a folder path from the corpus.

    Deletes from PostgreSQL, Elasticsearch, Qdrant, and inDoc object storage only.
    Never touches the user's original filesystem / source folder.
    """
    from app.services.atomic_deletion_service import AtomicDeletionService

    path = (folder_path or "").strip().strip("/")
    if not path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="folder_path is required",
        )
    if ".." in path.split("/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid folder_path",
        )

    # Exact folder + all nested children (prefix match)
    result = await db.execute(
        select(Document).where(
            Document.tenant_id == current_user.tenant_id,
            (
                (Document.folder_path == path)
                | (Document.folder_path.like(f"{path}/%"))
            ),
        )
    )
    documents = list(result.scalars().all())

    if not documents:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No documents found under folder '{path}'",
        )

    deletion_service = AtomicDeletionService(db)
    deleted: List[str] = []
    failed: List[dict] = []

    for doc in documents:
        try:
            await deletion_service.delete_document_atomic(
                document_id=str(doc.uuid),
                user_id=current_user.id,
                user_email=current_user.email,
                user_role=getattr(current_user.role, "value", current_user.role),
                tenant_id=current_user.tenant_id,
            )
            deleted.append(str(doc.uuid))
        except Exception as e:
            logger.error(f"Folder delete failed for {doc.uuid} under {path}: {e}")
            failed.append({"uuid": str(doc.uuid), "filename": doc.filename, "error": str(e)})

    # Folder-level audit (per-doc audits already written by atomic deletion)
    db.add(
        AuditLog(
            user_id=current_user.id,
            user_email=current_user.email,
            user_role=getattr(current_user.role, "value", current_user.role),
            action="folder_delete",
            resource_type="folder",
            resource_id=path,
            details={
                "folder_path": path,
                "requested_count": len(documents),
                "deleted_count": len(deleted),
                "failed_count": len(failed),
                "scope": "indoc_corpus_only",
            },
        )
    )

    return {
        "success": len(failed) == 0,
        "message": (
            f"Removed {len(deleted)} document(s) under '{path}' from inDoc. "
            "Source files on disk were not modified."
        ),
        "folder_path": path,
        "deleted_count": len(deleted),
        "failed_count": len(failed),
        "deleted": deleted,
        "failed": failed,
    }


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Delete a document atomically from all systems (Admin only)
    
    Uses 2-phase commit to ensure atomic deletion across:
    - PostgreSQL database
    - Elasticsearch index
    - Qdrant vector store
    - Local file storage
    - Remote object storage (S3/MinIO)
    
    If ANY step fails, the entire operation is rolled back.
    Does not modify the user's original filesystem outside inDoc.
    """
    from app.services.atomic_deletion_service import AtomicDeletionService
    
    # Initialize atomic deletion service
    deletion_service = AtomicDeletionService(db)
    
    try:
        # Execute atomic deletion with 2-phase commit
        result = await deletion_service.delete_document_atomic(
            document_id=document_id,
            user_id=current_user.id,
            user_email=current_user.email,
            user_role=getattr(current_user.role, "value", current_user.role),
            tenant_id=current_user.tenant_id
        )
        
        logger.info(f"✅ Document {document_id} deleted atomically by {current_user.email}")
        
        return {
            "success": True,
            "message": result["message"],
            "document_id": result["document_id"],
            "audit_trail": result["audit"]
        }
        
    except ValueError as e:
        # Document not found or access denied
        logger.warning(f"Document deletion failed - not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    
    except Exception as e:
        # Atomic deletion failed (with or without successful rollback)
        logger.error(f"❌ Atomic document deletion failed for {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document atomically: {str(e)}"
        )


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

    # Validate storage file exists to provide immediate feedback if unrecoverable
    storage_path = Path(document.storage_path)
    if not storage_path.exists():
        document.status = "failed"
        document.error_message = f"File not found on disk: {document.storage_path}"
        # Will be committed by get_db dependency when exception is raised
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=document.error_message)

    # Reset minimal fields and enqueue processing
    try:
        document.status = "uploaded"
        document.error_message = None
        document.updated_at = func.now()
        # Will be committed by get_db dependency

        from app.tasks.document import process_document
        async_result = process_document.delay(str(document.uuid))

        audit_log = AuditLog(
            user_id=current_user.id,
            user_email=current_user.email,
            user_role=user_role_value,
            action="retry",
            resource_type="document",
            resource_id=str(document.uuid)
        )
        db.add(audit_log)
        # Will be committed by get_db dependency

        return {"ok": True, "message": "Document re-queued for processing", "task_id": async_result.id, "queue": "document_processing"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/cancel/{document_id}")
async def cancel_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Cancel processing for a document (mark as failed)."""
    result = await db.execute(select(Document).where(Document.uuid == document_id))
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    user_role_value = getattr(current_user.role, "value", current_user.role)
    if user_role_value not in ["Admin", "Reviewer"] and document.uploaded_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    document.status = "failed"
    document.error_message = "Cancelled by user"
    # Will be committed by get_db dependency

    audit_log = AuditLog(
        user_id=current_user.id,
        user_email=current_user.email,
        user_role=user_role_value,
        action="cancel",
        resource_type="document",
        resource_id=str(document.uuid)
    )
    db.add(audit_log)
    # Will be committed by get_db dependency

    return {"ok": True}


@router.get("/download/{document_id}")
async def download_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> FileResponse:
    """Download a document file with DLP enforcement"""
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
    
    # DLP Check: Can user export this document?
    can_export, deny_reason = DLPPolicy.can_export(current_user, document, ExportAction.DOWNLOAD)
    if not can_export:
        # Log denied download
        audit_log = AuditLog(
            user_id=current_user.id,
            user_email=current_user.email,
            user_role=getattr(current_user.role, "value", current_user.role),
            action="download_denied",
            resource_type="document",
            resource_id=str(document.uuid),
            details={"reason": deny_reason}
        )
        db.add(audit_log)
        # Will be committed by get_db dependency when exception is raised
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=deny_reason
        )
    
    # Check export rate limit
    limit_ok, limit_reason = export_limiter.check_export_limit(current_user)
    if not limit_ok:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=limit_reason
        )
    
    # Check RBAC access (legacy check - DLP already verified)
    user_role_value = getattr(current_user.role, "value", current_user.role)
    if user_role_value not in ["Admin", "Manager", "Reviewer"] and document.uploaded_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Check if file exists locally; if missing try object storage redirect
    file_path = Path(document.storage_path)
    if not file_path.exists():
        from fastapi.responses import RedirectResponse
        meta = document.custom_metadata or {}
        object_key = meta.get('object_storage_key')
        if object_key:
            s_primary = get_primary_storage()
            if s_primary and s_primary.exists(object_key):
                try:
                    url = s_primary.get_presigned_url(object_key, expires_in=settings.S3_PRESIGN_TTL_S)
                    return RedirectResponse(url)
                except Exception:
                    pass
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found in storage"
        )
    
    # Log download (audit trail)
    if DLPPolicy.requires_audit_log(document, ExportAction.DOWNLOAD):
        watermark_text = Watermarker.generate_watermark_text(current_user, document, ExportAction.DOWNLOAD)
        audit_log = AuditLog(
            user_id=current_user.id,
            user_email=current_user.email,
            user_role=user_role_value,
            action="download",
            resource_type="document",
            resource_id=str(document.uuid),
            details={
                "classification": document.classification.value if hasattr(document.classification, 'value') else str(document.classification),
                "watermark": watermark_text,
                "requires_watermark": DLPPolicy.requires_watermark(document)
            }
        )
        db.add(audit_log)
        # Will be committed by get_db dependency
    
    # Return file with correct media type
    if document.file_type in ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp']:
        media_type = f"image/{document.file_type}"
    elif document.file_type == 'pdf':
        media_type = "application/pdf"
    else:
        media_type = "application/octet-stream"
    
    # Add DLP watermark header for tracking
    headers = {}
    if DLPPolicy.requires_watermark(document):
        watermark_metadata = Watermarker.generate_watermark_metadata(current_user, document, ExportAction.DOWNLOAD)
        headers["X-InDoc-Watermark"] = watermark_metadata.get("indoc_exported_by", "")
        headers["X-InDoc-Classification"] = document.classification.value if hasattr(document.classification, 'value') else str(document.classification)
    
    return FileResponse(
        path=file_path,
        filename=document.filename,
        headers=headers,
        media_type=media_type
    )


@router.get("/preview/{document_id}")
async def preview_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> FileResponse:
    """Preview a document file (inline view) with DLP enforcement"""
    # Get document by UUID
    result = await db.execute(
        select(Document).where(Document.uuid == document_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Check if user can view this document
    effective_ids = await get_effective_document_ids(db, current_user, enforce_classification=True)
    if document.id not in effective_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Check if file exists locally; if missing try object storage redirect
    file_path = Path(document.storage_path)
    if not file_path.exists():
        from fastapi.responses import RedirectResponse
        meta = document.custom_metadata or {}
        object_key = meta.get('object_storage_key')
        if object_key:
            s_primary = get_primary_storage()
            if s_primary and s_primary.exists(object_key):
                try:
                    url = s_primary.get_presigned_url(object_key, expires_in=settings.S3_PRESIGN_TTL_S)
                    return RedirectResponse(url)
                except Exception:
                    pass
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found in storage"
        )

    # Log preview access
    audit_log = AuditLog(
        user_id=current_user.id,
        user_email=current_user.email,
        user_role=getattr(current_user.role, "value", current_user.role),
        action="preview",
        resource_type="document",
        resource_id=str(document.uuid),
        details={
            "classification": document.classification.value if hasattr(document.classification, 'value') else str(document.classification)
        }
    )
    db.add(audit_log)

    # Return file for inline viewing (browser preview)
    if document.file_type in ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp']:
        media_type = f"image/{document.file_type}"
    elif document.file_type == 'pdf':
        media_type = "application/pdf"
    else:
        media_type = "application/octet-stream"

    # Set headers for inline viewing (not download)
    headers = {
        "Content-Disposition": f"inline; filename=\"{document.filename}\"",
        "Cache-Control": "public, max-age=3600"  # Cache for 1 hour
    }

    return FileResponse(
        path=file_path,
        filename=document.filename,
        headers=headers,
        media_type=media_type
    )


@router.post("/bulk-action")
async def bulk_document_action(
    action: str,
    document_ids: List[str],
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Perform bulk actions on multiple documents (Manager/Admin only)
    
    Supported actions: delete, reindex, archive
    """
    from uuid import UUID
    
    # Convert string IDs to UUID objects
    try:
        uuid_list = [UUID(doc_id) for doc_id in document_ids]
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document ID format"
        )
    
    # Get documents
    query = select(Document).where(Document.uuid.in_(uuid_list))
    result = await db.execute(query)
    documents = result.scalars().all()
    
    if not documents:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No documents found"
        )
    
    # Verify user has access to these documents via scope enforcement
    doc_id_set = {doc.id for doc in documents}
    effective_ids = await get_effective_document_ids(db, current_user, doc_id_set)
    
    # Filter to only accessible documents
    accessible_docs = [doc for doc in documents if doc.id in effective_ids]
    
    if not accessible_docs:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to any of these documents"
        )
    
    success_count = 0
    error_count = 0
    
    # Perform action
    if action == "delete":
        for doc in accessible_docs:
            try:
                await db.delete(doc)
                success_count += 1
            except Exception as e:
                logger.error(f"Error deleting document {doc.uuid}: {e}")
                error_count += 1
        
        # Will be committed by get_db dependency
    
    elif action == "reindex":
        # Queue reindexing tasks
        from app.tasks.search import index_document_task
        for doc in accessible_docs:
            try:
                index_document_task.delay(doc.id)
                success_count += 1
            except Exception as e:
                logger.error(f"Error queuing reindex for document {doc.uuid}: {e}")
                error_count += 1
    
    elif action == "archive":
        # Update status to archived
        for doc in accessible_docs:
            try:
                doc.status = "archived"
                success_count += 1
            except Exception as e:
                logger.error(f"Error archiving document {doc.uuid}: {e}")
                error_count += 1
        
        # Will be committed by get_db dependency
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported action: {action}"
        )
    
    # Log bulk action
    audit_log = AuditLog(
        user_id=current_user.id,
        user_email=current_user.email,
        user_role=getattr(current_user.role, "value", current_user.role),
        action=f"bulk_{action}",
        resource_type="documents",
        details={
            "action": action,
            "requested_count": len(document_ids),
            "accessible_count": len(accessible_docs),
            "success_count": success_count,
            "error_count": error_count
        }
    )
    db.add(audit_log)
    # Will be committed by get_db dependency
    
    return {
        "message": f"Bulk {action} completed",
        "requested": len(document_ids),
        "accessible": len(accessible_docs),
        "success": success_count,
        "errors": error_count
    }