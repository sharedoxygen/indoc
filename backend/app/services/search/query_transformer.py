"""
Query transformation service for improving search queries
"""
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class QueryTransformer:
    """Transform and enhance search queries"""
    
    def __init__(self):
        self.synonyms = {
            "document": ["doc", "file", "paper"],
            "create": ["make", "build", "generate"],
            "delete": ["remove", "erase", "destroy"],
            "update": ["modify", "change", "edit"],
            "search": ["find", "look for", "query"],
        }
    
    async def transform(self, query: str) -> Dict[str, Any]:
        """
        Transform a natural language query into structured search parameters
        
        Args:
            query: Natural language search query
            
        Returns:
            Dictionary with transformed query parameters
        """
        try:
            # Basic transformation - can be enhanced with NLP
            transformed = {
                "keyword_queries": [query],  # For Elasticsearch
                "semantic_queries": [query], # For Weaviate
                "original_query": query,
                "expanded_query": self._expand_with_synonyms(query),
                "keywords": self._extract_keywords(query),
                "filters": self._extract_filters(query)
            }
            
            logger.info(f"Transformed query: {query} -> {transformed}")
            return transformed
            
        except Exception as e:
            logger.error(f"Error transforming query: {e}")
            return {
                "keyword_queries": [query],  # For Elasticsearch
                "semantic_queries": [query], # For Weaviate
                "original_query": query,
                "expanded_query": query,
                "keywords": [query],
                "filters": {}
            }
    
    def _expand_with_synonyms(self, query: str) -> str:
        """Expand query with synonyms"""
        words = query.lower().split()
        expanded_words = []
        
        for word in words:
            expanded_words.append(word)
            # Add synonyms if found
            for key, synonyms in self.synonyms.items():
                if word == key:
                    expanded_words.extend(synonyms[:2])  # Add first 2 synonyms
                elif word in synonyms:
                    expanded_words.append(key)
        
        return " ".join(expanded_words)
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract keywords from query"""
        # Simple keyword extraction - can be enhanced with NLP
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for"}
        words = query.lower().split()
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        return keywords
    
    def _extract_filters(self, query: str) -> Dict[str, Any]:
        """Extract filters from query"""
        filters = {}
        
        # Extract file type filters
        if "pdf" in query.lower():
            filters["file_type"] = "pdf"
        elif "doc" in query.lower() or "word" in query.lower():
            filters["file_type"] = "docx"
        elif "excel" in query.lower() or "spreadsheet" in query.lower():
            filters["file_type"] = "xlsx"
        
        # Extract date filters (simple pattern matching)
        if "today" in query.lower():
            filters["date_range"] = "today"
        elif "yesterday" in query.lower():
            filters["date_range"] = "yesterday"
        elif "this week" in query.lower():
            filters["date_range"] = "week"
        elif "this month" in query.lower():
            filters["date_range"] = "month"
        
        return filters
    
    async def suggest_queries(self, partial_query: str) -> List[str]:
        """
        Suggest query completions based on partial input
        
        Args:
            partial_query: Partial search query
            
        Returns:
            List of suggested query completions
        """
        # Simple suggestion system - can be enhanced with ML
        common_queries = [
            "find all pdf documents",
            "search for contracts",
            "show recent uploads",
            "find documents by author",
            "search in file contents",
            "find documents from last week",
            "show all excel files",
            "search for invoices"
        ]
        
        suggestions = [q for q in common_queries if q.startswith(partial_query.lower())]
        return suggestions[:5]  # Return top 5 suggestions