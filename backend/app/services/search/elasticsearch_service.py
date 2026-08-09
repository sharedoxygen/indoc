"""
Elasticsearch service for keyword search
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from elasticsearch import AsyncElasticsearch
from app.core.config import settings

logger = logging.getLogger(__name__)


class ElasticsearchService:
    """Service for Elasticsearch keyword search operations"""
    
    def __init__(self):
        self.client = AsyncElasticsearch([settings.ELASTICSEARCH_URL])
        self.index_name = settings.ELASTICSEARCH_INDEX
    
    async def search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search documents in Elasticsearch using keyword matching
        
        Args:
            query: Search query
            limit: Maximum number of results
            filters: Optional filters (file_type, date_range, etc.)
            
        Returns:
            List of search results with relevance scores
        """
        try:
            # Build Elasticsearch query
            must_clauses = []
            
            # Main text search across multiple fields
            must_clauses.append({
                "multi_match": {
                    "query": query,
                    "fields": [
                        "filename^3",      # Boost filename matches
                        "title^2",         # Boost title matches  
                        "content^1",       # Standard content matches
                        "description^1.5", # Boost description matches
                        "tags^2"          # Boost tag matches
                    ],
                    "type": "best_fields",
                    "fuzziness": "AUTO"
                }
            })
            
            # Add filters
            filter_clauses = []
            if filters:
                if filters.get("file_type"):
                    filter_clauses.append({
                        "terms": {"file_type": filters["file_type"]}
                    })
                
                if filters.get("date_range"):
                    date_range = filters["date_range"]
                    range_filter = {"range": {"created_at": {}}}
                    if date_range.get("start"):
                        range_filter["range"]["created_at"]["gte"] = date_range["start"]
                    if date_range.get("end"):
                        range_filter["range"]["created_at"]["lte"] = date_range["end"]
                    filter_clauses.append(range_filter)
                
                if filters.get("tags"):
                    filter_clauses.append({
                        "terms": {"tags": filters["tags"]}
                    })
                
                if filters.get("uploaded_by"):
                    filter_clauses.append({
                        "term": {"uploaded_by": filters["uploaded_by"]}
                    })
                if filters.get("tenant_id"):
                    filter_clauses.append({
                        "term": {"tenant_id": filters["tenant_id"]}
                    })
            
            # Build complete query
            es_query = {
                "query": {
                    "bool": {
                        "must": must_clauses,
                        "filter": filter_clauses
                    }
                },
                "highlight": {
                    "fields": {
                        "content": {"fragment_size": 150, "number_of_fragments": 3},
                        "title": {},
                        "description": {}
                    }
                },
                "sort": [
                    {"_score": {"order": "desc"}},
                    {"created_at": {"order": "desc"}}
                ],
                "size": limit
            }
            
            # Execute search
            response = await self.client.search(
                index=self.index_name,
                body=es_query
            )
            
            # Process results
            results = []
            for hit in response["hits"]["hits"]:
                source = hit["_source"]
                highlights = hit.get("highlight", {})
                
                # Build snippet from highlights or content
                snippet = ""
                if highlights.get("content"):
                    snippet = "...".join(highlights["content"])
                elif highlights.get("description"):
                    snippet = highlights["description"][0]
                else:
                    snippet = source.get("description", "")[:200] + "..."
                
                result = {
                    "id": source["document_id"],
                    "filename": source["filename"],
                    "title": source.get("title", source["filename"]),
                    "snippet": snippet,
                    "score": hit["_score"],
                    "file_type": source["file_type"],
                    "tags": source.get("tags", []),
                    "tenant_id": source.get("tenant_id", ""),
                    "created_at": source["created_at"],
                    "uploaded_by": source.get("uploaded_by", ""),
                    "search_type": "keyword"
                }
                results.append(result)
            
            logger.info(f"Elasticsearch found {len(results)} results for: {query[:50]}")
            return results
            
        except Exception as e:
            logger.error(f"Elasticsearch search error: {str(e)}")
            return []
    
    async def index_document(
        self,
        document_id: str,
        content: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Index a document in Elasticsearch for keyword search
        
        Args:
            document_id: Document ID
            content: Document content
            metadata: Document metadata (filename, title, file_type, etc.)
            
        Returns:
            Success status
        """
        try:
            # Prepare document for indexing
            doc_body = {
                "document_id": document_id,
                "filename": metadata.get("filename", ""),
                "title": metadata.get("title", ""),
                "content": content,
                "description": metadata.get("description", ""),
                "file_type": metadata.get("file_type", ""),
                "tags": metadata.get("tags", []),
                "uploaded_by": metadata.get("uploaded_by", ""),
                "tenant_id": metadata.get("tenant_id", ""),
                "folder_path": metadata.get("folder_path", None),
                "created_at": metadata.get("created_at") or datetime.utcnow().isoformat(),
                "updated_at": metadata.get("updated_at") or metadata.get("created_at") or datetime.utcnow().isoformat(),
                "file_size": metadata.get("file_size", 0),
                "indexed_at": datetime.utcnow().isoformat()
            }
            
            # Index the document
            await self.client.index(
                index=self.index_name,
                id=document_id,
                body=doc_body
            )
            
            logger.info(f"Document indexed in Elasticsearch: {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Elasticsearch indexing error: {str(e)}")
            return False
    
    async def ensure_index_exists(self) -> bool:
        """
        Ensure the Elasticsearch index exists with proper mapping
        """
        try:
            # Check if index exists
            if await self.client.indices.exists(index=self.index_name):
                return True
            
            # Create index with mapping
            mapping = {
                "mappings": {
                    "properties": {
                        "document_id": {"type": "keyword"},
                        "filename": {"type": "text", "analyzer": "standard"},
                        "title": {"type": "text", "analyzer": "standard"},
                        "content": {"type": "text", "analyzer": "standard"},
                        "description": {"type": "text", "analyzer": "standard"},
                        "file_type": {"type": "keyword"},
                        "tags": {"type": "keyword"},
                        "uploaded_by": {"type": "keyword"},
                        "tenant_id": {"type": "keyword"},
                        "folder_path": {"type": "keyword"},
                        "created_at": {"type": "date"},
                        "updated_at": {"type": "date"},
                        "file_size": {"type": "long"},
                        "indexed_at": {"type": "date"}
                    }
                }
            }
            
            await self.client.indices.create(
                index=self.index_name,
                body=mapping
            )
            
            logger.info(f"Created Elasticsearch index: {self.index_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating Elasticsearch index: {str(e)}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Elasticsearch cluster health"""
        try:
            health = await self.client.cluster.health()
            return {
                "status": "healthy",
                "cluster_status": health["status"],
                "number_of_nodes": health["number_of_nodes"],
                "active_shards": health["active_primary_shards"]
            }
        except Exception as e:
            logger.error(f"Elasticsearch health check failed: {str(e)}")
            return {"status": "unhealthy", "error": str(e)}