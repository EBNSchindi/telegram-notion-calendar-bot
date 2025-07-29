"""Memo model for note entities."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


@dataclass
class Memo:
    """Represents a memo/note entity."""
    
    notion_id: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    
    def __str__(self) -> str:
        """String representation of memo."""
        return f"Memo: {self.title or 'Untitled'}"
    
    def to_dict(self) -> dict:
        """Convert memo to dictionary."""
        return {
            "notion_id": self.notion_id,
            "title": self.title,
            "content": self.content,
            "tags": self.tags,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }