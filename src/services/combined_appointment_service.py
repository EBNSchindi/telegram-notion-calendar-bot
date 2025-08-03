"""Combined appointment service for private and shared databases."""
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
import pytz
from dataclasses import dataclass

from src.models.appointment import Appointment
from src.services.notion_service import NotionService
from config.user_config import UserConfig, UserConfigManager
from src.utils.duplicate_checker import DuplicateChecker

logger = logging.getLogger(__name__)


@dataclass
class AppointmentSource:
    """Indicates the source of an appointment."""
    appointment: Appointment
    is_shared: bool  # True if from shared database, False if from private database
    
    def __str__(self):
        source = "🌐 Gemeinsam" if self.is_shared else "👤 Privat"
        return f"{source}: {self.appointment.title}"


class CombinedAppointmentService:
    """Service that combines appointments from private and shared databases.
    
    This service provides a unified interface for managing appointments across
    multiple Notion databases (private, shared, and business). It handles:
    - Creating appointments with AI extraction
    - Retrieving appointments from all databases
    - Duplicate detection and prevention
    - Partner sharing coordination
    
    Attributes:
        user_config: User configuration with API keys and database IDs
        private_service: Service for private database operations
        shared_service: Service for shared database operations (optional)
        ai_service: AI service for natural language processing
        duplicate_checker: Service for detecting duplicate appointments
    """
    
    def __init__(self, user_config: UserConfig, user_config_manager: Optional[UserConfigManager] = None):
        """Initialize the combined appointment service.
        
        Args:
            user_config: User configuration containing API keys and database IDs
            user_config_manager: Optional manager for accessing shared configurations
        """
        self.user_config = user_config
        self.user_config_manager = user_config_manager
        
        # Handle timezone with fallback
        timezone_str = user_config.timezone if user_config.timezone else 'Europe/Berlin'
        try:
            self.timezone = pytz.timezone(timezone_str)
        except Exception as e:
            logger.warning(f"Invalid timezone '{timezone_str}', falling back to Europe/Berlin: {e}")
            self.timezone = pytz.timezone('Europe/Berlin')
        
        # Create notion services for both databases
        self.private_service = NotionService(
            notion_api_key=user_config.notion_api_key,
            database_id=user_config.notion_database_id
        )
        
        # Only create shared service if configured
        self.shared_service = None
        if user_config.shared_notion_database_id:
            # Use appropriate API key for shared database
            if user_config_manager:
                shared_api_key = user_config_manager.get_shared_database_api_key(user_config)
            else:
                # Fallback if no manager provided
                shared_api_key = user_config.teamspace_owner_api_key or user_config.notion_api_key
                
            self.shared_service = NotionService(
                notion_api_key=shared_api_key,
                database_id=user_config.shared_notion_database_id
            )
    
    async def get_all_appointments(self, limit: int = 50) -> List[AppointmentSource]:
        """
        Get appointments from both private and shared databases.
        
        Args:
            limit: Maximum number of appointments per database
            
        Returns:
            List of AppointmentSource objects sorted by date
        """
        all_appointments = []
        seen_ids = set()  # Track seen appointments by ID to avoid duplicates
        seen_keys = set()  # Track seen appointments by content key
        
        # Get private appointments
        try:
            private_appointments = await self.private_service.get_appointments(limit=limit)
            for apt in private_appointments:
                # Check for duplicates by ID
                if apt.notion_page_id and apt.notion_page_id in seen_ids:
                    logger.debug(f"Skipping duplicate private appointment by ID: {apt.notion_page_id}")
                    continue
                    
                # Check for duplicates by content using DuplicateChecker
                content_key = DuplicateChecker.create_appointment_key(apt)
                if content_key in seen_keys:
                    logger.debug(f"Skipping duplicate private appointment by content: {apt.title}")
                    continue
                
                all_appointments.append(AppointmentSource(apt, is_shared=False))
                if apt.notion_page_id:
                    seen_ids.add(apt.notion_page_id)
                seen_keys.add(content_key)
                
            logger.info(f"Retrieved {len(private_appointments)} private appointments, {len([a for a in all_appointments if not a.is_shared])} unique")
        except Exception as e:
            logger.error(f"Error retrieving private appointments: {e}")
        
        # Get shared appointments (if configured)
        if self.shared_service:
            try:
                shared_appointments = await self.shared_service.get_appointments(limit=limit)
                for apt in shared_appointments:
                    # Check for duplicates by ID
                    if apt.notion_page_id and apt.notion_page_id in seen_ids:
                        logger.debug(f"Skipping duplicate shared appointment by ID: {apt.notion_page_id}")
                        continue
                        
                    # Check for duplicates by content using DuplicateChecker
                    content_key = DuplicateChecker.create_appointment_key(apt)
                    if content_key in seen_keys:
                        logger.debug(f"Skipping duplicate shared appointment by content: {apt.title}")
                        continue
                    
                    # Additional check: Skip if this is a synced copy of a private appointment we already have
                    if hasattr(apt, 'source_private_id') and apt.source_private_id in seen_ids:
                        logger.debug(f"Skipping shared appointment that's a synced copy of private: {apt.title}")
                        continue
                    
                    all_appointments.append(AppointmentSource(apt, is_shared=True))
                    if apt.notion_page_id:
                        seen_ids.add(apt.notion_page_id)
                    seen_keys.add(content_key)
                    
                logger.info(f"Retrieved {len(shared_appointments)} shared appointments, {len([a for a in all_appointments if a.is_shared])} unique")
            except Exception as e:
                logger.error(f"Error retrieving shared appointments: {e}")
        
        # Sort by date/time
        all_appointments.sort(key=lambda x: x.appointment.date)
        
        logger.info(f"Total unique appointments: {len(all_appointments)}")
        
        return all_appointments
    
    async def get_today_appointments(self) -> List[AppointmentSource]:
        """Get today's appointments from both databases."""
        all_appointments = await self.get_all_appointments()
        
        # Filter for today
        today = datetime.now(self.timezone).date()
        today_appointments = [
            apt_src for apt_src in all_appointments
            if apt_src.appointment.date.astimezone(self.timezone).date() == today
        ]
        
        return today_appointments
    
    async def get_tomorrow_appointments(self) -> List[AppointmentSource]:
        """Get tomorrow's appointments from both databases."""
        all_appointments = await self.get_all_appointments()
        
        # Filter for tomorrow
        tomorrow = (datetime.now(self.timezone) + timedelta(days=1)).date()
        tomorrow_appointments = [
            apt_src for apt_src in all_appointments
            if apt_src.appointment.date.astimezone(self.timezone).date() == tomorrow
        ]
        
        return tomorrow_appointments
    
    async def get_upcoming_appointments(self, days_ahead: int = 30) -> List[AppointmentSource]:
        """Get upcoming appointments from both databases."""
        all_appointments = await self.get_all_appointments()
        
        # Filter for future appointments within the specified range
        now = datetime.now(self.timezone)
        future_cutoff = now + timedelta(days=days_ahead)
        
        upcoming_appointments = [
            apt_src for apt_src in all_appointments
            if now <= apt_src.appointment.date.astimezone(self.timezone) <= future_cutoff
        ]
        
        return upcoming_appointments
    
    async def create_appointment(self, appointment: Appointment, use_shared: bool = False) -> str:
        """
        Create appointment in either private or shared database.
        Enhanced with partner sync functionality.
        
        Args:
            appointment: Appointment to create
            use_shared: If True, create in shared database; if False, create in private database
            
        Returns:
            Notion page ID of created appointment
        """
        # Create the appointment in the target database
        if use_shared and self.shared_service:
            page_id = await self.shared_service.create_appointment(appointment)
        else:
            page_id = await self.private_service.create_appointment(appointment)
            
            # If creating in private DB and appointment is partner-relevant, sync to shared DB
            if appointment.partner_relevant and self.user_config_manager:
                try:
                    # Import here to avoid circular dependency
                    from src.services.partner_sync_service import PartnerSyncService
                    
                    sync_service = PartnerSyncService(self.user_config_manager)
                    appointment.notion_page_id = page_id  # Set the page ID for sync
                    
                    # Sync immediately with retry mechanism
                    logger.info(f"Attempting to sync partner-relevant appointment {page_id} to shared database")
                    sync_result = await sync_service.sync_single_appointment(
                        appointment, 
                        self.user_config,
                        force_sync=True
                    )
                    
                    if sync_result["success"]:
                        logger.info(
                            f"Successfully synced appointment {page_id} to shared database. "
                            f"Action: {sync_result['action']}, Shared ID: {sync_result.get('shared_id')}"
                        )
                    else:
                        logger.warning(
                            f"Failed to sync appointment {page_id} to shared database. "
                            f"Error: {sync_result.get('error', 'Unknown error')}"
                        )
                    
                except Exception as e:
                    logger.error(f"Error during immediate partner sync (after retries exhausted): {e}")
                    # Don't fail the appointment creation if sync fails
        
        return page_id
    
    async def test_connections(self) -> Tuple[bool, bool]:
        """
        Test connections to both databases.
        
        Returns:
            Tuple of (private_connection_ok, shared_connection_ok)
        """
        private_ok = False
        shared_ok = False
        
        try:
            private_ok = await self.private_service.test_connection()
        except Exception as e:
            logger.error(f"Private database connection test failed: {e}")
        
        if self.shared_service:
            try:
                shared_ok = await self.shared_service.test_connection()
            except Exception as e:
                logger.error(f"Shared database connection test failed: {e}")
        else:
            shared_ok = None  # Not configured
        
        return private_ok, shared_ok
    
    def format_appointments_for_telegram(self, appointments: List[AppointmentSource], 
                                       title: str = "Termine") -> str:
        """
        Format appointments for Telegram display.
        
        Args:
            appointments: List of appointment sources
            title: Title for the message
            
        Returns:
            Formatted string for Telegram
        """
        if not appointments:
            return f"📅 Keine {title.lower()} vorhanden."
        
        message_parts = [f"📋 *{title}:*\n"]
        
        current_date = None
        for i, apt_src in enumerate(appointments, 1):
            apt = apt_src.appointment
            apt_date = apt.date.astimezone(self.timezone).date()
            
            # Add date header if date changed
            if current_date != apt_date:
                current_date = apt_date
                date_str = apt_date.strftime('%d.%m.%Y (%A)')
                message_parts.append(f"\n📅 *{date_str}*")
            
            # Format appointment
            time_str = apt.date.astimezone(self.timezone).strftime('%H:%M')
            source_icon = "🌐" if apt_src.is_shared else "👤"
            
            message_parts.append(f"{source_icon} {time_str} - *{apt.title}*")
            
            # Add description if present
            if apt.description:
                message_parts.append(f"   📝 _{apt.description}_")
            
            # Add location if present
            if apt.location:
                message_parts.append(f"   📍 {apt.location}")
        
        return "\n".join(message_parts)
    
    def has_shared_database(self) -> bool:
        """Check if shared database is configured."""
        return self.shared_service is not None