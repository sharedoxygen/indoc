#!/usr/bin/env python3
"""
Seed RBAC system with roles, permissions, and migrate existing users
"""
import sys
import asyncio
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import AsyncSessionLocal
from app.models.role import Role, Permission, UserRole as UserRoleModel, RolePermission
from app.models.user import User, UserRole as UserRoleEnum
from sqlalchemy import select

# System Roles
SYSTEM_ROLES = [
    {
        "name": "admin",
        "description": "Full system access - can perform all operations",
        "is_system": True
    },
    {
        "name": "manager",
        "description": "Manage documents, view analytics, manage team members",
        "is_system": True
    },
    {
        "name": "analyst",
        "description": "Create and view own documents, use chat and search",
        "is_system": True
    }
]

# All Permissions
ALL_PERMISSIONS = [
    # Document permissions
    {"name": "documents.create", "resource": "documents", "action": "create", "description": "Create new documents"},
    {"name": "documents.read", "resource": "documents", "action": "read", "description": "View documents"},
    {"name": "documents.update", "resource": "documents", "action": "update", "description": "Edit document metadata"},
    {"name": "documents.delete", "resource": "documents", "action": "delete", "description": "Delete documents"},
    {"name": "documents.list", "resource": "documents", "action": "list", "description": "List/search documents"},
    {"name": "documents.download", "resource": "documents", "action": "download", "description": "Download document files"},
    {"name": "documents.share", "resource": "documents", "action": "share", "description": "Share documents with others"},
    
    # User permissions
    {"name": "users.create", "resource": "users", "action": "create", "description": "Create new users"},
    {"name": "users.read", "resource": "users", "action": "read", "description": "View user details"},
    {"name": "users.update", "resource": "users", "action": "update", "description": "Edit user information"},
    {"name": "users.delete", "resource": "users", "action": "delete", "description": "Delete users"},
    {"name": "users.list", "resource": "users", "action": "list", "description": "List users"},
    {"name": "users.assign_roles", "resource": "users", "action": "assign_roles", "description": "Assign roles to users"},
    
    # Role permissions
    {"name": "roles.create", "resource": "roles", "action": "create", "description": "Create new roles"},
    {"name": "roles.read", "resource": "roles", "action": "read", "description": "View role details"},
    {"name": "roles.update", "resource": "roles", "action": "update", "description": "Edit roles"},
    {"name": "roles.delete", "resource": "roles", "action": "delete", "description": "Delete custom roles"},
    {"name": "roles.list", "resource": "roles", "action": "list", "description": "List all roles"},
    {"name": "roles.assign_permissions", "resource": "roles", "action": "assign_permissions", "description": "Manage role permissions"},
    
    # System permissions
    {"name": "system.admin", "resource": "system", "action": "admin", "description": "Full admin access (wildcard)"},
    {"name": "analytics.view", "resource": "analytics", "action": "view", "description": "View analytics dashboards"},
    {"name": "audit.view", "resource": "audit", "action": "view", "description": "View audit logs"},
    {"name": "settings.manage", "resource": "settings", "action": "manage", "description": "Manage system settings"},
    
    # Chat & Search
    {"name": "chat.use", "resource": "chat", "action": "use", "description": "Use chat functionality"},
    {"name": "search.use", "resource": "search", "action": "use", "description": "Use search functionality"},
]

# Role-Permission Mapping
ROLE_PERMISSIONS = {
    "admin": ["system.admin"],  # Admin has wildcard, gets all permissions
    "manager": [
        "documents.create", "documents.read", "documents.update", "documents.delete",
        "documents.list", "documents.download", "documents.share",
        "users.read", "users.list",
        "analytics.view",
        "chat.use", "search.use"
    ],
    "analyst": [
        "documents.create", "documents.read", "documents.update",  # Own documents only
        "documents.list", "documents.download",
        "chat.use", "search.use"
    ]
}


