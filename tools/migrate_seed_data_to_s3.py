#!/usr/bin/env python3
"""
Migrate Existing Seed Data to S3

Uploads all seed-generated documents from local storage to S3 bucket.
Updates database with object_storage_key for each document.
"""

import asyncio
import sys
import os
import logging
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.db.session import AsyncSessionLocal
from app.models.document import Document
from app.services.storage.factory import get_primary_storage
from app.services.storage.base import build_object_key

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def migrate_seed_data_to_s3():
    """Upload all seed data files to S3 with progress tracking"""
    
    logger.info("🚀 Starting S3 migration for seed data...")
    
    # Get S3 client
    try:
        s3_client = get_primary_storage()
        if not s3_client:
            logger.error("❌ S3 storage not configured")
            logger.info("💡 Configure S3_BUCKET_NAME and AWS credentials in config")
            return
    except Exception as e:
        logger.error(f"❌ Failed to initialize S3 client: {e}")
        return
    
    async with AsyncSessionLocal() as session:
        # Get all seed documents that don't have S3 keys
        result = await session.execute(
            select(Document).where(
                Document.custom_metadata['enterprise_seed'].astext == 'true'
            )
        )
        seed_documents = result.scalars().all()
        
        if not seed_documents:
            logger.info("✅ No seed documents found to migrate")
            return
        
        logger.info(f"📊 Found {len(seed_documents)} seed documents")
        
        success_count = 0
        skip_count = 0
        error_count = 0
        
        for idx, document in enumerate(seed_documents, 1):
            try:
                # Check if already uploaded to S3
                if document.custom_metadata and document.custom_metadata.get('s3_uploaded'):
                    skip_count += 1
                    continue
                
                # Check if file exists locally
                if not os.path.exists(document.storage_path):
                    logger.warning(f"⚠️  File not found: {document.filename}")
                    error_count += 1
                    continue
                
                # Read file
                with open(document.storage_path, 'rb') as f:
                    content = f.read()
                
                # Build S3 key using configured prefix
                from app.core.config import settings
                object_key = build_object_key(
                    tenant_id=document.tenant_id,
                    file_hash=document.file_hash,
                    file_extension=document.file_type,
                    prefix=settings.S3_PREFIX  # Use configured prefix: 'file-storage'
                )
                
                # Upload to S3
                s3_client.put_bytes(
                    object_key,
                    content,
                    content_type=f'application/{document.file_type}'
                )
                
                # Update metadata
                meta = document.custom_metadata or {}
                meta['object_storage_key'] = object_key
                meta['s3_uploaded'] = True
                meta['s3_migrated_at'] = str(asyncio.get_event_loop().time())
                document.custom_metadata = meta
                
                success_count += 1
                
                # Progress logging
                if idx % 50 == 0:
                    logger.info(f"📊 Progress: {idx}/{len(seed_documents)} ({success_count} uploaded, {skip_count} skipped, {error_count} errors)")
                
            except Exception as e:
                logger.error(f"❌ Error uploading {document.filename}: {e}")
                error_count += 1
        
        # Commit all metadata updates
        await session.commit()
        
        # Final summary
        logger.info("\n" + "=" * 70)
        logger.info("📋 S3 MIGRATION SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Total documents processed: {len(seed_documents)}")
        logger.info(f"✅ Successfully uploaded: {success_count}")
        logger.info(f"⏭️  Already in S3 (skipped): {skip_count}")
        logger.info(f"❌ Errors: {error_count}")
        logger.info(f"\n☁️  S3 Bucket: s3://shaoxy-indoc/")
        logger.info(f"📁 Prefix: {settings.S3_PREFIX}/")
        logger.info(f"🌐 URL: https://shaoxy-indoc.s3.{settings.S3_REGION}.amazonaws.com/{settings.S3_PREFIX}/")
        logger.info("=" * 70)


async def verify_s3_migration():
    """Verify that seed documents are accessible from S3"""
    logger.info("\n🔍 Verifying S3 migration...")
    
    async with AsyncSessionLocal() as session:
        # Get documents with S3 keys
        result = await session.execute(
            select(Document).where(
                Document.custom_metadata['s3_uploaded'].astext == 'true'
            ).limit(5)
        )
        docs = result.scalars().all()
        
        logger.info(f"\n📊 Sample verification ({len(docs)} documents):")
        
        s3_client = get_primary_storage()
        for doc in docs:
            object_key = doc.custom_metadata.get('object_storage_key')
            if object_key:
                exists = s3_client.exists(object_key)
                status = "✅ Exists" if exists else "❌ Missing"
                logger.info(f"  {status}: {doc.filename}")
                logger.info(f"           S3 key: {object_key}")


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate seed data to S3')
    parser.add_argument('--verify-only', action='store_true', help='Only verify, dont migrate')
    parser.add_argument('--yes', action='store_true', help='Auto-confirm')
    
    args = parser.parse_args()
    
    if args.verify_only:
        await verify_s3_migration()
        return
    
    if not args.yes:
        logger.warning("⚠️  This will upload all seed data files to S3")
        response = input("Continue? (y/N): ")
        if response.lower() != 'y':
            logger.info("Cancelled")
            return
    
    await migrate_seed_data_to_s3()
    await verify_s3_migration()


if __name__ == "__main__":
    asyncio.run(main())

