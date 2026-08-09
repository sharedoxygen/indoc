"""
Unit tests for security module
"""
import pytest
from datetime import datetime, timedelta
from jose import jwt, JWTError

from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_token,
    FieldEncryption
)
from app.core.config import settings


class TestPasswordSecurity:
    """Test password hashing and verification"""
    
    def test_password_hashing(self):
        """Test password hashing"""
        password = "test_password_123"
        hashed = get_password_hash(password)
        
        assert hashed != password
        assert len(hashed) > 50  # bcrypt hashes are typically 60 chars
        assert hashed.startswith("$2b$")  # bcrypt identifier
    
    def test_password_verification(self):
        """Test password verification"""
        password = "test_password_123"
        hashed = get_password_hash(password)
        
        # Correct password should verify
        assert verify_password(password, hashed) is True
        
        # Incorrect password should not verify
        assert verify_password("wrong_password", hashed) is False
        assert verify_password("", hashed) is False
    
    def test_different_passwords_different_hashes(self):
        """Test that different passwords produce different hashes"""
        password1 = "password123"
        password2 = "password456"
        
        hash1 = get_password_hash(password1)
        hash2 = get_password_hash(password2)
        
        assert hash1 != hash2
    
    def test_same_password_different_hashes(self):
        """Test that same password produces different hashes (salt)"""
        password = "test_password"
        
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        # Hashes should be different due to salt
        assert hash1 != hash2
        
        # But both should verify the same password
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestJWTTokens:
    """Test JWT token creation and validation"""
    
    def test_create_access_token(self):
        """Test JWT token creation"""
        data = {"sub": "123", "username": "testuser"}
        token = create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 100  # JWT tokens are long
        assert token.count(".") == 2  # JWT has 3 parts separated by dots
    
    def test_create_token_with_expiration(self):
        """Test JWT token with custom expiration"""
        data = {"sub": "123"}
        expires_delta = timedelta(minutes=30)
        token = create_access_token(data, expires_delta)
        
        # Decode without verification to check expiration
        payload = jwt.decode(token, key="", options={"verify_signature": False})
        
        # Check that expiration field exists and contains expected data
        assert "exp" in payload
        assert "sub" in payload
        assert payload["sub"] == "123"
        
        # Just verify expiration is a numeric timestamp
        exp_timestamp = payload["exp"]
        assert isinstance(exp_timestamp, (int, float))
    
    def test_decode_valid_token(self):
        """Test decoding valid JWT token"""
        data = {"sub": "123", "username": "testuser"}
        token = create_access_token(data)
        
        decoded = decode_token(token)
        
        assert decoded["sub"] == "123"
        assert decoded["username"] == "testuser"
        assert "exp" in decoded
    
    def test_decode_invalid_token(self):
        """Test decoding invalid JWT token"""
        invalid_token = "invalid.jwt.token"
        
        with pytest.raises(Exception):  # Should raise HTTPException
            decode_token(invalid_token)
    
    def test_decode_expired_token(self):
        """Test decoding expired JWT token"""
        data = {"sub": "123"}
        expires_delta = timedelta(seconds=-1)  # Already expired
        token = create_access_token(data, expires_delta)
        
        with pytest.raises(Exception):  # Should raise HTTPException
            decode_token(token)
    
    def test_token_with_wrong_secret(self):
        """Test token created with different secret"""
        data = {"sub": "123"}
        
        # Create token with different secret
        wrong_token = jwt.encode(
            data, 
            "wrong_secret", 
            algorithm=settings.JWT_ALGORITHM
        )
        
        with pytest.raises(Exception):  # Should raise HTTPException
            decode_token(wrong_token)


class TestFieldEncryption:
    """Test field-level encryption"""
    
    def test_encrypt_decrypt_cycle(self):
        """Test encrypt/decrypt cycle"""
        encryption = FieldEncryption()
        original_text = "sensitive data that needs encryption"
        
        # Encrypt
        encrypted = encryption.encrypt(original_text)
        assert encrypted != original_text
        assert len(encrypted) > len(original_text)
        
        # Decrypt
        decrypted = encryption.decrypt(encrypted)
        assert decrypted == original_text
    
    def test_encrypt_empty_string(self):
        """Test encrypting empty string"""
        encryption = FieldEncryption()
        
        encrypted = encryption.encrypt("")
        decrypted = encryption.decrypt(encrypted)
        
        assert decrypted == ""
    
    def test_encrypt_unicode(self):
        """Test encrypting unicode characters"""
        encryption = FieldEncryption()
        unicode_text = "Hello 世界 🌍 Émojis"
        
        encrypted = encryption.encrypt(unicode_text)
        decrypted = encryption.decrypt(encrypted)
        
        assert decrypted == unicode_text
    
    def test_different_texts_different_encryption(self):
        """Test that different texts produce different encrypted values"""
        encryption = FieldEncryption()
        text1 = "first text"
        text2 = "second text"
        
        encrypted1 = encryption.encrypt(text1)
        encrypted2 = encryption.encrypt(text2)
        
        assert encrypted1 != encrypted2
    
    def test_same_text_different_encryption(self):
        """Test that same text can produce different encrypted values"""
        encryption = FieldEncryption()
        text = "same text"
        
        encrypted1 = encryption.encrypt(text)
        encrypted2 = encryption.encrypt(text)
        
        # With Fernet, same text produces different encrypted values due to random IV
        assert encrypted1 != encrypted2
        
        # But both should decrypt to the same original text
        assert encryption.decrypt(encrypted1) == text
        assert encryption.decrypt(encrypted2) == text
    
    def test_decrypt_invalid_data(self):
        """Test decrypting invalid encrypted data"""
        encryption = FieldEncryption()
        invalid_encrypted = "invalid_encrypted_data"
        
        with pytest.raises(Exception):  # Should raise cryptography exception
            encryption.decrypt(invalid_encrypted)
