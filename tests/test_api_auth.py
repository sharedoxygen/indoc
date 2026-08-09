"""
Integration tests for authentication API endpoints
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.crud.user import get_user_by_email


class TestAuthAPI:
    """Test authentication API endpoints"""
    
    async def test_register_user(self, client: AsyncClient, test_db: AsyncSession):
        """Test user registration"""
        user_data = {
            "email": "newuser@example.com",
            "username": "newuser",
            "full_name": "New User",
            "password": "password123",
            "role": "Viewer"
        }
        
        response = await client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["email"] == "newuser@example.com"
        assert data["username"] == "newuser"
        assert data["full_name"] == "New User"
        assert data["role"] == "Viewer"
        assert data["is_active"] is True
        assert data["is_verified"] is False
        assert "id" in data
        assert "created_at" in data
        
        # Verify user was created in database
        user = await get_user_by_email(test_db, "newuser@example.com")
        assert user is not None
        assert user.email == "newuser@example.com"
    
    async def test_register_duplicate_email(self, client: AsyncClient, test_user: User):
        """Test registration with duplicate email"""
        user_data = {
            "email": test_user.email,
            "username": "differentuser",
            "password": "password123"
        }
        
        response = await client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "email already registered" in data["detail"].lower()
    
    async def test_register_duplicate_username(self, client: AsyncClient, test_user: User):
        """Test registration with duplicate username"""
        user_data = {
            "email": "different@example.com",
            "username": test_user.username,
            "password": "password123"
        }
        
        response = await client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "username already exists" in data["detail"].lower()
    
    async def test_register_invalid_email(self, client: AsyncClient):
        """Test registration with invalid email"""
        user_data = {
            "email": "invalid-email",
            "username": "testuser",
            "password": "password123"
        }
        
        response = await client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 422  # Validation error
    
    async def test_register_missing_fields(self, client: AsyncClient):
        """Test registration with missing required fields"""
        user_data = {
            "email": "test@example.com"
            # Missing username and password
        }
        
        response = await client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 422  # Validation error
    
    async def test_login_success(self, client: AsyncClient, test_user: User):
        """Test successful login"""
        login_data = {
            "username": test_user.email,  # Can use email as username
            "password": "testpassword"
        }
        
        response = await client.post(
            "/api/v1/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 100  # JWT tokens are long
    
    async def test_login_with_username(self, client: AsyncClient, test_user: User):
        """Test login with username"""
        login_data = {
            "username": test_user.username,
            "password": "testpassword"
        }
        
        response = await client.post(
            "/api/v1/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
    
    async def test_login_wrong_password(self, client: AsyncClient, test_user: User):
        """Test login with wrong password"""
        login_data = {
            "username": test_user.email,
            "password": "wrongpassword"
        }
        
        response = await client.post(
            "/api/v1/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code == 401
        data = response.json()
        assert "incorrect" in data["detail"].lower()
    
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login with non-existent user"""
        login_data = {
            "username": "nonexistent@example.com",
            "password": "password123"
        }
        
        response = await client.post(
            "/api/v1/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code == 401
    
    async def test_login_inactive_user(self, client: AsyncClient, test_db: AsyncSession):
        """Test login with inactive user"""
        from app.crud.user import create_user, deactivate_user
        from app.schemas.auth import UserCreate
        
        # Create and deactivate user
        user_data = UserCreate(
            email="inactive@example.com",
            username="inactive",
            password="password123"
        )
        user = await create_user(test_db, user_data)
        await deactivate_user(test_db, user.id)
        
        login_data = {
            "username": "inactive@example.com",
            "password": "password123"
        }
        
        response = await client.post(
            "/api/v1/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code == 401
        data = response.json()
        assert "inactive" in data["detail"].lower()
    
    async def test_protected_endpoint_without_token(self, client: AsyncClient):
        """Test accessing protected endpoint without token"""
        response = await client.get("/api/v1/users/me")
        
        assert response.status_code == 401
        data = response.json()
        assert "not authenticated" in data["detail"].lower()
    
    async def test_protected_endpoint_with_invalid_token(self, client: AsyncClient):
        """Test accessing protected endpoint with invalid token"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = await client.get("/api/v1/users/me", headers=headers)
        
        assert response.status_code == 401
        data = response.json()
        assert "could not validate credentials" in data["detail"].lower()
    
    async def test_protected_endpoint_with_valid_token(self, client: AsyncClient, test_token: str, test_user: User):
        """Test accessing protected endpoint with valid token"""
        headers = {"Authorization": f"Bearer {test_token}"}
        response = await client.get("/api/v1/users/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == test_user.id
        assert data["email"] == test_user.email
        assert data["username"] == test_user.username
    
    async def test_get_current_user(self, client: AsyncClient, test_token: str, test_user: User):
        """Test getting current user information"""
        headers = {"Authorization": f"Bearer {test_token}"}
        response = await client.get("/api/v1/users/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == test_user.id
        assert data["email"] == test_user.email
        assert data["username"] == test_user.username
        assert data["role"] == test_user.role.value
        assert data["is_active"] == test_user.is_active
        assert "hashed_password" not in data  # Should not expose password
    
    async def test_token_expiration_format(self, client: AsyncClient, test_user: User):
        """Test that token contains proper expiration"""
        from jose import jwt
        from app.core.config import settings
        
        login_data = {
            "username": test_user.email,
            "password": "testpassword"
        }
        
        response = await client.post(
            "/api/v1/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code == 200
        data = response.json()
        token = data["access_token"]
        
        # Decode token without verification to check structure
        payload = jwt.decode(token, key="", options={"verify_signature": False})
        
        assert "sub" in payload  # Subject (user email)
        assert "exp" in payload  # Expiration
        assert payload["sub"] == test_user.email  # Now using email instead of ID
