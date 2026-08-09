"""
Data Loss Prevention (DLP) for document downloads and exports

Features:
- Classification-based download restrictions
- Export audit logging
- Watermarking (text/metadata)
- Rate limiting for bulk exports
- Role-based export permissions
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

from app.models.user import User, UserRole
from app.models.document import Document
from app.models.classification import DocumentClassification

logger = logging.getLogger(__name__)


class ExportAction(str, Enum):
    """Types of export actions"""
    DOWNLOAD = "download"
    PRINT = "print"
    SHARE = "share"
    COPY = "copy"


class DLPPolicy:
    """
    Data Loss Prevention policy enforcement
    
    Rules:
    - Confidential: Admin only, watermarked, logged
    - Restricted: Manager+, watermarked, logged
    - Internal: Analyst+, logged
    - Public: All users, not logged
    """
    
    @staticmethod
    def can_export(
        user: User,
        document: Document,
        action: ExportAction = ExportAction.DOWNLOAD
    ) -> tuple[bool, Optional[str]]:
        """
        Check if a user can export a document
        
        Args:
            user: User attempting export
            document: Document being exported
            action: Type of export action
        
        Returns:
            (is_allowed, reason_if_denied)
        """
        role_str = getattr(user.role, "value", user.role)
        classification = document.classification
        
        # Check ABAC - user role must be able to access classification
        if not DocumentClassification.can_access(role_str, classification):
            return False, f"Your role ({role_str}) cannot access {classification.value} documents"
        
        # Additional restrictions for Confidential documents
        if classification == DocumentClassification.CONFIDENTIAL:
            # Only Admin can export Confidential
            if user.role != UserRole.ADMIN:
                return False, "Only Admins can export Confidential documents"
            
            # No sharing Confidential documents
            if action == ExportAction.SHARE:
                return False, "Confidential documents cannot be shared externally"
        
        # Additional restrictions for Restricted documents
        if classification == DocumentClassification.RESTRICTED:
            # No sharing Restricted by Analysts
            if user.role == UserRole.ANALYST and action == ExportAction.SHARE:
                return False, "Analysts cannot share Restricted documents"
        
        return True, None
    
    @staticmethod
    def requires_watermark(document: Document) -> bool:
        """Check if document requires watermarking on export"""
        # Confidential and Restricted documents must be watermarked
        return document.classification in [
            DocumentClassification.CONFIDENTIAL,
            DocumentClassification.RESTRICTED
        ]
    
    @staticmethod
    def requires_audit_log(document: Document, action: ExportAction) -> bool:
        """Check if export action should be audit logged"""
        # Log all exports except Public downloads
        if document.classification == DocumentClassification.PUBLIC and action == ExportAction.DOWNLOAD:
            return False
        return True
    
    @staticmethod
    def get_max_exports_per_hour(user: User) -> int:
        """Get max export rate limit for user role"""
        rate_limits = {
            UserRole.ADMIN: 1000,  # High limit for admins
            UserRole.MANAGER: 100,
            UserRole.ANALYST: 20,
        }
        return rate_limits.get(user.role, 10)  # Default 10 for unknown roles


class Watermarker:
    """
    Document watermarking for DLP
    
    Supports:
    - Text watermarks (visible)
    - Metadata watermarks (hidden)
    - User/timestamp/classification tagging
    """
    
    @staticmethod
    def generate_watermark_text(
        user: User,
        document: Document,
        action: ExportAction
    ) -> str:
        """
        Generate watermark text for document export
        
        Returns:
            Watermark text to be embedded in document
        """
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        watermark_lines = [
            f"Classification: {document.classification.value}",
            f"Exported by: {user.email} ({user.role.value if hasattr(user.role, 'value') else user.role})",
            f"Export time: {timestamp}",
            f"Document ID: {document.uuid}",
            f"Action: {action.value}"
        ]
        
        return " | ".join(watermark_lines)
    
    @staticmethod
    def generate_watermark_metadata(
        user: User,
        document: Document,
        action: ExportAction
    ) -> Dict[str, Any]:
        """
        Generate metadata watermark (hidden in document properties)
        
        Returns:
            Dictionary of metadata to embed
        """
        return {
            "indoc_classification": document.classification.value,
            "indoc_exported_by": user.email,
            "indoc_user_id": user.id,
            "indoc_export_time": datetime.utcnow().isoformat(),
            "indoc_document_id": str(document.uuid),
            "indoc_action": action.value,
            "indoc_watermark_version": "1.0"
        }
    
    @staticmethod
    def apply_text_watermark(content: str, watermark: str, position: str = "footer") -> str:
        """
        Apply visible text watermark to document content
        
        Args:
            content: Original document content
            watermark: Watermark text
            position: Where to place watermark (header/footer/both)
        
        Returns:
            Content with watermark
        """
        separator = "\n" + "=" * 80 + "\n"
        
        if position == "header":
            return f"{separator}{watermark}{separator}{content}"
        elif position == "footer":
            return f"{content}{separator}{watermark}{separator}"
        elif position == "both":
            return f"{separator}{watermark}{separator}{content}{separator}{watermark}{separator}"
        else:
            return content  # No watermark
    
    @staticmethod
    def apply_pdf_watermark(pdf_path: str, watermark: str) -> bytes:
        """
        Apply watermark to PDF file (placeholder)
        
        Requires PyPDF2 or reportlab for implementation
        
        Args:
            pdf_path: Path to PDF file
            watermark: Watermark text
        
        Returns:
            Watermarked PDF bytes
        """
        logger.warning("PDF watermarking not yet implemented. Use metadata watermark for now.")
        # TODO: Implement PDF watermarking using PyPDF2
        with open(pdf_path, 'rb') as f:
            return f.read()


class ExportLimiter:
    """
    Rate limiting for document exports (in-memory)
    
    Prevents bulk data exfiltration
    """
    
    def __init__(self):
        self.export_counts: Dict[int, list] = {}  # user_id -> [timestamps]
        self.window_seconds = 3600  # 1 hour
    
    def check_export_limit(self, user: User) -> tuple[bool, Optional[str]]:
        """
        Check if user has exceeded export rate limit
        
        Returns:
            (is_allowed, reason_if_denied)
        """
        import time
        now = time.time()
        max_exports = DLPPolicy.get_max_exports_per_hour(user)
        
        # Get user's recent exports
        user_exports = self.export_counts.get(user.id, [])
        
        # Remove exports outside window
        user_exports = [ts for ts in user_exports if ts > now - self.window_seconds]
        
        # Check limit
        if len(user_exports) >= max_exports:
            remaining_time = int(self.window_seconds - (now - user_exports[0]))
            return False, f"Export limit reached. {max_exports} exports per hour. Try again in {remaining_time}s."
        
        # Record this export
        user_exports.append(now)
        self.export_counts[user.id] = user_exports
        
        return True, None
    
    def get_remaining_exports(self, user: User) -> int:
        """Get number of remaining exports for user in current window"""
        import time
        now = time.time()
        max_exports = DLPPolicy.get_max_exports_per_hour(user)
        
        user_exports = self.export_counts.get(user.id, [])
        user_exports = [ts for ts in user_exports if ts > now - self.window_seconds]
        
        return max(0, max_exports - len(user_exports))


# Global instances
export_limiter = ExportLimiter()