async def seed_rbac():
    """Seed RBAC system"""
    print("🌱 Seeding RBAC System\n")
    print("=" * 70)
    
    async with AsyncSessionLocal() as session:
        # Step 1: Create Roles
        print("\n1️⃣  Creating system roles...")
        role_map = {}
        for role_data in SYSTEM_ROLES:
            # Check if exists
            result = await session.execute(
                select(Role).where(Role.name == role_data["name"])
            )
            role = result.scalars().first()
            
            if not role:
                role = Role(**role_data)
                session.add(role)
                await session.flush()
                print(f"   ✅ Created role: {role.name}")
            else:
                print(f"   ℹ️  Role already exists: {role.name}")
            
            role_map[role.name] = role
        
        await session.commit()
        
        # Step 2: Create Permissions
        print("\n2️⃣  Creating permissions...")
        permission_map = {}
        for perm_data in ALL_PERMISSIONS:
            # Check if exists
            result = await session.execute(
                select(Permission).where(Permission.name == perm_data["name"])
            )
            perm = result.scalars().first()
            
            if not perm:
                perm = Permission(**perm_data)
                session.add(perm)
                await session.flush()
                print(f"   ✅ Created permission: {perm.name}")
            else:
                print(f"   ℹ️  Permission already exists: {perm.name}")
            
            permission_map[perm.name] = perm
        
        await session.commit()
        
        # Step 3: Assign Permissions to Roles
        print("\n3️⃣  Assigning permissions to roles...")
        for role_name, perm_names in ROLE_PERMISSIONS.items():
            role = role_map[role_name]
            for perm_name in perm_names:
                perm = permission_map[perm_name]
                
                # Check if already assigned
                result = await session.execute(
                    select(RolePermission).where(
                        RolePermission.role_id == role.id,
                        RolePermission.permission_id == perm.id
                    )
                )
                existing = result.scalars().first()
                
                if not existing:
                    rp = RolePermission(role_id=role.id, permission_id=perm.id)
                    session.add(rp)
                    print(f"   ✅ {role_name} → {perm_name}")
        
        await session.commit()
        
        # Step 4: Migrate existing users to user_roles
        print("\n4️⃣  Migrating existing users to RBAC...")
        result = await session.execute(select(User))
        users = result.scalars().all()
        
        migrated = 0
        for user in users:
            # Map old role enum to new role name
            role_name_map = {
                UserRoleEnum.ADMIN: "admin",
                UserRoleEnum.MANAGER: "manager",
                UserRoleEnum.ANALYST: "analyst",
                # Legacy roles → analyst
                UserRoleEnum.REVIEWER: "analyst",
                UserRoleEnum.UPLOADER: "analyst",
                UserRoleEnum.VIEWER: "analyst",
                UserRoleEnum.COMPLIANCE: "analyst",
            }
            
            role_name = role_name_map.get(user.role, "analyst")
            role = role_map[role_name]
            
            # Check if user already has this role
            result = await session.execute(
                select(UserRoleModel).where(
                    UserRoleModel.user_id == user.id,
                    UserRoleModel.role_id == role.id
                )
            )
            existing = result.scalars().first()
            
            if not existing:
                ur = UserRoleModel(user_id=user.id, role_id=role.id)
                session.add(ur)
                migrated += 1
                print(f"   ✅ {user.username} ({user.role.value}) → {role_name} role")
        
        await session.commit()
        
        print(f"\n   Migrated {migrated} users")
        
        print("\n" + "=" * 70)
        print("✅ RBAC SYSTEM SEEDED SUCCESSFULLY!")
        print("=" * 70)
        print(f"\n📊 Summary:")
        print(f"   Roles: {len(SYSTEM_ROLES)}")
        print(f"   Permissions: {len(ALL_PERMISSIONS)}")
        print(f"   Users migrated: {migrated}")
        print("\n🔐 All users now have role-based access via RBAC!")


if __name__ == "__main__":
    asyncio.run(seed_rbac())

