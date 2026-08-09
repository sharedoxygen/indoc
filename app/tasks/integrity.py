"""
Data Integrity Monitoring Tasks

Automated scheduled checks to ensure data consistency across:
- PostgreSQL (source of truth)
- Elasticsearch (keyword search)
- Qdrant (vector search)

Runs periodically to detect and alert on misalignment.
"""

import logging
from typing import Dict, Any, List
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.document import Document
from app.services.search.elasticsearch_service import ElasticsearchService
from app.services.search.qdrant_service import QdrantService

logger = logging.getLogger(__name__)


def run_async(coro):
    """Helper to run async code in sync context"""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@celery_app.task(name="app.tasks.integrity.check_data_integrity")
def check_data_integrity() -> Dict[str, Any]:
    """
    Periodic task to verify data consistency across all storage systems.
    
    Checks:
    1. Count mismatches between PostgreSQL, Elasticsearch, and Qdrant
    2. Documents marked 'indexed' but missing from search indices
    3. Documents in search indices but not in PostgreSQL
    
    Returns:
        Dict with integrity report and any issues found
    """
    logger.info("🔍 Starting scheduled data integrity check...")
    
    try:
        db = SessionLocal()
        
        # Initialize search services
        es = ElasticsearchService()
        qdrant = QdrantService()
        
        # ===== Count Checks =====
        # PostgreSQL counts
        pg_total_stmt = select(func.count(Document.uuid))
        pg_total = run_async(db.execute(pg_total_stmt)).scalar()
        
        pg_indexed_stmt = select(func.count(Document.uuid)).where(Document.status == 'indexed')
        pg_indexed = run_async(db.execute(pg_indexed_stmt)).scalar()
        
        pg_stored_stmt = select(func.count(Document.uuid)).where(Document.status == 'stored')
        pg_stored = run_async(db.execute(pg_stored_stmt)).scalar()
        
        pg_processing_stmt = select(func.count(Document.uuid)).where(
            Document.status.in_(['processing', 'pending'])
        )
        pg_processing = run_async(db.execute(pg_processing_stmt)).scalar()
        
        pg_failed_stmt = select(func.count(Document.uuid)).where(
            Document.status.in_(['failed', 'partially_indexed'])
        )
        pg_failed = run_async(db.execute(pg_failed_stmt)).scalar()
        
        # Elasticsearch count
        es_total = run_async(es.count_documents())
        
        # Qdrant count (should match pg_indexed)
        qdrant_info = qdrant.collection_info()
        qdrant_total = qdrant_info.get('vectors_count', 0)
        
        # ===== Integrity Checks =====
        issues = []
        warnings = []
        
        # Check 1: Elasticsearch should have all indexed + stored docs (not failed/processing)
        expected_es_count = pg_indexed + pg_stored
        if es_total != expected_es_count:
            issues.append({
                "type": "count_mismatch",
                "system": "Elasticsearch",
                "expected": expected_es_count,
                "actual": es_total,
                "diff": abs(es_total - expected_es_count),
                "message": f"Elasticsearch has {es_total} docs but PostgreSQL has {expected_es_count} indexed/stored"
            })
        
        # Check 2: Qdrant should have exactly pg_indexed docs (text-searchable only)
        if qdrant_total != pg_indexed:
            issues.append({
                "type": "count_mismatch",
                "system": "Qdrant",
                "expected": pg_indexed,
                "actual": qdrant_total,
                "diff": abs(qdrant_total - pg_indexed),
                "message": f"Qdrant has {qdrant_total} vectors but PostgreSQL has {pg_indexed} indexed docs"
            })
        
        # Check 3: Find documents marked 'indexed' but missing Elasticsearch ID
        broken_es_stmt = select(Document.uuid, Document.filename).where(
            Document.status == 'indexed',
            Document.elasticsearch_id.is_(None)
        )
        broken_es = run_async(db.execute(broken_es_stmt)).all()
        
        if broken_es:
            warnings.append({
                "type": "missing_search_id",
                "system": "Elasticsearch",
                "count": len(broken_es),
                "documents": [{"id": str(uuid), "filename": filename} for uuid, filename in broken_es[:10]],
                "message": f"{len(broken_es)} documents marked 'indexed' but missing Elasticsearch ID"
            })
        
        # Check 4: Find documents marked 'indexed' but missing Qdrant ID
        broken_qdrant_stmt = select(Document.uuid, Document.filename).where(
            Document.status == 'indexed',
            Document.qdrant_id.is_(None)
        )
        broken_qdrant = run_async(db.execute(broken_qdrant_stmt)).all()
        
        if broken_qdrant:
            warnings.append({
                "type": "missing_search_id",
                "system": "Qdrant",
                "count": len(broken_qdrant),
                "documents": [{"id": str(uuid), "filename": filename} for uuid, filename in broken_qdrant[:10]],
                "message": f"{len(broken_qdrant)} documents marked 'indexed' but missing Qdrant ID"
            })
        
        # Check 5: Warn about processing documents stuck for too long
        if pg_processing > 0:
            from sqlalchemy import and_
            from datetime import timedelta
            stuck_threshold = datetime.utcnow() - timedelta(minutes=30)
            
            stuck_stmt = select(Document.uuid, Document.filename, Document.updated_at).where(
                and_(
                    Document.status.in_(['processing', 'pending']),
                    Document.updated_at < stuck_threshold
                )
            )
            stuck_docs = run_async(db.execute(stuck_stmt)).all()
            
            if stuck_docs:
                warnings.append({
                    "type": "stuck_processing",
                    "count": len(stuck_docs),
                    "documents": [
                        {
                            "id": str(uuid),
                            "filename": filename,
                            "stuck_since": updated_at.isoformat()
                        }
                        for uuid, filename, updated_at in stuck_docs[:10]
                    ],
                    "message": f"{len(stuck_docs)} documents stuck in processing for >30 minutes"
                })
        
        # ===== Generate Report =====
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "counts": {
                "postgresql": {
                    "total": pg_total,
                    "indexed": pg_indexed,
                    "stored": pg_stored,
                    "processing": pg_processing,
                    "failed": pg_failed
                },
                "elasticsearch": {
                    "total": es_total
                },
                "qdrant": {
                    "vectors": qdrant_total
                }
            },
            "status": "healthy" if not issues else "warning" if not issues and warnings else "unhealthy",
            "issues": issues,
            "warnings": warnings
        }
        
        # Log results
        if issues:
            logger.error(f"❌ Data integrity check FAILED with {len(issues)} issue(s)")
            for issue in issues:
                logger.error(f"   • {issue['message']}")
        elif warnings:
            logger.warning(f"⚠️ Data integrity check passed with {len(warnings)} warning(s)")
            for warning in warnings:
                logger.warning(f"   • {warning['message']}")
        else:
            logger.info(f"✅ Data integrity check PASSED - all systems aligned")
            logger.info(f"   PostgreSQL: {pg_total} total ({pg_indexed} indexed, {pg_stored} stored)")
            logger.info(f"   Elasticsearch: {es_total} docs")
            logger.info(f"   Qdrant: {qdrant_total} vectors")
        
        run_async(db.close())
        return report
        
    except Exception as e:
        logger.error(f"❌ Data integrity check failed: {e}", exc_info=True)
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "error",
            "error": str(e)
        }


