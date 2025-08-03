"""Partner sync service to bypass Notion Plus plan limitations."""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Callable, TypeVar, Union
import uuid
import functools
import random

from src.models.appointment import Appointment
from src.models.shared_appointment import SharedAppointment
from src.services.notion_service import NotionService
from config.user_config import UserConfigManager, UserConfig
from src.utils.duplicate_checker import DuplicateChecker
from src.constants import (
    PARTNER_SYNC_INTERVAL_HOURS, 
    SYNC_MAX_RETRIES,
    SYNC_INITIAL_RETRY_DELAY,
    SYNC_RETRY_BACKOFF_FACTOR
)

# Define missing constants
DATABASE_REFRESH_INTERVAL = 300  # 5 minutes
PARTNER_SYNC_INTERVAL = PARTNER_SYNC_INTERVAL_HOURS * 3600  # Convert hours to seconds

logger = logging.getLogger(__name__)

# Type variable for retry decorator
T = TypeVar('T')


def async_retry_with_backoff(
    max_retries: int = SYNC_MAX_RETRIES,
    initial_delay: float = SYNC_INITIAL_RETRY_DELAY,
    backoff_factor: float = SYNC_RETRY_BACKOFF_FACTOR,
    retryable_exceptions: tuple = (Exception,),
    permanent_exceptions: tuple = (),
    on_retry: Optional[Callable] = None
):
    """
    Async retry decorator with exponential backoff and jitter.
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Factor to multiply delay by after each retry
        retryable_exceptions: Tuple of exceptions that trigger retry
        permanent_exceptions: Tuple of exceptions that should not be retried
        on_retry: Optional callback function called on each retry
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except permanent_exceptions as e:
                    # Don't retry permanent failures
                    logger.error(f"{func.__name__} failed with permanent error: {e}")
                    raise
                except retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        # Final attempt failed
                        logger.error(
                            f"{func.__name__} failed after {max_retries} retries: {e}"
                        )
                        raise
                    
                    # Calculate delay with exponential backoff
                    delay = initial_delay * (backoff_factor ** attempt)
                    
                    # Add jitter to prevent thundering herd
                    jittered_delay = delay * (0.5 + random.random())
                    
                    logger.warning(
                        f"{func.__name__} attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {jittered_delay:.2f} seconds..."
                    )
                    
                    # Call retry callback if provided
                    if on_retry:
                        if asyncio.iscoroutinefunction(on_retry):
                            await on_retry(attempt, e, jittered_delay)
                        else:
                            on_retry(attempt, e, jittered_delay)
                    
                    await asyncio.sleep(jittered_delay)
            
            # Should never reach here, but just in case
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator


class SyncError(Exception):
    """Base exception for sync errors."""
    pass


class TemporarySyncError(SyncError):
    """Temporary sync error that should be retried."""
    pass


class PermanentSyncError(SyncError):
    """Permanent sync error that should not be retried."""
    pass


class PartnerSyncService:
    """
    Service that automatically syncs partner-relevant appointments to shared database.
    
    This service bypasses Notion Plus limitations by copying appointments
    with PartnerRelevant=True from private databases to the shared database.
    """
    
    def __init__(self, user_config_manager: UserConfigManager):
        """
        Initialize the partner sync service.
        
        Args:
            user_config_manager: Manager for user configurations
        """
        self.user_config_manager = user_config_manager
        self._running = False
        self._sync_task = None
        self.sync_interval_hours = 2  # Default sync interval
        
    async def sync_partner_relevant_appointments(self, user_config: UserConfig) -> Dict[str, Any]:
        """
        Sync all partner-relevant appointments for a specific user.
        
        Args:
            user_config: User configuration containing database credentials
            
        Returns:
            Dictionary with sync results and statistics
        """
        logger.info(f"Starting partner sync for user {user_config.telegram_user_id}")
        
        if not user_config.shared_notion_database_id:
            logger.warning(f"User {user_config.telegram_user_id} has no shared database configured")
            return {"success": False, "error": "No shared database configured"}
        
        try:
            private_service = NotionService(
                notion_api_key=user_config.notion_api_key,
                database_id=user_config.notion_database_id
            )
            
            # Use appropriate API key for shared database
            shared_api_key = self.user_config_manager.get_shared_database_api_key(user_config)
            shared_service = NotionService(
                notion_api_key=shared_api_key,
                database_id=user_config.shared_notion_database_id
            )
            
            # Get all appointments from private database
            all_appointments = await private_service.get_appointments(limit=200)
            if not all_appointments:
                logger.warning(f"No appointments returned from private database for user {user_config.telegram_user_id}")
                all_appointments = []
            partner_relevant = [apt for apt in all_appointments if apt.partner_relevant]
            
            stats = {
                "total_processed": len(partner_relevant),
                "created": 0,
                "updated": 0,
                "errors": 0,
                "removed": 0
            }
            
            # Process each partner-relevant appointment
            logger.info(f"Processing {len(partner_relevant)} partner-relevant appointments")
            for i, appointment in enumerate(partner_relevant, 1):
                try:
                    logger.debug(f"Processing appointment {i}/{len(partner_relevant)}: {appointment.title}")
                    await self._sync_single_appointment_internal(
                        appointment, private_service, shared_service, 
                        user_config.telegram_user_id, stats
                    )
                except Exception as e:
                    logger.error(f"Error syncing appointment '{appointment.title}' (ID: {appointment.notion_page_id}): {e}", exc_info=True)
                    stats["errors"] += 1
            
            # Check for appointments that are no longer partner-relevant
            await self._cleanup_removed_appointments(private_service, shared_service, user_config.telegram_user_id, stats)
            
            logger.info(f"Partner sync completed for user {user_config.telegram_user_id}: {stats}")
            return {"success": True, "stats": stats}
            
        except Exception as e:
            logger.error(f"Error during sync for user {user_config.telegram_user_id}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    @async_retry_with_backoff(
        retryable_exceptions=(TemporarySyncError, asyncio.TimeoutError, ConnectionError),
        permanent_exceptions=(PermanentSyncError, ValueError, KeyError)
    )
    async def sync_single_appointment(self, appointment: Appointment, 
                                    user_config: UserConfig, 
                                    force_sync: bool = False) -> Dict[str, Any]:
        """
        Sync a single appointment if it's partner-relevant with retry mechanism.
        
        Args:
            appointment: The appointment to sync
            user_config: User configuration
            force_sync: If True, sync even if already synced
            
        Returns:
            Dictionary with sync result details:
            - success: bool - Whether sync succeeded
            - action: str - Action taken (created/updated/removed/skipped)
            - error: str - Error message if failed
            - shared_id: str - ID in shared database if synced
        """
        result = {
            "success": False,
            "action": "skipped",
            "error": None,
            "shared_id": None
        }
        
        if not user_config.shared_notion_database_id:
            logger.warning(f"User {user_config.telegram_user_id} has no shared database configured")
            result["error"] = "No shared database configured"
            return result
        
        if not appointment.partner_relevant and not force_sync:
            # If not partner relevant, check if we need to remove from shared DB
            removed = await self.remove_from_shared(appointment.notion_page_id or "", user_config)
            result["success"] = removed
            result["action"] = "removed" if removed else "remove_failed"
            return result
        
        try:
            private_service = NotionService(
                notion_api_key=user_config.notion_api_key,
                database_id=user_config.notion_database_id
            )
            
            # Use appropriate API key for shared database
            shared_api_key = self.user_config_manager.get_shared_database_api_key(user_config)
            shared_service = NotionService(
                notion_api_key=shared_api_key,
                database_id=user_config.shared_notion_database_id
            )
            
            stats = {"created": 0, "updated": 0, "errors": 0}
            
            # Add timeout to prevent hanging
            try:
                success = await asyncio.wait_for(
                    self._sync_single_appointment_internal(
                        appointment, private_service, shared_service, 
                        user_config.telegram_user_id, stats
                    ),
                    timeout=30.0  # 30 second timeout
                )
                
                if success:
                    result["success"] = True
                    result["action"] = "created" if stats["created"] > 0 else "updated"
                    # Try to get the shared ID
                    sync_id = await self._get_sync_tracking(private_service, appointment.notion_page_id)
                    result["shared_id"] = sync_id
                else:
                    result["error"] = "Sync returned false"
                    
            except asyncio.TimeoutError:
                logger.error(f"Timeout syncing appointment '{appointment.title}'")
                raise TemporarySyncError("Sync operation timed out")
                
            return result
            
        except (ConnectionError, asyncio.TimeoutError) as e:
            # Network-related errors are temporary
            logger.error(f"Network error syncing appointment: {e}")
            raise TemporarySyncError(f"Network error: {str(e)}")
        except ValueError as e:
            # Data validation errors are permanent
            logger.error(f"Data validation error: {e}")
            result["error"] = f"Invalid data: {str(e)}"
            raise PermanentSyncError(f"Data validation error: {str(e)}")
        except Exception as e:
            # Unexpected errors - analyze if temporary or permanent
            error_str = str(e).lower()
            if any(temp in error_str for temp in ['timeout', 'connection', 'network', 'rate limit']):
                raise TemporarySyncError(f"Temporary error: {str(e)}")
            else:
                logger.error(f"Unexpected error syncing appointment: {e}", exc_info=True)
                result["error"] = str(e)
                return result
    
    async def remove_from_shared(self, appointment_id: str, user_config: UserConfig) -> bool:
        """
        Remove appointment from shared database if it exists.
        
        Args:
            appointment_id: Private database appointment ID
            user_config: User configuration
            
        Returns:
            True if removed or not found, False on error
        """
        if not user_config.shared_notion_database_id or not appointment_id:
            return True
        
        try:
            # Use appropriate API key for shared database
            shared_api_key = self.user_config_manager.get_shared_database_api_key(user_config)
            shared_service = NotionService(
                notion_api_key=shared_api_key,
                database_id=user_config.shared_notion_database_id
            )
            
            # Find appointment in shared database by SourcePrivateId
            shared_appointments = await shared_service.get_appointments(limit=500)
            if not shared_appointments:
                shared_appointments = []
            
            for shared_apt in shared_appointments:
                if hasattr(shared_apt, 'source_private_id') and shared_apt.source_private_id == appointment_id:
                    # Delete from shared database
                    await shared_service.delete_appointment(shared_apt.notion_page_id)
                    
                    # Clear sync tracking in private database
                    private_service = NotionService(
                        notion_api_key=user_config.notion_api_key,
                        database_id=user_config.notion_database_id
                    )
                    await self._clear_sync_tracking(private_service, appointment_id)
                    
                    logger.info(f"Removed appointment {appointment_id} from shared database")
                    return True
            
            return True  # Not found in shared DB, which is fine
            
        except Exception as e:
            logger.error(f"Error removing appointment from shared database: {e}")
            return False
    
    async def start_background_sync(self, interval_hours: int = 2):
        """
        Start background sync task that runs at specified intervals.
        
        Args:
            interval_hours: Sync interval in hours (default: 2)
        """
        if self._running:
            logger.warning("Background sync is already running")
            return
        
        self.sync_interval_hours = interval_hours
        self._running = True
        
        logger.info(f"Starting background partner sync (interval: {interval_hours}h)")
        self._sync_task = asyncio.create_task(self._background_sync_loop())
    
    def stop_background_sync(self):
        """Stop background sync task."""
        self._running = False
        if self._sync_task and not self._sync_task.done():
            self._sync_task.cancel()
            logger.info("Background partner sync stopped")
    
    async def _background_sync_loop(self):
        """Background sync loop that runs periodically."""
        while self._running:
            try:
                logger.info("Starting scheduled partner sync for all users")
                
                valid_users = self.user_config_manager.get_valid_users()
                for user_id, user_config in valid_users.items():
                    if user_config.shared_notion_database_id:
                        result = await self.sync_partner_relevant_appointments(user_config)
                        if result["success"]:
                            logger.info(f"Sync successful for user {user_id}")
                        else:
                            logger.error(f"Sync failed for user {user_id}: {result.get('error')}")
                
                # Wait for next sync cycle
                await asyncio.sleep(self.sync_interval_hours * 3600)
                
            except asyncio.CancelledError:
                logger.info("Background sync task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in background sync loop: {e}")
                # Wait before retrying to avoid tight error loops
                await asyncio.sleep(DATABASE_REFRESH_INTERVAL)  # Refresh interval
    
    async def _sync_single_appointment_internal(self, appointment: Appointment, 
                                              private_service: NotionService,
                                              shared_service: NotionService,
                                              user_id: int,
                                              stats: Dict[str, int]) -> bool:
        """
        Internal method to sync a single appointment with enhanced error handling.
        
        Args:
            appointment: The appointment to sync
            private_service: Private database service
            shared_service: Shared database service
            user_id: Telegram user ID
            stats: Statistics dictionary to update
            
        Returns:
            True if synced successfully
            
        Raises:
            TemporarySyncError: For transient errors that should be retried
            PermanentSyncError: For permanent errors that should not be retried
        """
        if not appointment.notion_page_id:
            logger.warning("Appointment has no notion_page_id, skipping sync")
            raise PermanentSyncError("Appointment has no notion_page_id")
        
        logger.debug(f"Syncing appointment: {appointment.title} (ID: {appointment.notion_page_id})")
        logger.debug(f"Appointment dates: start={appointment.start_date}, end={appointment.end_date}")
        
        # Check if already synced by looking for SyncedToSharedId
        sync_id = await self._get_sync_tracking(private_service, appointment.notion_page_id)
        
        if sync_id:
            # Already synced, check if shared appointment still exists and update if needed
            try:
                shared_appointment = await shared_service.get_appointment_by_id(sync_id)
                if shared_appointment:
                    # Update shared appointment with current data
                    updated_appointment = self._prepare_appointment_for_shared(appointment, user_id)
                    try:
                        await shared_service.update_appointment(sync_id, updated_appointment)
                        stats["updated"] += 1
                        logger.debug(f"Updated synced appointment {sync_id}")
                        return True
                    except (ConnectionError, asyncio.TimeoutError) as e:
                        logger.error(f"Network error updating shared appointment: {e}")
                        raise TemporarySyncError(f"Network error during update: {str(e)}")
                    except Exception as e:
                        error_str = str(e).lower()
                        if any(temp in error_str for temp in ['timeout', 'connection', 'network', 'rate limit', '429', '503']):
                            raise TemporarySyncError(f"Temporary API error during update: {str(e)}")
                        else:
                            logger.error(f"Failed to update shared appointment: {e}", exc_info=True)
                            # Don't raise permanent error here, try to recreate instead
                            sync_id = None
                else:
                    # Shared appointment was deleted, clear tracking and recreate
                    await self._clear_sync_tracking(private_service, appointment.notion_page_id)
                    sync_id = None
            except TemporarySyncError:
                # Re-raise temporary errors for retry
                raise
            except Exception as e:
                logger.warning(f"Error checking shared appointment {sync_id}: {e}")
                # Assume shared appointment might be deleted, try to recreate
                sync_id = None
        
        if not sync_id:
            # Not synced yet, check if a duplicate already exists in shared database
            # This prevents creating duplicates if sync tracking was lost
            existing_shared = await self._find_existing_shared_appointment(
                shared_service, appointment, user_id
            )
            
            if existing_shared:
                # Found existing shared appointment, update sync tracking
                await self._update_sync_tracking(private_service, appointment.notion_page_id, existing_shared.notion_page_id)
                
                # Update the existing appointment with current data
                updated_appointment = self._prepare_appointment_for_shared(appointment, user_id)
                await shared_service.update_appointment(existing_shared.notion_page_id, updated_appointment)
                
                stats["updated"] += 1
                logger.debug(f"Found and linked existing shared appointment {existing_shared.notion_page_id}")
                return True
            else:
                # Before creating, do one more check for duplicates across ALL appointments
                # This handles edge cases where multiple users might create similar appointments
                all_shared = await shared_service.get_appointments(limit=500)
                if not all_shared:
                    all_shared = []
                duplicate = DuplicateChecker.find_appointment_by_content(appointment, all_shared)
                
                if duplicate:
                    # Found a duplicate from another user, log and skip
                    logger.warning(
                        f"Skipping creation of '{appointment.title}' at {appointment.start_date} - "
                        f"duplicate already exists in shared database (created by different user)"
                    )
                    stats["errors"] += 1
                    return False
                
                # Create new appointment in shared database
                shared_appointment = self._prepare_appointment_for_shared(appointment, user_id)
                logger.debug(f"Creating new shared appointment with data: title={shared_appointment.title}, start={shared_appointment.start_date}, end={shared_appointment.end_date}")
                
                try:
                    shared_page_id = await shared_service.create_appointment(shared_appointment)
                    logger.debug(f"Successfully created shared appointment with ID: {shared_page_id}")
                    
                    # Update private database with sync tracking
                    await self._update_sync_tracking(private_service, appointment.notion_page_id, shared_page_id)
                    
                    stats["created"] += 1
                    logger.info(f"Created new synced appointment '{appointment.title}' (shared ID: {shared_page_id})")
                    return True
                except (ConnectionError, asyncio.TimeoutError) as e:
                    logger.error(f"Network error creating shared appointment: {e}")
                    raise TemporarySyncError(f"Network error: {str(e)}")
                except ValueError as e:
                    logger.error(f"Data validation error creating shared appointment: {e}")
                    raise PermanentSyncError(f"Invalid appointment data: {str(e)}")
                except Exception as e:
                    error_str = str(e).lower()
                    if any(temp in error_str for temp in ['timeout', 'connection', 'network', 'rate limit', '429', '503']):
                        logger.error(f"Temporary error creating shared appointment: {e}")
                        raise TemporarySyncError(f"Temporary API error: {str(e)}")
                    else:
                        logger.error(f"Failed to create shared appointment: {e}", exc_info=True)
                        raise PermanentSyncError(f"Failed to create appointment: {str(e)}")
        
        return False
    
    def _prepare_appointment_for_shared(self, appointment: Appointment, user_id: int) -> SharedAppointment:
        """
        Prepare appointment data for shared database with tracking fields.
        
        Args:
            appointment: Original appointment
            user_id: Telegram user ID of the creator
            
        Returns:
            SharedAppointment optimized for shared database
        """
        logger.debug(f"Preparing appointment '{appointment.title}' for shared database")
        logger.debug(f"Start date: {appointment.start_date}, End date: {appointment.end_date}")
        
        # Create SharedAppointment (excludes PartnerRelevant property)
        shared_appointment = SharedAppointment(
            title=appointment.title,
            start_date=appointment.start_date,  # Use new field
            end_date=appointment.end_date,      # Use new field
            date=appointment.date,              # Keep for backward compatibility
            description=appointment.description,
            location=appointment.location,
            tags=appointment.tags,
            outlook_id=appointment.outlook_id,
            organizer=appointment.organizer,
            duration_minutes=appointment.duration_minutes,
            is_business_event=appointment.is_business_event,
            partner_relevant=True,  # Always True in shared database
            source_private_id=appointment.notion_page_id,
            source_user_id=user_id,
            created_at=appointment.created_at
        )
        
        logger.debug(f"Created SharedAppointment with dates: start={shared_appointment.start_date}, end={shared_appointment.end_date}")
        return shared_appointment
    
    async def _get_sync_tracking(self, private_service: NotionService, appointment_id: str) -> Optional[str]:
        """
        Get the SyncedToSharedId from private database.
        
        Args:
            private_service: Private database service
            appointment_id: Appointment ID in private database
            
        Returns:
            Shared database ID if synced, None otherwise
        """
        try:
            appointment = await private_service.get_appointment_by_id(appointment_id)
            if appointment:
                return appointment.synced_to_shared_id
            return None
        except Exception as e:
            logger.warning(f"Error getting sync tracking for {appointment_id}: {e}")
            return None
    
    async def _update_sync_tracking(self, private_service: NotionService, 
                                  appointment_id: str, shared_id: str) -> bool:
        """
        Update private database with sync tracking information.
        
        Args:
            private_service: Private database service
            appointment_id: Appointment ID in private database
            shared_id: Corresponding ID in shared database
            
        Returns:
            True if updated successfully
        """
        try:
            # Get the current appointment
            appointment = await private_service.get_appointment_by_id(appointment_id)
            if not appointment:
                logger.error(f"Appointment {appointment_id} not found for sync tracking update")
                return False
            
            # Update sync tracking field
            appointment.synced_to_shared_id = shared_id
            
            # Update in Notion
            success = await private_service.update_appointment(appointment_id, appointment)
            if success:
                logger.debug(f"Updated sync tracking: {appointment_id} -> {shared_id}")
            return success
            
        except Exception as e:
            logger.error(f"Error updating sync tracking: {e}")
            return False
    
    async def _clear_sync_tracking(self, private_service: NotionService, appointment_id: str) -> bool:
        """
        Clear sync tracking information from private database.
        
        Args:
            private_service: Private database service
            appointment_id: Appointment ID in private database
            
        Returns:
            True if cleared successfully
        """
        try:
            # Get the current appointment
            appointment = await private_service.get_appointment_by_id(appointment_id)
            if not appointment:
                logger.error(f"Appointment {appointment_id} not found for sync tracking clear")
                return False
            
            # Clear sync tracking field
            appointment.synced_to_shared_id = None
            
            # Update in Notion
            success = await private_service.update_appointment(appointment_id, appointment)
            if success:
                logger.debug(f"Cleared sync tracking for: {appointment_id}")
            return success
            
        except Exception as e:
            logger.error(f"Error clearing sync tracking: {e}")
            return False
    
    async def _cleanup_removed_appointments(self, private_service: NotionService,
                                          shared_service: NotionService,
                                          user_id: int,
                                          stats: Dict[str, int]):
        """
        Remove appointments from shared database that are no longer partner-relevant.
        
        Args:
            private_service: Private database service
            shared_service: Shared database service
            user_id: Telegram user ID
            stats: Statistics dictionary to update
        """
        try:
            # Get all appointments in shared database for this user
            shared_appointments = await shared_service.get_appointments(limit=500)
            if not shared_appointments:
                shared_appointments = []
            user_shared = [apt for apt in shared_appointments 
                         if hasattr(apt, 'source_user_id') and apt.source_user_id == user_id]
            
            # Get all partner-relevant appointments from private database
            private_appointments = await private_service.get_appointments(limit=500)
            if not private_appointments:
                private_appointments = []
            partner_relevant_ids = {apt.notion_page_id for apt in private_appointments if apt.partner_relevant}
            
            # Remove appointments that are no longer partner-relevant
            for shared_apt in user_shared:
                if hasattr(shared_apt, 'source_private_id') and shared_apt.source_private_id not in partner_relevant_ids:
                    await shared_service.delete_appointment(shared_apt.notion_page_id)
                    stats["removed"] += 1
                    logger.debug(f"Removed non-partner-relevant appointment {shared_apt.notion_page_id}")
        
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    async def _find_existing_shared_appointment(self, shared_service: NotionService, 
                                               appointment: Appointment, 
                                               user_id: int) -> Optional[Appointment]:
        """
        Find an existing appointment in shared database that matches the given appointment.
        
        This helps prevent duplicates when sync tracking is lost.
        
        Args:
            shared_service: Shared database service
            appointment: Appointment to find
            user_id: User ID who created the appointment
            
        Returns:
            Existing shared appointment if found, None otherwise
        """
        try:
            # Get all appointments from shared database
            shared_appointments = await shared_service.get_appointments(limit=500)
            if not shared_appointments:
                shared_appointments = []
            
            # Filter appointments from the same user
            user_appointments = [
                apt for apt in shared_appointments
                if hasattr(apt, 'source_user_id') and apt.source_user_id == user_id
            ]
            
            # Use DuplicateChecker to find matching appointment
            matching_appointment = DuplicateChecker.find_appointment_by_content(
                appointment, user_appointments
            )
            
            return matching_appointment
            
        except Exception as e:
            logger.warning(f"Error finding existing shared appointment: {e}")
            return None
    
    async def get_sync_status(self, user_config: UserConfig) -> Dict[str, Any]:
        """
        Get sync status and statistics for a user.
        
        Args:
            user_config: User configuration
            
        Returns:
            Dictionary with sync status information
        """
        try:
            if not user_config.shared_notion_database_id:
                return {
                    "enabled": False,
                    "error": "No shared database configured"
                }
            
            private_service = NotionService(
                notion_api_key=user_config.notion_api_key,
                database_id=user_config.notion_database_id
            )
            
            # Use appropriate API key for shared database
            shared_api_key = self.user_config_manager.get_shared_database_api_key(user_config)
            shared_service = NotionService(
                notion_api_key=shared_api_key,
                database_id=user_config.shared_notion_database_id
            )
            
            # Get statistics
            private_appointments = await private_service.get_appointments(limit=200)
            if not private_appointments:
                private_appointments = []
            partner_relevant_count = sum(1 for apt in private_appointments if apt.partner_relevant)
            
            shared_appointments = await shared_service.get_appointments(limit=200)
            if not shared_appointments:
                shared_appointments = []
            user_shared_count = sum(1 for apt in shared_appointments 
                                  if hasattr(apt, 'source_user_id') and apt.source_user_id == user_config.telegram_user_id)
            
            return {
                "enabled": True,
                "running": self._running,
                "interval_hours": self.sync_interval_hours,
                "private_partner_relevant": partner_relevant_count,
                "shared_synced": user_shared_count,
                "last_sync": "N/A"  # Could be enhanced to track last sync time
            }
            
        except Exception as e:
            logger.error(f"Error getting sync status: {e}")
            return {
                "enabled": False,
                "error": str(e)
            }