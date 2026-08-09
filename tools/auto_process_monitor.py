#!/usr/bin/env python3
"""
Auto-Processing Monitor
Continuously monitors for uploaded documents and automatically processes them
"""

import asyncio
import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta

# Add the backend directory to the Python path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.document import Document
from app.tasks.document import process_document

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AutoProcessMonitor:
    """Monitor and automatically process uploaded documents"""
    
    def __init__(self, check_interval: int = 30):
        self.check_interval = check_interval  # seconds
        self.running = False
    
    async def start_monitoring(self):
        """Start the monitoring loop"""
        self.running = True
        logger.info("🚀 Auto-processing monitor started")
        
        while self.running:
            try:
                await self.process_pending_documents()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def process_pending_documents(self):
        """Find and process uploaded documents"""
        async with AsyncSessionLocal() as session:
            # Find documents uploaded in last hour that need processing
            cutoff_time = datetime.utcnow() - timedelta(hours=1)
            
            result = await session.execute(
                select(Document).where(
                    Document.status == 'uploaded',
                    Document.created_at >= cutoff_time
                )
            )
            docs = result.scalars().all()
            
            if docs:
                logger.info(f"📄 Found {len(docs)} documents to process")
                
                for doc in docs:
                    try:
                        # Trigger processing
                        task = process_document.delay(str(doc.uuid))
                        logger.info(f"🚀 Processing triggered for {doc.filename} (task: {task.id})")
                        
                        # Update status to prevent reprocessing
                        doc.status = 'processing'
                        session.add(doc)
                        
                    except Exception as e:
                        logger.error(f"Failed to trigger processing for {doc.filename}: {e}")
                
                await session.commit()
    
    def stop_monitoring(self):
        """Stop the monitoring loop"""
        self.running = False
        logger.info("🛑 Auto-processing monitor stopped")


async def main():
    """Main function"""
    monitor = AutoProcessMonitor(check_interval=30)  # Check every 30 seconds
    
    try:
        await monitor.start_monitoring()
    except KeyboardInterrupt:
        monitor.stop_monitoring()
        logger.info("🔄 Monitor stopped by user")


if __name__ == "__main__":
    asyncio.run(main())
