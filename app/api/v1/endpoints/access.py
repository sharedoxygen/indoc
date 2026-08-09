"""
Document Access Management API Endpoints
Provides fine-grained permission management for documents
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, delete
from datetime import datetime
from pydantic import BaseModel, Field

from app.api.deps import get_db, get_current_user
from app.models.user import User, UserRole
from app.models.document import Document
from app.models.document_permission import DocumentPermission
from app.models.audit import AuditLog
import logging
from sqlalchemy.orm import aliased

logger = logging.getLogger(__name__)

router = APIRouter()


# Schemas
class PermissionGrantRequest(BaseModel):
    document_id: int
    user_id: int
    permission_type: str = Field(..., pattern="^(read|write|share|delete)$")
    expires_at: Optional[datetime] = None
    reason: Optional[str] = None


class BulkPermissionGrantRequest(BaseModel):
    document_ids: List[int]
    user_ids: List[int]
    permission_type: str = Field(..., pattern="^(read|write|share|delete)$")
    expires_at: Optional[datetime] = None
    reason: Optional[str] = None


class PermissionResponse(BaseModel):
    id: int
    document_id: int
    user_id: int
    user_email: str
    user_name: str
    permission_type: str
    granted_by: int
    granted_by_email: str
    granted_at: datetime
    expires_at: Optional[datetime]
    reason: Optional[str]
    
    class Config:
        from_attributes = True


class DocumentAccessInfo(BaseModel):
    document_id: int
    document_title: str
    owner_id: int
    owner_email: str
    permissions: List[PermissionResponse]
    total_users_with_access: int


# Helper Functions
async def has_manage_permission(db: AsyncSession, user: User, document_id: int) -> bool:
    """Check if user can manage permissions for a document"""
    # Admins can manage all
    if user.role == UserRole.ADMIN:
        return True
    
    # Get document
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        return False
    
    # Document owner can manage
    if document.uploaded_by == user.id:
        return True
    
    # Manager can manage documents uploaded by their analysts
    if user.role == UserRole.MANAGER:
        analyst_query = select(User.id).where(User.manager_id == user.id)
        analyst_result = await db.execute(analyst_query)
        analyst_ids = {row[0] for row in analyst_result.all()}
        
        if document.uploaded_by in analyst_ids:
            return True
    
    # Check if user has 'share' permission on the document
    perm_query = select(DocumentPermission).where(
        and_(
            DocumentPermission.document_id == document_id,
            DocumentPermission.user_id == user.id,
            DocumentPermission.permission_type == 'share',
            or_(
                DocumentPermission.expires_at.is_(None),
                DocumentPermission.expires_at > datetime.utcnow()
            )
        )
    )
    perm_result = await db.execute(perm_query)
    
    return perm_result.scalar_one_or_none() is not None


# Endpoints
@router.post("/grant", response_model=PermissionResponse)
async def grant_permission(
    request: PermissionGrantRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Grant a user permission to access a document"""
    
    # Check if current user can manage this document's permissions
    if not await has_manage_permission(db, current_user, request.document_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to manage access for this document"
        )
    
    # Verify document exists
    doc_result = await db.execute(
        select(Document).where(Document.id == request.document_id)
    )
    document = doc_result.scalar_one_or_none()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Verify user exists
    user_result = await db.execute(
        select(User).where(User.id == request.user_id)
    )
    target_user = user_result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if permission already exists
    existing_perm = await db.execute(
        select(DocumentPermission).where(
            and_(
                DocumentPermission.document_id == request.document_id,
                DocumentPermission.user_id == request.user_id,
                DocumentPermission.permission_type == request.permission_type
            )
        )
    )
    existing = existing_perm.scalar_one_or_none()
    
    if existing:
        # Update expiration if provided
        if request.expires_at:
            existing.expires_at = request.expires_at
            existing.reason = request.reason
            await db.flush()
            
            # Log the update
            audit_log = AuditLog(
                user_id=current_user.id,
                user_email=current_user.email,
                user_role=getattr(current_user.role, "value", current_user.role),
                action="update_permission",
                resource_type="document_permission",
                resource_id=str(existing.id),
                details={
                    "document_id": request.document_id,
                    "user_id": request.user_id,
                    "permission_type": request.permission_type,
                    "expires_at": request.expires_at.isoformat() if request.expires_at else None
                }
            )
            db.add(audit_log)
            
            return PermissionResponse(
                id=existing.id,
                document_id=existing.document_id,
                user_id=existing.user_id,
                user_email=target_user.email,
                user_name=target_user.full_name,
                permission_type=existing.permission_type,
                granted_by=existing.granted_by,
                granted_by_email=current_user.email,
                granted_at=existing.granted_at,
                expires_at=existing.expires_at,
                reason=existing.reason
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Permission already exists"
            )
    
    # Create new permission
    permission = DocumentPermission(
        document_id=request.document_id,
        user_id=request.user_id,
        permission_type=request.permission_type,
        granted_by=current_user.id,
        expires_at=request.expires_at,
        reason=request.reason
    )
    
    db.add(permission)
    await db.flush()
    
    # Log the grant
    audit_log = AuditLog(
        user_id=current_user.id,
        user_email=current_user.email,
        user_role=getattr(current_user.role, "value", current_user.role),
        action="grant_permission",
        resource_type="document_permission",
        resource_id=str(permission.id),
        details={
            "document_id": request.document_id,
            "document_title": document.title,
            "user_id": request.user_id,
            "user_email": target_user.email,
            "permission_type": request.permission_type,
            "expires_at": request.expires_at.isoformat() if request.expires_at else None
        }
    )
    db.add(audit_log)
    
    logger.info(f"User {current_user.email} granted {request.permission_type} permission on document {document.title} to {target_user.email}")
    
    return PermissionResponse(
        id=permission.id,
        document_id=permission.document_id,
        user_id=permission.user_id,
        user_email=target_user.email,
        user_name=target_user.full_name,
        permission_type=permission.permission_type,
        granted_by=permission.granted_by,
        granted_by_email=current_user.email,
        granted_at=permission.granted_at,
        expires_at=permission.expires_at,
        reason=permission.reason
    )


