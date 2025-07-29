"""Refactored NotionService using Repository pattern."""
import logging
from typing import List, Optional, Union
from datetime import datetime, timedelta
from notion_client import Client
import pytz

from src.models.appointment import Appointment
from src.repositories.appointment_repository import AppointmentRepository
from src.repositories.memo_repository import MemoRepository
from config.settings import Settings
from config.user_config import UserConfig
from src.utils.error_handler import BotError, ErrorType, ErrorSeverity, handle_bot_error


logger = logging.getLogger(__name__)


class NotionService:
    """Service for interacting with Notion API using Repository pattern."""
    
    def __init__(self, settings: Optional[Settings] = None, 
                 notion_api_key: Optional[str] = None,
                 database_id: Optional[str] = None,
                 memo_database_id: Optional[str] = None):
        """
        Initialize NotionService with either Settings object or direct parameters.
        
        Args:
            settings: Settings object (for backward compatibility)
            notion_api_key: Direct API key (for multi-user support)
            database_id: Direct database ID (for multi-user support)
            memo_database_id: Database ID for memos (optional)
        """
        if settings:
            # Backward compatibility
            self.settings = settings
            self.client = Client(auth=settings.notion_api_key)
            self.database_id = settings.notion_database_id
            self.memo_database_id = getattr(settings, 'notion_memo_database_id', None)
            timezone = settings.timezone
        else:
            # Multi-user support
            if not notion_api_key or not database_id:
                raise BotError(
                    "notion_api_key and database_id are required",
                    ErrorType.VALIDATION,
                    ErrorSeverity.HIGH
                )
            self.settings = None
            self.client = Client(auth=notion_api_key)
            self.database_id = database_id
            self.memo_database_id = memo_database_id
            timezone = 'Europe/Berlin'
        
        # Initialize repositories
        self.appointment_repository = AppointmentRepository(
            notion_client=self.client,
            database_id=self.database_id,
            timezone=timezone
        )
        
        # Initialize memo repository if database ID is provided
        self.memo_repository = None
        if self.memo_database_id:
            self.memo_repository = MemoRepository(
                notion_client=self.client,
                database_id=self.memo_database_id
            )
    
    @classmethod
    def from_user_config(cls, user_config: UserConfig) -> 'NotionService':
        """Create NotionService from UserConfig."""
        return cls(
            notion_api_key=user_config.notion_api_key,
            database_id=user_config.notion_database_id,
            memo_database_id=getattr(user_config, 'notion_memo_database_id', None)
        )
    
    @handle_bot_error(ErrorType.NOTION_API, ErrorSeverity.HIGH)
    async def create_appointment(self, appointment: Appointment) -> str:
        """
        Create a new appointment in Notion database.
        
        Args:
            appointment: Appointment object to create
            
        Returns:
            str: Notion page ID of created appointment
        """
        return await self.appointment_repository.create(appointment)
    
    @handle_bot_error(ErrorType.NOTION_API, ErrorSeverity.MEDIUM)
    async def get_appointments(self, limit: int = 10) -> List[Appointment]:
        """
        Get appointments from Notion database.
        
        Args:
            limit: Maximum number of appointments to retrieve
            
        Returns:
            List[Appointment]: List of appointments
        """
        from src.repositories.base_repository import PaginationParams
        
        result = await self.appointment_repository.get_all(
            PaginationParams(page_size=limit)
        )
        return result.items
    
    @handle_bot_error(ErrorType.NOTION_API, ErrorSeverity.MEDIUM)
    async def get_todays_appointments(self) -> List[Appointment]:
        """Get today's appointments."""
        return await self.appointment_repository.get_todays_appointments()
    
    @handle_bot_error(ErrorType.NOTION_API, ErrorSeverity.MEDIUM)
    async def get_tomorrows_appointments(self) -> List[Appointment]:
        """Get tomorrow's appointments."""
        return await self.appointment_repository.get_tomorrows_appointments()
    
    @handle_bot_error(ErrorType.NOTION_API, ErrorSeverity.MEDIUM)
    async def get_appointment_by_id(self, appointment_id: str) -> Optional[Appointment]:
        """Get appointment by Notion page ID."""
        return await self.appointment_repository.get_by_id(appointment_id)
    
    @handle_bot_error(ErrorType.NOTION_API, ErrorSeverity.MEDIUM)
    async def update_appointment(self, appointment_id: str, appointment: Appointment) -> bool:
        """Update an existing appointment."""
        return await self.appointment_repository.update(appointment_id, appointment)
    
    @handle_bot_error(ErrorType.NOTION_API, ErrorSeverity.MEDIUM)
    async def delete_appointment(self, appointment_id: str) -> bool:
        """Delete (archive) an appointment."""
        return await self.appointment_repository.delete(appointment_id)
    
    @handle_bot_error(ErrorType.NOTION_API, ErrorSeverity.MEDIUM)
    async def find_duplicate_appointments(self, appointment: Appointment, 
                                        time_window_minutes: int = 30) -> List[Appointment]:
        """Find potential duplicate appointments."""
        return await self.appointment_repository.find_duplicates(
            appointment, time_window_minutes
        )
    
    @handle_bot_error(ErrorType.NOTION_API, ErrorSeverity.MEDIUM)
    async def get_appointments_for_date_range(self, start_date: datetime, 
                                            end_date: datetime) -> List[Appointment]:
        """Get appointments within a date range."""
        return await self.appointment_repository.get_appointments_for_date_range(
            start_date, end_date
        )
    
    def clear_cache(self):
        """Clear appointment cache."""
        self.appointment_repository.clear_cache()
        if self.memo_repository:
            self.memo_repository.clear_cache()
    
    # Memo-related methods (if memo repository is available)
    
    async def create_memo(self, title: str, content: str, tags: Optional[List[str]] = None):
        """Create a new memo."""
        if not self.memo_repository:
            raise BotError(
                "Memo database not configured",
                ErrorType.CONFIGURATION,
                ErrorSeverity.MEDIUM
            )
        
        from src.models.memo import Memo
        memo = Memo(
            title=title,
            content=content,
            tags=tags or []
        )
        
        return await self.memo_repository.create(memo)
    
    async def search_memos(self, search_term: str, limit: int = 10):
        """Search for memos."""
        if not self.memo_repository:
            raise BotError(
                "Memo database not configured",
                ErrorType.CONFIGURATION,
                ErrorSeverity.MEDIUM
            )
        
        return await self.memo_repository.search_memos(search_term, limit)
    
    async def get_recent_memos(self, limit: int = 10):
        """Get recent memos."""
        if not self.memo_repository:
            raise BotError(
                "Memo database not configured",
                ErrorType.CONFIGURATION,
                ErrorSeverity.MEDIUM
            )
        
        return await self.memo_repository.get_recent_memos(limit)