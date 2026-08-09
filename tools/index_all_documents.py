#!/usr/bin/env python3
"""
Index All Documents

Indexes all documents from PostgreSQL into Elasticsearch (keyword) and Qdrant (semantic),
updating their status to 'indexed'.

Usage:
  conda run -n indoc python tools/index_all_documents.py [--all] [--batch 200]

- --all: include documents regardless of current status
- --batch: number of documents per commit batch (default 200)
"""

import asyncio
import sys
import logging
from pathlib import Path
from typing import List, Tuple
from datetime import datetime
import argparse

# Ensure backend is on import path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.document import Document
from app.services.search.elasticsearch_service import ElasticsearchService
from app.services.search.qdrant_service import QdrantService
from app.services.text_extraction_service import TextExtractionService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def ensure_indices(es: ElasticsearchService, wv: QdrantService) -> None:
    ok1 = await es.ensure_index_exists()
    ok2 = await wv.ensure_schema_exists()
    if not (ok1 and ok2):
        raise RuntimeError("Failed to initialize search indices")


def build_metadata(doc: Document) -> dict:
    return {
        "filename": doc.filename,
        "title": doc.title or doc.filename,
        "description": doc.description or "",
        "file_type": doc.file_type,
        "tags": doc.tags or [],
        "uploaded_by": str(doc.uploaded_by),
        "created_at": doc.created_at.isoformat() if doc.created_at else datetime.utcnow().isoformat(),
        "updated_at": (doc.updated_at or doc.created_at or datetime.utcnow()).isoformat(),
        "file_size": doc.file_size,
    }


async def get_content(doc: Document, text_service: TextExtractionService) -> str:
    if doc.full_text:
        return doc.full_text
    if doc.storage_path:
        try:
            return await text_service.extract_text(doc.storage_path, doc.file_type)
        except Exception:
            pass
    return doc.description or doc.filename


async def index_document(
    doc: Document,
    es: ElasticsearchService,
    wv: QdrantService,
    text_service: TextExtractionService,
) -> Tuple[bool, str]:
    try:
        content = await get_content(doc, text_service)
        metadata = build_metadata(doc)
        es_ok, wv_ok = await asyncio.gather(
            es.index_document(str(doc.uuid), content, metadata),
            wv.add_document(str(doc.uuid), content, metadata),
            return_exceptions=False,
        )
        success = bool(es_ok) and bool(wv_ok)
        return success, ""
    except Exception as e:
        return False, str(e)


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="Index all documents regardless of status")
    parser.add_argument("--batch", type=int, default=200, help="Batch size for commits")
    args = parser.parse_args()

    es = ElasticsearchService()
    wv = QdrantService()
    text_service = TextExtractionService()

    logger.info("🔍 Health check for search backends...")
    await es.health_check()
    await wv.health_check()

    logger.info("🚀 Ensuring indices/schemas exist...")
    await ensure_indices(es, wv)

    async with AsyncSessionLocal() as session:
        # Select docs
        if args.all:
            query = select(Document)
        else:
            query = select(Document).where(Document.status != 'indexed')
        result = await session.execute(query)
        docs: List[Document] = result.scalars().all()

        if not docs:
            logger.info("No documents to index.")
            return

        logger.info(f"📄 Indexing {len(docs)} documents (batch={args.batch})...")

        processed = 0
        successes = 0
        failures = 0
        for doc in docs:
            ok, err = await index_document(doc, es, wv, text_service)
            if ok:
                successes += 1
                doc.status = 'indexed'
            else:
                failures += 1
                doc.status = doc.status or 'failed'
                doc.error_message = err
            session.add(doc)
            processed += 1

            if processed % args.batch == 0:
                await session.commit()
                logger.info(f"✅ Committed batch: {processed}/{len(docs)} (ok={successes}, fail={failures})")

        # Final commit
        await session.commit()
        logger.info(f"🎉 Finished indexing. Total={len(docs)}, ok={successes}, fail={failures}")


if __name__ == "__main__":
    asyncio.run(main())
