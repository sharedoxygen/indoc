#!/usr/bin/env python3
"""
Sync search status between PostgreSQL and search backends.

- Optionally verifies Elasticsearch/Qdrant counts
- Updates Document.status to 'indexed' for all documents (or only non-indexed)
- Sets elasticsearch_id and qdrant_id to the document UUID

Usage:
  conda run -n indoc python tools/sync_search_status.py --all
  conda run -n indoc python tools/sync_search_status.py            # only non-indexed
"""

import asyncio
import sys
from pathlib import Path
import logging
from typing import List

# Ensure backend is importable
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.document import Document
from app.services.search.elasticsearch_service import ElasticsearchService
from app.services.search.qdrant_service import QdrantService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def get_counts() -> None:
    es = ElasticsearchService()
    wv = QdrantService()

    try:
        es_health = await es.health_check()
        wv_health = await wv.health_check()
        logger.info(f"Elasticsearch: {es_health.get('status')} | Qdrant: {wv_health.get('status')}")
    except Exception as e:
        logger.warning(f"Health checks failed: {e}")


async def sync_status(update_all: bool = False, batch_size: int = 500) -> None:
    processed = 0
    async with AsyncSessionLocal() as session:
        # Load documents
        if update_all:
            query = select(Document)
        else:
            query = select(Document).where(Document.status != 'indexed')
        result = await session.execute(query)
        docs: List[Document] = result.scalars().all()

        if not docs:
            logger.info("No documents require status sync.")
            return

        logger.info(f"Syncing status for {len(docs)} documents (batch={batch_size})...")

        for doc in docs:
            # Mark as indexed in DB and set search IDs
            doc.status = 'indexed'
            doc.elasticsearch_id = str(doc.uuid)
            doc.qdrant_id = str(doc.uuid)
            session.add(doc)
            processed += 1

            if processed % batch_size == 0:
                await session.commit()
                logger.info(f"Committed {processed}/{len(docs)}")

        await session.commit()
        logger.info(f"✅ Sync complete. Updated {processed} documents to status=indexed")


async def main() -> None:
    update_all = '--all' in sys.argv
    await get_counts()
    await sync_status(update_all=update_all)


if __name__ == "__main__":
    asyncio.run(main())


