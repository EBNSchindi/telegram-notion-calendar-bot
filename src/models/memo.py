"""Memo model for task and note management."""
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
import pytz
from src.constants import (
    MAX_MEMO_TITLE_LENGTH,
    MAX_MEMO_NOTES_LENGTH,
    MEMO_STATUS_NOT_STARTED,
    MEMO_STATUS_IN_PROGRESS,
    MEMO_STATUS_COMPLETED,
    MEMO_STATUS_POSTPONED
)


class Memo(BaseModel):
    """Memo model for tasks and notes in Notion."""
    
    # Core fields matching Notion database
    aufgabe: str = Field(..., min_length=1, max_length=MAX_MEMO_TITLE_LENGTH, description="Task/memo title")
    status_check: bool = Field(default=False, description="Status checkbox")
    faelligkeitsdatum: Optional[datetime] = Field(None, description="Due date")
    bereich: Optional[str] = Field(None, description="Area/category")
    projekt: Optional[str] = Field(None, description="Project")
    notizen: Optional[str] = Field(None, max_length=MAX_MEMO_NOTES_LENGTH, description="Additional notes")
    
    # System fields
    notion_page_id: Optional[str] = Field(None, description="Notion page ID after creation")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp")
    
    
    @field_validator('aufgabe')
    @classmethod
    def validate_aufgabe(cls, v):
        """Validate task title is not empty after stripping and within length limits."""
        if not v.strip():
            raise ValueError("Aufgabe cannot be empty")
        
        stripped_value = v.strip()
        if len(stripped_value) > MAX_MEMO_TITLE_LENGTH:
            raise ValueError(f"Aufgabe exceeds maximum length of {MAX_MEMO_TITLE_LENGTH} characters")
        
        return stripped_value
    
    @field_validator('notizen')
    @classmethod
    def validate_notizen(cls, v):
        """Validate notes field length for security (DoS prevention)."""
        if v is not None and len(v) > MAX_MEMO_NOTES_LENGTH:
            raise ValueError(f"Notizen exceeds maximum length of {MAX_MEMO_NOTES_LENGTH} characters")
        return v
    
    @field_validator('status_check')
    @classmethod
    def validate_status_check(cls, v):
        """Validate status_check is a boolean."""
        return v if v is not None else False
    
    def to_notion_properties(self, timezone: str = "Europe/Berlin") -> dict:
        """Convert memo to Notion database properties."""
        properties = {
            "Aufgabe": {
                "title": [
                    {
                        "text": {
                            "content": self.aufgabe
                        }
                    }
                ]
            },
            "Status_Check": {
                "checkbox": self.status_check
            }
        }
        
        if self.faelligkeitsdatum:
            # Convert to timezone for display
            tz = pytz.timezone(timezone)
            local_date = self.faelligkeitsdatum.astimezone(tz) if self.faelligkeitsdatum.tzinfo else tz.localize(self.faelligkeitsdatum)
            properties["Fälligkeitsdatum"] = {
                "date": {
                    "start": local_date.isoformat()
                }
            }
        
        if self.bereich:
            properties["Bereich"] = {
                "multi_select": [{"name": self.bereich}]
            }
        
        if self.projekt:
            properties["Projekt"] = {
                "multi_select": [{"name": self.projekt}]
            }
        
        # Always include Notizen field, even if empty (fixes Issue #13)
        properties["Notizen"] = {
            "rich_text": [
                {
                    "text": {
                        "content": self.notizen or ""
                    }
                }
            ] if self.notizen else []
        }
        
        
        return properties
    
    @classmethod
    def from_notion_page(cls, page: dict) -> 'Memo':
        """Create memo from Notion page data."""
        properties = page['properties']
        
        # Extract task title
        aufgabe_prop = properties.get('Aufgabe', {})
        aufgabe = ""
        if aufgabe_prop.get('title') and aufgabe_prop['title']:
            aufgabe = aufgabe_prop['title'][0]['text']['content']
        
        # Extract status_check
        status_check = False
        status_check_prop = properties.get('Status_Check', {})
        if status_check_prop.get('checkbox') is not None:
            status_check = status_check_prop['checkbox']
        
        # Extract due date
        faelligkeitsdatum = None
        date_prop = properties.get('Fälligkeitsdatum', {})
        if date_prop.get('date') and date_prop['date']:
            date_str = date_prop['date']['start']
            faelligkeitsdatum = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        
        # Extract area
        bereich = None
        bereich_prop = properties.get('Bereich', {})
        if bereich_prop.get('multi_select') and bereich_prop['multi_select']:
            bereich = bereich_prop['multi_select'][0]['name']
        
        # Extract project
        projekt = None
        projekt_prop = properties.get('Projekt', {})
        if projekt_prop.get('multi_select') and projekt_prop['multi_select']:
            projekt = projekt_prop['multi_select'][0]['name']
        
        # Extract notes
        notizen = None
        notizen_prop = properties.get('Notizen', {})
        if notizen_prop.get('rich_text') and notizen_prop['rich_text']:
            notizen = notizen_prop['rich_text'][0]['text']['content']
        
        # Extract status check
        status_check = False
        status_check_prop = properties.get('Status Check', {})
        if status_check_prop.get('checkbox') is not None:
            status_check = status_check_prop['checkbox']
        
        # Extract creation date
        created_at = datetime.fromisoformat(page['created_time'].replace('Z', '+00:00'))
        
        return cls(
            aufgabe=aufgabe,
            status_check=status_check,
            faelligkeitsdatum=faelligkeitsdatum,
            bereich=bereich,
            projekt=projekt,
            notizen=notizen,
            notion_page_id=page['id'],
            created_at=created_at
        )
    
    def format_for_telegram(self, timezone: str = "Europe/Berlin") -> str:
        """Format memo for Telegram display with proper XSS protection."""
        from src.utils.security import InputSanitizer
        
        # Checkbox emoji
        emoji = "✅" if self.status_check else "☐"
        
        # Escape all text fields for Telegram markdown to prevent XSS
        escaped_aufgabe = InputSanitizer.sanitize_telegram_markdown(self.aufgabe)
        
        formatted = f"{emoji} *{escaped_aufgabe}*\n"
        
        if self.faelligkeitsdatum:
            tz = pytz.timezone(timezone)
            local_date = self.faelligkeitsdatum.astimezone(tz) if self.faelligkeitsdatum.tzinfo else tz.localize(self.faelligkeitsdatum)
            formatted += f"📅 Fällig: {local_date.strftime('%d.%m.%Y')}\n"
        
        if self.bereich:
            escaped_bereich = InputSanitizer.sanitize_telegram_markdown(self.bereich)
            formatted += f"🏷️ Bereich: {escaped_bereich}\n"
        
        if self.projekt:
            escaped_projekt = InputSanitizer.sanitize_telegram_markdown(self.projekt)
            formatted += f"📁 Projekt: {escaped_projekt}\n"
        
        if self.notizen:
            escaped_notizen = InputSanitizer.sanitize_telegram_markdown(self.notizen)
            formatted += f"📝 Notizen: {escaped_notizen}\n"
        
        return formatted
    
    def format_for_telegram_with_checkbox(self, timezone: str = "Europe/Berlin") -> str:
        """Format memo for Telegram display with checkbox status.
        
        This is an alias for format_for_telegram() for backward compatibility.
        """
        return self.format_for_telegram(timezone)
    
