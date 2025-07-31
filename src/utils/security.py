"""Security utilities for encryption and secure storage."""
import os
import json
import logging
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

logger = logging.getLogger(__name__)


class SecureConfig:
    """Secure configuration management with encryption."""
    
    def __init__(self, key_file: str = ".encryption_key"):
        """
        Initialize secure config with encryption key.
        
        Args:
            key_file: Path to encryption key file
        """
        self.key_file = key_file
        self.cipher = Fernet(self._load_or_generate_key())
    
    def _load_or_generate_key(self) -> bytes:
        """Load existing key or generate new one."""
        if os.path.exists(self.key_file):
            with open(self.key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            # Store key securely - in production use proper key management
            with open(self.key_file, 'wb') as f:
                f.write(key)
            os.chmod(self.key_file, 0o600)  # Restrict access
            logger.info("Generated new encryption key")
            return key
    
    def encrypt_credential(self, credential: str) -> str:
        """
        Encrypt a credential string.
        
        Args:
            credential: Plain text credential
            
        Returns:
            Base64 encoded encrypted credential
        """
        if not credential:
            return ""
        encrypted = self.cipher.encrypt(credential.encode())
        return base64.b64encode(encrypted).decode()
    
    def decrypt_credential(self, encrypted: str) -> str:
        """
        Decrypt an encrypted credential.
        
        Args:
            encrypted: Base64 encoded encrypted credential
            
        Returns:
            Decrypted plain text credential
        """
        if not encrypted:
            return ""
        try:
            decoded = base64.b64decode(encrypted.encode())
            return self.cipher.decrypt(decoded).decode()
        except Exception as e:
            logger.error(f"Failed to decrypt credential: {e}")
            raise ValueError("Invalid encrypted credential")
    
    def secure_env_var(self, var_name: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get environment variable with secure handling.
        
        Args:
            var_name: Environment variable name
            default: Default value if not found
            
        Returns:
            Environment variable value or default
        """
        value = os.getenv(var_name, default)
        if value and var_name.upper().endswith(('_KEY', '_PASSWORD', '_TOKEN')):
            # Log access to sensitive variables (without value)
            logger.debug(f"Accessed sensitive environment variable: {var_name}")
        return value
    
    def sanitize_for_logging(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize sensitive data for logging.
        
        Args:
            data: Dictionary containing potentially sensitive data
            
        Returns:
            Sanitized dictionary safe for logging
        """
        sensitive_keys = ['api_key', 'password', 'token', 'secret', 'credential']
        sanitized = data.copy()
        
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                if isinstance(value, str) and len(value) > 0:
                    # Show first 4 chars only
                    sanitized[key] = f"{value[:4]}..." if len(value) > 4 else "***"
                else:
                    sanitized[key] = "***"
        
        return sanitized


class InputSanitizer:
    """Input validation and sanitization."""
    
    @staticmethod
    def sanitize_for_notion(text: str) -> str:
        """
        Sanitize text for Notion API to prevent injection.
        
        Args:
            text: Input text
            
        Returns:
            Sanitized text
        """
        if not text:
            return ""
        
        # Remove potentially dangerous characters
        dangerous_chars = ['\\', '"', "'", ';', '--', '/*', '*/']
        sanitized = text
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')
        
        # Limit length to prevent DoS
        max_length = 2000
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        return sanitized.strip()
    
    @staticmethod
    def sanitize_telegram_markdown(text: str) -> str:
        """
        Escape special characters for Telegram markdown.
        
        Args:
            text: Input text
            
        Returns:
            Escaped text safe for Telegram
        """
        if not text:
            return ""
        
        # Telegram MarkdownV2 special characters
        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        
        escaped = text
        for char in special_chars:
            escaped = escaped.replace(char, f'\\{char}')
        
        return escaped
    
    @staticmethod
    def validate_telegram_user_id(user_id: Any) -> int:
        """
        Validate Telegram user ID.
        
        Args:
            user_id: User ID to validate
            
        Returns:
            Valid user ID
            
        Raises:
            ValueError: If user ID is invalid
        """
        try:
            user_id_int = int(user_id)
            if user_id_int <= 0:
                raise ValueError("User ID must be positive")
            return user_id_int
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid user ID: {user_id}") from e
    
    @staticmethod
    def validate_notion_id(notion_id: str) -> str:
        """
        Validate Notion database/page ID format.
        
        Args:
            notion_id: Notion ID to validate
            
        Returns:
            Valid Notion ID
            
        Raises:
            ValueError: If ID is invalid
        """
        if not notion_id or not isinstance(notion_id, str):
            raise ValueError("Notion ID must be a non-empty string")
        
        # Remove hyphens for validation
        clean_id = notion_id.replace('-', '')
        
        # Notion IDs are 32 character hex strings
        if len(clean_id) != 32 or not all(c in '0123456789abcdef' for c in clean_id.lower()):
            raise ValueError(f"Invalid Notion ID format: {notion_id}")
        
        return notion_id