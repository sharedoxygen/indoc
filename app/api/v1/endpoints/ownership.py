"""
Document Ownership Management API

Enables Admin and Managers to:
- View document ownership and allocation
- Reassign document ownership
- Bulk reassign documents
- View ownership statistics
"""
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

from app.core.security import get_current_user, require_manager
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.document import Document
from app.models.audit import AuditLog

router = APIRouter()


# Pydantic models
class OwnershipStats(BaseModel):
    user_id: int
    user_email: str
    user_name: str
    user_role: str
    department: Optional[str]
    total_documents: int
    by_file_type: dict
    by_classification: dict
    total_size_mb: float

class DocumentOwnershipInfo(BaseModel):
    document_id: int
    document_uuid: str
    filename: str
    file_type: str
    file_size: int
    title: Optional[str]
    classification: str
    uploaded_by: int
    owner_email: str
    owner_name: str
    owner_role: str
    owner_department: Optional[str]
    created_at: str

class ReassignRequest(BaseModel):
    document_ids: List[int]
    new_owner_id: int
    reason: Optional[str] = "Ownership reassignment"

class BulkReassignRequest(BaseModel):
    from_user_id: int
    to_user_id: int
    document_ids: Optional[List[int]] = None  # If None, reassign ALL documents
    reason: Optional[str] = "Bulk ownership reassignment"


@router.get("/stats", summary="Get ownership statistics")
async def get_ownership_stats(
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
) -> List[OwnershipStats]:
    """
    Get document ownership statistics for all users.
    Shows document counts, file types, classifications per user.
    
    Admin: Can see all users
    Manager: Can see their analysts + themselves
    """
    logger.info(f"User {current_user.email} requesting ownership stats")
    
    # Determine which users to show
    if current_user.role == UserRole.ADMIN:
        # Admin sees all users
        user_query = select(User)
    elif current_user.role == UserRole.MANAGER:
        # Manager sees their analysts + themselves
        result = await db.execute(select(User.id).where(User.manager_id == current_user.id))
        analyst_ids = [row[0] for row in result.all()]
        analyst_ids.append(current_user.id)
        user_query = select(User).where(User.id.in_(analyst_ids))
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    result = await db.execute(user_query)
    users = result.scalars().all()
    
    stats_list = []
    for user in users:
        # Get documents for this user
        doc_result = await db.execute(
            select(Document).where(Document.uploaded_by == user.id)
        )
        documents = doc_result.scalars().all()
        
        if not documents:
            continue
        
        # Calculate statistics
        by_file_type = {}
        by_classification = {}
        total_size = 0
        
        for doc in documents:
            # File type count
            ft = doc.file_type or 'unknown'
            by_file_type[ft] = by_file_type.get(ft, 0) + 1
            
            # Classification count
            cls = doc.classification.value if hasattr(doc.classification, 'value') else str(doc.classification)
            by_classification[cls] = by_classification.get(cls, 0) + 1
            
            # Total size
            total_size += doc.file_size or 0
        
        stats_list.append(OwnershipStats(
            user_id=user.id,
            user_email=user.email,
            user_name=user.full_name or user.username,
            user_role=user.role.value if hasattr(user.role, 'value') else str(user.role),
            department=user.department,
            total_documents=len(documents),
            by_file_type=by_file_type,
            by_classification=by_classification,
            total_size_mb=round(total_size / (1024 * 1024), 2)
        ))
    
    # Sort by document count descending
    stats_list.sort(key=lambda x: x.total_documents, reverse=True)
    
    logger.info(f"Returning ownership stats for {len(stats_list)} users")
    return stats_list


