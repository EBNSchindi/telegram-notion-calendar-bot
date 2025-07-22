"""Input validation and sanitization utilities."""
import re
import html
import logging
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, validator
from pydantic.error_wrappers import ValidationError

logger = logging.getLogger(__name__)


class SafeString(BaseModel):
    """Safe string with validation and sanitization."""
    value: str = Field(max_length=4096)
    
    @validator('value')
    def sanitize_value(cls, v):
        """Sanitize input string."""
        if not isinstance(v, str):
            raise ValueError("Value must be a string")
        
        # Remove null bytes and control characters
        v = ''.join(char for char in v if ord(char) >= 32 or char in '\n\r\t')
        
        # HTML escape
        v = html.escape(v.strip())
        
        # Limit length
        if len(v) > 4096:
            raise ValueError("Input too long")
        
        return v


class AppointmentTitle(BaseModel):
    """Validated appointment title."""
    title: str = Field(min_length=1, max_length=200)
    
    @validator('title')
    def validate_title(cls, v):
        """Validate appointment title."""
        if not v or not v.strip():
            raise ValueError("Title cannot be empty")
        
        # Remove excessive whitespace
        v = re.sub(r'\s+', ' ', v.strip())
        
        # Check for suspicious patterns
        suspicious_patterns = [
            r'<script.*?>.*?</script>',
            r'javascript:',
            r'data:',
            r'vbscript:',
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError("Invalid characters in title")
        
        return html.escape(v)


class AppointmentDescription(BaseModel):
    """Validated appointment description."""
    description: str = Field(max_length=2000)
    
    @validator('description')
    def validate_description(cls, v):
        """Validate appointment description."""
        if v is None:
            return ""
        
        # Remove excessive whitespace
        v = re.sub(r'\s+', ' ', v.strip())
        
        # HTML escape
        return html.escape(v)


class TelegramUserInput(BaseModel):
    """Validated Telegram user input."""
    user_id: int = Field(gt=0)
    username: Optional[str] = Field(max_length=32)
    message_text: str = Field(max_length=4096)
    
    @validator('username')
    def validate_username(cls, v):
        """Validate Telegram username."""
        if v is None:
            return None
        
        # Telegram username validation
        if not re.match(r'^[a-zA-Z0-9_]{5,32}$', v):
            raise ValueError("Invalid username format")
        
        return v
    
    @validator('message_text')
    def validate_message(cls, v):
        """Validate message text."""
        # Remove null bytes and control characters
        v = ''.join(char for char in v if ord(char) >= 32 or char in '\n\r\t')
        
        # HTML escape
        return html.escape(v.strip())


class DateInput(BaseModel):
    """Validated date input."""
    date_str: str = Field(max_length=20)
    
    @validator('date_str')
    def validate_date(cls, v):
        """Validate date string."""
        # Allow common date formats and keywords
        allowed_patterns = [
            r'^\d{1,2}\.\d{1,2}\.\d{4}$',  # DD.MM.YYYY
            r'^\d{1,2}\.\d{1,2}\.\d{2}$',  # DD.MM.YY
            r'^\d{4}-\d{1,2}-\d{1,2}$',   # YYYY-MM-DD
            r'^(heute|today|morgen|tomorrow)$',  # Keywords
        ]
        
        v = v.lower().strip()
        
        if not any(re.match(pattern, v, re.IGNORECASE) for pattern in allowed_patterns):
            raise ValueError("Invalid date format")
        
        return v


class TimeInput(BaseModel):
    """Validated time input."""
    time_str: str = Field(max_length=20)
    
    @validator('time_str')
    def validate_time(cls, v):
        """Validate time string."""
        # Allow various time formats
        allowed_patterns = [
            r'^\d{1,2}:\d{2}$',           # HH:MM
            r'^\d{1,2}\.\d{2}$',          # HH.MM
            r'^\d{3,4}$',                 # HHMM or HMM
            r'^\d{1,2}\s*uhr$',           # H Uhr
            r'^\d{1,2}:\d{2}\s*uhr$',     # HH:MM Uhr
            r'^\d{1,2}\s*(am|pm)$',       # H AM/PM
            r'^\d{1,2}:\d{2}\s*(am|pm)$', # HH:MM AM/PM
            r'^(halb|viertel vor|viertel nach|quarter past|quarter to|half past)\s+\d{1,2}$',
        ]
        
        v = v.lower().strip()
        
        if not any(re.match(pattern, v, re.IGNORECASE) for pattern in allowed_patterns):
            raise ValueError("Invalid time format")
        
        return v


class InputValidator:
    """Main input validator class."""
    
    @staticmethod
    def validate_appointment_input(title: str, description: str = "", date_str: str = "", time_str: str = "") -> dict:
        """
        Validate complete appointment input.
        
        Returns:
            dict: Validated and sanitized input
        
        Raises:
            ValidationError: If validation fails
        """
        try:
            validated_data = {}
            
            if title:
                validated_title = AppointmentTitle(title=title)
                validated_data['title'] = validated_title.title
            
            if description:
                validated_desc = AppointmentDescription(description=description)
                validated_data['description'] = validated_desc.description
            
            if date_str:
                validated_date = DateInput(date_str=date_str)
                validated_data['date_str'] = validated_date.date_str
            
            if time_str:
                validated_time = TimeInput(time_str=time_str)
                validated_data['time_str'] = validated_time.time_str
            
            return validated_data
            
        except ValidationError as e:
            logger.warning(f"Input validation failed: {e}")
            raise
    
    @staticmethod
    def validate_telegram_input(user_id: int, username: str = None, message_text: str = "") -> dict:
        """
        Validate Telegram user input.
        
        Returns:
            dict: Validated and sanitized input
        """
        try:
            validated_input = TelegramUserInput(
                user_id=user_id,
                username=username,
                message_text=message_text
            )
            return validated_input.dict()
        except ValidationError as e:
            logger.warning(f"Telegram input validation failed: {e}")
            raise
    
    @staticmethod
    def sanitize_string(text: str, max_length: int = 4096) -> str:
        """
        Sanitize a string for safe usage.
        
        Args:
            text: Input text
            max_length: Maximum allowed length
            
        Returns:
            str: Sanitized string
        """
        if not text:
            return ""
        
        try:
            safe_str = SafeString(value=text[:max_length])
            return safe_str.value
        except ValidationError:
            logger.warning(f"String sanitization failed for: {text[:100]}...")
            return html.escape(str(text)[:max_length])
    
    @staticmethod
    def is_safe_command_arg(arg: str) -> bool:
        """
        Check if command argument is safe.
        
        Args:
            arg: Command argument
            
        Returns:
            bool: True if safe
        """
        if not arg or len(arg) > 100:
            return False
        
        # Check for dangerous patterns
        dangerous_patterns = [
            r'[<>"\';]',  # HTML/Script characters
            r'\$\(',      # Command substitution
            r'`',         # Backticks
            r'\|',        # Pipes
            r'&',         # Command chaining
            r'\.\.',      # Directory traversal
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, arg):
                return False
        
        return True