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

def setup_secure_logging(log_file: str = 'bot.log', log_level: str = 'INFO', enable_debug: bool = False):
    """Setup logging with sensitive data sanitization.
    
    Args:
        log_file: Path to the log file
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_debug: Enable debug mode with detailed error tracking
    """
    
    # Create different formatters for different use cases
    if enable_debug:
        # Detailed format for debugging
        formatter = SanitizingFormatter(
            '%(asctime)s - [%(name)s:%(lineno)d] - %(levelname)s - %(funcName)s() - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        # Standard format
        formatter = SanitizingFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add file handler with sanitization
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Add console handler with sanitization
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Configure specific loggers for better granularity
    loggers_config = {
        'telegram': log_level,
        'httpx': 'WARNING',  # Reduce noise from HTTP client
        'openai': 'INFO',
        'notion_client': 'INFO',
        'src.services.ai_assistant_service': 'DEBUG' if enable_debug else 'INFO',
        'src.handlers.memo_handler': 'DEBUG' if enable_debug else 'INFO',
        'src.services.partner_sync_service': 'DEBUG' if enable_debug else 'INFO',
    }
    
    for logger_name, level in loggers_config.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(getattr(logging, level.upper()))
    
    # Log that secure logging is enabled
    logging.info(f"Secure logging enabled - Level: {log_level}, Debug: {enable_debug}")