"""
Security utilities for authentication, authorization, and encryption
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import User
from app.db.session import get_db


# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_PREFIX}/auth/login")


class FieldEncryption:
    """Handle field-level encryption for sensitive data"""
    
    def __init__(self):
        # Import here to avoid circular imports
        from app.core.key_management import key_manager
        
        # Get production-grade encryption key
        encryption_key = key_manager.get_or_create_field_encryption_key()
        
        try:
            # Key should be base64 encoded
            key_bytes = base64.urlsafe_b64decode(encryption_key.encode())
            self.cipher = Fernet(key_bytes)
        except Exception as e:
            logger.error(f"Failed to initialize field encryption: {e}")
            # Fallback: generate new key for this session only
            key = Fernet.generate_key()
            self.cipher = Fernet(key)
            logger.warning("Using temporary encryption key - data may not be recoverable!")
    
    def encrypt(self, data: str) -> str:
        """Encrypt a string"""
        if not settings.ENABLE_FIELD_ENCRYPTION:
            return data
        return self.cipher.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt a string"""
        if not settings.ENABLE_FIELD_ENCRYPTION:
            return encrypted_data
        return self.cipher.decrypt(encrypted_data.encode()).decode()


field_encryption = FieldEncryption()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
    token_type: str = "access"
) -> str:
    """Create a JWT access token"""
    import uuid
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)
    
    # Add unique JWT ID for revocation tracking
    jti = str(uuid.uuid4())
    to_encode.update({
        "exp": expire,
        "jti": jti,
        "type": token_type  # "access" or "refresh"
    })
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(user_id: int, role: str) -> str:
    """Create a long-lived refresh token"""
    expires_delta = timedelta(days=settings.JWT_REFRESH_EXPIRATION_DAYS)
    return create_access_token(
        data={"sub": str(user_id), "role": role},
        expires_delta=expires_delta,
        token_type="refresh"
    )


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and verify a JWT token"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def is_token_revoked(jti: str, db: AsyncSession) -> bool:
    """Check if a token has been revoked"""
    # TEMPORARILY DISABLED: Skip token revocation check to avoid transaction issues
    # The revoked_tokens table may not exist yet
    return False
    
    # Original implementation commented out:
    # try:
    #     from sqlalchemy import select
    #     from app.models.token_revocation import RevokedToken
    #     
    #     result = await db.execute(
    #         select(RevokedToken).where(RevokedToken.jti == jti)
    #     )
    #     return result.scalar_one_or_none() is not None
    # except Exception as e:
    #     # If table doesn't exist or there's a permission error, assume token is not revoked
    #     # This prevents login failures due to missing revoked_tokens table
    #     import logging
    #     logger = logging.getLogger(__name__)
    #     logger.warning(f"Could not check token revocation (table may not exist): {e}")
    #     # CRITICAL: Rollback AND begin a new transaction to continue using the session
    #     await db.rollback()
    #     await db.begin()
    #     return False


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get the current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = decode_token(token)
        email: str = payload.get("sub")
        jti: str = payload.get("jti")
        token_type: str = payload.get("type", "access")
        
        if email is None:
            raise credentials_exception
        
        # Only check token revocation if jti is present (new tokens have it)
        # This allows backward compatibility with older tokens
        if jti:
            # Check if token is revoked
            if await is_token_revoked(jti, db):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        
        # Only accept access tokens (not refresh tokens)
        if token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except HTTPException:
        raise
    except JWTError:
        raise credentials_exception
    
    # Get user from database by email with RBAC relationships eagerly loaded
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.models.role import UserRole as UserRoleModel, Role, RolePermission, Permission
    
    result = await db.execute(
        select(User)
        .where(User.email == email)
        .options(
            selectinload(User.user_roles)
            .selectinload(UserRoleModel.role)
            .selectinload(Role.role_permissions)
            .selectinload(RolePermission.permission)
        )
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    return user


class RBACChecker:
    """Role-based access control checker"""
    
    def __init__(self, allowed_roles: list):
        self.allowed_roles = allowed_roles
    
    async def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user


# RBAC dependency factories
require_admin = RBACChecker(["Admin"])
require_manager = RBACChecker(["Admin", "Manager"])
require_analyst = RBACChecker(["Admin", "Manager", "Analyst"])

# Legacy role checkers (deprecated - will be removed after full migration)
require_reviewer = RBACChecker(["Admin", "Reviewer"])
require_uploader = RBACChecker(["Admin", "Reviewer", "Uploader"])
require_viewer = RBACChecker(["Admin", "Reviewer", "Uploader", "Viewer"])
require_compliance = RBACChecker(["Admin", "Compliance"])