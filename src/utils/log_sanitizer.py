"""
Log sanitizer to prevent sensitive data exposure in logs.
"""
import re
import logging
from typing import Dict, List

class SanitizingFormatter(logging.Formatter):
    """Custom logging formatter that sanitizes sensitive data."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Define patterns for sensitive data
        self.sensitive_patterns = [
            # Telegram bot tokens
            (r'bot\d+:[A-Za-z0-9_-]+', 'bot***:***'),
            # Email addresses 
            (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '***@***.***'),
            # Notion API keys
            (r'secret_[A-Za-z0-9]+', 'secret_***'),
            (r'ntn_[A-Za-z0-9]+', 'ntn_***'),
            # Database IDs (32 char hex)
            (r'\b[a-f0-9]{32}\b', '***db_id***'),
            # Outlook IDs (base64-like)
            (r'[A-Za-z0-9+/]{50,}=*', '***outlook_id***'),
            # Gmail app passwords
            (r'\b[a-z]{4}\s[a-z]{4}\s[a-z]{4}\s[a-z]{4}\b', '*** *** *** ***'),
            # Generic passwords in URLs
            (r'://[^:]+:([^@]+)@', r'://***:***@'),
            # Authorization headers
            (r'Authorization:\s*[A-Za-z]+\s+[A-Za-z0-9+/=]+', 'Authorization: *** ***'),
        ]
    
    def format(self, record):
        """Format log record and sanitize sensitive data."""
        # Get the formatted message
        msg = super().format(record)
        
        # Apply all sanitization patterns
        for pattern, replacement in self.sensitive_patterns:
            msg = re.sub(pattern, replacement, msg, flags=re.IGNORECASE)
        
        return msg

def setup_secure_logging(log_file: str = 'bot.log', log_level: str = 'INFO'):
    """Setup logging with sensitive data sanitization."""
    
    # Create sanitizing formatter
    formatter = SanitizingFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add file handler with sanitization
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Add console handler with sanitization
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Log that secure logging is enabled
    logging.info("Secure logging with data sanitization enabled")

def sanitize_string(text: str) -> str:
    """Manually sanitize a string of sensitive data."""
    formatter = SanitizingFormatter()
    # Create a dummy log record to use the formatter
    record = logging.LogRecord(
        name='manual', level=logging.INFO, pathname='', lineno=0,
        msg=text, args=(), exc_info=None
    )
    return formatter.format(record).split(' - ')[-1]  # Extract just the message part