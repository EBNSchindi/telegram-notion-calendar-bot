"""Shared appointment model without PartnerRelevant property."""

from datetime import datetime, timezone, timedelta
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
import pytz

from .appointment import Appointment


class SharedAppointment(Appointment):
    """
    Appointment model specifically for shared databases.
    Excludes PartnerRelevant property since all appointments in shared DB are partner-relevant by definition.
    """
    
    def to_notion_properties(self, timezone: str = "Europe/Berlin") -> dict:
        """Convert appointment to Notion database properties for shared database."""
        # Get base properties from parent class
        properties = super().to_notion_properties(timezone)
        
        # Remove PartnerRelevant from shared database properties
        if "PartnerRelevant" in properties:
            del properties["PartnerRelevant"]
        
        # Remove SyncedToSharedId from shared database (not needed there)
        if "SyncedToSharedId" in properties:
            del properties["SyncedToSharedId"]
        
        return properties
    
    @classmethod
    def from_notion_page(cls, page: dict) -> 'SharedAppointment':
        """Create shared appointment from Notion page data.
        
        Handles both new format (separate Startdatum/Endedatum fields) and
        old format (single Datum field) for backward compatibility.
        
        Args:
            page: Notion page data from API
            
        Returns:
            SharedAppointment: Parsed appointment instance
            
        Migration logic:
        1. First tries to read from new Startdatum/Endedatum fields
        2. Falls back to old Datum field if new fields not found
        3. Uses Duration field or defaults to 60 minutes for end time calculation
        """
        properties = page['properties']
        
        # Extract title (from "Name" or "Title" field for backward compatibility)
        title_prop = properties.get('Name', properties.get('Title', {}))
        title = ""
        if title_prop.get('title') and title_prop['title']:
            title = title_prop['title'][0]['text']['content']
        
        # Extract dates with backward compatibility
        start_date = None
        end_date = None
        date = None
        
        # Try to read from new fields first
        start_date_prop = properties.get('Startdatum', {})
        if start_date_prop.get('date') and start_date_prop['date']:
            start_date_str = start_date_prop['date']['start']
            start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
        
        end_date_prop = properties.get('Endedatum', {})
        if end_date_prop.get('date') and end_date_prop['date']:
            end_date_str = end_date_prop['date']['start']
            end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
        
        # Fallback to old "Datum" field if new fields not available
        if not start_date or not end_date:
            date_prop = properties.get('Datum', properties.get('Date', {}))
            if date_prop and 'date' in date_prop and date_prop['date'] is not None:
                date_str = date_prop['date']['start']
                date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                
                # If only old date field exists, use it for both start and end
                if not start_date:
                    start_date = date
                if not end_date:
                    # Check if duration_minutes is available
                    duration_minutes = None
                    duration_prop = properties.get('Duration', {})
                    if duration_prop.get('number') is not None:
                        duration_minutes = duration_prop['number']
                    
                    # Use duration or default to 60 minutes
                    duration = duration_minutes if duration_minutes else 60
                    end_date = start_date + timedelta(minutes=duration)
            
        # Ensure we have required dates
        if not start_date or not end_date:
            raise ValueError("Missing or invalid date fields in Notion page")
        
        # Extract description
        description = None
        desc_prop = properties.get('Beschreibung', {})
        if desc_prop.get('rich_text') and desc_prop['rich_text']:
            description = desc_prop['rich_text'][0]['text']['content']
        
        # Extract location
        location = None
        loc_prop = properties.get('Ort', {})
        if loc_prop.get('rich_text') and loc_prop['rich_text']:
            location = loc_prop['rich_text'][0]['text']['content']
        
        # Extract tags
        tags = None
        tags_prop = properties.get('Tags', {})
        if tags_prop.get('rich_text') and tags_prop['rich_text']:
            tags_text = tags_prop['rich_text'][0]['text']['content']
            tags = [tag.strip() for tag in tags_text.split(',') if tag.strip()]
        
        # Business calendar fields
        outlook_id = None
        outlook_prop = properties.get('OutlookID', {})
        if outlook_prop.get('rich_text') and outlook_prop['rich_text']:
            outlook_id = outlook_prop['rich_text'][0]['text']['content']
        
        organizer = None
        organizer_prop = properties.get('Organizer', {})
        if organizer_prop.get('rich_text') and organizer_prop['rich_text']:
            organizer = organizer_prop['rich_text'][0]['text']['content']
        
        # Tracking fields specific to shared database
        source_private_id = None
        source_prop = properties.get('SourcePrivateId', {})
        if source_prop.get('rich_text') and source_prop['rich_text']:
            source_private_id = source_prop['rich_text'][0]['text']['content']
        
        source_user_id = None
        user_prop = properties.get('SourceUserId', {})
        if user_prop.get('number') is not None:
            source_user_id = user_prop['number']
        
        # Extract creation date
        created_at = datetime.fromisoformat(page['created_time'].replace('Z', '+00:00'))
        
        # Calculate duration from dates if not explicitly set
        duration_minutes = None
        duration_prop = properties.get('Duration', {})
        if duration_prop.get('number') is not None:
            duration_minutes = duration_prop['number']
        elif start_date and end_date:
            # Calculate duration from date difference
            duration_minutes = int((end_date - start_date).total_seconds() / 60)
        
        return cls(
            title=title,
            start_date=start_date,
            end_date=end_date,
            date=date if date else start_date,  # Set date for backward compatibility
            description=description,
            location=location,
            tags=tags,
            notion_page_id=page['id'],
            created_at=created_at,
            outlook_id=outlook_id,
            organizer=organizer,
            duration_minutes=duration_minutes,
            is_business_event=False,
            partner_relevant=True,  # Always True in shared database
            synced_to_shared_id=None,  # Not used in shared database
            source_private_id=source_private_id,
            source_user_id=source_user_id
        )