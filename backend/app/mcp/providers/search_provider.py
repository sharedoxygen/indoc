"""
Search Provider for MCP - Handles hybrid search operations
"""
from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime

from app.services.search.elasticsearch_service import ElasticsearchService
from app.services.search.weaviate_service import WeaviateService
from app.services.search.reranker import Reranker
from app.services.search.query_transformer import QueryTransformer
from app.core.config import settings


class SearchProvider:
    """Provider for search-related tools"""
    
    def __init__(self):
        self.es_service = ElasticsearchService()
        self.weaviate_service = WeaviateService()
        self.reranker = Reranker()
        self.query_transformer = QueryTransformer()
    
    async def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Perform hybrid search across Elasticsearch and Weaviate
        
        Args:
            query: Search query
            filters: Optional filters (file_type, date_range, tags, etc.)
            limit: Maximum number of results
            context: Optional context (user info, etc.)
        
        Returns:
            Search results with relevance scores
        """
        start_time = datetime.utcnow()
        
        # Transform query for better retrieval
        transformed_queries = await self.query_transformer.transform(query)
        
        # Ensure tenant scoping
        effective_filters = filters.copy() if filters else {}
        tenant_id = None
        if context and isinstance(context, dict):
            tenant_id = context.get("user", {}).get("tenant_id") or context.get("tenant_id")
        if tenant_id:
            effective_filters["tenant_id"] = tenant_id

        # Execute searches in parallel
        search_tasks = []
        
        # Elasticsearch keyword search
        for q in transformed_queries.get("keyword_queries", [query]):
            search_tasks.append(
                self.es_service.search(q, limit * 2, effective_filters)
            )
        
        # Weaviate vector search
        for q in transformed_queries.get("semantic_queries", [query]):
            search_tasks.append(
                self.weaviate_service.vector_search(q, limit * 2, effective_filters)
            )
        
        # Wait for all searches to complete
        search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        # Merge and deduplicate results
        merged_results = self._merge_results(search_results)
        
        # Re-rank results
        if merged_results:
            reranked = await self.reranker.rerank(query, merged_results[:limit * 2])
            final_results = reranked[:limit]
        else:
            final_results = []
        
        # Calculate execution time
        execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return {
            "query": query,
            "transformed_queries": transformed_queries,
            "results": final_results,
            "total_results": len(final_results),
            "execution_time_ms": execution_time,
            "filters": effective_filters
        }
    
    async def rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Re-rank search results for better relevance
        
        Args:
            query: Original search query
            results: List of search results to re-rank
            context: Optional context
        
        Returns:
            Re-ranked results
        """
        return await self.reranker.rerank(query, results)
    
    async def get_similar_documents(
        self,
        document_id: str,
        limit: int = 5,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find documents similar to a given document
        
        Args:
            document_id: ID of the reference document
            limit: Maximum number of similar documents
            context: Optional context
        
        Returns:
            List of similar documents
        """
        # Get document embedding from Weaviate
        document = await self.weaviate_service.get_document(document_id)
        if not document:
            return []
        
        # Search for similar documents
        similar = await self.weaviate_service.search_by_vector(
            document.get("embedding"),
            limit=limit + 1  # +1 to exclude the source document
        )
        
        # Filter out the source document
        return [doc for doc in similar if doc["id"] != document_id][:limit]
    
    async def extract_keywords(
        self,
        text: str,
        max_keywords: int = 10,
        context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Extract keywords from text
        
        Args:
            text: Text to extract keywords from
            max_keywords: Maximum number of keywords
            context: Optional context
        
        Returns:
            List of extracted keywords
        """
        return await self.query_transformer.extract_keywords(text, max_keywords)
    
    def _merge_results(
        self,
        search_results: List[Any]
    ) -> List[Dict[str, Any]]:
        """
        Merge and deduplicate search results from multiple sources
        
        Args:
            search_results: List of search results from different sources
        
        Returns:
            Merged and deduplicated results
        """
        merged = {}
        
        for result_set in search_results:
            if isinstance(result_set, Exception):
                continue  # Skip failed searches
            
            # Handle list of results from search services
            if isinstance(result_set, list):
                for result in result_set:
                    if isinstance(result, dict) and result.get("id"):
                        doc_id = result["id"]
                        # Keep highest score for each document
                        if doc_id not in merged or result.get("score", 0) > merged[doc_id].get("score", 0):
                            merged[doc_id] = result
                continue
            
            if not isinstance(result_set, dict):
                continue
            
            for doc in result_set.get("results", []):
                doc_id = doc.get("id")
                if doc_id not in merged:
                    merged[doc_id] = doc
                else:
                    # Merge scores and metadata
                    existing = merged[doc_id]
                    existing["score"] = max(
                        existing.get("score", 0),
                        doc.get("score", 0)
                    )
                    
                    # Merge provenance information
                    if "provenance" not in existing:
                        existing["provenance"] = []
                    if "provenance" in doc:
                        existing["provenance"].extend(doc["provenance"])
        
        # Sort by score
        sorted_results = sorted(
            merged.values(),
            key=lambda x: x.get("score", 0),
            reverse=True
        )
        
        return sorted_results