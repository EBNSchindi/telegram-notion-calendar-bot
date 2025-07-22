"""Tests for enhanced TimeParser with English support."""
import pytest
from datetime import time
from src.utils.robust_time_parser import RobustTimeParser as TimeParser


class TestEnhancedTimeParser:
    """Test cases for enhanced TimeParser with English support."""
    
    def test_english_am_pm_formats(self):
        """Test English AM/PM time formats."""
        # AM formats
        assert TimeParser.parse_time("8 AM") == time(8, 0)
        assert TimeParser.parse_time("8am") == time(8, 0)
        assert TimeParser.parse_time("12 AM") == time(0, 0)  # Midnight
        assert TimeParser.parse_time("1 AM") == time(1, 0)
        
        # PM formats
        assert TimeParser.parse_time("4 PM") == time(16, 0)
        assert TimeParser.parse_time("4pm") == time(16, 0)
        assert TimeParser.parse_time("12 PM") == time(12, 0)  # Noon
        assert TimeParser.parse_time("11 PM") == time(23, 0)
        
        # With minutes
        assert TimeParser.parse_time("8:30 AM") == time(8, 30)
        assert TimeParser.parse_time("4:30 PM") == time(16, 30)
        assert TimeParser.parse_time("8.30 AM") == time(8, 30)
        assert TimeParser.parse_time("4.30 PM") == time(16, 30)
    
    def test_english_quarter_half_formats(self):
        """Test English quarter and half hour formats."""
        # Half past
        assert TimeParser.parse_time("half past 2") == time(2, 30)
        assert TimeParser.parse_time("Half past 2") == time(2, 30)
        assert TimeParser.parse_time("half past 14") == time(14, 30)
        
        # Quarter past
        assert TimeParser.parse_time("quarter past 2") == time(2, 15)
        assert TimeParser.parse_time("Quarter past 2") == time(2, 15)
        assert TimeParser.parse_time("quarter past 14") == time(14, 15)
        
        # Quarter to
        assert TimeParser.parse_time("quarter to 3") == time(2, 45)
        assert TimeParser.parse_time("Quarter to 3") == time(2, 45)
        assert TimeParser.parse_time("quarter to 15") == time(14, 45)
    
    def test_mixed_language_support(self):
        """Test that both German and English formats work."""
        # German
        assert TimeParser.parse_time("16 Uhr") == time(16, 0)
        assert TimeParser.parse_time("halb 3") == time(2, 30)
        assert TimeParser.parse_time("viertel vor 5") == time(4, 45)
        
        # English
        assert TimeParser.parse_time("4 PM") == time(16, 0)
        assert TimeParser.parse_time("half past 2") == time(2, 30)
        assert TimeParser.parse_time("quarter to 5") == time(4, 45)
        
        # Standard (universal)
        assert TimeParser.parse_time("14:30") == time(14, 30)
        assert TimeParser.parse_time("14.30") == time(14, 30)
    
    def test_edge_cases_am_pm(self):
        """Test edge cases for AM/PM formats."""
        # Midnight variations
        assert TimeParser.parse_time("12 AM") == time(0, 0)
        assert TimeParser.parse_time("12:00 AM") == time(0, 0)
        assert TimeParser.parse_time("12.00 AM") == time(0, 0)
        
        # Noon variations
        assert TimeParser.parse_time("12 PM") == time(12, 0)
        assert TimeParser.parse_time("12:00 PM") == time(12, 0)
        assert TimeParser.parse_time("12.00 PM") == time(12, 0)
        
        # Edge times
        assert TimeParser.parse_time("11:59 PM") == time(23, 59)
        assert TimeParser.parse_time("1:00 AM") == time(1, 0)
    
    def test_case_insensitive_english(self):
        """Test that English formats are case insensitive."""
        # AM/PM variations
        assert TimeParser.parse_time("4 PM") == time(16, 0)
        assert TimeParser.parse_time("4 pm") == time(16, 0)
        assert TimeParser.parse_time("4 Pm") == time(16, 0)
        assert TimeParser.parse_time("4 pM") == time(16, 0)
        
        # Quarter/Half variations
        assert TimeParser.parse_time("HALF PAST 2") == time(2, 30)
        assert TimeParser.parse_time("half past 2") == time(2, 30)
        assert TimeParser.parse_time("Half Past 2") == time(2, 30)
        
        assert TimeParser.parse_time("QUARTER TO 3") == time(2, 45)
        assert TimeParser.parse_time("quarter to 3") == time(2, 45)
        assert TimeParser.parse_time("Quarter To 3") == time(2, 45)
    
    def test_invalid_am_pm_formats(self):
        """Test that invalid AM/PM formats raise errors."""
        with pytest.raises(ValueError):
            TimeParser.parse_time("25 PM")  # Invalid hour
        
        with pytest.raises(ValueError):
            TimeParser.parse_time("13 AM")  # Invalid for AM
        
        with pytest.raises(ValueError):
            TimeParser.parse_time("0 PM")   # Invalid for PM
        
        with pytest.raises(ValueError):
            TimeParser.parse_time("12:60 AM")  # Invalid minutes
    
    def test_comprehensive_examples(self):
        """Test comprehensive examples mixing all formats."""
        examples = [
            # German
            ("8 Uhr", time(8, 0)),
            ("16 Uhr 30", time(16, 30)),
            ("halb 9", time(8, 30)),
            ("viertel nach 3", time(3, 15)),
            
            # English
            ("8 AM", time(8, 0)),
            ("4:30 PM", time(16, 30)),
            ("half past 8", time(8, 30)),
            ("quarter past 3", time(3, 15)),
            
            # Standard
            ("14:30", time(14, 30)),
            ("09:15", time(9, 15)),
            ("1430", time(14, 30)),
            
            # Mixed case and spacing
            ("4   PM", time(16, 0)),
            ("HALB 3", time(2, 30)),
            ("  14:30  ", time(14, 30)),
        ]
        
        for time_str, expected in examples:
            assert TimeParser.parse_time(time_str) == expected, f"Failed for: '{time_str}'"