@router.get("/documents", summary="Get document ownership details")
async def get_document_ownership(
    user_id: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get detailed document ownership information.
    
    Can filter by user_id to see specific user's documents.
    """
    logger.info(f"User {current_user.email} requesting document ownership (user_id={user_id})")
    
    # Build base query
    query = select(Document, User).join(User, Document.uploaded_by == User.id)
    
    # Apply user filter
    if user_id:
        # Check if current user can see this user's documents
        if current_user.role == UserRole.MANAGER:
            # Manager can see their own + analysts'
            result = await db.execute(select(User.id).where(User.manager_id == current_user.id))
            analyst_ids = [row[0] for row in result.all()]
            analyst_ids.append(current_user.id)
            
            if user_id not in analyst_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot access this user's documents"
                )
        
        query = query.where(Document.uploaded_by == user_id)
    elif current_user.role == UserRole.MANAGER:
        # Manager without filter sees their hierarchy
        result = await db.execute(select(User.id).where(User.manager_id == current_user.id))
        analyst_ids = [row[0] for row in result.all()]
        analyst_ids.append(current_user.id)
        query = query.where(Document.uploaded_by.in_(analyst_ids))
    
    # Apply pagination
    query = query.limit(limit).offset(offset)
    
    result = await db.execute(query)
    rows = result.all()
    
    documents = []
    for doc, user in rows:
        documents.append(DocumentOwnershipInfo(
            document_id=doc.id,
            document_uuid=str(doc.uuid),
            filename=doc.filename,
            file_type=doc.file_type,
            file_size=doc.file_size,
            title=doc.title,
            classification=doc.classification.value if hasattr(doc.classification, 'value') else str(doc.classification),
            uploaded_by=user.id,
            owner_email=user.email,
            owner_name=user.full_name or user.username,
            owner_role=user.role.value if hasattr(user.role, 'value') else str(user.role),
            owner_department=user.department,
            created_at=doc.created_at.isoformat() if doc.created_at else None
        ))
    
    return {
        "total": len(documents),
        "documents": documents
    }


@router.post("/reassign", summary="Reassign document ownership")
async def reassign_documents(
    request: ReassignRequest,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Reassign ownership of specific documents to a new user.
    
    Admin: Can reassign any documents
    Manager: Can reassign documents from their analysts
    """
    logger.info(f"User {current_user.email} reassigning {len(request.document_ids)} documents to user {request.new_owner_id}")
    
    # Verify new owner exists
    new_owner_result = await db.execute(select(User).where(User.id == request.new_owner_id))
    new_owner = new_owner_result.scalar_one_or_none()
    
    if not new_owner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {request.new_owner_id} not found"
        )
    
    # Get documents
    doc_result = await db.execute(
        select(Document).where(Document.id.in_(request.document_ids))
    )
    documents = doc_result.scalars().all()
    
    if not documents:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No documents found"
        )
    
    # Check permissions
    if current_user.role == UserRole.MANAGER:
        # Manager can only reassign documents from their analysts
        result = await db.execute(select(User.id).where(User.manager_id == current_user.id))
        analyst_ids = [row[0] for row in result.all()]
        analyst_ids.append(current_user.id)
        
        for doc in documents:
            if doc.uploaded_by not in analyst_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Cannot reassign document '{doc.filename}' - not in your hierarchy"
                )
    
    # Perform reassignment
    success_count = 0
    for doc in documents:
        old_owner_id = doc.uploaded_by
        doc.uploaded_by = request.new_owner_id
        success_count += 1
        
        # Log the reassignment
        audit_log = AuditLog(
            user_id=current_user.id,
            user_email=current_user.email,
            user_role=current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role),
            action="reassign_ownership",
            resource_type="document",
            resource_id=str(doc.uuid),
            details={
                "document_filename": doc.filename,
                "old_owner_id": old_owner_id,
                "new_owner_id": request.new_owner_id,
                "new_owner_email": new_owner.email,
                "reason": request.reason
            }
        )
        db.add(audit_log)
    
    await db.commit()
    
    logger.info(f"Successfully reassigned {success_count} documents")
    
    return {
        "success": True,
        "reassigned_count": success_count,
        "new_owner": {
            "id": new_owner.id,
            "email": new_owner.email,
            "name": new_owner.full_name or new_owner.username
        }
    }


@router.post("/bulk-reassign", summary="Bulk reassign all documents from one user to another")
async def bulk_reassign_documents(
    request: BulkReassignRequest,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Bulk reassign ALL documents (or specific subset) from one user to another.
    Useful when users leave or role changes occur.
    
    Admin: Can bulk reassign any user's documents
    Manager: Can bulk reassign their analysts' documents
    """
    logger.info(f"User {current_user.email} bulk reassigning from user {request.from_user_id} to {request.to_user_id}")
    
    # Verify users exist
    from_user_result = await db.execute(select(User).where(User.id == request.from_user_id))
    from_user = from_user_result.scalar_one_or_none()
    
    to_user_result = await db.execute(select(User).where(User.id == request.to_user_id))
    to_user = to_user_result.scalar_one_or_none()
    
    if not from_user or not to_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both users not found"
        )
    
    # Check permissions
    if current_user.role == UserRole.MANAGER:
        # Manager can only reassign from their analysts
        result = await db.execute(select(User.id).where(User.manager_id == current_user.id))
        analyst_ids = [row[0] for row in result.all()]
        analyst_ids.append(current_user.id)
        
        if request.from_user_id not in analyst_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot reassign documents - source user not in your hierarchy"
            )
    
    # Get documents to reassign
    if request.document_ids:
        # Specific documents
        doc_query = select(Document).where(
            and_(
                Document.uploaded_by == request.from_user_id,
                Document.id.in_(request.document_ids)
            )
        )
    else:
        # All documents from user
        doc_query = select(Document).where(Document.uploaded_by == request.from_user_id)
    
    result = await db.execute(doc_query)
    documents = result.scalars().all()
    
    if not documents:
        return {
            "success": True,
            "reassigned_count": 0,
            "message": "No documents to reassign"
        }
    
    # Perform bulk reassignment
    await db.execute(
        update(Document)
        .where(Document.id.in_([d.id for d in documents]))
        .values(uploaded_by=request.to_user_id)
    )
    
    # Log the bulk reassignment
    audit_log = AuditLog(
        user_id=current_user.id,
        user_email=current_user.email,
        user_role=current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role),
        action="bulk_reassign_ownership",
        resource_type="documents",
        details={
            "from_user_id": request.from_user_id,
            "from_user_email": from_user.email,
            "to_user_id": request.to_user_id,
            "to_user_email": to_user.email,
            "document_count": len(documents),
            "reason": request.reason,
            "specific_documents": request.document_ids is not None
        }
    )
    db.add(audit_log)
    
    await db.commit()
    
    logger.info(f"Successfully bulk reassigned {len(documents)} documents")
    
    return {
        "success": True,
        "reassigned_count": len(documents),
        "from_user": {
            "id": from_user.id,
            "email": from_user.email
        },
        "to_user": {
            "id": to_user.id,
            "email": to_user.email
        }
    }