@router.post("/revoke")
async def revoke_permission(
    document_id: int,
    user_id: int,
    permission_type: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Revoke a user's permission to access a document"""
    
    # Check if current user can manage this document's permissions
    if not await has_manage_permission(db, current_user, document_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to manage access for this document"
        )
    
    # Find and delete the permission
    result = await db.execute(
        delete(DocumentPermission).where(
            and_(
                DocumentPermission.document_id == document_id,
                DocumentPermission.user_id == user_id,
                DocumentPermission.permission_type == permission_type
            )
        ).returning(DocumentPermission.id)
    )
    
    deleted_id = result.scalar_one_or_none()
    
    if not deleted_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )
    
    # Log the revocation
    audit_log = AuditLog(
        user_id=current_user.id,
        user_email=current_user.email,
        user_role=getattr(current_user.role, "value", current_user.role),
        action="revoke_permission",
        resource_type="document_permission",
        resource_id=str(deleted_id),
        details={
            "document_id": document_id,
            "user_id": user_id,
            "permission_type": permission_type
        }
    )
    db.add(audit_log)
    
    logger.info(f"User {current_user.email} revoked {permission_type} permission on document {document_id} from user {user_id}")
    
    return {"message": "Permission revoked successfully", "id": deleted_id}


@router.get("/document/{document_id}", response_model=DocumentAccessInfo)
async def get_document_permissions(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all users with access to a document"""
    
    # Check if user can view this document's permissions
    if not await has_manage_permission(db, current_user, document_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view access for this document"
        )
    
    # Get document
    doc_result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = doc_result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Get owner info
    owner_result = await db.execute(
        select(User).where(User.id == document.uploaded_by)
    )
    owner = owner_result.scalar_one_or_none()
    
    # Get all permissions
    perm_query = select(DocumentPermission, User).join(
        User, DocumentPermission.user_id == User.id
    ).where(
        DocumentPermission.document_id == document_id
    ).order_by(DocumentPermission.granted_at.desc())
    
    perm_result = await db.execute(perm_query)
    permissions_data = perm_result.all()
    
    # Get granter info for each permission
    permissions = []
    for perm, user in permissions_data:
        granter_result = await db.execute(
            select(User).where(User.id == perm.granted_by)
        )
        granter = granter_result.scalar_one_or_none()
        
        permissions.append(PermissionResponse(
            id=perm.id,
            document_id=perm.document_id,
            user_id=perm.user_id,
            user_email=user.email,
            user_name=user.full_name,
            permission_type=perm.permission_type,
            granted_by=perm.granted_by,
            granted_by_email=granter.email if granter else "Unknown",
            granted_at=perm.granted_at,
            expires_at=perm.expires_at,
            reason=perm.reason
        ))
    
    return DocumentAccessInfo(
        document_id=document.id,
        document_title=document.title,
        owner_id=document.uploaded_by,
        owner_email=owner.email if owner else "Unknown",
        permissions=permissions,
        total_users_with_access=len(permissions) + 1  # +1 for owner
    )


@router.get("/user/{user_id}")
async def get_user_accessible_documents(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500)
):
    """List all documents a user has explicit permission to access"""
    
    # Only admins or the user themselves can view this
    if current_user.role != UserRole.ADMIN and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this user's document access"
        )
    
    # Get all active permissions for the user
    query = select(DocumentPermission, Document).join(
        Document, DocumentPermission.document_id == Document.id
    ).where(
        and_(
            DocumentPermission.user_id == user_id,
            or_(
                DocumentPermission.expires_at.is_(None),
                DocumentPermission.expires_at > datetime.utcnow()
            )
        )
    ).order_by(DocumentPermission.granted_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    permissions_data = result.all()
    
    documents_with_permissions = []
    for perm, doc in permissions_data:
        documents_with_permissions.append({
            "document_id": doc.id,
            "document_title": doc.title,
            "document_filename": doc.filename,
            "permission_type": perm.permission_type,
            "granted_at": perm.granted_at,
            "expires_at": perm.expires_at,
            "reason": perm.reason
        })
    
    return {
        "user_id": user_id,
        "total_explicit_permissions": len(documents_with_permissions),
        "documents": documents_with_permissions
    }


@router.post("/bulk-grant")
async def bulk_grant_permissions(
    request: BulkPermissionGrantRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Grant multiple users access to multiple documents"""
    
    # Only admins and managers can bulk grant
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admins and Managers can bulk grant permissions"
        )
    
    granted = []
    failed = []
    
    for document_id in request.document_ids:
        # Check permission to manage this document
        if not await has_manage_permission(db, current_user, document_id):
            failed.append({
                "document_id": document_id,
                "reason": "No permission to manage this document"
            })
            continue
        
        for user_id in request.user_ids:
            try:
                # Check if permission already exists
                existing = await db.execute(
                    select(DocumentPermission).where(
                        and_(
                            DocumentPermission.document_id == document_id,
                            DocumentPermission.user_id == user_id,
                            DocumentPermission.permission_type == request.permission_type
                        )
                    )
                )
                
                if existing.scalar_one_or_none():
                    continue  # Skip existing permissions
                
                # Create permission
                permission = DocumentPermission(
                    document_id=document_id,
                    user_id=user_id,
                    permission_type=request.permission_type,
                    granted_by=current_user.id,
                    expires_at=request.expires_at,
                    reason=request.reason
                )
                
                db.add(permission)
                granted.append({
                    "document_id": document_id,
                    "user_id": user_id,
                    "permission_type": request.permission_type
                })
                
            except Exception as e:
                logger.error(f"Failed to grant permission: {e}")
                failed.append({
                    "document_id": document_id,
                    "user_id": user_id,
                    "reason": str(e)
                })
    
    await db.flush()
    
    # Log bulk grant
    audit_log = AuditLog(
        user_id=current_user.id,
        user_email=current_user.email,
        user_role=getattr(current_user.role, "value", current_user.role),
        action="bulk_grant_permissions",
        resource_type="document_permission",
        details={
            "document_ids": request.document_ids,
            "user_ids": request.user_ids,
            "permission_type": request.permission_type,
            "granted_count": len(granted),
            "failed_count": len(failed)
        }
    )
    db.add(audit_log)
    
    return {
        "granted": granted,
        "failed": failed,
        "summary": {
            "total_granted": len(granted),
            "total_failed": len(failed)
        }
    }


