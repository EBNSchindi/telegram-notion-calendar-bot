"""Refactored Combined appointment service using Repository pattern."""
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
import pytz
from dataclasses import dataclass
from notion_client import Client

from src.models.appointment import Appointment
from src.repositories.appointment_repository import AppointmentRepository
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
    """Service that combines appointments from private and shared databases using Repository pattern."""
    
    def __init__(self, user_config: UserConfig, user_config_manager: Optional[UserConfigManager] = None):
        self.user_config = user_config
        self.user_config_manager = user_config_manager
        
        # Handle timezone with fallback
        timezone_str = user_config.timezone if user_config.timezone else 'Europe/Berlin'
        try:
            self.timezone = pytz.timezone(timezone_str)
        except Exception as e:
            logger.warning(f"Invalid timezone '{timezone_str}', falling back to Europe/Berlin: {e}")
            self.timezone = pytz.timezone('Europe/Berlin')
        
        # Create Notion client
        notion_client = Client(auth=user_config.notion_api_key)
        
        # Create appointment repository for private database
        self.private_repository = AppointmentRepository(
            notion_client=notion_client,
            database_id=user_config.notion_database_id,
            timezone=str(self.timezone)
        )
        
        # Only create shared repository if configured
        self.shared_repository = None
        if user_config.shared_notion_database_id:
            self.shared_repository = AppointmentRepository(
                notion_client=notion_client,
                database_id=user_config.shared_notion_database_id,
                timezone=str(self.timezone)
            )
        
        # Initialize duplicate checker
        self.duplicate_checker = DuplicateChecker()
    
    async def create_appointment(self, appointment: Appointment, 
                               use_shared: bool = False) -> Tuple[str, List[AppointmentSource]]:
        """
        Create appointment with duplicate checking.
        
        Args:
            appointment: The appointment to create
            use_shared: Whether to create in shared database
            
        Returns:
            Tuple of (notion_id, list of duplicates found)
        """
        # Check for duplicates before creating
        duplicates = await self._check_for_duplicates(appointment)
        
        if duplicates:
            logger.warning(f"Found {len(duplicates)} potential duplicate(s) for appointment: {appointment.title}")
        
        # Select repository based on preference
        repository = self.shared_repository if use_shared and self.shared_repository else self.private_repository
        
        # Create the appointment
        notion_id = await repository.create(appointment)
        
        return notion_id, duplicates
    
    async def get_all_appointments(self, limit: int = 100) -> List[AppointmentSource]:
        """
        Get appointments from both private and shared databases.
        
        Args:
            limit: Maximum number of appointments to retrieve
            
        Returns:
            List of AppointmentSource objects
        """
        appointments = []
        
        # Get from private database
        from src.repositories.base_repository import PaginationParams
        private_result = await self.private_repository.get_all(
            PaginationParams(page_size=limit)
        )
        
        for appointment in private_result.items:
            appointments.append(AppointmentSource(appointment, is_shared=False))
        
        # Get from shared database if available
        if self.shared_repository:
            shared_result = await self.shared_repository.get_all(
                PaginationParams(page_size=limit)
            )
            
            for appointment in shared_result.items:
                appointments.append(AppointmentSource(appointment, is_shared=True))
        
        # Sort by date
        appointments.sort(key=lambda x: x.appointment.date or datetime.min.replace(tzinfo=self.timezone))
        
        return appointments[:limit]
    
    async def get_todays_appointments(self) -> List[AppointmentSource]:
        """Get today's appointments from both databases."""
        appointments = []
        
        # Get from private database
        private_appointments = await self.private_repository.get_todays_appointments()
        for appointment in private_appointments:
            appointments.append(AppointmentSource(appointment, is_shared=False))
        
        # Get from shared database if available
        if self.shared_repository:
            shared_appointments = await self.shared_repository.get_todays_appointments()
            for appointment in shared_appointments:
                appointments.append(AppointmentSource(appointment, is_shared=True))
        
        # Sort by date/time
        appointments.sort(key=lambda x: x.appointment.date or datetime.min.replace(tzinfo=self.timezone))
        
        return appointments
    
    async def get_tomorrows_appointments(self) -> List[AppointmentSource]:
        """Get tomorrow's appointments from both databases."""
        appointments = []
        
        # Get from private database
        private_appointments = await self.private_repository.get_tomorrows_appointments()
        for appointment in private_appointments:
            appointments.append(AppointmentSource(appointment, is_shared=False))
        
        # Get from shared database if available
        if self.shared_repository:
            shared_appointments = await self.shared_repository.get_tomorrows_appointments()
            for appointment in shared_appointments:
                appointments.append(AppointmentSource(appointment, is_shared=True))
        
        # Sort by date/time
        appointments.sort(key=lambda x: x.appointment.date or datetime.min.replace(tzinfo=self.timezone))
        
        return appointments
    
    async def get_appointments_for_date_range(self, start_date: datetime, 
                                            end_date: datetime) -> List[AppointmentSource]:
        """Get appointments within a date range from both databases."""
        appointments = []
        
        # Get from private database
        private_appointments = await self.private_repository.get_appointments_for_date_range(
            start_date, end_date
        )
        for appointment in private_appointments:
            appointments.append(AppointmentSource(appointment, is_shared=False))
        
        # Get from shared database if available
        if self.shared_repository:
            shared_appointments = await self.shared_repository.get_appointments_for_date_range(
                start_date, end_date
            )
            for appointment in shared_appointments:
                appointments.append(AppointmentSource(appointment, is_shared=True))
        
        # Sort by date/time
        appointments.sort(key=lambda x: x.appointment.date or datetime.min.replace(tzinfo=self.timezone))
        
        return appointments
    
    async def find_appointment_by_id(self, appointment_id: str) -> Optional[AppointmentSource]:
        """Find appointment by ID in both databases."""
        # Try private database first
        appointment = await self.private_repository.get_by_id(appointment_id)
        if appointment:
            return AppointmentSource(appointment, is_shared=False)
        
        # Try shared database if available
        if self.shared_repository:
            appointment = await self.shared_repository.get_by_id(appointment_id)
            if appointment:
                return AppointmentSource(appointment, is_shared=True)
        
        return None
    
    async def update_appointment(self, appointment_id: str, appointment: Appointment) -> bool:
        """Update appointment in the appropriate database."""
        # Find which database contains the appointment
        source = await self.find_appointment_by_id(appointment_id)
        if not source:
            return False
        
        # Update in the correct repository
        repository = self.shared_repository if source.is_shared else self.private_repository
        return await repository.update(appointment_id, appointment)
    
    async def delete_appointment(self, appointment_id: str) -> bool:
        """Delete appointment from the appropriate database."""
        # Find which database contains the appointment
        source = await self.find_appointment_by_id(appointment_id)
        if not source:
            return False
        
        # Delete from the correct repository
        repository = self.shared_repository if source.is_shared else self.private_repository
        return await repository.delete(appointment_id)
    
    async def _check_for_duplicates(self, appointment: Appointment) -> List[AppointmentSource]:
        """
        Check for duplicate appointments across both databases.
        
        Args:
            appointment: The appointment to check
            
        Returns:
            List of potential duplicates as AppointmentSource objects
        """
        if not appointment.date:
            return []
        
        duplicates = []
        
        # Check in private database
        private_duplicates = await self.private_repository.find_duplicates(appointment)
        for dup in private_duplicates:
            duplicates.append(AppointmentSource(dup, is_shared=False))
        
        # Check in shared database if available
        if self.shared_repository:
            shared_duplicates = await self.shared_repository.find_duplicates(appointment)
            for dup in shared_duplicates:
                duplicates.append(AppointmentSource(dup, is_shared=True))
        
        return duplicates
    
    def clear_cache(self):
        """Clear cache in all repositories."""
        self.private_repository.clear_cache()
        if self.shared_repository:
            self.shared_repository.clear_cache()
    
    def get_database_info(self) -> dict:
        """Get information about configured databases."""
        info = {
            'private_database_id': self.user_config.notion_database_id,
            'has_shared_database': bool(self.shared_repository),
            'timezone': str(self.timezone)
        }
        
        if self.shared_repository:
            info['shared_database_id'] = self.user_config.shared_notion_database_id
        
        return info