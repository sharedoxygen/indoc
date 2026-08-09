"""
Password Policy Enforcement

Per Review C2.2: Prevent weak passwords
Per AI Guide: Configuration-driven, no hard-coding
"""
import re
from typing import Optional, List
from pydantic import BaseModel
from app.core.config import settings


class PasswordValidationError(Exception):
    """Raised when password doesn't meet policy requirements"""
    pass


class PasswordPolicy(BaseModel):
    """Password policy configuration"""
    min_length: int = 12
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_digit: bool = True
    require_special: bool = True
    special_chars: str = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    max_length: int = 128
    prevent_common: bool = True


class PasswordValidator:
    """Validate passwords against policy requirements"""
    
    def __init__(self, policy: Optional[PasswordPolicy] = None):
        self.policy = policy or PasswordPolicy()
        
        # Common weak passwords to reject
        self.common_passwords = {
            "password", "password123", "admin", "admin123", "admin123!",
            "Password1", "Password1!", "Welcome1", "Welcome1!",
            "123456", "12345678", "qwerty", "abc123", "letmein",
            "indoc", "indoc123", "indoc123!", "test", "test123"
        }
    
    def validate(self, password: str) -> tuple[bool, Optional[str]]:
        """
        Validate password against policy
        
        Returns:
            (is_valid, error_message)
        """
        if not password:
            return False, "Password cannot be empty"
        
        # Length check
        if len(password) < self.policy.min_length:
            return False, f"Password must be at least {self.policy.min_length} characters long"
        
        if len(password) > self.policy.max_length:
            return False, f"Password cannot exceed {self.policy.max_length} characters"
        
        # Uppercase check
        if self.policy.require_uppercase and not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        
        # Lowercase check
        if self.policy.require_lowercase and not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"
        
        # Digit check
        if self.policy.require_digit and not re.search(r'\d', password):
            return False, "Password must contain at least one digit"
        
        # Special character check
        if self.policy.require_special:
            if not any(c in self.policy.special_chars for c in password):
                return False, f"Password must contain at least one special character: {self.policy.special_chars}"
        
        # Common password check
        if self.policy.prevent_common:
            if password.lower() in self.common_passwords:
                return False, "This password is too common and easily guessable"
            
            # Check for simple patterns
            if password.lower().startswith("password"):
                return False, "Password cannot start with 'password'"
            if password.lower().startswith("admin"):
                return False, "Password cannot start with 'admin'"
            if password == password.lower() or password == password.upper():
                return False, "Password must use mixed case"
        
        return True, None
    
    def get_requirements_text(self) -> str:
        """Get human-readable password requirements"""
        requirements = []
        requirements.append(f"At least {self.policy.min_length} characters long")
        
        if self.policy.require_uppercase:
            requirements.append("At least one uppercase letter")
        if self.policy.require_lowercase:
            requirements.append("At least one lowercase letter")
        if self.policy.require_digit:
            requirements.append("At least one number")
        if self.policy.require_special:
            requirements.append(f"At least one special character ({self.policy.special_chars[:10]}...)")
        if self.policy.prevent_common:
            requirements.append("Not a common or easily guessable password")
        
        return "Password requirements:\n- " + "\n- ".join(requirements)


# Global validator instance
password_validator = PasswordValidator()


def validate_password(password: str) -> None:
    """
    Validate password and raise exception if invalid
    
    Usage:
        try:
            validate_password(user_password)
        except PasswordValidationError as e:
            return {"error": str(e)}
    """
    is_valid, error_message = password_validator.validate(password)
    if not is_valid:
        raise PasswordValidationError(error_message)

