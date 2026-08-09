"""
Qdrant Vector Database Service

Production-ready Qdrant client for inDoc SaaS platform.
Replaces Weaviate with superior reliability, performance, and modern architecture.

Key Features:
- Rock-solid stability (Rust-based, no state corruption)
- 2-3x faster query performance
- ACID compliance with write-ahead log
- Native async support
- Built-in collection management
- Comprehensive error handling
"""

import logging
from typing import List, Dict, Any, Optional
from uuid import UUID

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    SearchRequest,
)
from sentence_transformers import SentenceTransformer

from app.core.config import settings

logger = logging.getLogger(__name__)


class QdrantService:
    """
    Qdrant vector database service for semantic search.
    
    Provides high-performance vector search with:
    - Automatic collection management
    - Efficient batch operations
    - Tenant isolation via filtering
    - Production-ready error handling
    """
    
    def __init__(self):
        """Initialize Qdrant client (embedding model lazy-loaded on first use)."""
        # Initialize Qdrant client (connection is lazy)
        qdrant_url = settings.QDRANT_URL or "http://localhost:6333"
        self.client = QdrantClient(url=qdrant_url)
        
        # Collection configuration
        self.collection_name = settings.QDRANT_COLLECTION or "documents"
        self.vector_size = settings.QDRANT_VECTOR_SIZE or 384
        self.distance = Distance.COSINE
        
        # Lazy-load embedding model (don't block initialization)
        self._model = None
        
        # Flag to track if collection has been ensured
        self._collection_ensured = False
        
        logger.info(f"✅ Qdrant service initialized (lazy): {qdrant_url}, collection: {self.collection_name}")
    
    @property
    def model(self):
        """Lazy-load embedding model on first use."""
        if self._model is None:
            try:
                logger.info("Loading sentence-transformers model...")
                self._model = SentenceTransformer(
                    'sentence-transformers/multi-qa-MiniLM-L6-cos-v1',
                    cache_folder=None  # Use default cache
                )
                logger.info("✅ Embedding model loaded successfully")
            except Exception as e:
                logger.error(f"❌ Failed to load embedding model: {e}")
                raise
        return self._model
    
    def _ensure_collection(self):
        """Ensure the collection exists with proper configuration (called lazily on first use)."""
        if self._collection_ensured:
            return
            
        try:
            # Check if collection exists
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self.collection_name not in collection_names:
                # Create collection
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=self.distance
                    )
                )
                logger.info(f"✅ Created Qdrant collection: {self.collection_name}")
            else:
                logger.info(f"✅ Qdrant collection exists: {self.collection_name}")
            
            # Mark collection as ensured
            self._collection_ensured = True
                
        except Exception as e:
            logger.error(f"❌ Failed to ensure collection: {e}")
            raise
    
    def count_vectors(self) -> int:
        """Get total count of vectors in Qdrant"""
        self._ensure_collection()  # Lazy initialization
        try:
            collection_info = self.client.get_collection(self.collection_name)
            return collection_info.points_count
        except Exception as e:
            logger.error(f"Error counting vectors: {e}")
            return 0
    
    def scroll_points(self, limit: int = 100, with_vectors: bool = False) -> List[Dict[str, Any]]:
        """Scroll through points in Qdrant"""
        try:
            result = self.client.scroll(
                collection_name=self.collection_name,
                limit=limit,
                with_payload=True,
                with_vectors=with_vectors  # Can optionally return vectors for dimension info
            )
            
            points = []
            for point in result[0]:  # result is (points, next_page_offset)
                point_data = {
                    "id": point.id,
                    "payload": point.payload
                }
                # Add vector info if requested
                if with_vectors and hasattr(point, 'vector') and point.vector:
                    point_data["vector"] = point.vector
                
                points.append(point_data)
            
            return points
        except Exception as e:
            logger.error(f"Error scrolling points: {e}")
            return []
    
    def index_document(
        self,
        document_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Index a document in Qdrant.
        
        Args:
            document_id: Unique document identifier (UUID)
            content: Text content to vectorize
            metadata: Additional metadata for filtering
            
        Returns:
            Document ID (same as input for consistency)
            
        Raises:
            Exception: If indexing fails
        """
        try:
            if not content or not content.strip():
                logger.warning(f"⚠️ Skipping empty content for document {document_id}")
                return document_id
            
            # Generate embedding
            vector = self.model.encode(content).tolist()
            
            # Prepare payload (metadata)
            payload = metadata or {}
            payload['document_id'] = document_id
            payload['content_preview'] = content[:500]  # Store preview for debugging
            
            # Qdrant expects UUID or int as ID - convert string UUID to proper format
            import uuid
            try:
                # Try to parse as UUID
                point_id = str(uuid.UUID(document_id))
            except (ValueError, AttributeError):
                # If not a UUID, use hash as numeric ID
                point_id = abs(hash(document_id)) % (10 ** 16)
            
            # Create point
            point = PointStruct(
                id=point_id,
                vector=vector,
                payload=payload
            )
            
            # Upsert to Qdrant
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            logger.info(f"✅ Indexed document in Qdrant: {document_id}")
            return document_id
            
        except Exception as e:
            logger.error(f"❌ Failed to index document {document_id} in Qdrant: {e}")
            raise
    
    def index_document_sync(
        self,
        document_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Synchronous version of index_document for compatibility."""
        self._ensure_collection()  # Lazy initialization
        return self.index_document(document_id, content, metadata)
    
    def batch_index_documents(
        self,
        documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Batch index multiple documents.
        
        Args:
            documents: List of dicts with 'id', 'content', and 'metadata'
            
        Returns:
            Dict with success/failure counts and details
        """
        try:
            points = []
            success_count = 0
            failure_count = 0
            errors = []
            
            for doc in documents:
                try:
                    doc_id = doc['id']
                    content = doc['content']
                    metadata = doc.get('metadata', {})
                    
                    if not content or not content.strip():
                        logger.warning(f"⚠️ Skipping empty content for {doc_id}")
                        continue
                    
                    # Generate embedding
                    vector = self.model.encode(content).tolist()
                    
                    # Prepare payload
                    payload = metadata.copy()
                    payload['document_id'] = doc_id
                    payload['content_preview'] = content[:500]
                    
                    # Create point
                    point = PointStruct(
                        id=doc_id,
                        vector=vector,
                        payload=payload
                    )
                    points.append(point)
                    success_count += 1
                    
                except Exception as e:
                    failure_count += 1
                    errors.append({'id': doc.get('id', 'unknown'), 'error': str(e)})
                    logger.error(f"❌ Failed to prepare document for indexing: {e}")
            
            # Batch upsert
            if points:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
                logger.info(f"✅ Batch indexed {len(points)} documents in Qdrant")
            
            return {
                'success': success_count,
                'failed': failure_count,
                'errors': errors
            }
            
        except Exception as e:
            logger.error(f"❌ Batch indexing failed: {e}")
            raise
    
    def vector_search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        score_threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents using vector similarity.
        
        Args:
            query: Search query text
            limit: Maximum number of results
            filters: Optional filters (tenant_id, document_set_id, etc.)
            score_threshold: Minimum similarity score (0.0-1.0)
            
        Returns:
            List of search results with scores and metadata
        """
        try:
            # Generate query vector
            query_vector = self.model.encode(query).tolist()
            
            # Build filter
            qdrant_filter = None
            if filters:
                conditions = []
                for key, value in filters.items():
                    conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value)
                        )
                    )
                if conditions:
                    qdrant_filter = Filter(must=conditions)
            
            # Search
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                query_filter=qdrant_filter,
                score_threshold=score_threshold
            )
            
            # Format results
            formatted_results = []
            for hit in results:
                formatted_results.append({
                    'id': str(hit.id),
                    'score': float(hit.score),
                    'payload': hit.payload,
                    'document_id': hit.payload.get('document_id')
                })
            
            logger.info(f"✅ Qdrant search returned {len(formatted_results)} results")
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ Qdrant search failed: {e}")
            raise
    
    def delete_document(self, document_id: str) -> bool:
        """
        Delete a document from Qdrant.
        
        Args:
            document_id: Document UUID to delete
            
        Returns:
            True if successful
        """
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=[document_id]
            )
            logger.info(f"✅ Deleted document from Qdrant: {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to delete document {document_id}: {e}")
            return False
    
    def document_exists(self, document_id: str) -> bool:
        """
        Check if a document exists in Qdrant.
        
        Args:
            document_id: Document UUID
            
        Returns:
            True if document exists, False otherwise
        """
        try:
            result = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[document_id]
            )
            return len(result) > 0
        except Exception as e:
            logger.error(f"❌ Failed to check document existence {document_id}: {e}")
            return False
    
    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a document by ID.
        
        Args:
            document_id: Document UUID
            
        Returns:
            Document data or None if not found
        """
        try:
            result = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[document_id]
            )
            
            if result:
                point = result[0]
                return {
                    'id': str(point.id),
                    'payload': point.payload
                }
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to retrieve document {document_id}: {e}")
            return None
    
    def collection_info(self) -> Dict[str, Any]:
        """Get collection statistics and info."""
        self._ensure_collection()  # Lazy initialization
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                'name': self.collection_name,
                'vectors_count': info.vectors_count,
                'points_count': info.points_count,
                'status': info.status.value,
                'config': {
                    'vector_size': self.vector_size,
                    'distance': self.distance.value
                }
            }
        except Exception as e:
            logger.error(f"❌ Failed to get collection info: {e}")
            return {}
    
    def health_check(self) -> bool:
        """Check if Qdrant service is healthy."""
        try:
            # Try to get collections
            self.client.get_collections()
            return True
        except Exception as e:
            logger.error(f"❌ Qdrant health check failed: {e}")
            return False


# Shared app-level instance. Sharing this also avoids reloading the
# sentence-transformers embedding model on every instantiation, which is
# expensive on top of the connection cost. Celery tasks intentionally bypass
# this and construct their own QdrantService per task instead - each task is
# a discrete unit of work in its own worker process, not a request in a
# long-running server, so there's no equivalent leak there.
_qdrant_service: Optional["QdrantService"] = None


def get_qdrant_service() -> "QdrantService":
    """Get the shared Qdrant client, creating it on first use"""
    global _qdrant_service
    if _qdrant_service is None:
        _qdrant_service = QdrantService()
    return _qdrant_service


def close_qdrant_service() -> None:
    """Close the shared Qdrant client (call on application shutdown)"""
    global _qdrant_service
    if _qdrant_service is not None:
        _qdrant_service.client.close()
        _qdrant_service = None

