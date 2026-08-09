"""
Document Relationship Analysis and Citation Tracking
Helps understand how documents relate to each other
"""
import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from uuid import UUID
from datetime import datetime
from dataclasses import dataclass
import re
from collections import defaultdict, Counter
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.document import Document
from app.services.search_service import SearchService

logger = logging.getLogger(__name__)


@dataclass
class DocumentCitation:
    """Represents a citation or reference between documents"""
    source_document_id: UUID
    target_document_id: UUID
    citation_type: str  # "reference", "quote", "similarity", "topic_overlap"
    confidence: float  # 0.0 to 1.0
    context: str
    location: Dict[str, Any]  # page, paragraph, line, etc.
    detected_at: datetime


@dataclass
class DocumentRelationship:
    """Represents a relationship between two documents"""
    document_a_id: UUID
    document_b_id: UUID
    relationship_type: str  # "cites", "similar_to", "part_of", "related_to", "contradicts"
    strength: float  # 0.0 to 1.0
    description: str
    evidence: List[str]  # Supporting evidence for the relationship


class DocumentRelationshipAnalyzer:
    """Analyze and track relationships between documents"""
    
    def __init__(self, db: Session):
        self.db = db
        self.search_service = SearchService(db)
        self.citation_patterns = self._initialize_citation_patterns()
    
    def _initialize_citation_patterns(self) -> List[Dict[str, Any]]:
        """Initialize patterns for detecting citations and references"""
        return [
            # Direct document references
            {
                "name": "document_reference",
                "pattern": r'(?:document|doc|file|report)\s+([A-Z0-9_-]+\.(?:pdf|docx?|txt))',
                "type": "reference",
                "confidence": 0.9
            },
            
            # Page references
            {
                "name": "page_reference", 
                "pattern": r'(?:page|p\.)\s+(\d+)',
                "type": "reference",
                "confidence": 0.7
            },
            
            # Section references
            {
                "name": "section_reference",
                "pattern": r'(?:section|chapter|part)\s+(\d+(?:\.\d+)*)',
                "type": "reference", 
                "confidence": 0.8
            },
            
            # Quote patterns
            {
                "name": "direct_quote",
                "pattern": r'"([^"]{20,200})"',
                "type": "quote",
                "confidence": 0.85
            },
            
            # According to patterns
            {
                "name": "attribution",
                "pattern": r'(?:according to|as stated in|per the|based on)\s+([^,.]{10,100})',
                "type": "reference",
                "confidence": 0.75
            },
            
            # Date references that might link documents
            {
                "name": "date_reference",
                "pattern": r'(?:dated|from|on)\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                "type": "temporal",
                "confidence": 0.6
            }
        ]
    
    async def analyze_document_relationships(self, document_id: UUID) -> Dict[str, Any]:
        """Analyze relationships for a specific document"""
        
        # Get the document
        document = self.db.query(Document).filter(Document.uuid == document_id).first()
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        logger.info(f"Analyzing relationships for document: {document.filename}")
        
        # Get document content (this would come from the stored chunks)
        content = await self._get_document_content(document_id)
        
        # Find citations within the document
        citations = self._extract_citations(content, document_id)
        
        # Find similar documents
        similar_docs = await self._find_similar_documents(document_id, content)
        
        # Find documents with overlapping topics
        topic_related = await self._find_topic_related_documents(document_id)
        
        # Build relationships
        relationships = []
        
        # Process citations
        for citation in citations:
            target_doc = await self._resolve_citation_target(citation)
            if target_doc:
                relationships.append(DocumentRelationship(
                    document_a_id=document_id,
                    document_b_id=target_doc,
                    relationship_type="cites",
                    strength=citation.confidence,
                    description=f"Document cites {citation.context}",
                    evidence=[citation.context]
                ))
        
        # Process similarities
        for sim_doc, similarity_score in similar_docs:
            if similarity_score > 0.7:
                relationships.append(DocumentRelationship(
                    document_a_id=document_id,
                    document_b_id=sim_doc,
                    relationship_type="similar_to",
                    strength=similarity_score,
                    description=f"Documents are {similarity_score:.1%} similar",
                    evidence=[f"Content similarity score: {similarity_score:.3f}"]
                ))
        
        # Process topic relationships
        for topic_doc, topic_overlap in topic_related:
            if topic_overlap > 0.5:
                relationships.append(DocumentRelationship(
                    document_a_id=document_id,
                    document_b_id=topic_doc,
                    relationship_type="related_to",
                    strength=topic_overlap,
                    description=f"Documents share common topics",
                    evidence=[f"Topic overlap score: {topic_overlap:.3f}"]
                ))
        
        return {
            "document_id": str(document_id),
            "filename": document.filename,
            "analysis_timestamp": datetime.utcnow().isoformat(),
            "relationships": [self._relationship_to_dict(r) for r in relationships],
            "citations_found": len(citations),
            "similar_documents": len([r for r in relationships if r.relationship_type == "similar_to"]),
            "related_documents": len([r for r in relationships if r.relationship_type == "related_to"]),
            "total_relationships": len(relationships)
        }
    
    def _extract_citations(self, content: str, document_id: UUID) -> List[DocumentCitation]:
        """Extract citations from document content"""
        citations = []
        
        for pattern_config in self.citation_patterns:
            pattern = pattern_config["pattern"]
            matches = re.finditer(pattern, content, re.IGNORECASE)
            
            for match in matches:
                citation = DocumentCitation(
                    source_document_id=document_id,
                    target_document_id=None,  # Will be resolved later
                    citation_type=pattern_config["type"],
                    confidence=pattern_config["confidence"],
                    context=match.group(),
                    location={
                        "start": match.start(),
                        "end": match.end(),
                        "line": content[:match.start()].count('\n') + 1
                    },
                    detected_at=datetime.utcnow()
                )
                citations.append(citation)
        
        return citations
    
    async def _find_similar_documents(self, document_id: UUID, content: str) -> List[Tuple[UUID, float]]:
        """Find documents similar to the given document"""
        try:
            # Use search service to find similar content
            # Take a sample of the content for similarity search
            content_sample = content[:2000] if len(content) > 2000 else content
            
            search_results = await self.search_service.semantic_search(
                query=content_sample,
                limit=10,
                filters={"exclude_document_id": str(document_id)}
            )
            
            similar_docs = []
            for result in search_results.get("results", []):
                similarity_score = result.get("score", 0.0)
                doc_id = UUID(result.get("document_id"))
                similar_docs.append((doc_id, similarity_score))
            
            return similar_docs
        
        except Exception as e:
            logger.warning(f"Error finding similar documents: {e}")
            return []
    
    async def _find_topic_related_documents(self, document_id: UUID) -> List[Tuple[UUID, float]]:
        """Find documents related by topic/keywords"""
        try:
            # Get document keywords/topics
            document = self.db.query(Document).filter(Document.uuid == document_id).first()
            if not document or not document.metadata:
                return []
            
            # Extract topics/keywords from metadata
            topics = document.metadata.get("topics", [])
            keywords = document.metadata.get("keywords", [])
            
            if not topics and not keywords:
                return []
            
            # Find other documents with similar topics
            related_docs = []
            
            # Query for documents with overlapping topics
            all_terms = topics + keywords
            for term in all_terms[:5]:  # Limit to top 5 terms
                search_results = await self.search_service.hybrid_search(
                    query=term,
                    limit=5,
                    filters={"exclude_document_id": str(document_id)}
                )
                
                for result in search_results.get("results", []):
                    doc_id = UUID(result.get("document_id"))
                    score = result.get("score", 0.0)
                    related_docs.append((doc_id, score))
            
            # Deduplicate and sort
            doc_scores = defaultdict(list)
            for doc_id, score in related_docs:
                doc_scores[doc_id].append(score)
            
            # Average scores for documents found multiple times
            final_scores = []
            for doc_id, scores in doc_scores.items():
                avg_score = sum(scores) / len(scores)
                final_scores.append((doc_id, avg_score))
            
            return sorted(final_scores, key=lambda x: x[1], reverse=True)[:10]
        
        except Exception as e:
            logger.warning(f"Error finding topic-related documents: {e}")
            return []
    
    async def _resolve_citation_target(self, citation: DocumentCitation) -> Optional[UUID]:
        """Try to resolve a citation to an actual document"""
        
        # Extract potential filename from citation context
        potential_filenames = re.findall(r'([A-Z0-9_-]+\.(?:pdf|docx?|txt))', citation.context, re.IGNORECASE)
        
        for filename in potential_filenames:
            # Look for document with similar filename
            doc = self.db.query(Document).filter(
                Document.filename.ilike(f"%{filename}%")
            ).first()
            
            if doc:
                return doc.uuid
        
        return None
    
    async def _get_document_content(self, document_id: UUID) -> str:
        """Get the full content of a document (from chunks)"""
        
        # This would typically get content from document chunks
        # For now, return a placeholder
        try:
            # In a real implementation, you'd query the DocumentChunk table
            # and concatenate all chunks for this document
            
            query = text("""
                SELECT content 
                FROM document_chunks 
                WHERE document_id = :document_id 
                ORDER BY chunk_index
            """)
            
            result = self.db.execute(query, {"document_id": str(document_id)})
            chunks = result.fetchall()
            
            if chunks:
                return "\n".join([chunk[0] for chunk in chunks])
            else:
                # Fallback: get from document metadata if available
                document = self.db.query(Document).filter(Document.uuid == document_id).first()
                if document and document.metadata:
                    return document.metadata.get("extracted_text", "")
                return ""
        
        except Exception as e:
            logger.warning(f"Error getting document content: {e}")
            return ""
    
    def _relationship_to_dict(self, relationship: DocumentRelationship) -> Dict[str, Any]:
        """Convert DocumentRelationship to dictionary"""
        return {
            "document_a_id": str(relationship.document_a_id),
            "document_b_id": str(relationship.document_b_id),
            "relationship_type": relationship.relationship_type,
            "strength": relationship.strength,
            "description": relationship.description,
            "evidence": relationship.evidence
        }
    
    async def get_document_network(self, document_ids: List[UUID]) -> Dict[str, Any]:
        """Get the relationship network for a set of documents"""
        
        network = {
            "nodes": [],
            "edges": [],
            "statistics": {}
        }
        
        # Analyze relationships for each document
        all_relationships = []
        for doc_id in document_ids:
            try:
                analysis = await self.analyze_document_relationships(doc_id)
                all_relationships.extend(analysis["relationships"])
                
                # Add node
                document = self.db.query(Document).filter(Document.uuid == doc_id).first()
                if document:
                    network["nodes"].append({
                        "id": str(doc_id),
                        "filename": document.filename,
                        "file_type": document.file_type,
                        "created_at": document.created_at.isoformat() if document.created_at else None
                    })
            
            except Exception as e:
                logger.error(f"Error analyzing document {doc_id}: {e}")
        
        # Process relationships into edges
        seen_edges = set()
        for rel in all_relationships:
            edge_key = f"{rel['document_a_id']}-{rel['document_b_id']}"
            reverse_key = f"{rel['document_b_id']}-{rel['document_a_id']}"
            
            if edge_key not in seen_edges and reverse_key not in seen_edges:
                network["edges"].append({
                    "source": rel["document_a_id"],
                    "target": rel["document_b_id"],
                    "type": rel["relationship_type"],
                    "strength": rel["strength"],
                    "description": rel["description"]
                })
                seen_edges.add(edge_key)
        
        # Calculate statistics
        network["statistics"] = {
            "total_documents": len(network["nodes"]),
            "total_relationships": len(network["edges"]),
            "relationship_types": dict(Counter([e["type"] for e in network["edges"]])),
            "average_strength": sum([e["strength"] for e in network["edges"]]) / len(network["edges"]) if network["edges"] else 0,
            "analysis_timestamp": datetime.utcnow().isoformat()
        }
        
        return network
    
    async def find_citation_path(self, source_doc: UUID, target_doc: UUID) -> Optional[List[UUID]]:
        """Find a citation path between two documents"""
        
        # This would implement a graph traversal algorithm
        # to find how documents are connected through citations
        
        # For now, return a simple direct connection check
        source_analysis = await self.analyze_document_relationships(source_doc)
        
        for rel in source_analysis["relationships"]:
            if rel["document_b_id"] == str(target_doc):
                return [source_doc, target_doc]
        
        return None
