"""
Input sanitization and validation utilities
"""
import re
import html
import logging
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse
import bleach
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class InputSanitizer:
    """Comprehensive input sanitization for security"""
    
    def __init__(self):
        # Allowed HTML tags and attributes (very restrictive)
        self.allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li']
        self.allowed_attributes = {
            '*': ['class'],
        }
        
        # Dangerous patterns to detect
        self.dangerous_patterns = [
            r'<script[^>]*>.*?</script>',  # Script tags
            r'javascript:',                # JavaScript URLs
            r'on\w+\s*=',                 # Event handlers
            r'<iframe[^>]*>.*?</iframe>',  # Iframes
            r'<object[^>]*>.*?</object>',  # Objects
            r'<embed[^>]*>',               # Embeds
            r'<form[^>]*>.*?</form>',      # Forms
            r'<input[^>]*>',               # Inputs
            r'eval\s*\(',                  # eval() calls
            r'exec\s*\(',                  # exec() calls
        ]
        
        # SQL injection patterns
        self.sql_patterns = [
            r"('\s*(or|and)\s*')",
            r"('\s*;\s*drop\s+table)",
            r"('\s*;\s*delete\s+from)",
            r"('\s*;\s*update\s+)",
            r"('\s*;\s*insert\s+into)",
            r"union\s+select",
            r"'\s*or\s*1\s*=\s*1",
        ]
        
        # Path traversal patterns
        self.path_traversal_patterns = [
            r'\.\./+',
            r'\.\.\\+',
            r'%2e%2e%2f',
            r'%2e%2e\\',
        ]
    
    def sanitize_string(self, value: str, max_length: Optional[int] = None) -> str:
        """Sanitize a string input"""
        if not isinstance(value, str):
            return str(value)
        
        # Limit length
        if max_length and len(value) > max_length:
            value = value[:max_length]
        
        # HTML escape
        value = html.escape(value)
        
        # Remove null bytes and control characters
        value = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', value)
        
        return value.strip()
    
    def sanitize_html(self, value: str, strict: bool = True) -> str:
        """Sanitize HTML content"""
        if not isinstance(value, str):
            return ""
        
        if strict:
            # Very strict: only plain text
            return bleach.clean(value, tags=[], attributes={}, strip=True)
        else:
            # Allow basic formatting tags
            return bleach.clean(
                value, 
                tags=self.allowed_tags, 
                attributes=self.allowed_attributes,
                strip=True
            )
    
    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe storage"""
        if not isinstance(filename, str):
            return "unknown"
        
        # Remove path separators and dangerous characters
        filename = re.sub(r'[/\\:*?"<>|]', '_', filename)
        
        # Remove leading/trailing dots and spaces
        filename = filename.strip('. ')
        
        # Limit length
        if len(filename) > 255:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            filename = name[:250] + ('.' + ext if ext else '')
        
        # Ensure not empty
        if not filename:
            filename = "unnamed_file"
        
        return filename
    
    def sanitize_email(self, email: str) -> str:
        """Sanitize email address"""
        if not isinstance(email, str):
            return ""
        
        # Basic email format validation and sanitization
        email = email.strip().lower()
        
        # Remove dangerous characters
        email = re.sub(r'[<>"\'\(\)]', '', email)
        
        return email
    
    def sanitize_url(self, url: str) -> Optional[str]:
        """Sanitize and validate URL"""
        if not isinstance(url, str):
            return None
        
        url = url.strip()
        
        try:
            parsed = urlparse(url)
            
            # Only allow http/https schemes
            if parsed.scheme not in ['http', 'https']:
                return None
            
            # Reconstruct clean URL
            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if parsed.query:
                clean_url += f"?{parsed.query}"
            
            return clean_url
            
        except Exception:
            return None
    
    def detect_dangerous_patterns(self, value: str) -> List[str]:
        """Detect dangerous patterns in input"""
        if not isinstance(value, str):
            return []
        
        threats = []
        value_lower = value.lower()
        
        # Check for dangerous HTML/JS patterns
        for pattern in self.dangerous_patterns:
            if re.search(pattern, value_lower, re.IGNORECASE | re.DOTALL):
                threats.append(f"Dangerous pattern: {pattern}")
        
        # Check for SQL injection patterns
        for pattern in self.sql_patterns:
            if re.search(pattern, value_lower, re.IGNORECASE):
                threats.append(f"SQL injection pattern: {pattern}")
        
        # Check for path traversal
        for pattern in self.path_traversal_patterns:
            if re.search(pattern, value_lower, re.IGNORECASE):
                threats.append(f"Path traversal pattern: {pattern}")
        
        return threats
    
    def sanitize_dict(self, data: Dict[str, Any], max_depth: int = 5) -> Dict[str, Any]:
        """Recursively sanitize dictionary data"""
        if max_depth <= 0:
            return {}
        
        sanitized = {}
        
        for key, value in data.items():
            # Sanitize key
            clean_key = self.sanitize_string(str(key), max_length=100)
            
            # Sanitize value based on type
            if isinstance(value, str):
                sanitized[clean_key] = self.sanitize_string(value, max_length=10000)
            elif isinstance(value, dict):
                sanitized[clean_key] = self.sanitize_dict(value, max_depth - 1)
            elif isinstance(value, list):
                sanitized[clean_key] = self.sanitize_list(value, max_depth - 1)
            elif isinstance(value, (int, float, bool)):
                sanitized[clean_key] = value
            else:
                # Convert other types to string and sanitize
                sanitized[clean_key] = self.sanitize_string(str(value), max_length=1000)
        
        return sanitized
    
    def sanitize_list(self, data: List[Any], max_depth: int = 5) -> List[Any]:
        """Recursively sanitize list data"""
        if max_depth <= 0:
            return []
        
        sanitized = []
        
        for item in data:
            if isinstance(item, str):
                sanitized.append(self.sanitize_string(item, max_length=10000))
            elif isinstance(item, dict):
                sanitized.append(self.sanitize_dict(item, max_depth - 1))
            elif isinstance(item, list):
                sanitized.append(self.sanitize_list(item, max_depth - 1))
            elif isinstance(item, (int, float, bool)):
                sanitized.append(item)
            else:
                sanitized.append(self.sanitize_string(str(item), max_length=1000))
        
        return sanitized
    
    def validate_and_sanitize_search_query(self, query: str) -> str:
        """Validate and sanitize search queries"""
        if not isinstance(query, str):
            return ""
        
        # Limit query length
        query = query[:1000]
        
        # Remove dangerous patterns
        threats = self.detect_dangerous_patterns(query)
        if threats:
            logger.warning(f"Dangerous patterns detected in search query: {threats}")
            # Strip dangerous content
            for pattern in self.dangerous_patterns:
                query = re.sub(pattern, '', query, flags=re.IGNORECASE | re.DOTALL)
        
        # Basic sanitization
        query = self.sanitize_string(query)
        
        return query.strip()
    
    def validate_json_input(self, data: Any, max_size: int = 1024 * 1024) -> bool:
        """Validate JSON input size and structure"""
        import json
        
        try:
            # Check serialized size
            serialized = json.dumps(data)
            if len(serialized) > max_size:
                return False
            
            # Check for reasonable nesting depth
            def check_depth(obj, depth=0):
                if depth > 20:  # Max nesting depth
                    return False
                if isinstance(obj, dict):
                    return all(check_depth(v, depth + 1) for v in obj.values())
                elif isinstance(obj, list):
                    return all(check_depth(item, depth + 1) for item in obj)
                return True
            
            return check_depth(data)
            
        except Exception:
            return False


# Global sanitizer instance
sanitizer = InputSanitizer()


def sanitize_user_input(data: Union[str, Dict, List]) -> Union[str, Dict, List]:
    """Sanitize user input - main entry point"""
    if isinstance(data, str):
        return sanitizer.sanitize_string(data)
    elif isinstance(data, dict):
        return sanitizer.sanitize_dict(data)
    elif isinstance(data, list):
        return sanitizer.sanitize_list(data)
    else:
        return sanitizer.sanitize_string(str(data))


def validate_input_safety(data: Any) -> List[str]:
    """Validate input for security threats"""
    if isinstance(data, str):
        return sanitizer.detect_dangerous_patterns(data)
    elif isinstance(data, dict):
        threats = []
        for key, value in data.items():
            threats.extend(validate_input_safety(key))
            threats.extend(validate_input_safety(value))
        return threats
    elif isinstance(data, list):
        threats = []
        for item in data:
            threats.extend(validate_input_safety(item))
        return threats
    else:
        return sanitizer.detect_dangerous_patterns(str(data))


def create_safe_filename(filename: str) -> str:
    """Create a safe filename"""
    return sanitizer.sanitize_filename(filename)
