"""Repository implementation for Appointment entities."""
import logging
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timedelta
from notion_client import Client
from notion_client.errors import APIResponseError
import pytz

from src.repositories.base_repository import BaseRepository, PaginationParams, PaginatedResult
from src.models.appointment import Appointment
from src.utils.error_handler import BotError, ErrorType, ErrorSeverity
from functools import lru_cache


logger = logging.getLogger(__name__)


class AppointmentRepository(BaseRepository[Appointment]):
    """
    Repository for managing appointment data in Notion.
    
    Handles data access for private, shared, and business appointments with caching support.
    """
    
    def __init__(self, notion_client: Client, database_id: str, timezone: str = 'Europe/Berlin'):
        """
        Initialize AppointmentRepository.
        
        Args:
            notion_client: Initialized Notion client
            database_id: Notion database ID
            timezone: Timezone for date operations
        """
        self.client = notion_client
        self.database_id = database_id
        self.timezone = pytz.timezone(timezone)
        self._cache: Dict[str, Appointment] = {}
        self._cache_ttl = 300  # 5 minutes cache TTL
        self._cache_timestamps: Dict[str, datetime] = {}
    
    async def create(self, appointment: Appointment) -> str:
        """Create a new appointment in Notion database."""
        try:
            properties = appointment.to_notion_properties(str(self.timezone))
            
            response = self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties
            )
            
            page_id = response["id"]
            logger.info(f"Created appointment in Notion: {page_id}")
            
            # Cache the created appointment
            self._update_cache(page_id, appointment)
            
            return page_id
            
        except APIResponseError as e:
            logger.error(f"Failed to create appointment in Notion: {e}")
            raise BotError(
                f"Failed to create appointment in Notion: {str(e)}",
                ErrorType.NOTION_API,
                ErrorSeverity.HIGH,
                user_message="📝 Fehler beim Erstellen des Termins in Notion. Bitte versuche es erneut."
            )
    
    async def get_by_id(self, entity_id: str) -> Optional[Appointment]:
        """Get appointment by Notion page ID."""
        # Check cache first
        cached = self._get_from_cache(entity_id)
        if cached:
            return cached
        
        try:
            response = self.client.pages.retrieve(page_id=entity_id)
            appointment = Appointment.from_notion_page(response, str(self.timezone))
            
            # Update cache
            self._update_cache(entity_id, appointment)
            
            return appointment
            
        except APIResponseError as e:
            if e.code == "object_not_found":
                return None
            logger.error(f"Failed to retrieve appointment: {e}")
            raise BotError(
                f"Failed to retrieve appointment: {str(e)}",
                ErrorType.NOTION_API,
                ErrorSeverity.MEDIUM
            )
    
    async def get_all(self, pagination: Optional[PaginationParams] = None) -> PaginatedResult[Appointment]:
        """Get all appointments with pagination."""
        if pagination is None:
            pagination = PaginationParams()
        
        try:
            query_params = {
                "database_id": self.database_id,
                "page_size": pagination.page_size,
                "sorts": [{"property": "📅 Date", "direction": "ascending"}]
            }
            
            if pagination.start_cursor:
                query_params["start_cursor"] = pagination.start_cursor
            
            response = self.client.databases.query(**query_params)
            
            appointments = []
            for page in response["results"]:
                try:
                    appointment = Appointment.from_notion_page(page, str(self.timezone))
                    appointments.append(appointment)
                    # Cache each appointment
                    self._update_cache(page["id"], appointment)
                except Exception as e:
                    logger.warning(f"Failed to parse appointment page {page.get('id')}: {e}")
            
            return PaginatedResult(
                items=appointments,
                has_more=response.get("has_more", False),
                next_cursor=response.get("next_cursor")
            )
            
        except APIResponseError as e:
            logger.error(f"Failed to query appointments: {e}")
            raise BotError(
                f"Failed to query appointments: {str(e)}",
                ErrorType.NOTION_API,
                ErrorSeverity.MEDIUM
            )
    
    async def update(self, entity_id: str, appointment: Appointment) -> bool:
        """Update an existing appointment."""
        try:
            properties = appointment.to_notion_properties(str(self.timezone))
            
            self.client.pages.update(
                page_id=entity_id,
                properties=properties
            )
            
            # Update cache
            self._update_cache(entity_id, appointment)
            
            logger.info(f"Updated appointment: {entity_id}")
            return True
            
        except APIResponseError as e:
            logger.error(f"Failed to update appointment: {e}")
            if e.code == "object_not_found":
                return False
            raise BotError(
                f"Failed to update appointment: {str(e)}",
                ErrorType.NOTION_API,
                ErrorSeverity.MEDIUM
            )
    
    async def delete(self, entity_id: str) -> bool:
        """Archive an appointment (Notion doesn't support hard delete)."""
        try:
            self.client.pages.update(
                page_id=entity_id,
                archived=True
            )
            
            # Remove from cache
            self._invalidate_cache(entity_id)
            
            logger.info(f"Archived appointment: {entity_id}")
            return True
            
        except APIResponseError as e:
            logger.error(f"Failed to archive appointment: {e}")
            if e.code == "object_not_found":
                return False
            raise BotError(
                f"Failed to archive appointment: {str(e)}",
                ErrorType.NOTION_API,
                ErrorSeverity.MEDIUM
            )
    
    async def find_by_criteria(self, criteria: Dict[str, Any], 
                             pagination: Optional[PaginationParams] = None) -> PaginatedResult[Appointment]:
        """Find appointments by criteria."""
        if pagination is None:
            pagination = PaginationParams()
        
        filter_conditions = []
        
        # Build filters based on criteria
        if "date_from" in criteria:
            filter_conditions.append({
                "property": "📅 Date",
                "date": {
                    "on_or_after": criteria["date_from"].isoformat()
                }
            })
        
        if "date_to" in criteria:
            filter_conditions.append({
                "property": "📅 Date",
                "date": {
                    "on_or_before": criteria["date_to"].isoformat()
                }
            })
        
        if "title_contains" in criteria:
            filter_conditions.append({
                "property": "Title",
                "rich_text": {
                    "contains": criteria["title_contains"]
                }
            })
        
        if "is_business" in criteria:
            filter_conditions.append({
                "property": "👔 Business",
                "checkbox": {
                    "equals": criteria["is_business"]
                }
            })
        
        # Build query
        query_params = {
            "database_id": self.database_id,
            "page_size": pagination.page_size,
            "sorts": [{"property": "📅 Date", "direction": "ascending"}]
        }
        
        if filter_conditions:
            if len(filter_conditions) == 1:
                query_params["filter"] = filter_conditions[0]
            else:
                query_params["filter"] = {
                    "and": filter_conditions
                }
        
        if pagination.start_cursor:
            query_params["start_cursor"] = pagination.start_cursor
        
        try:
            response = self.client.databases.query(**query_params)
            
            appointments = []
            for page in response["results"]:
                try:
                    appointment = Appointment.from_notion_page(page, str(self.timezone))
                    appointments.append(appointment)
                    self._update_cache(page["id"], appointment)
                except Exception as e:
                    logger.warning(f"Failed to parse appointment page {page.get('id')}: {e}")
            
            return PaginatedResult(
                items=appointments,
                has_more=response.get("has_more", False),
                next_cursor=response.get("next_cursor")
            )
            
        except APIResponseError as e:
            logger.error(f"Failed to query appointments with criteria: {e}")
            raise BotError(
                f"Failed to query appointments: {str(e)}",
                ErrorType.NOTION_API,
                ErrorSeverity.MEDIUM
            )
    
    async def exists(self, entity_id: str) -> bool:
        """Check if appointment exists."""
        try:
            await self.get_by_id(entity_id)
            return True
        except:
            return False
    
    async def get_appointments_for_date_range(self, start_date: datetime, 
                                            end_date: datetime) -> List[Appointment]:
        """Get appointments within a date range."""
        criteria = {
            "date_from": start_date,
            "date_to": end_date
        }
        
        all_appointments = []
        pagination = PaginationParams(page_size=100)
        
        while True:
            result = await self.find_by_criteria(criteria, pagination)
            all_appointments.extend(result.items)
            
            if not result.has_more:
                break
                
            pagination.start_cursor = result.next_cursor
        
        return all_appointments
    
    async def get_todays_appointments(self) -> List[Appointment]:
        """Get appointments for today."""
        now = datetime.now(self.timezone)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        return await self.get_appointments_for_date_range(start_of_day, end_of_day)
    
    async def get_tomorrows_appointments(self) -> List[Appointment]:
        """Get appointments for tomorrow."""
        now = datetime.now(self.timezone)
        tomorrow = now + timedelta(days=1)
        start_of_day = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        return await self.get_appointments_for_date_range(start_of_day, end_of_day)
    
    async def find_duplicates(self, appointment: Appointment, 
                            time_window_minutes: int = 30) -> List[Appointment]:
        """Find potential duplicate appointments."""
        if not appointment.date:
            return []
        
        # Search in a time window around the appointment
        start_time = appointment.date - timedelta(minutes=time_window_minutes)
        end_time = appointment.date + timedelta(minutes=time_window_minutes)
        
        potential_duplicates = await self.get_appointments_for_date_range(start_time, end_time)
        
        # Filter to find actual duplicates
        duplicates = []
        for existing in potential_duplicates:
            if existing.notion_id == appointment.notion_id:
                continue
                
            # Check if titles are similar
            if appointment.title and existing.title:
                title_similarity = self._calculate_title_similarity(
                    appointment.title.lower(), 
                    existing.title.lower()
                )
                if title_similarity > 0.8:  # 80% similarity threshold
                    duplicates.append(existing)
        
        return duplicates
    
    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity between two titles (simple implementation)."""
        # Simple character-based similarity
        if title1 == title2:
            return 1.0
        
        # Check if one contains the other
        if title1 in title2 or title2 in title1:
            return 0.9
        
        # Calculate common characters ratio
        common_chars = set(title1) & set(title2)
        total_chars = set(title1) | set(title2)
        
        if not total_chars:
            return 0.0
            
        return len(common_chars) / len(total_chars)
    
    def _get_from_cache(self, entity_id: str) -> Optional[Appointment]:
        """Get appointment from cache if not expired."""
        if entity_id not in self._cache:
            return None
        
        # Check if cache entry is expired
        timestamp = self._cache_timestamps.get(entity_id)
        if timestamp and (datetime.now() - timestamp).seconds > self._cache_ttl:
            self._invalidate_cache(entity_id)
            return None
        
        return self._cache.get(entity_id)
    
    def _update_cache(self, entity_id: str, appointment: Appointment):
        """Update cache with appointment."""
        self._cache[entity_id] = appointment
        self._cache_timestamps[entity_id] = datetime.now()
    
    def _invalidate_cache(self, entity_id: str):
        """Remove appointment from cache."""
        self._cache.pop(entity_id, None)
        self._cache_timestamps.pop(entity_id, None)
    
    def clear_cache(self):
        """Clear all cached appointments."""
        self._cache.clear()
        self._cache_timestamps.clear()