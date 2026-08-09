"""
Fix orphaned documents by assigning them to admin user
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.document import Document
from app.models.user import User, UserRole
from app.core.config import settings

async def fix_documents():
    # Create async engine
    db_url = settings.DATABASE_URL
    if not db_url.startswith('postgresql+asyncpg://'):
        db_url = db_url.replace('postgresql://', 'postgresql+asyncpg://')
    
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Find admin user
        result = await session.execute(
            select(User).where(User.role == UserRole.ADMIN).limit(1)
        )
        admin = result.scalar_one_or_none()
        
        if not admin:
            print("❌ No admin user found!")
            return
        
        print(f"✅ Found admin: {admin.email} (ID: {admin.id}, Tenant: {admin.tenant_id})")
        
        # Count orphaned documents
        result = await session.execute(
            select(Document).where(Document.uploaded_by.is_(None))
        )
        orphaned_docs = result.scalars().all()
        
        print(f"\n📋 Found {len(orphaned_docs)} orphaned documents")
        
        if len(orphaned_docs) == 0:
            print("✅ No orphaned documents to fix!")
            return
        
        # Update all orphaned documents
        result = await session.execute(
            update(Document)
            .where(Document.uploaded_by.is_(None))
            .values(
                uploaded_by=admin.id,
                tenant_id=admin.tenant_id
            )
        )
        
        await session.commit()
        
        print(f"✅ Assigned all {len(orphaned_docs)} documents to {admin.email}")
        print(f"   Tenant ID: {admin.tenant_id}")
        
        # Verify
        result = await session.execute(
            select(Document).where(Document.uploaded_by.is_(None))
        )
        remaining = result.scalars().all()
        print(f"\n✅ Remaining orphaned documents: {len(remaining)}")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(fix_documents())

