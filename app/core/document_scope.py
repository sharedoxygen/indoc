"""
Document scope enforcement for role-based access control with ABAC.

A document is visible when the role scope includes it, or when the user holds
an unexpired document grant. Grants do not raise a user's classification
clearance. Documents marked visibility=grant are omitted from the Admin
blanket; an admin sees those only as owner or grantee.
"""

from datetime import datetime
from typing import Optional, Set

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.classification import DocumentClassification
from app.models.document import Document
from app.models.document_permission import DocumentPermission
from app.models.user import User, UserRole

GRANT_VISIBILITY = "grant"
_READ_GRANT_TYPES = ("read", "write", "share", "delete")


def is_grant_restricted(custom_metadata) -> bool:
    """True when a document is hidden unless the caller owns it or holds a grant."""
    return (
        isinstance(custom_metadata, dict)
        and custom_metadata.get("visibility") == GRANT_VISIBILITY
    )


async def get_effective_document_ids(
    db: AsyncSession,
    user: User,
    selected_ids: Optional[Set[int]] = None,
    enforce_classification: bool = True,
) -> Set[int]:
    """
    Calculate the effective set of document IDs a user can access.

    Rules (applied in order):
    1. RBAC: Start with all documents the user's role permits (respecting hierarchy)
    2. ABAC: Filter by document classification level (if enforce_classification=True)
    3. Selection: If selected_ids is provided, intersect with that set

    RBAC Rules:
    - Admin sees every document that is not grant-restricted, plus grant-restricted
      documents they own
    - Manager sees documents from their analysts + their own
    - Analyst sees only their own documents
    - Any role also sees documents with an unexpired read/write/share/delete grant,
      still limited by classification clearance

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

    # Admin sees the library, but not grant-restricted documents they do not own.
    # An explicit grant is unioned below and is the only other way in.
    if user.role == UserRole.ADMIN:
        result = await db.execute(
            select(Document.id, Document.uploaded_by, Document.custom_metadata)
        )
        permitted_ids = {
            doc_id
            for doc_id, owner_id, metadata in result.all()
            if not is_grant_restricted(metadata) or owner_id == user.id
        }

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
                row[0]
                for row in doc_result.all()
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
                row[0]
                for row in doc_result.all()
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
                row[0]
                for row in doc_result.all()
                if DocumentClassification.can_access(role_str, row[1])
            }
        else:
            permitted_ids = {row[0] for row in doc_result.all()}

    permitted_ids |= await _granted_document_ids(db, user, enforce_classification)

    # If user selected specific documents, intersect with permitted set
    # Only apply intersection if selected_ids is not None AND not empty
    if selected_ids is not None and len(selected_ids) > 0:
        permitted_ids = permitted_ids.intersection(selected_ids)

    return permitted_ids


async def _granted_document_ids(
    db: AsyncSession,
    user: User,
    enforce_classification: bool,
) -> Set[int]:
    """Document ids the user may read because of an unexpired grant."""
    result = await db.execute(
        select(Document.id, Document.classification)
        .join(DocumentPermission, DocumentPermission.document_id == Document.id)
        .where(
            DocumentPermission.user_id == user.id,
            DocumentPermission.permission_type.in_(_READ_GRANT_TYPES),
            or_(
                DocumentPermission.expires_at.is_(None),
                DocumentPermission.expires_at > datetime.utcnow(),
            ),
        )
    )
    rows = result.all()
    if not enforce_classification or user.role == UserRole.ADMIN:
        return {row[0] for row in rows}
    role_str = getattr(user.role, "value", user.role)
    return {
        row[0] for row in rows if DocumentClassification.can_access(role_str, row[1])
    }


async def filter_documents_by_scope(
    db: AsyncSession, user: User, base_query, selected_ids: Optional[Set[int]] = None
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