@celery_app.task(name="app.tasks.integrity.auto_repair_integrity")
def auto_repair_integrity() -> Dict[str, Any]:
    """
    Attempt to automatically repair common integrity issues.
    
    Actions:
    1. Re-queue documents marked 'indexed' but missing search IDs
    2. Mark documents as 'failed' if stuck in processing >1 hour
    
    Returns:
        Dict with repair actions taken
    """
    logger.info("🔧 Starting automated integrity repair...")
    
    try:
        db = SessionLocal()
        actions = []
        
        # Find documents marked 'indexed' but missing Elasticsearch or Qdrant IDs
        from sqlalchemy import or_
        broken_stmt = select(Document).where(
            Document.status == 'indexed',
            or_(
                Document.elasticsearch_id.is_(None),
                Document.qdrant_id.is_(None)
            )
        )
        broken_docs = run_async(db.execute(broken_stmt)).scalars().all()
        
        if broken_docs:
            from app.tasks.document import process_document
            
            for doc in broken_docs:
                logger.info(f"🔧 Re-queueing broken document: {doc.filename}")
                
                # Reset status to pending
                doc.status = 'pending'
                doc.elasticsearch_id = None
                doc.qdrant_id = None
                
                # Re-queue for processing
                process_document.delay(str(doc.uuid))
                
                actions.append({
                    "action": "requeue",
                    "document_id": str(doc.uuid),
                    "filename": doc.filename
                })
            
            run_async(db.commit())
            logger.info(f"✅ Re-queued {len(broken_docs)} broken documents")
        
        # Mark stuck documents as failed
        from datetime import timedelta
        stuck_threshold = datetime.utcnow() - timedelta(hours=1)
        
        stuck_stmt = select(Document).where(
            Document.status.in_(['processing', 'pending']),
            Document.updated_at < stuck_threshold
        )
        stuck_docs = run_async(db.execute(stuck_stmt)).scalars().all()
        
        if stuck_docs:
            for doc in stuck_docs:
                logger.warning(f"⏱️ Marking stuck document as failed: {doc.filename}")
                doc.status = 'failed'
                doc.error_message = f"Processing stuck for >1 hour (last update: {doc.updated_at})"
                
                actions.append({
                    "action": "mark_failed",
                    "document_id": str(doc.uuid),
                    "filename": doc.filename,
                    "stuck_since": doc.updated_at.isoformat()
                })
            
            run_async(db.commit())
            logger.info(f"✅ Marked {len(stuck_docs)} stuck documents as failed")
        
        run_async(db.close())
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "actions_taken": len(actions),
            "details": actions
        }
        
    except Exception as e:
        logger.error(f"❌ Auto-repair failed: {e}", exc_info=True)
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "error",
            "error": str(e)
        }