# -------- New endpoint used by Document Access Map (frontend) --------
class DocumentAccessMapPermission(BaseModel):
    user_id: int
    user_email: str
    user_name: str | None = None
    user_role: str
    permission_type: str
    granted_at: datetime | None = None
    expires_at: datetime | None = None

    class Config:
        from_attributes = True


class DocumentAccessMapEntry(BaseModel):
    document_id: int
    document_title: str
    document_type: str | None = None
    owner_email: str
    permissions: List[DocumentAccessMapPermission]

    class Config:
        from_attributes = True


@router.get("/documents", response_model=List[DocumentAccessMapEntry])
async def list_documents_with_explicit_permissions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all documents that have explicit permissions granted, with users.

    - Admin: sees all documents with permissions
    - Manager: documents owned by self or team analysts, plus documents where
      they have been granted permissions directly or granted by them
    """
    # Aliases for joining the User table twice
    perm_user = aliased(User)
    owner_user = aliased(User)

    base_query = (
        select(Document, DocumentPermission, perm_user, owner_user)
        .join(Document, Document.id == DocumentPermission.document_id)
        .join(perm_user, DocumentPermission.user_id == perm_user.id)
        .join(owner_user, Document.uploaded_by == owner_user.id)
    )

    if current_user.role == UserRole.MANAGER:
        # Determine team analyst ids
        team_result = await db.execute(select(User.id).where(User.manager_id == current_user.id))
        team_ids = {row[0] for row in team_result.all()}
        allowed_uploader_ids = team_ids | {current_user.id}

        base_query = base_query.where(
            (
                Document.uploaded_by.in_(allowed_uploader_ids)
            )
            | (DocumentPermission.user_id == current_user.id)
            | (DocumentPermission.granted_by == current_user.id)
        )
    elif current_user.role != UserRole.ADMIN:
        # Non-admin/manager: only show documents where the user has explicit permissions
        base_query = base_query.where(DocumentPermission.user_id == current_user.id)

    result = await db.execute(base_query.order_by(Document.id.asc(), DocumentPermission.granted_at.desc()))
    rows = result.all()

    # Group by document id
    doc_map: dict[int, DocumentAccessMapEntry] = {}
    for doc, perm, p_user, o_user in rows:
        if doc.id not in doc_map:
            doc_map[doc.id] = DocumentAccessMapEntry(
                document_id=doc.id,
                document_title=doc.title,
                document_type=doc.file_type,
                owner_email=o_user.email if o_user else "Unknown",
                permissions=[],
            )

        doc_map[doc.id].permissions.append(
            DocumentAccessMapPermission(
                user_id=p_user.id,
                user_email=p_user.email,
                user_name=getattr(p_user, "full_name", None),
                user_role=getattr(p_user.role, "value", p_user.role),
                permission_type=perm.permission_type,
                granted_at=perm.granted_at,
                expires_at=perm.expires_at,
            )
        )

    # Return as list (only documents that actually have explicit permissions)
    return list(doc_map.values())


@router.get("/audit")
async def get_access_audit_log(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    document_id: Optional[int] = None,
    user_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500)
):
    """Get audit log of permission changes"""
    
    # Only admins can view full audit log
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admins can view the access audit log"
        )
    
    # Build query
    query = select(AuditLog).where(
        AuditLog.resource_type == "document_permission"
    )
    
    if document_id:
        query = query.where(AuditLog.details["document_id"].astext == str(document_id))
    
    if user_id:
        query = query.where(
            or_(
                AuditLog.user_id == user_id,
                AuditLog.details["user_id"].astext == str(user_id)
            )
        )
    
    query = query.order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    audit_logs = result.scalars().all()
    
    return {
        "total": len(audit_logs),
        "logs": [
            {
                "id": log.id,
                "action": log.action,
                "performed_by": log.user_email,
                "timestamp": log.timestamp,
                "details": log.details
            }
            for log in audit_logs
        ]
    }

