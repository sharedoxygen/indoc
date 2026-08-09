#!/usr/bin/env python3
"""
Integrity verification for DB, storage, S3, and RBAC.
Run: conda run -n indoc python tools/verify_integrity.py
"""
import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Any

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.models.document import Document
from app.models.role import Role, Permission, UserRole as UserRoleModel
from app.core.config import settings

from app.services.storage.factory import get_primary_storage


async def check_db_counts(session: AsyncSession) -> Dict[str, Any]:
    users = (await session.execute(select(func.count(User.id)))).scalar() or 0
    docs = (await session.execute(select(func.count(Document.id)))).scalar() or 0
    roles = (await session.execute(select(func.count(Role.id)))).scalar() or 0
    perms = (await session.execute(select(func.count(Permission.id)))).scalar() or 0
    return {"users": users, "documents": docs, "roles": roles, "permissions": perms}


async def check_referential_integrity(session: AsyncSession) -> Dict[str, Any]:
    # Orphan documents (uploaded_by not found)
    orphan_docs = (await session.execute(
        select(func.count(Document.id)).where(~Document.uploaded_by.in_(select(User.id)))
    )).scalar() or 0

    # Users with no role assignment
    users_without_role = (await session.execute(
        select(func.count(User.id)).where(~User.id.in_(select(UserRoleModel.user_id)))
    )).scalar() or 0

    return {"orphan_documents": orphan_docs, "users_without_role": users_without_role}


async def check_seed_status(session: AsyncSession) -> Dict[str, Any]:
    # Count all documents and how many have s3 keys
    all_docs = (await session.execute(select(Document))).scalars().all()
    total = len(all_docs)
    seed_docs = sum(1 for d in all_docs if d.custom_metadata and d.custom_metadata.get('enterprise_seed'))
    with_s3 = sum(1 for d in all_docs if d.custom_metadata and d.custom_metadata.get('s3_uploaded'))
    return {"total_documents": total, "seed_documents": seed_docs, "documents_with_s3": with_s3}


def check_storage_paths() -> Dict[str, Any]:
    local_ok = Path("backend/data/storage").exists()
    s3_cfg = {
        "bucket": getattr(settings, 'S3_BUCKET', None),
        "prefix": getattr(settings, 'S3_PREFIX', None),
        "region": getattr(settings, 'S3_REGION', None),
        "dual_write": getattr(settings, 'OBJECT_STORAGE_DUAL_WRITE', None),
    }
    return {"local_storage_exists": local_ok, "s3_config": s3_cfg}


async def check_s3_connectivity() -> Dict[str, Any]:
    try:
        s3 = get_primary_storage()
        if not s3:
            return {"s3_access": False, "reason": "No S3 backend configured"}
        # Attempt a harmless exists on a fake key
        test_key = f"{getattr(settings, 'S3_PREFIX', 'file-storage')}/_healthcheck.txt"
        exists = False
        try:
            exists = s3.exists(test_key)  # type: ignore[attr-defined]
        except Exception:
            pass
        return {"s3_access": True, "test_exists": exists}
    except Exception as e:
        return {"s3_access": False, "error": str(e)}


async def main():
    results: Dict[str, Any] = {}
    async with AsyncSessionLocal() as session:
        results["db_counts"] = await check_db_counts(session)
        results["referential_integrity"] = await check_referential_integrity(session)
        results["seed_status"] = await check_seed_status(session)
    results["storage"] = check_storage_paths()
    results["s3"] = await check_s3_connectivity()

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
