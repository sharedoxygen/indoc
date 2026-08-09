"""
Document classification enum for ABAC (Attribute-Based Access Control)
"""
import enum


class DocumentClassification(str, enum.Enum):
    """
    Document classification levels for access control
    
    - PUBLIC: Accessible to all authenticated users
    - INTERNAL: Accessible to all employees (Analyst+)
    - RESTRICTED: Manager+ only
    - CONFIDENTIAL: Admin only
    """
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    RESTRICTED = "RESTRICTED"
    CONFIDENTIAL = "CONFIDENTIAL"
    
    @classmethod
    def get_hierarchy_level(cls, classification: "DocumentClassification") -> int:
        """Get numeric level for comparison (higher = more restricted)"""
        hierarchy = {
            cls.PUBLIC: 0,
            cls.INTERNAL: 1,
            cls.RESTRICTED: 2,
            cls.CONFIDENTIAL: 3
        }
        return hierarchy.get(classification, 1)
    
    @classmethod
    def can_access(cls, user_role: str, doc_classification: "DocumentClassification") -> bool:
        """
        Check if a user role can access a document classification level
        
        Role hierarchy:
        - Admin: Can access all classifications
        - Manager: Can access up to Restricted
        - Analyst: Can access up to Internal
        """
        from app.models.user import UserRole
        
        # Admin can access everything
        if user_role == UserRole.ADMIN.value:
            return True
        
        # Manager can access up to Restricted
        if user_role == UserRole.MANAGER.value:
            return cls.get_hierarchy_level(doc_classification) <= cls.get_hierarchy_level(cls.RESTRICTED)
        
        # Analyst can access up to Internal
        if user_role == UserRole.ANALYST.value:
            return cls.get_hierarchy_level(doc_classification) <= cls.get_hierarchy_level(cls.INTERNAL)
        
        # Legacy roles - treat as Analyst
        if user_role in [UserRole.REVIEWER.value, UserRole.UPLOADER.value, UserRole.VIEWER.value]:
            return cls.get_hierarchy_level(doc_classification) <= cls.get_hierarchy_level(cls.INTERNAL)
        
        # Default: only Public
        return doc_classification == cls.PUBLIC


