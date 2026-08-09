"""
Fix all documents by cleaning search indices and re-queuing
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.document import Document
from app.core.config import settings
from app.services.search.elasticsearch_service import ElasticsearchService
from app.services.search.qdrant_service import QdrantService

async def fix_all():
    # Setup DB
    db_url = settings.DATABASE_URL
    if not db_url.startswith('postgresql+asyncpg://'):
        db_url = db_url.replace('postgresql://', 'postgresql+asyncpg://')
    
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    print("\n" + "="*80)
    print("🔧 FIXING ALL DOCUMENTS - CLEAN & RE-INDEX")
    print("="*80)
    
    # Step 1: Clean Elasticsearch
    print("\n[1/4] Cleaning Elasticsearch...")
    try:
        es = ElasticsearchService()
        
        # Delete and recreate index
        await es.client.indices.delete(index=es.index_name, ignore=[404])
        print(f"   ✓ Deleted index: {es.index_name}")
        
        # Recreate with mapping
        await es.ensure_index_exists()
        print(f"   ✓ Recreated index with proper mapping")
        
        count = await es.count_documents()
        print(f"   ✓ Elasticsearch now has: {count} documents")
    except Exception as e:
        print(f"   ❌ Elasticsearch error: {e}")
        return
    
    # Step 2: Clean Qdrant
    print("\n[2/4] Cleaning Qdrant...")
    try:
        qdrant = QdrantService()
        
        # Delete and recreate collection
        qdrant.client.delete_collection(collection_name=qdrant.collection_name)
        print(f"   ✓ Deleted collection: {qdrant.collection_name}")
        
        # Recreate will happen automatically on first index
        qdrant._collection_ensured = False
        qdrant._ensure_collection()
        print(f"   ✓ Recreated collection")
        
        count = qdrant.count_vectors()
        print(f"   ✓ Qdrant now has: {count} vectors")
    except Exception as e:
        print(f"   ❌ Qdrant error: {e}")
        return
    
    # Step 3: Reset document status in PostgreSQL
    print("\n[3/4] Resetting document status in PostgreSQL...")
    async with async_session() as session:
        # Get count of documents to fix
        result = await session.execute(
            select(func.count(Document.id))
            .where(Document.status.in_(['indexed', 'stored', 'partially_indexed']))
        )
        to_fix = result.scalar()
        
        # Reset status, clear search IDs
        await session.execute(
            update(Document)
            .where(Document.status.in_(['indexed', 'stored', 'partially_indexed']))
            .values(
                status='pending',
                elasticsearch_id=None,
                qdrant_id=None,
                error_message=None
            )
        )
        
        await session.commit()
        print(f"   ✓ Reset {to_fix} documents to 'pending' status")
        
        # Verify
        result = await session.execute(
            select(func.count(Document.id))
            .where(Document.status == 'pending')
        )
        pending = result.scalar()
        print(f"   ✓ Documents now pending re-index: {pending}")
    
    # Step 4: Trigger Celery re-indexing
    print("\n[4/4] Triggering Celery re-indexing...")
    try:
        from app.tasks.document import process_document
        
        async with async_session() as session:
            # Get all pending documents
            result = await session.execute(
                select(Document.id, Document.filename)
                .where(Document.status == 'pending')
            )
            pending_docs = result.all()
            
            print(f"   📋 Queueing {len(pending_docs)} documents for processing...")
            
            for doc_id, filename in pending_docs:
                process_document.delay(doc_id)
                print(f"   ✓ Queued: {filename} (ID: {doc_id})")
            
            print(f"\n   ✅ All {len(pending_docs)} documents queued!")
            print(f"   🔄 Celery workers will process them now")
            print(f"   📊 Monitor progress in Search Inspector")
    except Exception as e:
        print(f"   ❌ Error queueing tasks: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*80)
    print("✅ FIX COMPLETE")
    print("="*80)
    print("\nNext steps:")
    print("1. Wait 2-3 minutes for Celery to process all documents")
    print("2. Refresh Search Inspector to see progress")
    print("3. Expected final state:")
    print("   - PostgreSQL: ~55 documents")
    print("   - Elasticsearch: ~55 indexed")
    print("   - Qdrant: ~40-45 vectors (images skip)")
    print()
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(fix_all())

