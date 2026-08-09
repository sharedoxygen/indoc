"""
CRUD operations for User management
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.core.security import get_password_hash, verify_password
from app.schemas.auth import UserCreate, UserUpdate


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """Get user by ID"""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Get user by email"""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """Get user by username"""
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def get_users(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    role: Optional[UserRole] = None
) -> List[User]:
    """Get list of users with optional filtering"""
    query = select(User)
    
    if role:
        query = query.where(User.role == role)
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def create_user(db: AsyncSession, user_data: UserCreate) -> User:
    """Create a new user"""
    user = User(
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        hashed_password=get_password_hash(user_data.password),
        role=UserRole(user_data.role) if user_data.role else UserRole.VIEWER,
        is_active=True,
        is_verified=False
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user(
    db: AsyncSession,
    user_id: int,
    user_update: UserUpdate
) -> Optional[User]:
    """Update user information"""
    user = await get_user_by_id(db, user_id)
    
    if not user:
        return None
    
    update_data = user_update.dict(exclude_unset=True)
    
    # Handle role update
    if 'role' in update_data and update_data['role']:
        update_data['role'] = UserRole(update_data['role'])
    
    for field, value in update_data.items():
        setattr(user, field, value)
    
    await db.commit()
    await db.refresh(user)
    return user


async def update_user_password(
    db: AsyncSession,
    user_id: int,
    new_password: str
) -> bool:
    """Update user password"""
    result = await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(hashed_password=get_password_hash(new_password))
    )
    await db.commit()
    return result.rowcount > 0


async def delete_user(db: AsyncSession, user_id: int) -> bool:
    """Delete a user"""
    result = await db.execute(
        delete(User).where(User.id == user_id)
    )
    await db.commit()
    return result.rowcount > 0


async def authenticate_user(
    db: AsyncSession,
    username: str,
    password: str
) -> Optional[User]:
    """Authenticate user by username/email and password"""
    # Try to find user by email first
    user = await get_user_by_email(db, username)
    
    # If not found, try username
    if not user:
        user = await get_user_by_username(db, username)
    
    # Verify password
    if user and verify_password(password, user.hashed_password):
        return user
    
    return None


async def verify_user(db: AsyncSession, user_id: int) -> bool:
    """Mark user as verified"""
    result = await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(is_verified=True)
    )
    await db.commit()
    return result.rowcount > 0


async def activate_user(db: AsyncSession, user_id: int) -> bool:
    """Activate a user account"""
    result = await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(is_active=True)
    )
    await db.commit()
    return result.rowcount > 0


async def deactivate_user(db: AsyncSession, user_id: int) -> bool:
    """Deactivate a user account"""
    result = await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(is_active=False)
    )
    await db.commit()
    return result.rowcount > 0


async def get_user_count(db: AsyncSession) -> int:
    """Get total number of users"""
    result = await db.execute(select(func.count()).select_from(User))
    return result.scalar()


async def get_users_by_role(db: AsyncSession, role: UserRole) -> List[User]:
    """Get all users with a specific role"""
    result = await db.execute(
        select(User).where(User.role == role)
    )
    return result.scalars().all()