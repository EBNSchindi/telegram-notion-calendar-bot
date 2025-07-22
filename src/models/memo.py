from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field, field_validator
import pytz
from src.constants import (
    MAX_MEMO_TITLE_LENGTH,
    MAX_CATEGORY_LENGTH,
    MAX_PROJECT_LENGTH,
    MAX_MEMO_NOTES_LENGTH,
    MAX_NOTES_PREVIEW_LENGTH,
    MEMO_STATUS_NOT_STARTED,
    MEMO_STATUS_IN_PROGRESS,
    MEMO_STATUS_COMPLETED
)


class Memo(BaseModel):
    """Memo model for tasks and notes."""
    
    aufgabe: str = Field(..., min_length=1, max_length=MAX_MEMO_TITLE_LENGTH, description="Task/memo title - REQUIRED")
    status: str = Field(default=MEMO_STATUS_NOT_STARTED, description="Task status")
    faelligkeitsdatum: Optional[datetime] = Field(None, description="Optional due date")
    bereich: Optional[str] = Field(None, max_length=MAX_CATEGORY_LENGTH, description="Optional area/category")
    projekt: Optional[str] = Field(None, max_length=MAX_PROJECT_LENGTH, description="Optional project")
    notizen: Optional[str] = Field(None, max_length=MAX_MEMO_NOTES_LENGTH, description="Optional additional notes")
    notion_page_id: Optional[str] = Field(None, description="Notion page ID after creation")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp")
    
    @field_validator('aufgabe')
    @classmethod
    def validate_aufgabe(cls, v):
        """Validate task title is not empty after stripping."""
        if not v or not v.strip():
            raise ValueError("Aufgabe cannot be empty")
        return v.strip()
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        """Validate status is one of the allowed values."""
        allowed_statuses = [MEMO_STATUS_NOT_STARTED, MEMO_STATUS_IN_PROGRESS, MEMO_STATUS_COMPLETED]
        if v not in allowed_statuses:
            # Default to "Nicht begonnen" if invalid status provided
            return MEMO_STATUS_NOT_STARTED
        return v
    
    def to_notion_properties(self, timezone: str = "Europe/Berlin") -> dict:
        """Convert memo to Notion database properties."""
        properties = {
            "Aufgabe": {  # Title field - REQUIRED
                "title": [
                    {
                        "text": {
                            "content": self.aufgabe
                        }
                    }
                ]
            },
            "Status": {  # Status field
                "status": {
                    "name": self.status
                }
            }
        }
        
        # Optional due date
        if self.faelligkeitsdatum:
            tz = pytz.timezone(timezone)
            local_date = self.faelligkeitsdatum.astimezone(tz) if self.faelligkeitsdatum.tzinfo else tz.localize(self.faelligkeitsdatum)
            properties["Fälligkeitsdatum"] = {
                "date": {
                    "start": local_date.date().isoformat()  # Date only, no time
                }
            }
        
        # Optional area/category (multi_select)
        if self.bereich:
            properties["Bereich"] = {
                "multi_select": [
                    {
                        "name": self.bereich
                    }
                ]
            }
        
        # Optional project (multi_select)
        if self.projekt:
            properties["Projekt"] = {
                "multi_select": [
                    {
                        "name": self.projekt
                    }
                ]
            }
        
        # Optional notes
        if self.notizen:
            properties["Notizen"] = {
                "rich_text": [
                    {
                        "text": {
                            "content": self.notizen
                        }
                    }
                ]
            }
        
        return properties
    
    @classmethod
    def from_notion_page(cls, page: dict) -> 'Memo':
        """Create memo from Notion page data."""
        properties = page['properties']
        
        # Extract title (from "Aufgabe" field - REQUIRED)
        aufgabe_prop = properties.get('Aufgabe', {})
        aufgabe = ""
        if aufgabe_prop.get('title') and aufgabe_prop['title']:
            aufgabe = aufgabe_prop['title'][0]['text']['content']
        
        if not aufgabe:
            raise ValueError("Missing or empty 'Aufgabe' field in Notion page")
        
        # Extract status (from "Status" field)
        status = MEMO_STATUS_NOT_STARTED  # Default
        status_prop = properties.get('Status', {})
        if status_prop.get('status') and status_prop['status'].get('name'):
            status = status_prop['status']['name']
        
        # Extract due date (from "Fälligkeitsdatum" field)
        faelligkeitsdatum = None
        due_date_prop = properties.get('Fälligkeitsdatum', {})
        if due_date_prop.get('date') and due_date_prop['date'].get('start'):
            date_str = due_date_prop['date']['start']
            # Handle date-only format (no time)
            if 'T' in date_str:
                faelligkeitsdatum = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                faelligkeitsdatum = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        
        # Extract area/category (from "Bereich" multi_select field)
        bereich = None
        bereich_prop = properties.get('Bereich', {})
        if bereich_prop.get('multi_select') and bereich_prop['multi_select']:
            bereich = bereich_prop['multi_select'][0]['name']
        
        # Extract project (from "Projekt" multi_select field)
        projekt = None
        projekt_prop = properties.get('Projekt', {})
        if projekt_prop.get('multi_select') and projekt_prop['multi_select']:
            projekt = projekt_prop['multi_select'][0]['name']
        
        # Extract notes (from "Notizen" field)
        notizen = None
        notizen_prop = properties.get('Notizen', {})
        if notizen_prop.get('rich_text') and notizen_prop['rich_text']:
            notizen = notizen_prop['rich_text'][0]['text']['content']
        
        # Extract creation date (use page creation time)
        created_at = datetime.fromisoformat(page['created_time'].replace('Z', '+00:00'))
        
        return cls(
            aufgabe=aufgabe,
            status=status,
            faelligkeitsdatum=faelligkeitsdatum,
            bereich=bereich,
            projekt=projekt,
            notizen=notizen,
            notion_page_id=page['id'],
            created_at=created_at
        )
    
    def format_for_telegram(self, timezone: str = "Europe/Berlin") -> str:
        """Format memo for Telegram display."""
        formatted = f"📝 *{self.aufgabe}*\n"
        
        # Status with emoji
        status_emoji = {
            MEMO_STATUS_NOT_STARTED: "⭕",
            MEMO_STATUS_IN_PROGRESS: "🔄", 
            MEMO_STATUS_COMPLETED: "✅"
        }
        emoji = status_emoji.get(self.status, "⭕")
        formatted += f"{emoji} Status: {self.status}\n"
        
        # Due date if available
        if self.faelligkeitsdatum:
            tz = pytz.timezone(timezone)
            local_date = self.faelligkeitsdatum.astimezone(tz) if self.faelligkeitsdatum.tzinfo else tz.localize(self.faelligkeitsdatum)
            formatted += f"📅 Fällig: {local_date.strftime('%d.%m.%Y')}\n"
        
        # Area/category if available
        if self.bereich:
            formatted += f"📂 Bereich: {self.bereich}\n"
        
        # Project if available
        if self.projekt:
            formatted += f"📁 Projekt: {self.projekt}\n"
        
        # Notes if available (truncated for display)
        if self.notizen:
            notes_display = self.notizen[:MAX_NOTES_PREVIEW_LENGTH] + "..." if len(self.notizen) > MAX_NOTES_PREVIEW_LENGTH else self.notizen
            formatted += f"🗒️ Notizen: {notes_display}\n"
        
        return formatted