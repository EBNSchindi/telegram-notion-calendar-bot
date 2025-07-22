"""Robust time parser with enhanced error handling and validation."""
import re
from datetime import time
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class RobustTimeParser:
    """Robust parser for various time formats with comprehensive error handling."""
    
    @staticmethod
    def _convert_12h_to_24h(hour: int, is_am: bool) -> int:
        """Convert 12-hour format to 24-hour format."""
        if not (1 <= hour <= 12):
            raise ValueError(f"Hour must be between 1-12 for AM/PM format, got {hour}")
        
        if is_am:
            return 0 if hour == 12 else hour  # 12 AM = 0, others stay same
        else:
            return hour if hour == 12 else hour + 12  # 12 PM = 12, others add 12
    
    @staticmethod
    def _safe_int(value: str) -> int:
        """Safely convert string to int with validation."""
        try:
            return int(value.strip())
        except (ValueError, AttributeError):
            raise ValueError(f"Cannot convert '{value}' to integer")
    
    @classmethod
    def parse_time(cls, time_str: str) -> time:
        """
        Parse various time formats into a time object with robust error handling.
        
        Supported formats:
        - Standard: 14:30, 14.30, 1430
        - German: 16 Uhr, halb 3, viertel vor 5
        - English: 4 PM, quarter past 2, half past 3
        
        Args:
            time_str: Time string in various formats
            
        Returns:
            time: Parsed time object
            
        Raises:
            ValueError: If time format is invalid or values are out of range
        """
        if not time_str or not isinstance(time_str, str):
            raise ValueError("Zeit muss ein nicht-leerer Text sein")
        
        # Clean and normalize input
        original_input = time_str
        time_str = time_str.strip()
        
        if not time_str:
            raise ValueError("Zeit darf nicht leer sein")
        
        # Track parsing attempts for debugging
        attempts = []
        
        # Pattern 1: Standard formats (HH:MM, HH.MM)
        try:
            for separator in [':', '.']:
                if separator in time_str:
                    parts = time_str.split(separator)
                    if len(parts) == 2:
                        hour = cls._safe_int(parts[0])
                        minute = cls._safe_int(parts[1])
                        attempts.append(f"Standard {separator} format: {hour}:{minute}")
                        return cls._validate_and_create_time(hour, minute, original_input)
        except ValueError as e:
            attempts.append(f"Standard format failed: {e}")
        
        # Pattern 2: Simple hour format (just a number like "15")
        try:
            if time_str.isdigit() and 1 <= len(time_str) <= 2:
                hour = cls._safe_int(time_str)
                if 0 <= hour <= 23:
                    attempts.append(f"Simple hour format: {hour}:00")
                    return cls._validate_and_create_time(hour, 0, original_input)
        except ValueError as e:
            attempts.append(f"Simple hour format failed: {e}")
        
        # Pattern 3: Compact format (HHMM, HMM)
        try:
            if time_str.isdigit() and 3 <= len(time_str) <= 4:
                if len(time_str) == 4:
                    hour = cls._safe_int(time_str[:2])
                    minute = cls._safe_int(time_str[2:])
                else:  # len == 3, format HMM
                    hour = cls._safe_int(time_str[0])
                    minute = cls._safe_int(time_str[1:])
                attempts.append(f"Compact format: {hour}:{minute}")
                return cls._validate_and_create_time(hour, minute, original_input)
        except ValueError as e:
            attempts.append(f"Compact format failed: {e}")
        
        # Pattern 4: German "Uhr" formats
        try:
            result = cls._parse_german_uhr_format(time_str)
            if result:
                hour, minute = result
                attempts.append(f"German Uhr format: {hour}:{minute}")
                return cls._validate_and_create_time(hour, minute, original_input)
        except ValueError as e:
            attempts.append(f"German Uhr format failed: {e}")
        
        # Pattern 5: English AM/PM formats
        try:
            result = cls._parse_am_pm_format(time_str)
            if result:
                hour, minute = result
                attempts.append(f"AM/PM format: {hour}:{minute}")
                return cls._validate_and_create_time(hour, minute, original_input)
        except ValueError as e:
            attempts.append(f"AM/PM format failed: {e}")
        
        # Pattern 6: German quarter/half hour expressions
        try:
            result = cls._parse_german_expressions(time_str)
            if result:
                hour, minute = result
                attempts.append(f"German expression: {hour}:{minute}")
                return cls._validate_and_create_time(hour, minute, original_input)
        except ValueError as e:
            attempts.append(f"German expressions failed: {e}")
        
        # Pattern 7: English quarter/half hour expressions
        try:
            result = cls._parse_english_expressions(time_str)
            if result:
                hour, minute = result
                attempts.append(f"English expression: {hour}:{minute}")
                return cls._validate_and_create_time(hour, minute, original_input)
        except ValueError as e:
            attempts.append(f"English expressions failed: {e}")
        
        # If all patterns failed, provide detailed error message
        logger.debug(f"All parsing attempts failed for '{original_input}': {attempts}")
        
        raise ValueError(
            f"Ungültiges Zeitformat: '{original_input}'\n\n"
            "Unterstützte Formate:\n"
            "• Einfach: 15 (= 15:00)\n"
            "• Standard: 14:00, 14.30, 1430\n"
            "• Deutsch: 16 Uhr, halb 3, viertel vor 5\n"
            "• English: 4 PM, quarter past 2, half past 3\n\n"
            "Beispiele:\n"
            "• 15 → 15:00\n"
            "• 14:30 → 14:30\n"
            "• 16 Uhr → 16:00\n" 
            "• 4 PM → 16:00\n"
            "• halb 3 → 02:30"
        )
    
    @classmethod
    def _parse_german_uhr_format(cls, time_str: str) -> Optional[Tuple[int, int]]:
        """Parse German 'Uhr' formats."""
        time_str_lower = time_str.lower()
        
        # "16 Uhr 30" format
        match = re.match(r'^(\d{1,2})\s*uhr\s*(\d{1,2})$', time_str_lower)
        if match:
            hour = cls._safe_int(match.group(1))
            minute = cls._safe_int(match.group(2))
            return hour, minute
        
        # "16:30 Uhr" format
        match = re.match(r'^(\d{1,2})[:\.](\d{2})\s*uhr$', time_str_lower)
        if match:
            hour = cls._safe_int(match.group(1))
            minute = cls._safe_int(match.group(2))
            return hour, minute
        
        # "16 Uhr" format
        match = re.match(r'^(\d{1,2})\s*uhr$', time_str_lower)
        if match:
            hour = cls._safe_int(match.group(1))
            return hour, 0
        
        return None
    
    @classmethod
    def _parse_am_pm_format(cls, time_str: str) -> Optional[Tuple[int, int]]:
        """Parse AM/PM formats."""
        time_str_lower = time_str.lower().replace(' ', '')
        
        # "4:30 PM" or "4.30 PM" format
        match = re.match(r'^(\d{1,2})[:\.](\d{2})(am|pm)$', time_str_lower)
        if match:
            hour = cls._safe_int(match.group(1))
            minute = cls._safe_int(match.group(2))
            is_am = match.group(3) == 'am'
            hour_24 = cls._convert_12h_to_24h(hour, is_am)
            return hour_24, minute
        
        # "4 PM" format
        match = re.match(r'^(\d{1,2})(am|pm)$', time_str_lower)
        if match:
            hour = cls._safe_int(match.group(1))
            is_am = match.group(2) == 'am'
            hour_24 = cls._convert_12h_to_24h(hour, is_am)
            return hour_24, 0
        
        return None
    
    @classmethod
    def _parse_german_expressions(cls, time_str: str) -> Optional[Tuple[int, int]]:
        """Parse German time expressions like 'halb 3', 'viertel vor 5'."""
        time_str_lower = time_str.lower()
        
        # "halb 3" = 2:30
        match = re.match(r'^halb\s*(\d{1,2})$', time_str_lower)
        if match:
            hour = cls._safe_int(match.group(1)) - 1
            if hour < 0:
                hour = 23
            return hour, 30
        
        # "viertel nach 3" = 3:15
        match = re.match(r'^viertel\s*nach\s*(\d{1,2})$', time_str_lower)
        if match:
            hour = cls._safe_int(match.group(1))
            return hour, 15
        
        # "viertel vor 3" = 2:45
        match = re.match(r'^viertel\s*vor\s*(\d{1,2})$', time_str_lower)
        if match:
            hour = cls._safe_int(match.group(1)) - 1
            if hour < 0:
                hour = 23
            return hour, 45
        
        return None
    
    @classmethod
    def _parse_english_expressions(cls, time_str: str) -> Optional[Tuple[int, int]]:
        """Parse English time expressions like 'half past 2', 'quarter to 3'."""
        time_str_lower = time_str.lower()
        
        # "half past 2" = 2:30
        match = re.match(r'^half\s*past\s*(\d{1,2})$', time_str_lower)
        if match:
            hour = cls._safe_int(match.group(1))
            return hour, 30
        
        # "quarter past 2" = 2:15
        match = re.match(r'^quarter\s*past\s*(\d{1,2})$', time_str_lower)
        if match:
            hour = cls._safe_int(match.group(1))
            return hour, 15
        
        # "quarter to 3" = 2:45
        match = re.match(r'^quarter\s*to\s*(\d{1,2})$', time_str_lower)
        if match:
            hour = cls._safe_int(match.group(1)) - 1
            if hour < 0:
                hour = 23
            return hour, 45
        
        return None
    
    @classmethod
    def _validate_and_create_time(cls, hour: int, minute: int, original_input: str) -> time:
        """Validate hour and minute values and create time object."""
        if not isinstance(hour, int) or not isinstance(minute, int):
            raise ValueError(f"Hour and minute must be integers")
        
        if not (0 <= hour <= 23):
            raise ValueError(f"Stunde muss zwischen 0-23 liegen, erhalten: {hour}")
        
        if not (0 <= minute <= 59):
            raise ValueError(f"Minute muss zwischen 0-59 liegen, erhalten: {minute}")
        
        try:
            result = time(hour, minute)
            logger.debug(f"Successfully parsed '{original_input}' → {result}")
            return result
        except ValueError as e:
            raise ValueError(f"Fehler beim Erstellen der Zeit für {hour}:{minute}: {e}")
    
    @classmethod
    def format_time(cls, time_obj: time, use_natural: bool = False, language: str = 'de') -> str:
        """
        Format time object to string.
        
        Args:
            time_obj: Time object to format
            use_natural: Whether to use natural language format
            language: Language for natural format ('de' or 'en')
            
        Returns:
            Formatted time string
        """
        if not isinstance(time_obj, time):
            raise ValueError("time_obj must be a time object")
        
        if not use_natural:
            return time_obj.strftime("%H:%M")
        
        hour = time_obj.hour
        minute = time_obj.minute
        
        if language == 'de':
            # German natural language
            if minute == 0:
                return f"{hour} Uhr"
            elif minute == 15:
                return f"viertel nach {hour}"
            elif minute == 30:
                return f"halb {hour + 1}"
            elif minute == 45:
                return f"viertel vor {hour + 1}"
            else:
                return f"{hour}:{minute:02d} Uhr"
        else:
            # English natural language
            if minute == 0:
                if hour == 0:
                    return "midnight"
                elif hour == 12:
                    return "noon"
                elif hour < 12:
                    return f"{hour} AM"
                else:
                    return f"{hour - 12} PM"
            elif minute == 15:
                return f"quarter past {hour}"
            elif minute == 30:
                return f"half past {hour}"
            elif minute == 45:
                return f"quarter to {hour + 1}"
            else:
                if hour < 12:
                    return f"{hour}:{minute:02d} AM"
                else:
                    return f"{hour - 12}:{minute:02d} PM"