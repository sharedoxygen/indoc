#!/usr/bin/env python3
"""
Update seed generator to assign RBAC roles after user creation
This runs as a post-processing step after enterprise_seed_generator
"""
import sys
import asyncio
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import AsyncSessionLocal
from app.models.user import User, UserRole as UserRoleEnum
from app.models.role import Role, UserRole as UserRoleModel
from sqlalchemy import select

async def assign_rbac_roles_to_seeds():
    """
    Ensure all seed users have RBAC roles assigned based on their UserRole enum
    This complements the existing migration and handles newly seeded users
    """
    print("🔄 Assigning RBAC roles to seed users...\n")
    
    async with AsyncSessionLocal() as session:
        # Get role mapping
        admin_role = (await session.execute(select(Role).where(Role.name == 'admin'))).scalars().first()
        manager_role = (await session.execute(select(Role).where(Role.name == 'manager'))).scalars().first()
        analyst_role = (await session.execute(select(Role).where(Role.name == 'analyst'))).scalars().first()
        
        if not all([admin_role, manager_role, analyst_role]):
            print("❌ System roles not found. Run seed_rbac_system.py first!")
            return
        
        role_map = {
            UserRoleEnum.ADMIN: admin_role,
            UserRoleEnum.MANAGER: manager_role,
            UserRoleEnum.ANALYST: analyst_role,
            # Legacy roles
            UserRoleEnum.REVIEWER: analyst_role,
            UserRoleEnum.UPLOADER: analyst_role,
            UserRoleEnum.VIEWER: analyst_role,
            UserRoleEnum.COMPLIANCE: analyst_role,
        }
        
        # Get all users
        result = await session.execute(select(User))
        users = result.scalars().all()
        
        assigned = 0
        skipped = 0
        
        for user in users:
            rbac_role = role_map.get(user.role)
            if not rbac_role:
                continue
            
            # Check if user already has this role
            existing = await session.execute(
                select(UserRoleModel).where(
                    UserRoleModel.user_id == user.id,
                    UserRoleModel.role_id == rbac_role.id
                )
            )
            if existing.scalars().first():
                skipped += 1
                continue
            
            # Assign role
            ur = UserRoleModel(user_id=user.id, role_id=rbac_role.id)
            session.add(ur)
            assigned += 1
            
            if assigned % 20 == 0:
                print(f"   Processed {assigned + skipped} users...")
        
        await session.commit()
        
        print(f"\n✅ Complete!")
        print(f"   Assigned: {assigned}")
        print(f"   Already had roles: {skipped}")
        print(f"   Total: {assigned + skipped}")

if __name__ == "__main__":
    asyncio.run(assign_rbac_roles_to_seeds())

