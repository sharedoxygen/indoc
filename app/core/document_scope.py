"""
Document scope enforcement for role-based access control with ABAC
"""
from typing import Optional, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.user import User, UserRole
from app.models.document import Document
from app.models.classification import DocumentClassification


async def get_effective_document_ids(
    db: AsyncSession,
    user: User,
    selected_ids: Optional[Set[int]] = None,
    enforce_classification: bool = True
) -> Set[int]:
    """
    Calculate the effective set of document IDs a user can access.
    
    Rules (applied in order):
    1. RBAC: Start with all documents the user's role permits (respecting hierarchy)
    2. ABAC: Filter by document classification level (if enforce_classification=True)
    3. Selection: If selected_ids is provided, intersect with that set
    
    RBAC Rules:
    - Admin sees all documents
    - Manager sees documents from their analysts + their own
    - Analyst sees only their own documents (or those explicitly shared)
    
    ABAC Rules:
    - Admin: Can access all classifications
    - Manager: Can access up to Restricted (Public, Internal, Restricted)
    - Analyst: Can access up to Internal (Public, Internal)
    
    Args:
        db: Database session
        user: Current user
        selected_ids: Optional set of document IDs from frontend selection/filter
        enforce_classification: Apply ABAC classification checks (default: True)
        
    Returns:
        Set of document IDs the user can access in this query
    """
    permitted_ids: Set[int] = set()
    role_str = getattr(user.role, "value", user.role)
    
    # Admin has access to all documents (both RBAC and ABAC)
    if user.role == UserRole.ADMIN:
        query = select(Document.id, Document.classification)
        result = await db.execute(query)
        # Admin bypasses classification checks
        permitted_ids = {row[0] for row in result.all()}
    
    # Manager sees their own documents + their analysts' documents
    elif user.role == UserRole.MANAGER:
        # Get analyst IDs under this manager
        analyst_query = select(User.id).where(User.manager_id == user.id)
        analyst_result = await db.execute(analyst_query)
        analyst_ids = {row[0] for row in analyst_result.all()}
        analyst_ids.add(user.id)  # Include manager's own documents
        
        # Get documents from manager and their analysts
        doc_query = select(Document.id, Document.classification).where(
            Document.uploaded_by.in_(analyst_ids)
        )
        doc_result = await db.execute(doc_query)
        
        # Apply classification filter for Manager (up to Restricted)
        if enforce_classification:
            permitted_ids = {
                row[0] for row in doc_result.all()
                if DocumentClassification.can_access(role_str, row[1])
            }
        else:
            permitted_ids = {row[0] for row in doc_result.all()}
    
    # Analyst sees only their own documents
    elif user.role == UserRole.ANALYST:
        doc_query = select(Document.id, Document.classification).where(
            Document.uploaded_by == user.id
        )
        doc_result = await db.execute(doc_query)
        
        # Apply classification filter for Analyst (up to Internal)
        if enforce_classification:
            permitted_ids = {
                row[0] for row in doc_result.all()
                if DocumentClassification.can_access(role_str, row[1])
            }
        else:
            permitted_ids = {row[0] for row in doc_result.all()}
    
    # Legacy roles (backward compatibility during migration)
    elif user.role in [UserRole.REVIEWER, UserRole.UPLOADER, UserRole.VIEWER]:
        # Treat legacy roles as having analyst-level access
        doc_query = select(Document.id, Document.classification).where(
            Document.uploaded_by == user.id
        )
        doc_result = await db.execute(doc_query)
        
        # Apply classification filter (up to Internal for legacy roles)
        if enforce_classification:
            permitted_ids = {
                row[0] for row in doc_result.all()
                if DocumentClassification.can_access(role_str, row[1])
            }
        else:
            permitted_ids = {row[0] for row in doc_result.all()}
    
    # If user selected specific documents, intersect with permitted set
    # Only apply intersection if selected_ids is not None AND not empty
    if selected_ids is not None and len(selected_ids) > 0:
        permitted_ids = permitted_ids.intersection(selected_ids)
    
    return permitted_ids


async def filter_documents_by_scope(
    db: AsyncSession,
    user: User,
    base_query,
    selected_ids: Optional[Set[int]] = None
):
    """
    Apply document scope filtering to a SQLAlchemy query.
    
    Args:
        db: Database session
        user: Current user
        base_query: Base SQLAlchemy query to filter
        selected_ids: Optional set of selected document IDs
        
    Returns:
        Filtered query
    """
    effective_ids = await get_effective_document_ids(db, user, selected_ids)
    
    if not effective_ids:
        # No accessible documents - return empty result
        return base_query.where(Document.id == -1)
    
    return base_query.where(Document.id.in_(effective_ids))

