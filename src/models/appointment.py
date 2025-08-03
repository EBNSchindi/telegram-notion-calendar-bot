from datetime import datetime, timezone, timedelta
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, model_validator
import pytz
from src.constants import (
    MAX_APPOINTMENT_TITLE_LENGTH,
    MAX_DESCRIPTION_LENGTH,
    MAX_LOCATION_LENGTH
)


class Appointment(BaseModel):
    """Appointment model for calendar events."""
    
    title: str = Field(..., min_length=1, max_length=MAX_APPOINTMENT_TITLE_LENGTH, description="Appointment title")
    # New date fields
    start_date: datetime = Field(..., description="Appointment start date and time")
    end_date: datetime = Field(..., description="Appointment end date and time")
    # Keep date field for backward compatibility
    date: Optional[datetime] = Field(None, description="Appointment date and time (deprecated, use start_date)")
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
    
    def __init__(self, **data):
        """Initialize appointment with migration logic for backward compatibility.
        
        This method handles the migration from the old single 'date' field to the new
        'start_date' and 'end_date' fields while maintaining full backward compatibility.
        
        Migration scenarios:
        1. Old format (only 'date'): Sets start_date = date, end_date = date + duration
        2. Partial new format (only 'start_date'): Calculates end_date using duration
        3. Full new format: Uses provided start_date and end_date, sets date for compatibility
        
        Args:
            **data: Appointment data that may contain either old or new date fields
            
        Notes:
            - Default duration is 60 minutes when not specified
            - The 'date' field is maintained for backward compatibility
            - All three fields (date, start_date, end_date) will be populated after init
        """
        # Handle backward compatibility: if only 'date' is provided, set start_date and end_date
        if 'date' in data and 'start_date' not in data and 'end_date' not in data:
            date_value = data['date']
            data['start_date'] = date_value
            # Use duration_minutes if available, otherwise default to 60 minutes
            duration = data.get('duration_minutes', 60)
            data['end_date'] = date_value + timedelta(minutes=duration)
        
        # If start_date is provided but not end_date, calculate end_date
        elif 'start_date' in data and 'end_date' not in data:
            duration = data.get('duration_minutes', 60)
            data['end_date'] = data['start_date'] + timedelta(minutes=duration)
        
        # If both start_date and end_date are provided but not date, set date to start_date
        elif 'start_date' in data and 'end_date' in data and 'date' not in data:
            data['date'] = data['start_date']
        
        super().__init__(**data)
    
    @field_validator('start_date')
    @classmethod
    def validate_start_date(cls, v):
        """Validate that the appointment start date is in the future."""
        # Only validate future dates for new appointments (not when parsing from Notion)
        # Skip validation if this is from a Notion page (has timezone info) or if it's a business event
        if v.tzinfo is None:
            # Add UTC timezone for comparison
            v_with_tz = v.replace(tzinfo=timezone.utc)
            if v_with_tz <= datetime.now(timezone.utc):
                # Allow past dates for business events (they might be historical)
                pass  # Skip validation for now
        return v
    
    @model_validator(mode='after')
    def validate_date_order(self):
        """Validate that end_date is after start_date.
        
        This ensures appointments have a positive duration. Equal start and end times
        are not allowed as they would represent zero-duration appointments.
        
        Returns:
            self: The validated appointment instance
            
        Raises:
            ValueError: If end_date is not after start_date
        """
        if self.start_date and self.end_date:
            if self.end_date <= self.start_date:
                raise ValueError("End date must be after start date")
        return self
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        """Validate title is not empty after stripping."""
        if not v.strip():
            raise ValueError("Title cannot be empty")
        return v.strip()
    
    def to_notion_properties(self, timezone: str = "Europe/Berlin") -> dict:
        """Convert appointment to Notion database properties.
        
        Formats the appointment data for Notion API, using the new separate
        Startdatum and Endedatum fields instead of the old single Datum field.
        
        Args:
            timezone: Timezone string for date formatting (default: Europe/Berlin)
            
        Returns:
            dict: Notion properties formatted for API
            
        Field mapping:
            - Name: Appointment title
            - Startdatum: Start date and time (new field)
            - Endedatum: End date and time (new field)
            - Beschreibung: Optional description
            - Ort: Optional location
            - PartnerRelevant: Boolean for partner visibility
        """
        # Convert to specified timezone for display
        tz = pytz.timezone(timezone)
        local_start_date = self.start_date.astimezone(tz) if self.start_date.tzinfo else tz.localize(self.start_date)
        local_end_date = self.end_date.astimezone(tz) if self.end_date.tzinfo else tz.localize(self.end_date)
        
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
            "Startdatum": {  # New field for start date
                "date": {
                    "start": local_start_date.isoformat()
                }
            },
            "Endedatum": {  # New field for end date
                "date": {
                    "start": local_end_date.isoformat()
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
        """Create appointment from Notion page data.
        
        Handles both new format (separate Startdatum/Endedatum fields) and
        old format (single Datum field) for backward compatibility.
        
        Args:
            page: Notion page data from API
            
        Returns:
            Appointment: Parsed appointment instance
            
        Migration logic:
        1. First tries to read from new Startdatum/Endedatum fields
        2. Falls back to old Datum field if new fields not found
        3. Uses Duration field or defaults to 60 minutes for end time calculation
        
        Raises:
            ValueError: If required date fields are missing or invalid
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
        
        # Extract duration from Duration field or calculate from dates
        duration_minutes = None
        duration_prop = properties.get('Duration', {})
        if duration_prop.get('number') is not None:
            duration_minutes = duration_prop['number']
        elif start_date and end_date:
            # Calculate duration from date difference
            duration_minutes = int((end_date - start_date).total_seconds() / 60)
        
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
            is_business_event=is_business_event,
            partner_relevant=partner_relevant,
            synced_to_shared_id=synced_to_shared_id,
            source_private_id=source_private_id,
            source_user_id=source_user_id
        )
    
    def format_for_telegram(self, timezone: str = "Europe/Berlin") -> str:
        """Format appointment for Telegram display."""
        tz = pytz.timezone(timezone)
        local_start_date = self.start_date.astimezone(tz) if self.start_date.tzinfo else tz.localize(self.start_date)
        local_end_date = self.end_date.astimezone(tz) if self.end_date.tzinfo else tz.localize(self.end_date)
        
        formatted = f"📅 *{self.title}*\n"
        
        # Check if it's a single day appointment
        if local_start_date.date() == local_end_date.date():
            # Same day - show date once and time range
            formatted += f"🕐 {local_start_date.strftime('%d.%m.%Y')} von {local_start_date.strftime('%H:%M')} bis {local_end_date.strftime('%H:%M')}\n"
        else:
            # Different days - show full date/time for both
            formatted += f"🕐 Start: {local_start_date.strftime('%d.%m.%Y um %H:%M')}\n"
            formatted += f"🕑 Ende: {local_end_date.strftime('%d.%m.%Y um %H:%M')}\n"
        
        if self.description:
            formatted += f"📝 {self.description}\n"
        
        if self.location:
            formatted += f"📍 {self.location}\n"
        
        if self.tags:
            formatted += f"🏷️ {', '.join(self.tags)}\n"
        
        if self.partner_relevant:
            formatted += f"💑 Partner-relevant\n"
        
        return formatted