from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
import pytz


class Appointment(BaseModel):
    """Appointment model for calendar events."""
    
    title: str = Field(..., min_length=1, max_length=200, description="Appointment title")
    date: datetime = Field(..., description="Appointment date and time")
    description: Optional[str] = Field(None, max_length=1000, description="Optional description")
    location: Optional[str] = Field(None, max_length=200, description="Optional location")
    tags: Optional[List[str]] = Field(None, description="Optional tags")
    notion_page_id: Optional[str] = Field(None, description="Notion page ID after creation")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp")
    
    @field_validator('date')
    @classmethod
    def validate_date(cls, v):
        """Validate that the appointment date is in the future."""
        # Only validate future dates for new appointments (not when parsing from Notion)
        # Skip validation if this is from a Notion page (has timezone info)
        if v.tzinfo is None and v <= datetime.now(timezone.utc):
            raise ValueError("Appointment date must be in the future")
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
        
        # Extract creation date (use page creation time as fallback)
        created_at = datetime.fromisoformat(page['created_time'].replace('Z', '+00:00'))
        
        return cls(
            title=title,
            date=date,
            description=description,
            location=location,
            tags=tags,
            notion_page_id=page['id'],
            created_at=created_at
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
        
        return formatted