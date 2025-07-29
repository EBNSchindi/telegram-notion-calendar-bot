"""Utility module for checking and preventing duplicate appointments."""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from src.models.appointment import Appointment

logger = logging.getLogger(__name__)


class DuplicateChecker:
    """Helper class to check for duplicate appointments."""
    
    @staticmethod
    def create_appointment_key(appointment: Appointment) -> str:
        """
        Create a unique key for an appointment based on title, date/time, and location.
        
        Args:
            appointment: The appointment to create a key for
            
        Returns:
            A string key that uniquely identifies the appointment
        """
        # Normalize date to minute precision (ignore seconds/microseconds)
        date_without_seconds = appointment.date.replace(second=0, microsecond=0)
        date_str = date_without_seconds.strftime('%Y-%m-%d %H:%M')
        
        # Normalize title and location
        title = appointment.title.lower().strip()
        location = (appointment.location or "").lower().strip()
        
        # Create key
        return f"{title}|{date_str}|{location}"
    
    @staticmethod
    def find_duplicate(appointment: Appointment, existing_appointments: List[Appointment]) -> Optional[Appointment]:
        """
        Find a duplicate appointment in a list of existing appointments.
        
        Args:
            appointment: The appointment to check
            existing_appointments: List of existing appointments to check against
            
        Returns:
            The duplicate appointment if found, None otherwise
        """
        target_key = DuplicateChecker.create_appointment_key(appointment)
        
        for existing in existing_appointments:
            if DuplicateChecker.create_appointment_key(existing) == target_key:
                return existing
        
        return None
    
    @staticmethod
    def check_for_duplicates(appointments: List[Appointment]) -> Dict[str, List[Appointment]]:
        """
        Check a list of appointments for duplicates.
        
        Args:
            appointments: List of appointments to check
            
        Returns:
            Dictionary mapping appointment keys to lists of duplicate appointments
        """
        duplicates = {}
        seen = {}
        
        for apt in appointments:
            key = DuplicateChecker.create_appointment_key(apt)
            
            if key in seen:
                # Found a duplicate
                if key not in duplicates:
                    duplicates[key] = [seen[key]]
                duplicates[key].append(apt)
            else:
                seen[key] = apt
        
        return duplicates
    
    @staticmethod
    def is_same_appointment(apt1: Appointment, apt2: Appointment, 
                           ignore_seconds: bool = True) -> bool:
        """
        Check if two appointments are the same based on content.
        
        Args:
            apt1: First appointment
            apt2: Second appointment
            ignore_seconds: Whether to ignore seconds in date comparison
            
        Returns:
            True if appointments are the same, False otherwise
        """
        # Compare titles
        if apt1.title.lower().strip() != apt2.title.lower().strip():
            return False
        
        # Compare dates
        if ignore_seconds:
            date1 = apt1.date.replace(second=0, microsecond=0)
            date2 = apt2.date.replace(second=0, microsecond=0)
            if date1 != date2:
                return False
        else:
            if apt1.date != apt2.date:
                return False
        
        # Compare locations
        loc1 = (apt1.location or "").lower().strip()
        loc2 = (apt2.location or "").lower().strip()
        if loc1 != loc2:
            return False
        
        return True
    
    @staticmethod
    def find_appointment_by_content(appointment: Appointment, 
                                   appointments_list: List[Appointment]) -> Optional[Appointment]:
        """
        Find an appointment by its content (title, date, location).
        
        Args:
            appointment: The appointment to find
            appointments_list: List of appointments to search in
            
        Returns:
            The matching appointment if found, None otherwise
        """
        for apt in appointments_list:
            if DuplicateChecker.is_same_appointment(appointment, apt):
                return apt
        
        return None
    
    @staticmethod
    def filter_unique_appointments(appointments: List[Appointment]) -> List[Appointment]:
        """
        Filter a list of appointments to keep only unique ones.
        
        Args:
            appointments: List of appointments to filter
            
        Returns:
            List of unique appointments (keeps the first occurrence)
        """
        seen_keys = set()
        unique_appointments = []
        
        for apt in appointments:
            key = DuplicateChecker.create_appointment_key(apt)
            if key not in seen_keys:
                seen_keys.add(key)
                unique_appointments.append(apt)
            else:
                logger.debug(f"Filtered out duplicate appointment: {apt.title} at {apt.date}")
        
        return unique_appointments
    
    @staticmethod
    def merge_appointment_lists(list1: List[Appointment], 
                               list2: List[Appointment]) -> List[Appointment]:
        """
        Merge two lists of appointments, removing duplicates.
        
        Args:
            list1: First list of appointments
            list2: Second list of appointments
            
        Returns:
            Merged list with no duplicates
        """
        # Combine lists
        all_appointments = list1 + list2
        
        # Filter unique
        return DuplicateChecker.filter_unique_appointments(all_appointments)