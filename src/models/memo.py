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
    MEMO_STATUS_COMPLETED
)


class Memo(BaseModel):
    """Memo model for tasks and notes in Notion."""
    
    # Core fields matching Notion database
    aufgabe: str = Field(..., min_length=1, max_length=MAX_MEMO_TITLE_LENGTH, description="Task/memo title")
    status: str = Field(default=MEMO_STATUS_NOT_STARTED, description="Task status")
    faelligkeitsdatum: Optional[datetime] = Field(None, description="Due date")
    bereich: Optional[str] = Field(None, description="Area/category")
    projekt: Optional[str] = Field(None, description="Project")
    notizen: Optional[str] = Field(None, max_length=MAX_MEMO_NOTES_LENGTH, description="Additional notes")
    
    # System fields
    notion_page_id: Optional[str] = Field(None, description="Notion page ID after creation")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp")
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        """Validate status is one of the allowed values."""
        allowed_statuses = [MEMO_STATUS_NOT_STARTED, MEMO_STATUS_IN_PROGRESS, MEMO_STATUS_COMPLETED]
        if v not in allowed_statuses:
            raise ValueError(f"Status must be one of: {', '.join(allowed_statuses)}")
        return v
    
    @field_validator('aufgabe')
    @classmethod
    def validate_aufgabe(cls, v):
        """Validate task title is not empty after stripping."""
        if not v.strip():
            raise ValueError("Aufgabe cannot be empty")
        return v.strip()
    
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
            "Status": {
                "select": {
                    "name": self.status
                }
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
        
        # Extract task title
        aufgabe_prop = properties.get('Aufgabe', {})
        aufgabe = ""
        if aufgabe_prop.get('title') and aufgabe_prop['title']:
            aufgabe = aufgabe_prop['title'][0]['text']['content']
        
        # Extract status
        status = MEMO_STATUS_NOT_STARTED
        status_prop = properties.get('Status', {})
        if status_prop.get('select') and status_prop['select']:
            status = status_prop['select']['name']
        
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
        
        # Extract creation date
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
        # Status emoji
        status_emoji = {
            MEMO_STATUS_NOT_STARTED: "⭕",
            MEMO_STATUS_IN_PROGRESS: "🔄",
            MEMO_STATUS_COMPLETED: "✅"
        }
        emoji = status_emoji.get(self.status, "⭕")
        
        formatted = f"{emoji} *{self.aufgabe}*\n"
        formatted += f"📊 Status: {self.status}\n"
        
        if self.faelligkeitsdatum:
            tz = pytz.timezone(timezone)
            local_date = self.faelligkeitsdatum.astimezone(tz) if self.faelligkeitsdatum.tzinfo else tz.localize(self.faelligkeitsdatum)
            formatted += f"📅 Fällig: {local_date.strftime('%d.%m.%Y')}\n"
        
        if self.bereich:
            formatted += f"🏷️ Bereich: {self.bereich}\n"
        
        if self.projekt:
            formatted += f"📁 Projekt: {self.projekt}\n"
        
        if self.notizen:
            formatted += f"📝 Notizen: {self.notizen}\n"
        
        return formatted