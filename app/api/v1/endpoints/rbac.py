"""
RBAC Management API Endpoints
"""
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from pydantic import BaseModel

from app.db.session import get_db
from app.models.user import User
from app.models.role import Role, Permission, UserRole as UserRoleModel, RolePermission
from app.core.security import get_current_user
from app.core.rbac import require_permission, require_role

router = APIRouter()


# Pydantic Schemas
class RoleCreate(BaseModel):
    name: str
    description: Optional[str] = None

class RoleUpdate(BaseModel):
    description: Optional[str] = None
    is_active: Optional[bool] = None

class RoleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    is_system: bool
    is_active: bool
    
    class Config:
        from_attributes = True

class PermissionResponse(BaseModel):
    id: int
    name: str
    resource: str
    action: str
    description: Optional[str]
    
    class Config:
        from_attributes = True

class UserRoleAssignment(BaseModel):
    user_id: int
    role_id: int
    expires_at: Optional[str] = None

class RolePermissionAssignment(BaseModel):
    role_id: int
    permission_id: int


# ==================== ROLE ENDPOINTS ====================

@router.get("/roles", response_model=List[RoleResponse])
async def list_roles(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all roles"""
    if (not current_user.has_permission("roles.list") and
        getattr(current_user.role, "value", current_user.role) != "Admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: requires 'roles.list'"
        )
    
    result = await db.execute(
        select(Role)
        .offset(skip)
        .limit(limit)
        .order_by(Role.name)
    )
    roles = result.scalars().all()
    return roles


@router.post("/roles", response_model=RoleResponse)
async def create_role(
    role_data: RoleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new custom role (admin only)"""
    if not current_user.has_permission("roles.create"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: requires 'roles.create'"
        )
    
    # Check if role already exists
    result = await db.execute(
        select(Role).where(Role.name == role_data.name)
    )
    existing = result.scalars().first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role '{role_data.name}' already exists"
        )
    
    # Create role
    role = Role(
        name=role_data.name,
        description=role_data.description,
        is_system=False,  # Custom roles are not system roles
        is_active=True
    )
    db.add(role)
    await db.commit()
    await db.refresh(role)
    
    return role


@router.get("/roles/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get role details"""
    if not current_user.has_permission("roles.read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: requires 'roles.read'"
        )
    
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalars().first()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    return role


@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    role_data: RoleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update role (admin only)"""
    if not current_user.has_permission("roles.update"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: requires 'roles.update'"
        )
    
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalars().first()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    # Cannot modify system roles
    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify system roles"
        )
    
    # Update fields
    if role_data.description is not None:
        role.description = role_data.description
    if role_data.is_active is not None:
        role.is_active = role_data.is_active
    
    await db.commit()
    await db.refresh(role)
    
    return role


@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete role (admin only, cannot delete system roles)"""
    if not current_user.has_permission("roles.delete"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: requires 'roles.delete'"
        )
    
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalars().first()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    # Cannot delete system roles
    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete system roles (admin, manager, analyst)"
        )
    
    await db.delete(role)
    await db.commit()
    
    return {"message": f"Role '{role.name}' deleted successfully"}


# ==================== PERMISSION ENDPOINTS ====================

@router.get("/permissions", response_model=List[PermissionResponse])
async def list_permissions(
    skip: int = 0,
    limit: int = 200,
    resource: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all permissions"""
    query = select(Permission).offset(skip).limit(limit).order_by(Permission.resource, Permission.action)
    
    if resource:
        query = query.where(Permission.resource == resource)
    
    result = await db.execute(query)
    permissions = result.scalars().all()
    return permissions


@router.get("/roles/{role_id}/permissions", response_model=List[PermissionResponse])
async def get_role_permissions(
    role_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all permissions for a role"""
    result = await db.execute(
        select(Permission)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == role_id)
    )
    permissions = result.scalars().all()
    return permissions


