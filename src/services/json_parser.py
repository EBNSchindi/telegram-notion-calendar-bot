"""JSON parser for extracting business calendar events from emails."""
import json
import re
import logging
from datetime import datetime
from typing import Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class BusinessEvent:
    """Represents a business calendar event extracted from email."""
    action: str  # Create, Update, Delete
    outlook_ical_id: str
    event_title: str
    event_start: datetime
    event_end: datetime
    organizer: str
    
    def is_team_event(self) -> bool:
        """Check if this event should be shared with the team."""
        team_keywords = [
            'gemeinsam', 'team', 'meeting', 'besprechung', 'workshop',
            'betriebsausflug', 'firmenevent', 'all hands', 'townhall',
            'kick-off', 'retrospective', 'planning', 'review'
        ]
        
        title_lower = self.event_title.lower()
        return any(keyword in title_lower for keyword in team_keywords)


class BusinessEventParser:
    """Parser for extracting business events from email content."""
    
    def __init__(self):
        self.json_pattern = re.compile(r'\{[^}]*\}', re.DOTALL)
        
    def extract_json_from_email(self, email_body: str, max_size: int = 50000) -> Optional[str]:
        """
        Extract JSON from email body with size limits.
        
        Args:
            email_body: The full email body content
            max_size: Maximum allowed email body size in characters
            
        Returns:
            JSON string if found, None otherwise
        """
        try:
            # Check email body size
            if len(email_body) > max_size:
                logger.warning(f"Email body too large: {len(email_body)} characters (max: {max_size})")
                return None
            # Split by lines and look for JSON in first few lines
            lines = email_body.strip().split('\n')
            
            for i, line in enumerate(lines[:5]):  # Check first 5 lines
                line = line.strip()
                if line.startswith('{') and line.endswith('}'):
                    return line
                    
            # If not found in single lines, try to find JSON pattern
            match = self.json_pattern.search(email_body)
            if match:
                return match.group(0)
                
            logger.warning("No JSON pattern found in email body")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting JSON from email: {e}")
            return None
    
    def parse_business_event(self, json_string: str, max_json_size: int = 10000) -> Optional[BusinessEvent]:
        """
        Parse JSON string into BusinessEvent object with size validation.
        
        Args:
            json_string: JSON string containing event data
            max_json_size: Maximum allowed JSON size in characters
            
        Returns:
            BusinessEvent object if parsing successful, None otherwise
        """
        try:
            # Check JSON size
            if len(json_string) > max_json_size:
                logger.warning(f"JSON too large: {len(json_string)} characters (max: {max_json_size})")
                return None
            
            data = json.loads(json_string)
            
            # Validate required fields
            required_fields = ['Action', 'OutlookICalID', 'EventTitle', 
                             'EventStart', 'EventEnd', 'Organizer']
            
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                logger.error(f"Missing required fields in JSON: {missing_fields}")
                return None
            
            # Parse datetime strings
            try:
                event_start = self._parse_datetime(data['EventStart'])
                event_end = self._parse_datetime(data['EventEnd'])
            except ValueError as e:
                logger.error(f"Error parsing datetime: {e}")
                return None
            
            # Validate action
            valid_actions = ['Create', 'Update', 'Delete']
            if data['Action'] not in valid_actions:
                logger.error(f"Invalid action: {data['Action']}. Must be one of {valid_actions}")
                return None
            
            return BusinessEvent(
                action=data['Action'],
                outlook_ical_id=data['OutlookICalID'],
                event_title=data['EventTitle'],
                event_start=event_start,
                event_end=event_end,
                organizer=data['Organizer']
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON format: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing business event: {e}")
            return None
    
    def _parse_datetime(self, datetime_string: str) -> datetime:
        """
        Parse datetime string from Outlook format.
        
        Expected format: "2025-06-03T14:30:00.0000000"
        
        Args:
            datetime_string: Datetime string from Outlook
            
        Returns:
            Parsed datetime object
            
        Raises:
            ValueError: If datetime format is invalid
        """
        try:
            # Remove microseconds part if present
            if '.' in datetime_string:
                datetime_string = datetime_string.split('.')[0]
            
            # Parse ISO format
            return datetime.fromisoformat(datetime_string)
            
        except ValueError:
            # Try alternative formats
            formats = [
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%dT%H:%M:%SZ'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(datetime_string, fmt)
                except ValueError:
                    continue
            
            raise ValueError(f"Unable to parse datetime: {datetime_string}")
    
    def parse_email_content(self, email_body: str) -> Optional[BusinessEvent]:
        """
        Complete parsing pipeline: extract JSON and parse event.
        
        Args:
            email_body: Full email body content
            
        Returns:
            BusinessEvent object if successful, None otherwise
        """
        json_string = self.extract_json_from_email(email_body)
        if not json_string:
            return None
            
        return self.parse_business_event(json_string)


def create_test_event() -> str:
    """Create a test JSON string for development purposes."""
    test_event = {
        "Action": "Create",
        "OutlookICalID": "040000008200E00074C5B7101A82E00807E9051B54BEE8D1F229DB0100000000000000001000000050CCE7B424DC2144B2C83BF866C22783",
        "EventTitle": "Team Meeting - Q1 Planning",
        "EventStart": "2025-06-03T14:30:00.0000000",
        "EventEnd": "2025-06-03T15:30:00.0000000",
        "Organizer": "Daniel.Schindler@dm.de"
    }
    return json.dumps(test_event)


if __name__ == "__main__":
    # Test the parser
    parser = BusinessEventParser()
    test_email = f"""
Betreff: Terminweiterleitung

{create_test_event()}

[Firmen-Footer kann ignoriert werden]
Mit freundlichen Grüßen
DM Corporate
"""
    
    event = parser.parse_email_content(test_email)
    if event:
        print(f"Successfully parsed event: {event.event_title}")
        print(f"Is team event: {event.is_team_event()}")
    else:
        print("Failed to parse event")