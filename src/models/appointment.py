from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
import pytz
from src.constants import (
    MAX_APPOINTMENT_TITLE_LENGTH,
    MAX_DESCRIPTION_LENGTH,
    MAX_LOCATION_LENGTH
)


class Appointment(BaseModel):
    """Appointment model for calendar events."""
    
    title: str = Field(..., min_length=1, max_length=MAX_APPOINTMENT_TITLE_LENGTH, description="Appointment title")
    date: datetime = Field(..., description="Appointment date and time")
    description: Optional[str] = Field(None, max_length=MAX_DESCRIPTION_LENGTH, description="Optional description")
    location: Optional[str] = Field(None, max_length=MAX_LOCATION_LENGTH, description="Optional location")
    tags: Optional[List[str]] = Field(None, description="Optional tags")
    notion_page_id: Optional[str] = Field(None, description="Notion page ID after creation")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp")
    
    # Business calendar specific fields
    outlook_id: Optional[str] = Field(None, description="Outlook/Exchange calendar ID for business events")
    organizer: Optional[str] = Field(None, description="Event organizer email")
    duration_minutes: Optional[int] = Field(None, description="Event duration in minutes")
    is_business_event: bool = Field(False, description="Whether this is a business calendar event")
    
    # Partner relevance field
    partner_relevant: bool = Field(False, description="Whether this appointment is relevant for partner")
    
    # Sync tracking fields for partner sync service
    synced_to_shared_id: Optional[str] = Field(None, description="ID of synced appointment in shared database")
    source_private_id: Optional[str] = Field(None, description="ID of source appointment in private database")
    source_user_id: Optional[int] = Field(None, description="Telegram user ID of appointment creator")
    
    @field_validator('date')
    @classmethod
    def validate_date(cls, v):
        """Validate that the appointment date is in the future."""
        # Only validate future dates for new appointments (not when parsing from Notion)
        # Skip validation if this is from a Notion page (has timezone info) or if it's a business event
        if v.tzinfo is None:
            # Add UTC timezone for comparison
            v_with_tz = v.replace(tzinfo=timezone.utc)
            if v_with_tz <= datetime.now(timezone.utc):
                # Allow past dates for business events (they might be historical)
                pass  # Skip validation for now
        return v
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        """Validate title is not empty after stripping."""
        if not v.strip():
            raise ValueError("Title cannot be empty")
        return v.strip()
    
    def to_notion_properties(self, timezone: str = "Europe/Berlin") -> dict:
        """Convert appointment to Notion database properties."""
        # Convert to specified timezone for display
        tz = pytz.timezone(timezone)
        local_date = self.date.astimezone(tz) if self.date.tzinfo else tz.localize(self.date)
        
        properties = {
            "Name": {  # Updated to match your database field
                "title": [
                    {
                        "text": {
                            "content": self.title
                        }
                    }
                ]
            },
            "Datum": {  # Updated to match your database field
                "date": {
                    "start": local_date.isoformat()
                }
            }
        }
        
        if self.description:
            properties["Beschreibung"] = {  # Updated to match your database field
                "rich_text": [
                    {
                        "text": {
                            "content": self.description
                        }
                    }
                ]
            }
        
        if self.location:
            properties["Ort"] = {  # New field for your database
                "rich_text": [
                    {
                        "text": {
                            "content": self.location
                        }
                    }
                ]
            }
        
        if self.tags:
            # Convert tags to comma-separated string for rich_text field
            properties["Tags"] = {  # New field for your database
                "rich_text": [
                    {
                        "text": {
                            "content": ", ".join(self.tags)
                        }
                    }
                ]
            }
        
        # Business calendar specific fields
        if self.outlook_id:
            properties["OutlookID"] = {
                "rich_text": [
                    {
                        "text": {
                            "content": self.outlook_id
                        }
                    }
                ]
            }
        
        if self.organizer:
            properties["Organizer"] = {
                "rich_text": [
                    {
                        "text": {
                            "content": self.organizer
                        }
                    }
                ]
            }
        
        # Duration and BusinessEvent fields are optional - skip if not needed
        
        # Partner relevance field
        properties["PartnerRelevant"] = {
            "checkbox": self.partner_relevant
        }
        
        # Sync tracking fields for partner sync service
        if self.synced_to_shared_id:
            properties["SyncedToSharedId"] = {
                "rich_text": [
                    {
                        "text": {
                            "content": self.synced_to_shared_id
                        }
                    }
                ]
            }
        
        if self.source_private_id:
            properties["SourcePrivateId"] = {
                "rich_text": [
                    {
                        "text": {
                            "content": self.source_private_id
                        }
                    }
                ]
            }
        
        if self.source_user_id:
            properties["SourceUserId"] = {
                "number": self.source_user_id
            }
        
        return properties
    
    @classmethod
    def from_notion_page(cls, page: dict) -> 'Appointment':
        """Create appointment from Notion page data."""
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
        
        # Extract description (from "Beschreibung" field)
        description = None
        desc_prop = properties.get('Beschreibung', {})
        if desc_prop.get('rich_text') and desc_prop['rich_text']:
            description = desc_prop['rich_text'][0]['text']['content']
        
        # Extract location (from "Ort" field)
        location = None
        loc_prop = properties.get('Ort', {})
        if loc_prop.get('rich_text') and loc_prop['rich_text']:
            location = loc_prop['rich_text'][0]['text']['content']
        
        # Extract tags (from "Tags" field as rich_text)
        tags = None
        tags_prop = properties.get('Tags', {})
        if tags_prop.get('rich_text') and tags_prop['rich_text']:
            tags_text = tags_prop['rich_text'][0]['text']['content']
            # Split comma-separated tags and clean them
            tags = [tag.strip() for tag in tags_text.split(',') if tag.strip()]
        
        # Extract business calendar specific fields
        outlook_id = None
        outlook_prop = properties.get('OutlookID', {})
        if outlook_prop.get('rich_text') and outlook_prop['rich_text']:
            outlook_id = outlook_prop['rich_text'][0]['text']['content']
        
        organizer = None
        organizer_prop = properties.get('Organizer', {})
        if organizer_prop.get('rich_text') and organizer_prop['rich_text']:
            organizer = organizer_prop['rich_text'][0]['text']['content']
        
        # Duration and BusinessEvent fields are optional - skip if not needed
        duration_minutes = None
        is_business_event = False
        
        # Extract partner relevance
        partner_relevant = False
        partner_prop = properties.get('PartnerRelevant', {})
        if partner_prop.get('checkbox') is not None:
            partner_relevant = partner_prop['checkbox']
        
        # Extract sync tracking fields (handle potential whitespace in property names)
        synced_to_shared_id = None
        sync_prop = properties.get('SyncedToSharedId', {})
        if sync_prop.get('rich_text') and sync_prop['rich_text']:
            synced_to_shared_id = sync_prop['rich_text'][0]['text']['content']
        
        source_private_id = None
        source_prop = properties.get('SourcePrivateId', {})
        if source_prop.get('rich_text') and source_prop['rich_text']:
            source_private_id = source_prop['rich_text'][0]['text']['content']
        
        source_user_id = None
        user_prop = properties.get('SourceUserId', {})
        if user_prop.get('number') is not None:
            source_user_id = user_prop['number']
        
        # Extract creation date (use page creation time as fallback)
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
            duration_minutes=duration_minutes,
            is_business_event=is_business_event,
            partner_relevant=partner_relevant,
            synced_to_shared_id=synced_to_shared_id,
            source_private_id=source_private_id,
            source_user_id=source_user_id
        )
    
    def format_for_telegram(self, timezone: str = "Europe/Berlin") -> str:
        """Format appointment for Telegram display."""
        tz = pytz.timezone(timezone)
        local_date = self.date.astimezone(tz) if self.date.tzinfo else tz.localize(self.date)
        
        formatted = f"📅 *{self.title}*\n"
        formatted += f"🕐 {local_date.strftime('%d.%m.%Y um %H:%M')}\n"
        
        if self.description:
            formatted += f"📝 {self.description}\n"
        
        if self.location:
            formatted += f"📍 {self.location}\n"
        
        if self.tags:
            formatted += f"🏷️ {', '.join(self.tags)}\n"
        
        if self.partner_relevant:
            formatted += f"💑 Partner-relevant\n"
        
        return formatted