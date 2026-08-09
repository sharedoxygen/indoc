"""
Unit tests for user CRUD operations
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.user import (
    get_user_by_id,
    get_user_by_email,
    get_user_by_username,
    get_users,
    create_user,
    update_user,
    delete_user,
    authenticate_user,
    verify_user,
    activate_user,
    deactivate_user,
    get_user_count,
    get_users_by_role
)
from app.schemas.auth import UserCreate, UserUpdate
from app.models.user import User, UserRole


class TestUserCRUD:
    """Test user CRUD operations"""
    
    async def test_get_user_by_id(self, test_db: AsyncSession, test_user: User):
        """Test getting user by ID"""
        user = await get_user_by_id(test_db, test_user.id)
        
        assert user is not None
        assert user.id == test_user.id
        assert user.email == test_user.email
        assert user.username == test_user.username
    
    async def test_get_user_by_id_not_found(self, test_db: AsyncSession):
        """Test getting non-existent user by ID"""
        user = await get_user_by_id(test_db, 99999)
        assert user is None
    
    async def test_get_user_by_email(self, test_db: AsyncSession, test_user: User):
        """Test getting user by email"""
        user = await get_user_by_email(test_db, test_user.email)
        
        assert user is not None
        assert user.id == test_user.id
        assert user.email == test_user.email
    
    async def test_get_user_by_email_not_found(self, test_db: AsyncSession):
        """Test getting non-existent user by email"""
        user = await get_user_by_email(test_db, "nonexistent@example.com")
        assert user is None
    
    async def test_get_user_by_username(self, test_db: AsyncSession, test_user: User):
        """Test getting user by username"""
        user = await get_user_by_username(test_db, test_user.username)
        
        assert user is not None
        assert user.id == test_user.id
        assert user.username == test_user.username
    
    async def test_get_user_by_username_not_found(self, test_db: AsyncSession):
        """Test getting non-existent user by username"""
        user = await get_user_by_username(test_db, "nonexistent")
        assert user is None
    
    async def test_create_user(self, test_db: AsyncSession):
        """Test creating a new user"""
        user_data = UserCreate(
            email="newuser@example.com",
            username="newuser",
            full_name="New User",
            password="password123",
            role="Uploader"
        )
        
        user = await create_user(test_db, user_data)
        
        assert user.id is not None
        assert user.email == "newuser@example.com"
        assert user.username == "newuser"
        assert user.full_name == "New User"
        assert user.role == UserRole.UPLOADER
        assert user.is_active is True
        assert user.is_verified is False
        
        # Verify password was hashed
        assert user.hashed_password != "password123"
        assert len(user.hashed_password) > 50
    
    async def test_create_user_default_role(self, test_db: AsyncSession):
        """Test creating user with default role"""
        user_data = UserCreate(
            email="defaultrole@example.com",
            username="defaultrole",
            password="password123"
        )
        
        user = await create_user(test_db, user_data)
        
        assert user.role == UserRole.VIEWER  # Default role
    
    async def test_get_users_list(self, test_db: AsyncSession, test_user: User, test_admin_user: User):
        """Test getting list of users"""
        users = await get_users(test_db, skip=0, limit=10)
        
        assert len(users) >= 2  # At least test_user and test_admin_user
        user_ids = [user.id for user in users]
        assert test_user.id in user_ids
        assert test_admin_user.id in user_ids
    
    async def test_get_users_with_pagination(self, test_db: AsyncSession):
        """Test getting users with pagination"""
        # Create additional users
        for i in range(5):
            user_data = UserCreate(
                email=f"user{i}@example.com",
                username=f"user{i}",
                password="password123"
            )
            await create_user(test_db, user_data)
        
        # Test pagination
        users_page1 = await get_users(test_db, skip=0, limit=3)
        users_page2 = await get_users(test_db, skip=3, limit=3)
        
        assert len(users_page1) == 3
        assert len(users_page2) >= 1
        
        # Ensure no overlap
        page1_ids = {user.id for user in users_page1}
        page2_ids = {user.id for user in users_page2}
        assert page1_ids.isdisjoint(page2_ids)
    
    async def test_get_users_by_role(self, test_db: AsyncSession, test_admin_user: User):
        """Test filtering users by role"""
        # Create users with different roles
        viewer_data = UserCreate(
            email="viewer@example.com",
            username="viewer",
            password="password123",
            role="Viewer"
        )
        await create_user(test_db, viewer_data)
        
        uploader_data = UserCreate(
            email="uploader@example.com",
            username="uploader",
            password="password123",
            role="Uploader"
        )
        await create_user(test_db, uploader_data)
        
        # Get admin users
        admin_users = await get_users(test_db, role=UserRole.ADMIN)
        assert len(admin_users) >= 1
        assert all(user.role == UserRole.ADMIN for user in admin_users)
        assert test_admin_user.id in [user.id for user in admin_users]
        
        # Get viewer users
        viewer_users = await get_users(test_db, role=UserRole.VIEWER)
        assert len(viewer_users) >= 1
        assert all(user.role == UserRole.VIEWER for user in viewer_users)
    
    async def test_update_user(self, test_db: AsyncSession, test_user: User):
        """Test updating user information"""
        update_data = UserUpdate(
            full_name="Updated Name",
            role="Admin"
        )
        
        updated_user = await update_user(test_db, test_user.id, update_data)
        
        assert updated_user is not None
        assert updated_user.id == test_user.id
        assert updated_user.full_name == "Updated Name"
        assert updated_user.role == UserRole.ADMIN
        assert updated_user.email == test_user.email  # Unchanged
    
    async def test_update_nonexistent_user(self, test_db: AsyncSession):
        """Test updating non-existent user"""
        update_data = UserUpdate(full_name="New Name")
        
        updated_user = await update_user(test_db, 99999, update_data)
        assert updated_user is None
    
    async def test_delete_user(self, test_db: AsyncSession):
        """Test deleting a user"""
        # Create user to delete
        user_data = UserCreate(
            email="todelete@example.com",
            username="todelete",
            password="password123"
        )
        user = await create_user(test_db, user_data)
        user_id = user.id
        
        # Delete user
        success = await delete_user(test_db, user_id)
        assert success is True
        
        # Verify user is deleted
        deleted_user = await get_user_by_id(test_db, user_id)
        assert deleted_user is None
    
    async def test_delete_nonexistent_user(self, test_db: AsyncSession):
        """Test deleting non-existent user"""
        success = await delete_user(test_db, 99999)
        assert success is False
    
    async def test_authenticate_user_by_email(self, test_db: AsyncSession, test_user: User):
        """Test authenticating user by email"""
        user = await authenticate_user(test_db, test_user.email, "testpassword")
        
        assert user is not None
        assert user.id == test_user.id
        assert user.email == test_user.email
    
    async def test_authenticate_user_by_username(self, test_db: AsyncSession, test_user: User):
        """Test authenticating user by username"""
        user = await authenticate_user(test_db, test_user.username, "testpassword")
        
        assert user is not None
        assert user.id == test_user.id
        assert user.username == test_user.username
    
    async def test_authenticate_user_wrong_password(self, test_db: AsyncSession, test_user: User):
        """Test authentication with wrong password"""
        user = await authenticate_user(test_db, test_user.email, "wrongpassword")
        assert user is None
    
    async def test_authenticate_nonexistent_user(self, test_db: AsyncSession):
        """Test authenticating non-existent user"""
        user = await authenticate_user(test_db, "nonexistent@example.com", "password")
        assert user is None
    
    async def test_verify_user(self, test_db: AsyncSession, test_user: User):
        """Test verifying a user"""
        # User should start unverified
        assert test_user.is_verified is False
        
        success = await verify_user(test_db, test_user.id)
        assert success is True
        
        # Check user is now verified
        updated_user = await get_user_by_id(test_db, test_user.id)
        assert updated_user.is_verified is True
    
    async def test_activate_user(self, test_db: AsyncSession):
        """Test activating a user"""
        # Create inactive user
        user_data = UserCreate(
            email="inactive@example.com",
            username="inactive",
            password="password123"
        )
        user = await create_user(test_db, user_data)
        
        # Deactivate first
        await deactivate_user(test_db, user.id)
        
        # Now activate
        success = await activate_user(test_db, user.id)
        assert success is True
        
        # Check user is active
        updated_user = await get_user_by_id(test_db, user.id)
        assert updated_user.is_active is True
    
    async def test_deactivate_user(self, test_db: AsyncSession, test_user: User):
        """Test deactivating a user"""
        # User should start active
        assert test_user.is_active is True
        
        success = await deactivate_user(test_db, test_user.id)
        assert success is True
        
        # Check user is now inactive
        updated_user = await get_user_by_id(test_db, test_user.id)
        assert updated_user.is_active is False
    
    async def test_get_user_count(self, test_db: AsyncSession, test_user: User, test_admin_user: User):
        """Test getting total user count"""
        count = await get_user_count(test_db)
        
        assert count >= 2  # At least test_user and test_admin_user
        assert isinstance(count, int)
    
    async def test_get_users_by_role_function(self, test_db: AsyncSession, test_admin_user: User):
        """Test getting users by specific role"""
        admin_users = await get_users_by_role(test_db, UserRole.ADMIN)
        
        assert len(admin_users) >= 1
        assert all(user.role == UserRole.ADMIN for user in admin_users)
        assert test_admin_user.id in [user.id for user in admin_users]
