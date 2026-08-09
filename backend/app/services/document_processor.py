"""
Document processing service
"""
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Service for processing uploaded documents"""
    
    def __init__(self):
        self.supported_formats = {
            'pdf', 'docx', 'xlsx', 'pptx', 'txt', 
            'html', 'xml', 'json', 'eml', 'png', 'jpg', 'jpeg'
        }
    
    async def process_document(
        self, 
        file_path: Path,
        user_id: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process an uploaded document
        
        Args:
            file_path: Path to the uploaded file
            user_id: ID of the user who uploaded the document
            metadata: Optional metadata for the document
            
        Returns:
            Processing result dictionary
        """
        try:
            file_extension = file_path.suffix.lower().strip('.')
            
            if file_extension not in self.supported_formats:
                raise ValueError(f"Unsupported file format: {file_extension}")
            
            # TODO: Implement actual processing logic
            result = {
                "status": "success",
                "document_id": "temp_id",
                "file_name": file_path.name,
                "file_size": file_path.stat().st_size if file_path.exists() else 0,
                "format": file_extension,
                "user_id": user_id,
                "metadata": metadata or {}
            }
            
            logger.info(f"Document processed: {file_path.name}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing document {file_path}: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def process_document_sync(
        self,
        file_path: Path,
        user_id: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Synchronous version for Celery tasks"""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self.process_document(file_path, user_id, metadata)
            )
        finally:
            loop.close()