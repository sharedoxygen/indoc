#!/usr/bin/env python3
"""
Ensure the FIXED admin user exists and cannot be deleted/deactivated
This user is immutable and always has full system access
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select  # noqa: E402

from app.core.security import get_password_hash  # noqa: E402
from app.db.session import AsyncSessionLocal  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402

# Fixed admin identity. The password is never stored in the repo.
FIXED_ADMIN_USERNAME = "admin"
FIXED_ADMIN_EMAIL = "admin@indoc.local"
FIXED_ADMIN_FULLNAME = "System Administrator"


def _fixed_admin_password() -> str:
    password = os.environ.get("FIXED_ADMIN_PASSWORD") or os.environ.get(
        "ADMIN_PASSWORD"
    )
    if not password:
        raise SystemExit(
            "Set ADMIN_PASSWORD or FIXED_ADMIN_PASSWORD. "
            "The admin password is not stored in the repository."
        )
    return password


async def ensure_fixed_admin():
    """Ensure the fixed admin user exists"""

    print("🔐 Ensuring Fixed Admin User Exists\n")
    print("=" * 70)

    async with AsyncSessionLocal() as session:
        # Check if fixed admin exists
        result = await session.execute(
            select(User).where(User.username == FIXED_ADMIN_USERNAME)
        )
        admin = result.scalars().first()

        if admin:
            print(f"✅ Fixed admin user already exists: {admin.username}")
            print(f"   Email: {admin.email}")
            print(f"   Full Name: {admin.full_name}")
            print(f"   Role: {admin.role.value}")

            # Ensure it's active and has admin role
            updated = False
            if not admin.is_active:
                admin.is_active = True
                updated = True
                print("   🔧 Reactivated admin user")

            if admin.role != UserRole.ADMIN:
                admin.role = UserRole.ADMIN
                updated = True
                print("   🔧 Reset role to Admin")

            if admin.email != FIXED_ADMIN_EMAIL:
                admin.email = FIXED_ADMIN_EMAIL
                updated = True
                print(f"   🔧 Reset email to {FIXED_ADMIN_EMAIL}")

            admin.hashed_password = get_password_hash(_fixed_admin_password())
            updated = True
            print("   🔧 Reset password")

            if updated:
                await session.commit()
                print("   ✅ Admin user updated and secured")
        else:
            print("⚠️  Fixed admin user does not exist. Creating...")

            # Create fixed admin user
            admin = User(
                username=FIXED_ADMIN_USERNAME,
                email=FIXED_ADMIN_EMAIL,
                full_name=FIXED_ADMIN_FULLNAME,
                hashed_password=get_password_hash(_fixed_admin_password()),
                role=UserRole.ADMIN,
                is_active=True,
                is_verified=True,
                department="System",
                location="System",
            )

            session.add(admin)
            await session.commit()
            await session.refresh(admin)

            print("   ✅ Fixed admin user created successfully!")
            print(f"   ID: {admin.id}")
            print(f"   Username: {admin.username}")
            print(f"   Email: {admin.email}")

        print("\n" + "=" * 70)
        print("Fixed admin identity:")
        print("=" * 70)
        print(f"Username: {FIXED_ADMIN_USERNAME}")
        print(f"Email:    {FIXED_ADMIN_EMAIL}")
        print(
            "Password: taken from ADMIN_PASSWORD or FIXED_ADMIN_PASSWORD (not printed)"
        )
        print("Role:     admin")
        print("=" * 70)
        print("\n⚠️  IMPORTANT: This user CANNOT be deleted or deactivated")
        print("   This ensures you always have system access")
        print("\n🌐 Login at: http://localhost:3000/login")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(ensure_fixed_admin())
