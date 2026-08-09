#!/usr/bin/env python3
"""
Canonical database reseed script - clears and reloads all data
Run: conda run -n indoc python tools/reseed_database.py [--clean]
"""
import asyncio
import sys
import argparse
from pathlib import Path
from typing import Dict, Any

# Add the backend directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.models.document import Document
from app.models.conversation import Conversation, Message
from app.models.audit import AuditLog
from app.models.document_permission import DocumentPermission
from app.models.role import Role, Permission, UserRole as UserRoleModel, RolePermission

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def clean_database(session: AsyncSession):
    """Remove all data except system roles"""
    logger.info("🗑️  Cleaning database...")
    
    # Order matters for foreign key constraints
    tables_to_clean = [
        Message, Conversation,
        DocumentPermission, Document,
        AuditLog,
        UserRoleModel,  # User-role associations
        User,
        RolePermission,  # Keep system roles but clear permissions first
    ]
    
    for table in tables_to_clean:
        try:
            await session.execute(delete(table))
            logger.info(f"  ✅ Cleared {table.__tablename__}")
        except Exception as e:
            logger.warning(f"  ⚠️  Could not clear {table.__tablename__}: {e}")
    
    # Don't delete system roles/permissions, but clear non-system ones
    await session.execute(delete(Role).where(Role.is_system == False))
    await session.execute(delete(Permission).where(Permission.name.like('custom.%')))
    
    await session.commit()
    logger.info("✅ Database cleaned")


async def seed_rbac(session: AsyncSession):
    """Ensure RBAC system is initialized"""
    logger.info("🔐 Setting up RBAC...")
    
    # Import and run the RBAC seeder
    from tools.seed_rbac_system import seed_rbac
    await seed_rbac()
    logger.info("✅ RBAC configured")


async def seed_fixed_admin(session: AsyncSession):
    """Ensure fixed admin exists"""
    logger.info("👤 Creating fixed admin...")
    
    # Import and run the fixed admin creator
    from tools.ensure_fixed_admin import ensure_fixed_admin
    await ensure_fixed_admin()
    logger.info("✅ Fixed admin ready")


async def seed_enterprise_data(session: AsyncSession):
    """Generate enterprise seed data"""
    logger.info("🏢 Generating enterprise data...")
    
    # Import and run the enterprise seed generator
    from tools.enterprise_seed_generator import main as enterprise_main
    await enterprise_main()
    logger.info("✅ Enterprise data seeded")


async def update_rbac_assignments(session: AsyncSession):
    """Ensure all users have RBAC roles"""
    logger.info("🔄 Updating RBAC assignments...")
    
    # Import and run the RBAC updater
    from tools.update_seed_rbac import assign_rbac_roles_to_seeds
    await assign_rbac_roles_to_seeds()
    logger.info("✅ RBAC assignments complete")


async def verify_integrity():
    """Run integrity checks"""
    logger.info("🔍 Verifying integrity...")
    
    # Import and run the integrity checker
    from tools.verify_integrity import main as verify_main
    await verify_main()
    logger.info("✅ Integrity verified")


async def main(clean: bool = False):
    """Main reseed pipeline"""
    print("\n" + "="*70)
    print("🚀 CANONICAL DATABASE RESEED PIPELINE")
    print("="*70 + "\n")
    
    async with AsyncSessionLocal() as session:
        if clean:
            await clean_database(session)
        
        # Run seed pipeline in order
        await seed_rbac(session)
        await seed_fixed_admin(session)
        await seed_enterprise_data(session)
        await update_rbac_assignments(session)
    
    # Verify everything worked
    await verify_integrity()
    
    print("\n" + "="*70)
    print("✅ RESEED COMPLETE!")
    print("="*70)
    print("\nTest credentials:")
    print("  Admin: admin / AdminSecure123!")
    print("  Manager: manager / ManagerSecure123!")
    print("  Analyst: analyst / AnalystSecure123!")
    print("\nAccess at: http://localhost:3000")
    print("="*70 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reseed database with canonical data")
    parser.add_argument("--clean", action="store_true", help="Clean database before seeding")
    args = parser.parse_args()
    
    asyncio.run(main(clean=args.clean))
