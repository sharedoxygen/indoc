"""
MFA (Multi-Factor Authentication) utilities using TOTP
"""
import pyotp
import secrets
import json
from typing import List, Tuple
from cryptography.fernet import Fernet
from app.core.config import settings


def generate_totp_secret() -> str:
    """Generate a random base32 TOTP secret"""
    return pyotp.random_base32()


def generate_backup_codes(count: int = 10) -> List[str]:
    """Generate backup codes for account recovery"""
    return [secrets.token_hex(4).upper() for _ in range(count)]


def encrypt_backup_codes(codes: List[str], encryption_key: str) -> str:
    """Encrypt backup codes using Fernet symmetric encryption"""
    fernet = Fernet(encryption_key.encode())
    codes_json = json.dumps(codes)
    encrypted = fernet.encrypt(codes_json.encode())
    return encrypted.decode()


def decrypt_backup_codes(encrypted_codes: str, encryption_key: str) -> List[str]:
    """Decrypt backup codes"""
    fernet = Fernet(encryption_key.encode())
    decrypted = fernet.decrypt(encrypted_codes.encode())
    return json.loads(decrypted.decode())


def generate_provisioning_uri(secret: str, email: str, issuer: str = None) -> str:
    """
    Generate otpauth:// URI for QR code generation
    
    Args:
        secret: Base32 encoded TOTP secret
        email: User's email address
        issuer: Issuer name (defaults to settings.MFA_ISSUER_NAME)
    
    Returns:
        otpauth:// URI string
    """
    if issuer is None:
        issuer = settings.MFA_ISSUER_NAME
    
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=issuer)


def verify_totp(secret: str, token: str, valid_window: int = 1) -> bool:
    """
    Verify a TOTP token
    
    Args:
        secret: Base32 encoded TOTP secret
        token: 6-digit TOTP code
        valid_window: Number of time steps to check (default 1 = ±30s)
    
    Returns:
        True if token is valid, False otherwise
    """
    totp = pyotp.TOTP(secret)
    return totp.verify(token, valid_window=valid_window)


def verify_backup_code(
    encrypted_codes: str,
    encryption_key: str,
    provided_code: str
) -> Tuple[bool, str]:
    """
    Verify a backup code and remove it from the list
    
    Args:
        encrypted_codes: Encrypted JSON array of backup codes
        encryption_key: Fernet encryption key
        provided_code: User-provided backup code
    
    Returns:
        Tuple of (is_valid, updated_encrypted_codes)
    """
    codes = decrypt_backup_codes(encrypted_codes, encryption_key)
    
    # Normalize for comparison
    provided_normalized = provided_code.upper().replace("-", "")
    codes_normalized = [c.replace("-", "") for c in codes]
    
    if provided_normalized in codes_normalized:
        # Remove the used code
        idx = codes_normalized.index(provided_normalized)
        codes.pop(idx)
        
        # Re-encrypt the remaining codes
        if codes:
            updated_encrypted = encrypt_backup_codes(codes, encryption_key)
        else:
            updated_encrypted = ""
        
        return True, updated_encrypted
    
    return False, encrypted_codes


def is_mfa_required_for_role(role: str) -> bool:
    """
    Check if MFA is required for a given role
    
    Args:
        role: User role string
    
    Returns:
        True if MFA is required for this role (when MFA_ENABLED=true)
    """
    return role in settings.MFA_REQUIRED_ROLES


