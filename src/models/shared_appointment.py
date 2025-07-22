"""Shared appointment model without PartnerRelevant property."""

from datetime import datetime, timezone
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
        """Create shared appointment from Notion page data."""
        properties = page['properties']
        
        # Extract title (from "Name" or "Title" field for backward compatibility)
        title_prop = properties.get('Name', properties.get('Title', {}))
        title = ""
        if title_prop.get('title') and title_prop['title']:
            title = title_prop['title'][0]['text']['content']
        
        # Extract date (from "Datum" or "Date" field for backward compatibility)
        date_prop = properties.get('Datum', properties.get('Date', {}))
        if not date_prop or 'date' not in date_prop:
            raise ValueError(f"Missing or invalid date field in Notion page")
        date_str = date_prop['date']['start']
        date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        
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
        
        return cls(
            title=title,
            date=date,
            description=description,
            location=location,
            tags=tags,
            notion_page_id=page['id'],
            created_at=created_at,
            outlook_id=outlook_id,
            organizer=organizer,
            duration_minutes=None,
            is_business_event=False,
            partner_relevant=True,  # Always True in shared database
            synced_to_shared_id=None,  # Not used in shared database
            source_private_id=source_private_id,
            source_user_id=source_user_id
        )