@router.post("/roles/{role_id}/permissions/{permission_id}")
async def assign_permission_to_role(
    role_id: int,
    permission_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Assign a permission to a role (admin only)"""
    if not current_user.has_permission("roles.assign_permissions"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: requires 'roles.assign_permissions'"
        )
    
    # Check if role and permission exist
    role_result = await db.execute(select(Role).where(Role.id == role_id))
    role = role_result.scalars().first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    perm_result = await db.execute(select(Permission).where(Permission.id == permission_id))
    permission = perm_result.scalars().first()
    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")
    
    # Check if already assigned
    existing = await db.execute(
        select(RolePermission).where(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission_id
        )
    )
    if existing.scalars().first():
        return {"message": "Permission already assigned to role"}
    
    # Assign permission
    rp = RolePermission(
        role_id=role_id,
        permission_id=permission_id,
        granted_by=current_user.id
    )
    db.add(rp)
    await db.commit()
    
    return {"message": f"Permission '{permission.name}' assigned to role '{role.name}'"}


@router.delete("/roles/{role_id}/permissions/{permission_id}")
async def remove_permission_from_role(
    role_id: int,
    permission_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove a permission from a role (admin only)"""
    if not current_user.has_permission("roles.assign_permissions"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )
    
    await db.execute(
        delete(RolePermission).where(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission_id
        )
    )
    await db.commit()
    
    return {"message": "Permission removed from role"}


# ==================== USER-ROLE ASSIGNMENT ENDPOINTS ====================

@router.get("/users/{user_id}/roles", response_model=List[RoleResponse])
async def get_user_roles(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all roles for a user"""
    # Users can view their own roles, admins/managers can view others
    if user_id != current_user.id and not current_user.has_permission("users.read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )
    
    result = await db.execute(
        select(Role)
        .join(UserRoleModel, UserRoleModel.role_id == Role.id)
        .where(UserRoleModel.user_id == user_id)
    )
    roles = result.scalars().all()
    return roles


@router.post("/users/{user_id}/roles/{role_id}")
async def assign_role_to_user(
    user_id: int,
    role_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Assign a role to a user (admin only)"""
    if not current_user.has_permission("users.assign_roles"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: requires 'users.assign_roles'"
        )
    
    # Check if user and role exist
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    role_result = await db.execute(select(Role).where(Role.id == role_id))
    role = role_result.scalars().first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # Check if already assigned
    existing = await db.execute(
        select(UserRoleModel).where(
            UserRoleModel.user_id == user_id,
            UserRoleModel.role_id == role_id
        )
    )
    if existing.scalars().first():
        return {"message": "Role already assigned to user"}
    
    # Assign role
    ur = UserRoleModel(
        user_id=user_id,
        role_id=role_id,
        assigned_by=current_user.id
    )
    db.add(ur)
    await db.commit()
    
    return {"message": f"Role '{role.name}' assigned to user '{user.username}'"}


@router.delete("/users/{user_id}/roles/{role_id}")
async def remove_role_from_user(
    user_id: int,
    role_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove a role from a user (admin only)"""
    if not current_user.has_permission("users.assign_roles"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )
    
    # Cannot remove admin role from fixed admin user
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalars().first()
    if user and user.username == "admin":
        role_result = await db.execute(select(Role).where(Role.id == role_id))
        role = role_result.scalars().first()
        if role and role.name == "admin":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove admin role from fixed admin user"
            )
    
    await db.execute(
        delete(UserRoleModel).where(
            UserRoleModel.user_id == user_id,
            UserRoleModel.role_id == role_id
        )
    )
    await db.commit()
    
    return {"message": "Role removed from user"}


@router.get("/users/{user_id}/permissions", response_model=List[PermissionResponse])
async def get_user_permissions(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all permissions for a user (from all their roles)"""
    # Users can view their own permissions
    if user_id != current_user.id and not current_user.has_permission("users.read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )
    
    # Get user
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get all permissions from user's roles
    result = await db.execute(
        select(Permission)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRoleModel, UserRoleModel.role_id == RolePermission.role_id)
        .where(UserRoleModel.user_id == user_id)
        .distinct()
    )
    permissions = result.scalars().all()
    return permissions

