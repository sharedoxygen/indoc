#!/usr/bin/env python3
"""
Data Integrity Checker for inDoc
Verifies synchronization across PostgreSQL, Elasticsearch, and Qdrant
"""
import asyncio
import sys
from typing import Dict, List, Set
from app.db.session import SessionLocal
from app.models.document import Document
from app.services.search.elasticsearch_service import ElasticsearchService
from app.services.search.qdrant_service import QdrantService
from sqlalchemy import select

class DataIntegrityChecker:
    def __init__(self):
        self.db = SessionLocal()
        self.es_service = ElasticsearchService()
        self.qdrant_service = QdrantService()
        
    async def check_integrity(self) -> Dict:
        """Check data integrity across all systems"""
        print("\n" + "="*70)
        print("🔍 inDoc Data Integrity Check".center(70))
        print("="*70 + "\n")
        
        # Get all document UUIDs from PostgreSQL
        pg_result = self.db.execute(select(Document.uuid, Document.status, Document.elasticsearch_id, Document.qdrant_id))
        pg_docs = {str(row[0]): {'status': row[1], 'es_id': row[2], 'qdrant_id': row[3]} for row in pg_result.all()}
        pg_uuids = set(pg_docs.keys())
        
        print(f"📊 PostgreSQL: {len(pg_uuids)} documents")
        print(f"   - Indexed: {sum(1 for d in pg_docs.values() if d['status'] == 'indexed')}")
        print(f"   - Processing: {sum(1 for d in pg_docs.values() if d['status'] == 'processing')}")
        print(f"   - Failed: {sum(1 for d in pg_docs.values() if d['status'] == 'failed')}")
        
        # Get all doc IDs from Elasticsearch
        es_docs = await self._get_all_es_docs()
        es_uuids = set(es_docs.keys())
        print(f"\n🔍 Elasticsearch: {len(es_uuids)} documents indexed")
        
        # Get all vector IDs from Qdrant
        qdrant_ids = self._get_all_qdrant_ids()
        qdrant_uuids = set(qdrant_ids)
        print(f"🧠 Qdrant: {len(qdrant_uuids)} vectors indexed")
        
        # Check for missing documents
        print("\n" + "-"*70)
        print("🔎 INTEGRITY ANALYSIS".center(70))
        print("-"*70 + "\n")
        
        # Documents in PG but missing from ES
        missing_from_es = pg_uuids - es_uuids
        if missing_from_es:
            print(f"⚠️  {len(missing_from_es)} documents in PostgreSQL but MISSING from Elasticsearch:")
            for uuid in list(missing_from_es)[:10]:  # Show first 10
                doc_info = pg_docs[uuid]
                print(f"   - {uuid} (status: {doc_info['status']}, es_id: {doc_info['es_id']})")
            if len(missing_from_es) > 10:
                print(f"   ... and {len(missing_from_es) - 10} more")
        else:
            print("✅ All PostgreSQL documents are in Elasticsearch")
        
        # Documents in PG but missing from Qdrant
        missing_from_qdrant = pg_uuids - qdrant_uuids
        if missing_from_qdrant:
            print(f"\n⚠️  {len(missing_from_qdrant)} documents in PostgreSQL but MISSING from Qdrant:")
            for uuid in list(missing_from_qdrant)[:10]:  # Show first 10
                doc_info = pg_docs[uuid]
                print(f"   - {uuid} (status: {doc_info['status']}, qdrant_id: {doc_info['qdrant_id']})")
            if len(missing_from_qdrant) > 10:
                print(f"   ... and {len(missing_from_qdrant) - 10} more")
        else:
            print("✅ All PostgreSQL documents are in Qdrant")
        
        # Documents in ES but not in PG (orphaned)
        orphaned_in_es = es_uuids - pg_uuids
        if orphaned_in_es:
            print(f"\n⚠️  {len(orphaned_in_es)} ORPHANED documents in Elasticsearch (not in PostgreSQL):")
            for uuid in list(orphaned_in_es)[:10]:
                print(f"   - {uuid}")
        else:
            print("\n✅ No orphaned documents in Elasticsearch")
        
        # Documents in Qdrant but not in PG (orphaned)
        orphaned_in_qdrant = qdrant_uuids - pg_uuids
        if orphaned_in_qdrant:
            print(f"\n⚠️  {len(orphaned_in_qdrant)} ORPHANED vectors in Qdrant (not in PostgreSQL):")
            for uuid in list(orphaned_in_qdrant)[:10]:
                print(f"   - {uuid}")
        else:
            print("\n✅ No orphaned vectors in Qdrant")
        
        # Summary
        print("\n" + "="*70)
        print("📋 SUMMARY".center(70))
        print("="*70)
        synced = len(missing_from_es) == 0 and len(missing_from_qdrant) == 0 and len(orphaned_in_es) == 0 and len(orphaned_in_qdrant) == 0
        if synced:
            print("\n✅ ✅ ✅  ALL SYSTEMS IN SYNC!  ✅ ✅ ✅\n")
        else:
            print(f"\n❌ DATA INTEGRITY ISSUES FOUND:")
            print(f"   - {len(missing_from_es)} docs missing from Elasticsearch")
            print(f"   - {len(missing_from_qdrant)} docs missing from Qdrant")
            print(f"   - {len(orphaned_in_es)} orphaned docs in Elasticsearch")
            print(f"   - {len(orphaned_in_qdrant)} orphaned vectors in Qdrant")
            print(f"\n💡 Run with --fix to automatically repair\n")
        
        return {
            'synced': synced,
            'postgresql': len(pg_uuids),
            'elasticsearch': len(es_uuids),
            'qdrant': len(qdrant_uuids),
            'missing_from_es': list(missing_from_es),
            'missing_from_qdrant': list(missing_from_qdrant),
            'orphaned_in_es': list(orphaned_in_es),
            'orphaned_in_qdrant': list(orphaned_in_qdrant)
        }
    
    async def _get_all_es_docs(self) -> Dict[str, Dict]:
        """Get all document IDs from Elasticsearch"""
        try:
            result = await self.es_service.client.search(
                index=self.es_service.index_name,
                body={
                    "query": {"match_all": {}},
                    "size": 10000,
                    "_source": ["document_id", "filename"]
                }
            )
            return {hit['_source']['document_id']: hit for hit in result['hits']['hits']}
        except Exception as e:
            print(f"Error querying Elasticsearch: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def _get_all_qdrant_ids(self) -> List[str]:
        """Get all vector IDs from Qdrant"""
        try:
            vectors, _ = self.qdrant_service.client.scroll(
                collection_name=self.qdrant_service.collection_name,
                limit=10000,
                with_payload=True,
                with_vectors=False
            )
            return [str(v.payload.get('document_id', '')) for v in vectors if v.payload.get('document_id')]
        except Exception as e:
            print(f"Error querying Qdrant: {e}")
            return []
    
    async def fix_integrity(self, issues: Dict):
        """Attempt to fix integrity issues"""
        from app.services.search_service import SearchService
        
        print("\n" + "="*70)
        print("🔧 REPAIRING DATA INTEGRITY".center(70))
        print("="*70 + "\n")
        
        search_service = SearchService()
        
        # Re-index documents missing from Elasticsearch
        if issues['missing_from_es']:
            print(f"🔍 Re-indexing {len(issues['missing_from_es'])} documents to Elasticsearch...")
            for uuid in issues['missing_from_es']:
                doc_result = self.db.execute(select(Document).where(Document.uuid == uuid))
                doc = doc_result.scalar_one_or_none()
                if doc and doc.status == 'indexed':
                    try:
                        await search_service.index_document_elasticsearch(doc)
                        print(f"   ✅ Re-indexed {doc.filename} to Elasticsearch")
                    except Exception as e:
                        print(f"   ❌ Failed to re-index {doc.filename}: {e}")
        
        # Re-index documents missing from Qdrant
        if issues['missing_from_qdrant']:
            print(f"\n🧠 Re-indexing {len(issues['missing_from_qdrant'])} documents to Qdrant...")
            for uuid in issues['missing_from_qdrant']:
                doc_result = self.db.execute(select(Document).where(Document.uuid == uuid))
                doc = doc_result.scalar_one_or_none()
                if doc and doc.status == 'indexed':
                    try:
                        await search_service.index_document_qdrant(doc)
                        print(f"   ✅ Re-indexed {doc.filename} to Qdrant")
                    except Exception as e:
                        print(f"   ❌ Failed to re-index {doc.filename}: {e}")
        
        # Clean up orphaned documents (optional - commented out for safety)
        # if issues['orphaned_in_es']:
        #     print(f"\n🗑️  Removing {len(issues['orphaned_in_es'])} orphaned docs from Elasticsearch...")
        
        print("\n✅ Repair complete! Re-run check to verify.\n")
    
    def close(self):
        self.db.close()

async def main():
    checker = DataIntegrityChecker()
    try:
        issues = await checker.check_integrity()
        
        if not issues['synced'] and '--fix' in sys.argv:
            await checker.fix_integrity(issues)
            # Re-check
            print("\n" + "="*70)
            print("🔄 RE-CHECKING AFTER REPAIR".center(70))
            print("="*70)
            await checker.check_integrity()
    finally:
        checker.close()

if __name__ == '__main__':
    asyncio.run(main())

