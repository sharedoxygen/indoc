"""
Production-grade key management for inDoc with vault integration
"""
import os
import secrets
import base64
from pathlib import Path
from typing import Optional, Dict
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

logger = logging.getLogger(__name__)


class KeyManager:
    """Secure key management for production environments with vault support"""
    
    def __init__(self, use_vault: bool = False):
        self.key_dir = Path("/etc/indoc/keys")  # Production key directory
        self.dev_key_dir = Path("./keys")       # Development key directory
        self.use_vault = use_vault
        
        # Use production directory if it exists, otherwise dev directory
        if self.key_dir.exists() and os.access(self.key_dir, os.R_OK):
            self.active_key_dir = self.key_dir
        else:
            self.active_key_dir = self.dev_key_dir
            self.active_key_dir.mkdir(exist_ok=True)
    
    def generate_master_key(self) -> str:
        """Generate a new master encryption key"""
        key = Fernet.generate_key()
        return base64.urlsafe_b64encode(key).decode('utf-8')
    
    def generate_jwt_secret(self, length: int = 64) -> str:
        """Generate a cryptographically secure JWT secret"""
        return secrets.token_urlsafe(length)
    
    def derive_key_from_password(self, password: str, salt: bytes) -> bytes:
        """Derive encryption key from password using PBKDF2"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,  # OWASP recommended minimum
        )
        return kdf.derive(password.encode())
    
    def get_or_create_field_encryption_key(self) -> str:
        """
        Get existing field encryption key or create new one
        
        If vault is enabled, try to get from vault first, then fall back to file
        """
        # Try vault first if enabled
        if self.use_vault:
            try:
                from app.core.secrets_vault import get_secret
                vault_key = get_secret("FIELD_ENCRYPTION_KEY")
                if vault_key:
                    logger.info("Using field encryption key from vault")
                    return vault_key
            except Exception as e:
                logger.warning(f"Failed to get key from vault, falling back to file: {e}")
        
        # Fall back to file-based key management
        key_file = self.active_key_dir / "field_encryption.key"
        
        try:
            if key_file.exists():
                with open(key_file, 'r') as f:
                    key = f.read().strip()
                    # Validate key format
                    try:
                        base64.urlsafe_b64decode(key.encode())
                        logger.info("Using existing field encryption key from file")
                        return key
                    except Exception:
                        logger.warning("Invalid existing key, generating new one")
            
            # Generate new key
            key = self.generate_master_key()
            
            # Save key with secure permissions
            key_file.parent.mkdir(parents=True, exist_ok=True)
            with open(key_file, 'w') as f:
                f.write(key)
            
            # Set secure file permissions (owner read/write only)
            os.chmod(key_file, 0o600)
            
            logger.info(f"Generated new field encryption key: {key_file}")
            return key
            
        except Exception as e:
            logger.error(f"Error managing field encryption key: {e}")
            # Fallback to environment variable or generated key
            return os.getenv('FIELD_ENCRYPTION_KEY', self.generate_master_key())
    
    def get_or_create_jwt_secret(self) -> str:
        """Get existing JWT secret or create new one"""
        key_file = self.active_key_dir / "jwt_secret.key"
        
        try:
            if key_file.exists():
                with open(key_file, 'r') as f:
                    secret = f.read().strip()
                    if len(secret) >= 32:  # Minimum 32 characters
                        logger.info("Using existing JWT secret")
                        return secret
                    else:
                        logger.warning("JWT secret too short, generating new one")
            
            # Generate new secret
            secret = self.generate_jwt_secret()
            
            # Save secret with secure permissions
            key_file.parent.mkdir(parents=True, exist_ok=True)
            with open(key_file, 'w') as f:
                f.write(secret)
            
            # Set secure file permissions
            os.chmod(key_file, 0o600)
            
            logger.info(f"Generated new JWT secret: {key_file}")
            return secret
            
        except Exception as e:
            logger.error(f"Error managing JWT secret: {e}")
            # Fallback to environment variable or generated secret
            return os.getenv('JWT_SECRET_KEY', self.generate_jwt_secret())
    
    def rotate_keys(self) -> Dict[str, str]:
        """Rotate all encryption keys (for maintenance)"""
        logger.warning("Starting key rotation - this will invalidate existing encrypted data!")
        
        # Backup old keys
        backup_dir = self.active_key_dir / "backup" / f"rotation_{secrets.token_hex(8)}"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        old_keys = {}
        
        # Backup existing keys
        for key_file in self.active_key_dir.glob("*.key"):
            if key_file.is_file():
                backup_file = backup_dir / key_file.name
                backup_file.write_text(key_file.read_text())
                old_keys[key_file.stem] = key_file.read_text().strip()
        
        # Generate new keys
        new_keys = {
            'field_encryption': self.generate_master_key(),
            'jwt_secret': self.generate_jwt_secret()
        }
        
        # Save new keys
        for key_name, key_value in new_keys.items():
            key_file = self.active_key_dir / f"{key_name}.key"
            key_file.write_text(key_value)
            os.chmod(key_file, 0o600)
        
        logger.info(f"Key rotation completed. Old keys backed up to: {backup_dir}")
        return {
            'old_keys_backup': str(backup_dir),
            'new_keys_generated': list(new_keys.keys())
        }
    
    def validate_key_security(self) -> Dict[str, bool]:
        """Validate that keys meet security requirements"""
        results = {}
        
        # Check field encryption key
        try:
            key = self.get_or_create_field_encryption_key()
            results['field_encryption_key_exists'] = bool(key)
            results['field_encryption_key_valid'] = len(key) >= 32
            
            # Try to create Fernet instance to validate key
            try:
                Fernet(base64.urlsafe_b64decode(key.encode()))
                results['field_encryption_key_format'] = True
            except Exception:
                results['field_encryption_key_format'] = False
                
        except Exception:
            results['field_encryption_key_exists'] = False
            results['field_encryption_key_valid'] = False
            results['field_encryption_key_format'] = False
        
        # Check JWT secret
        try:
            secret = self.get_or_create_jwt_secret()
            results['jwt_secret_exists'] = bool(secret)
            results['jwt_secret_length'] = len(secret) >= 32
            results['jwt_secret_entropy'] = len(set(secret)) > 10  # Basic entropy check
            
        except Exception:
            results['jwt_secret_exists'] = False
            results['jwt_secret_length'] = False
            results['jwt_secret_entropy'] = False
        
        # Check file permissions
        try:
            for key_file in self.active_key_dir.glob("*.key"):
                if key_file.exists():
                    stat = key_file.stat()
                    # Check if file is readable only by owner (600 permissions)
                    results[f'{key_file.stem}_permissions_secure'] = (stat.st_mode & 0o077) == 0
        except Exception:
            pass
        
        return results
    
    def get_key_status(self) -> Dict[str, str]:
        """Get status of all keys"""
        status = {
            'key_directory': str(self.active_key_dir),
            'directory_exists': self.active_key_dir.exists(),
            'directory_writable': os.access(self.active_key_dir, os.W_OK) if self.active_key_dir.exists() else False
        }
        
        # Check each key file
        for key_name in ['field_encryption', 'jwt_secret']:
            key_file = self.active_key_dir / f"{key_name}.key"
            status[f'{key_name}_file_exists'] = key_file.exists()
            if key_file.exists():
                status[f'{key_name}_file_size'] = key_file.stat().st_size
                status[f'{key_name}_file_permissions'] = oct(key_file.stat().st_mode)[-3:]
        
        return status


# Global key manager instance
key_manager = KeyManager()


def get_production_keys() -> Dict[str, str]:
    """Get all production keys"""
    return {
        'field_encryption_key': key_manager.get_or_create_field_encryption_key(),
        'jwt_secret_key': key_manager.get_or_create_jwt_secret()
    }


def validate_production_security() -> bool:
    """Validate that production security requirements are met"""
    validation = key_manager.validate_key_security()
    
    required_checks = [
        'field_encryption_key_exists',
        'field_encryption_key_valid', 
        'field_encryption_key_format',
        'jwt_secret_exists',
        'jwt_secret_length',
        'jwt_secret_entropy'
    ]
    
    return all(validation.get(check, False) for check in required_checks)
