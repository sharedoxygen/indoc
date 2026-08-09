#!/usr/bin/env python3
"""
List Admin/Reviewer users (email, role) to help with demo logins.
All enterprise seed users share the password: Enterprise2024!
"""
import asyncio
from pathlib import Path
import sys

# Ensure backend is importable
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.user import User, UserRole


async def main():
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(User).where(User.role.in_([UserRole.ADMIN, UserRole.REVIEWER])).limit(20)
        )
        users = res.scalars().all()
        if not users:
            print("No admin/reviewer users found.")
            return
        print("Role,Email")
        for u in users:
            try:
                role = u.role.value if hasattr(u.role, 'value') else str(u.role)
            except Exception:
                role = str(u.role)
            print(f"{role},{u.email}")


if __name__ == "__main__":
    asyncio.run(main())


