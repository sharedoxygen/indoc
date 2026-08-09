"""
Simple integrity check script
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.document import Document
from app.core.config import settings
from app.services.search.elasticsearch_service import ElasticsearchService
from app.services.search.qdrant_service import QdrantService

async def check():
    # Setup DB
    db_url = settings.DATABASE_URL
    if not db_url.startswith('postgresql+asyncpg://'):
        db_url = db_url.replace('postgresql://', 'postgresql+asyncpg://')
    
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        print("\n" + "="*80)
        print("📊 DATA INTEGRITY CHECK")
        print("="*80)
        
        # PostgreSQL counts
        result = await session.execute(select(func.count(Document.id)))
        pg_total = result.scalar()
        
        result = await session.execute(
            select(func.count(Document.id)).where(Document.status == 'indexed')
        )
        pg_indexed = result.scalar()
        
        result = await session.execute(
            select(func.count(Document.id)).where(Document.status == 'stored')
        )
        pg_stored = result.scalar()
        
        result = await session.execute(
            select(func.count(Document.id)).where(Document.status == 'partially_indexed')
        )
        pg_partial = result.scalar()
        
        result = await session.execute(
            select(func.count(Document.id)).where(Document.status == 'failed')
        )
        pg_failed = result.scalar()
        
        result = await session.execute(
            select(func.count(Document.id)).where(Document.elasticsearch_id.isnot(None))
        )
        pg_with_es = result.scalar()
        
        result = await session.execute(
            select(func.count(Document.id)).where(Document.qdrant_id.isnot(None))
        )
        pg_with_qdrant = result.scalar()
        
        print(f"\n📋 PostgreSQL:")
        print(f"   Total documents: {pg_total}")
        print(f"   Status 'indexed': {pg_indexed}")
        print(f"   Status 'stored': {pg_stored}")
        print(f"   Status 'partially_indexed': {pg_partial}")
        print(f"   Status 'failed': {pg_failed}")
        print(f"   Have elasticsearch_id: {pg_with_es}")
        print(f"   Have qdrant_id: {pg_with_qdrant}")
        
        # Elasticsearch
        try:
            es = ElasticsearchService()
            es_count = await es.count_documents()
            print(f"\n📋 Elasticsearch:")
            print(f"   Indexed documents: {es_count}")
            print(f"   Expected (indexed + stored): {pg_indexed + pg_stored}")
            print(f"   Missing: {(pg_indexed + pg_stored) - es_count}")
        except Exception as e:
            print(f"\n❌ Elasticsearch error: {e}")
        
        # Qdrant
        try:
            qdrant = QdrantService()
            qdrant_count = qdrant.count_vectors()
            print(f"\n📋 Qdrant:")
            print(f"   Vector points: {qdrant_count}")
            print(f"   Expected (indexed only, images skip): {pg_indexed}")
            print(f"   Difference: {pg_indexed - qdrant_count}")
        except Exception as e:
            print(f"\n❌ Qdrant error: {e}")
        
        # Get sample of broken documents
        result = await session.execute(
            select(Document.filename, Document.status, Document.elasticsearch_id, Document.qdrant_id, Document.error_message)
            .where(Document.status.in_(['partially_indexed', 'failed']))
            .limit(10)
        )
        broken = result.all()
        
        print(f"\n⚠️  Sample Broken Documents (first 10):")
        for filename, status, es_id, q_id, error in broken:
            print(f"   {filename}")
            print(f"      Status: {status}")
            print(f"      ES ID: {'✓' if es_id else '✗'}")
            print(f"      Qdrant ID: {'✓' if q_id else '✗'}")
            print(f"      Error: {error}")
        
        print("\n" + "="*80)
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check())

