"""
Document Analysis Provider for MCP
Provides intelligent document analysis tools for AI conversations
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
import json
import statistics
from collections import Counter, defaultdict

from app.models.document import Document, DocumentChunk
from app.models.conversation import Conversation, Message
from app.services.document_relationships import DocumentRelationshipAnalyzer
from app.core.compliance import compliance_manager, ComplianceMode
from app.services.search_service import SearchService

logger = logging.getLogger(__name__)


class DocumentAnalysisProvider:
    """Provides intelligent document analysis tools for MCP"""
    
    def __init__(self, db: Session):
        self.db = db
        self.search_service = SearchService(db)
        self.relationship_analyzer = DocumentRelationshipAnalyzer(db)
    
    async def analyze_document_insights(
        self,
        document_ids: List[str],
        analysis_type: str = "comprehensive",
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extract key insights from one or more documents
        
        Tool: document_insights
        Description: Analyze documents to extract key themes, insights, and patterns
        """
        
        try:
            doc_uuids = [UUID(doc_id) for doc_id in document_ids]
            documents = self.db.query(Document).filter(Document.uuid.in_(doc_uuids)).all()
            
            if not documents:
                return {"error": "No documents found with provided IDs"}
            
            insights = {
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "documents_analyzed": len(documents),
                "analysis_type": analysis_type,
                "insights": {}
            }
            
            # Document metadata analysis
            file_types = Counter([doc.file_type for doc in documents])
            total_size = sum([doc.file_size for doc in documents])
            creation_dates = [doc.created_at for doc in documents if doc.created_at]
            
            insights["insights"]["overview"] = {
                "total_documents": len(documents),
                "file_types": dict(file_types),
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "date_range": {
                    "earliest": min(creation_dates).isoformat() if creation_dates else None,
                    "latest": max(creation_dates).isoformat() if creation_dates else None
                }
            }
            
            # Content analysis
            all_content = []
            for doc in documents:
                # Get document content from chunks
                chunks = self.db.query(DocumentChunk).filter(
                    DocumentChunk.document_id == doc.id
                ).all()
                
                doc_content = " ".join([chunk.content for chunk in chunks])
                all_content.append({
                    "document_id": str(doc.uuid),
                    "filename": doc.filename,
                    "content": doc_content,
                    "word_count": len(doc_content.split()),
                    "char_count": len(doc_content)
                })
            
            insights["insights"]["content_analysis"] = {
                "documents": all_content,
                "total_words": sum([doc["word_count"] for doc in all_content]),
                "average_words_per_doc": statistics.mean([doc["word_count"] for doc in all_content]) if all_content else 0
            }
            
            # Relationship analysis if multiple documents
            if len(documents) > 1:
                relationship_insights = await self._analyze_document_relationships(doc_uuids)
                insights["insights"]["relationships"] = relationship_insights
            
            # Compliance analysis
            if compliance_manager.current_mode != ComplianceMode.STANDARD:
                compliance_insights = await self._analyze_compliance_issues(all_content)
                insights["insights"]["compliance"] = compliance_insights
            
            # Key themes and topics (basic implementation)
            theme_insights = self._extract_themes(all_content)
            insights["insights"]["themes"] = theme_insights
            
            return insights
            
        except Exception as e:
            logger.error(f"Error in document insights analysis: {e}")
            return {"error": f"Analysis failed: {str(e)}"}
    
    async def compare_documents(
        self,
        document_ids: List[str],
        comparison_criteria: List[str] = ["content", "themes", "dates"],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Compare multiple documents across various criteria
        
        Tool: compare_documents  
        Description: Compare documents to find similarities, differences, and patterns
        """
        
        if len(document_ids) < 2:
            return {"error": "At least 2 documents required for comparison"}
        
        try:
            doc_uuids = [UUID(doc_id) for doc_id in document_ids]
            documents = self.db.query(Document).filter(Document.uuid.in_(doc_uuids)).all()
            
            comparison_result = {
                "comparison_timestamp": datetime.utcnow().isoformat(),
                "documents_compared": len(documents),
                "criteria": comparison_criteria,
                "results": {}
            }
            
            # Content comparison
            if "content" in comparison_criteria:
                content_comparison = await self._compare_document_content(documents)
                comparison_result["results"]["content"] = content_comparison
            
            # Metadata comparison  
            if "metadata" in comparison_criteria:
                metadata_comparison = self._compare_document_metadata(documents)
                comparison_result["results"]["metadata"] = metadata_comparison
            
            # Date/timeline comparison
            if "dates" in comparison_criteria:
                date_comparison = self._compare_document_dates(documents)
                comparison_result["results"]["dates"] = date_comparison
            
            # Themes comparison
            if "themes" in comparison_criteria:
                theme_comparison = await self._compare_document_themes(documents)
                comparison_result["results"]["themes"] = theme_comparison
            
            return comparison_result
            
        except Exception as e:
            logger.error(f"Error in document comparison: {e}")
            return {"error": f"Comparison failed: {str(e)}"}
    
    async def generate_document_summary(
        self,
        document_ids: List[str],
        summary_type: str = "executive",
        length: str = "medium",
        focus_areas: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate intelligent summaries of documents
        
        Tool: document_summary
        Description: Create executive summaries, detailed analysis, or focused summaries
        """
        
        try:
            doc_uuids = [UUID(doc_id) for doc_id in document_ids]
            documents = self.db.query(Document).filter(Document.uuid.in_(doc_uuids)).all()
            
            summary_result = {
                "summary_timestamp": datetime.utcnow().isoformat(),
                "documents_summarized": len(documents),
                "summary_type": summary_type,
                "length": length,
                "focus_areas": focus_areas or [],
                "summaries": {}
            }
            
            # Generate individual document summaries
            individual_summaries = []
            for doc in documents:
                chunks = self.db.query(DocumentChunk).filter(
                    DocumentChunk.document_id == doc.id
                ).all()
                
                content = " ".join([chunk.content for chunk in chunks])
                
                # Basic summary generation (would integrate with LLM in full implementation)
                doc_summary = {
                    "document_id": str(doc.uuid),
                    "filename": doc.filename,
                    "key_points": self._extract_key_points(content, focus_areas),
                    "word_count": len(content.split()),
                    "estimated_read_time": f"{len(content.split()) // 200} minutes"
                }
                
                individual_summaries.append(doc_summary)
            
            summary_result["summaries"]["individual"] = individual_summaries
            
            # Generate combined summary for multiple documents
            if len(documents) > 1:
                combined_summary = self._generate_combined_summary(individual_summaries)
                summary_result["summaries"]["combined"] = combined_summary
            
            return summary_result
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return {"error": f"Summary generation failed: {str(e)}"}
    
    async def detect_document_anomalies(
        self,
        document_ids: List[str],
        anomaly_types: List[str] = ["compliance", "content", "metadata"],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Detect anomalies, inconsistencies, and potential issues in documents
        
        Tool: detect_anomalies
        Description: Find unusual patterns, compliance issues, or content problems
        """
        
        try:
            doc_uuids = [UUID(doc_id) for doc_id in document_ids]
            documents = self.db.query(Document).filter(Document.uuid.in_(doc_uuids)).all()
            
            anomaly_result = {
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "documents_analyzed": len(documents),
                "anomaly_types_checked": anomaly_types,
                "anomalies_found": [],
                "summary": {}
            }
            
            anomalies = []
            
            # Compliance anomalies
            if "compliance" in anomaly_types:
                compliance_anomalies = await self._detect_compliance_anomalies(documents)
                anomalies.extend(compliance_anomalies)
            
            # Content anomalies
            if "content" in anomaly_types:
                content_anomalies = await self._detect_content_anomalies(documents)
                anomalies.extend(content_anomalies)
            
            # Metadata anomalies
            if "metadata" in anomaly_types:
                metadata_anomalies = self._detect_metadata_anomalies(documents)
                anomalies.extend(metadata_anomalies)
            
            # Categorize anomalies by severity
            severity_counts = Counter([a["severity"] for a in anomalies])
            
            anomaly_result["anomalies_found"] = anomalies
            anomaly_result["summary"] = {
                "total_anomalies": len(anomalies),
                "by_severity": dict(severity_counts),
                "recommendations": self._generate_anomaly_recommendations(anomalies)
            }
            
            return anomaly_result
            
        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
            return {"error": f"Anomaly detection failed: {str(e)}"}
    
    async def generate_document_report(
        self,
        document_ids: List[str],
        report_type: str = "analysis",
        include_sections: List[str] = ["overview", "insights", "recommendations"],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive reports about document sets
        
        Tool: document_report
        Description: Create analysis reports, compliance reports, or custom reports
        """
        
        try:
            # Combine multiple analysis functions for comprehensive reporting
            insights = await self.analyze_document_insights(document_ids, "comprehensive")
            
            if len(document_ids) > 1:
                comparison = await self.compare_documents(document_ids)
                anomalies = await self.detect_document_anomalies(document_ids)
            else:
                comparison = {"results": {}}
                anomalies = {"anomalies_found": []}
            
            summary = await self.generate_document_summary(document_ids, "executive")
            
            # Build comprehensive report
            report = {
                "report_timestamp": datetime.utcnow().isoformat(),
                "report_type": report_type,
                "document_ids": document_ids,
                "sections": {}
            }
            
            if "overview" in include_sections:
                report["sections"]["overview"] = {
                    "total_documents": insights["documents_analyzed"],
                    "file_types": insights["insights"]["overview"]["file_types"],
                    "total_size": insights["insights"]["overview"]["total_size_mb"],
                    "analysis_scope": f"Analyzed {len(document_ids)} document(s) for insights and patterns"
                }
            
            if "insights" in include_sections:
                report["sections"]["insights"] = {
                    "key_themes": insights["insights"].get("themes", {}),
                    "content_patterns": summary["summaries"],
                    "relationships": comparison.get("results", {}),
                    "anomalies": anomalies.get("summary", {})
                }
            
            if "recommendations" in include_sections:
                recommendations = []
                
                # Add compliance recommendations
                if anomalies.get("summary", {}).get("total_anomalies", 0) > 0:
                    recommendations.extend(anomalies["summary"].get("recommendations", []))
                
                # Add general recommendations
                if len(document_ids) > 5:
                    recommendations.append("Consider organizing documents into smaller, focused collections")
                
                if any("pdf" in doc["file_type"] for doc in insights["insights"]["content_analysis"]["documents"]):
                    recommendations.append("Ensure PDF text extraction quality is optimal for best AI analysis")
                
                report["sections"]["recommendations"] = recommendations
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating document report: {e}")
            return {"error": f"Report generation failed: {str(e)}"}
    
    # Helper methods
    async def _analyze_document_relationships(self, doc_uuids: List[UUID]) -> Dict[str, Any]:
        """Analyze relationships between documents"""
        try:
            network = await self.relationship_analyzer.get_document_network(doc_uuids)
            return {
                "total_relationships": network["statistics"]["total_relationships"],
                "relationship_types": network["statistics"]["relationship_types"],
                "average_strength": network["statistics"]["average_strength"],
                "most_connected": self._find_most_connected_document(network)
            }
        except Exception as e:
            logger.warning(f"Relationship analysis error: {e}")
            return {"error": "Relationship analysis unavailable"}
    
    async def _analyze_compliance_issues(self, content_list: List[Dict]) -> Dict[str, Any]:
        """Analyze documents for compliance issues"""
        compliance_results = {
            "mode": compliance_manager.current_mode.value,
            "phi_detections": 0,
            "total_redactions": 0,
            "high_risk_documents": []
        }
        
        for doc_content in content_list:
            scan_result = compliance_manager.phi_detector.scan_text(
                doc_content["content"],
                compliance_manager.current_mode
            )
            
            if scan_result["phi_found"]:
                compliance_results["phi_detections"] += 1
                compliance_results["total_redactions"] += len(scan_result["detections"])
                
                if scan_result["high_sensitivity_count"] > 0:
                    compliance_results["high_risk_documents"].append({
                        "document_id": doc_content["document_id"],
                        "filename": doc_content["filename"],
                        "high_sensitivity_items": scan_result["high_sensitivity_count"]
                    })
        
        return compliance_results
    
    def _extract_themes(self, content_list: List[Dict]) -> Dict[str, Any]:
        """Extract key themes from documents (basic implementation)"""
        
        # Simple keyword extraction (would be enhanced with NLP in full implementation)
        all_text = " ".join([doc["content"] for doc in content_list])
        words = all_text.lower().split()
        
        # Filter common words and find frequent terms
        common_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
        meaningful_words = [word for word in words if len(word) > 3 and word not in common_words]
        
        word_freq = Counter(meaningful_words)
        top_themes = word_freq.most_common(10)
        
        return {
            "top_keywords": [{"word": word, "frequency": freq} for word, freq in top_themes],
            "total_unique_words": len(set(meaningful_words)),
            "vocabulary_diversity": len(set(meaningful_words)) / len(meaningful_words) if meaningful_words else 0
        }
    
    def _extract_key_points(self, content: str, focus_areas: Optional[List[str]] = None) -> List[str]:
        """Extract key points from document content"""
        
        # Simple key point extraction (would use advanced NLP in full implementation)
        sentences = content.split('.')
        
        # Look for sentences with key indicator words
        key_indicators = ["important", "critical", "key", "significant", "main", "primary", "conclusion", "result"]
        
        key_points = []
        for sentence in sentences[:20]:  # Limit to first 20 sentences
            if any(indicator in sentence.lower() for indicator in key_indicators):
                cleaned = sentence.strip()
                if len(cleaned) > 20 and len(cleaned) < 200:
                    key_points.append(cleaned)
        
        return key_points[:5]  # Return top 5 key points
    
    def _find_most_connected_document(self, network: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find the document with the most connections in the network"""
        if not network.get("edges"):
            return None
        
        # Count connections per document
        connections = defaultdict(int)
        for edge in network["edges"]:
            connections[edge["source"]] += 1
            connections[edge["target"]] += 1
        
        if not connections:
            return None
        
        most_connected_id = max(connections.keys(), key=lambda x: connections[x])
        
        # Find document info
        for node in network["nodes"]:
            if node["id"] == most_connected_id:
                return {
                    "document_id": most_connected_id,
                    "filename": node["filename"],
                    "connection_count": connections[most_connected_id]
                }
        
        return None
    
    async def _compare_document_content(self, documents: List[Document]) -> Dict[str, Any]:
        """Compare content similarity between documents"""
        
        # Basic similarity calculation (would use embeddings in full implementation)
        content_data = []
        for doc in documents:
            chunks = self.db.query(DocumentChunk).filter(
                DocumentChunk.document_id == doc.id
            ).all()
            
            content = " ".join([chunk.content for chunk in chunks])
            content_data.append({
                "document_id": str(doc.uuid),
                "filename": doc.filename,
                "word_count": len(content.split()),
                "char_count": len(content)
            })
        
        # Calculate basic statistics
        word_counts = [doc["word_count"] for doc in content_data]
        char_counts = [doc["char_count"] for doc in content_data]
        
        return {
            "content_similarity": "Basic similarity analysis - upgrade to semantic analysis for better results",
            "size_comparison": {
                "average_words": statistics.mean(word_counts) if word_counts else 0,
                "word_range": {"min": min(word_counts), "max": max(word_counts)} if word_counts else {},
                "size_variance": statistics.stdev(word_counts) if len(word_counts) > 1 else 0
            },
            "documents": content_data
        }
    
    def _compare_document_metadata(self, documents: List[Document]) -> Dict[str, Any]:
        """Compare metadata across documents"""
        
        metadata_comparison = {
            "file_types": Counter([doc.file_type for doc in documents]),
            "size_distribution": {
                "total_size": sum([doc.file_size for doc in documents]),
                "average_size": statistics.mean([doc.file_size for doc in documents]),
                "largest": max([doc.file_size for doc in documents]),
                "smallest": min([doc.file_size for doc in documents])
            },
            "processing_status": Counter([doc.status for doc in documents]),
            "creation_timeline": {
                "earliest": min([doc.created_at for doc in documents if doc.created_at]),
                "latest": max([doc.created_at for doc in documents if doc.created_at])
            }
        }
        
        return metadata_comparison
    
    def _compare_document_dates(self, documents: List[Document]) -> Dict[str, Any]:
        """Compare document dates and timeline"""
        
        dates = [(doc.created_at, doc.filename) for doc in documents if doc.created_at]
        dates.sort(key=lambda x: x[0])
        
        return {
            "chronological_order": [{"filename": filename, "date": date.isoformat()} for date, filename in dates],
            "date_span": {
                "earliest": dates[0][0].isoformat() if dates else None,
                "latest": dates[-1][0].isoformat() if dates else None,
                "span_days": (dates[-1][0] - dates[0][0]).days if len(dates) > 1 else 0
            }
        }
    
    async def _compare_document_themes(self, documents: List[Document]) -> Dict[str, Any]:
        """Compare themes across documents"""
        
        # Get content for all documents
        all_themes = []
        for doc in documents:
            chunks = self.db.query(DocumentChunk).filter(
                DocumentChunk.document_id == doc.id
            ).all()
            
            content = " ".join([chunk.content for chunk in chunks])
            doc_themes = self._extract_themes([{
                "document_id": str(doc.uuid),
                "filename": doc.filename,
                "content": content
            }])
            
            all_themes.append({
                "document_id": str(doc.uuid),
                "filename": doc.filename,
                "themes": doc_themes["top_keywords"][:5]
            })
        
        # Find common themes across documents
        all_keywords = []
        for doc_themes in all_themes:
            all_keywords.extend([kw["word"] for kw in doc_themes["themes"]])
        
        common_themes = Counter(all_keywords)
        
        return {
            "document_themes": all_themes,
            "common_themes": [{"word": word, "document_count": count} for word, count in common_themes.most_common(10)],
            "theme_diversity": len(set(all_keywords)) / len(all_keywords) if all_keywords else 0
        }
    
    async def _detect_compliance_anomalies(self, documents: List[Document]) -> List[Dict[str, Any]]:
        """Detect compliance-related anomalies"""
        anomalies = []
        
        for doc in documents:
            chunks = self.db.query(DocumentChunk).filter(
                DocumentChunk.document_id == doc.id
            ).all()
            
            content = " ".join([chunk.content for chunk in chunks])
            
            # Scan for PHI
            phi_scan = compliance_manager.phi_detector.scan_text(content, compliance_manager.current_mode)
            
            if phi_scan["phi_found"]:
                anomalies.append({
                    "type": "compliance",
                    "severity": "high" if phi_scan["high_sensitivity_count"] > 0 else "medium",
                    "document_id": str(doc.uuid),
                    "filename": doc.filename,
                    "description": f"PHI detected: {len(phi_scan['detections'])} items found",
                    "details": phi_scan["detections"][:3]  # First 3 detections
                })
        
        return anomalies
    
    async def _detect_content_anomalies(self, documents: List[Document]) -> List[Dict[str, Any]]:
        """Detect content-related anomalies"""
        anomalies = []
        
        # Check for unusually short/long documents
        sizes = [doc.file_size for doc in documents]
        if len(sizes) > 1:
            avg_size = statistics.mean(sizes)
            std_size = statistics.stdev(sizes) if len(sizes) > 1 else 0
            
            for doc in documents:
                if abs(doc.file_size - avg_size) > 2 * std_size:  # More than 2 standard deviations
                    anomalies.append({
                        "type": "content",
                        "severity": "low",
                        "document_id": str(doc.uuid),
                        "filename": doc.filename,
                        "description": f"Unusual file size: {doc.file_size} bytes (avg: {avg_size:.0f})",
                        "details": {"size": doc.file_size, "average": avg_size}
                    })
        
        return anomalies
    
    def _detect_metadata_anomalies(self, documents: List[Document]) -> List[Dict[str, Any]]:
        """Detect metadata-related anomalies"""
        anomalies = []
        
        # Check for missing metadata
        for doc in documents:
            if not doc.metadata or len(doc.metadata.keys()) < 3:
                anomalies.append({
                    "type": "metadata", 
                    "severity": "medium",
                    "document_id": str(doc.uuid),
                    "filename": doc.filename,
                    "description": "Limited metadata available - may affect search and analysis quality",
                    "details": {"metadata_keys": len(doc.metadata.keys()) if doc.metadata else 0}
                })
        
        return anomalies
    
    def _generate_combined_summary(self, individual_summaries: List[Dict]) -> Dict[str, Any]:
        """Generate combined summary from individual document summaries"""
        
        total_words = sum([doc["word_count"] for doc in individual_summaries])
        total_read_time = sum([int(doc["estimated_read_time"].split()[0]) for doc in individual_summaries])
        
        # Combine key points
        all_key_points = []
        for doc in individual_summaries:
            all_key_points.extend(doc["key_points"])
        
        return {
            "collection_overview": f"Analysis of {len(individual_summaries)} documents totaling {total_words:,} words",
            "estimated_total_read_time": f"{total_read_time} minutes",
            "combined_key_points": all_key_points[:10],  # Top 10 key points
            "document_types": list(set([doc["filename"].split('.')[-1] for doc in individual_summaries])),
            "analysis_depth": "comprehensive" if len(individual_summaries) <= 5 else "overview"
        }
    
    def _generate_anomaly_recommendations(self, anomalies: List[Dict]) -> List[str]:
        """Generate recommendations based on detected anomalies"""
        
        recommendations = []
        
        # Count anomaly types
        anomaly_types = Counter([a["type"] for a in anomalies])
        severity_counts = Counter([a["severity"] for a in anomalies])
        
        if anomaly_types.get("compliance", 0) > 0:
            recommendations.append("Review compliance settings and consider enabling stricter PHI protection")
        
        if severity_counts.get("high", 0) > 0:
            recommendations.append("Address high-severity issues immediately to maintain security and compliance")
        
        if anomaly_types.get("metadata", 0) > 2:
            recommendations.append("Improve document metadata quality to enhance search and analysis capabilities")
        
        if not recommendations:
            recommendations.append("Document set appears healthy with no significant issues detected")
        
        return recommendations
