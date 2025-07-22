"""Partner sync service to bypass Notion Plus plan limitations."""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import uuid

from src.models.appointment import Appointment
from src.models.shared_appointment import SharedAppointment
from src.services.notion_service import NotionService
from config.user_config import UserConfigManager, UserConfig

logger = logging.getLogger(__name__)


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
        if not user_config.shared_notion_database_id:
            logger.warning(f"User {user_config.telegram_user_id} has no shared database configured")
            return {"success": False, "error": "No shared database configured"}
        
        try:
            private_service = NotionService(
                notion_api_key=user_config.notion_api_key,
                database_id=user_config.notion_database_id
            )
            
            shared_service = NotionService(
                notion_api_key=user_config.notion_api_key,
                database_id=user_config.shared_notion_database_id
            )
            
            # Get all appointments from private database
            all_appointments = await private_service.get_appointments(limit=200)
            partner_relevant = [apt for apt in all_appointments if apt.partner_relevant]
            
            stats = {
                "total_processed": len(partner_relevant),
                "created": 0,
                "updated": 0,
                "errors": 0,
                "removed": 0
            }
            
            # Process each partner-relevant appointment
            for appointment in partner_relevant:
                try:
                    await self._sync_single_appointment_internal(
                        appointment, private_service, shared_service, 
                        user_config.telegram_user_id, stats
                    )
                except Exception as e:
                    logger.error(f"Error syncing appointment {appointment.notion_page_id}: {e}")
                    stats["errors"] += 1
            
            # Check for appointments that are no longer partner-relevant
            await self._cleanup_removed_appointments(private_service, shared_service, user_config.telegram_user_id, stats)
            
            logger.info(f"Sync completed for user {user_config.telegram_user_id}: {stats}")
            return {"success": True, "stats": stats}
            
        except Exception as e:
            logger.error(f"Error during sync for user {user_config.telegram_user_id}: {e}")
            return {"success": False, "error": str(e)}
    
    async def sync_single_appointment(self, appointment: Appointment, 
                                    user_config: UserConfig, 
                                    force_sync: bool = False) -> bool:
        """
        Sync a single appointment if it's partner-relevant.
        
        Args:
            appointment: The appointment to sync
            user_config: User configuration
            force_sync: If True, sync even if already synced
            
        Returns:
            True if synced successfully, False otherwise
        """
        if not user_config.shared_notion_database_id:
            logger.warning(f"User {user_config.telegram_user_id} has no shared database configured")
            return False
        
        if not appointment.partner_relevant and not force_sync:
            # If not partner relevant, check if we need to remove from shared DB
            return await self.remove_from_shared(appointment.notion_page_id or "", user_config)
        
        try:
            private_service = NotionService(
                notion_api_key=user_config.notion_api_key,
                database_id=user_config.notion_database_id
            )
            
            shared_service = NotionService(
                notion_api_key=user_config.notion_api_key,
                database_id=user_config.shared_notion_database_id
            )
            
            stats = {"created": 0, "updated": 0, "errors": 0}
            
            success = await self._sync_single_appointment_internal(
                appointment, private_service, shared_service, 
                user_config.telegram_user_id, stats
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Error syncing single appointment: {e}")
            return False
    
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
            shared_service = NotionService(
                notion_api_key=user_config.notion_api_key,
                database_id=user_config.shared_notion_database_id
            )
            
            # Find appointment in shared database by SourcePrivateId
            shared_appointments = await shared_service.get_appointments(limit=500)
            
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
                await asyncio.sleep(300)  # 5 minutes
    
    async def _sync_single_appointment_internal(self, appointment: Appointment, 
                                              private_service: NotionService,
                                              shared_service: NotionService,
                                              user_id: int,
                                              stats: Dict[str, int]) -> bool:
        """
        Internal method to sync a single appointment.
        
        Args:
            appointment: The appointment to sync
            private_service: Private database service
            shared_service: Shared database service
            user_id: Telegram user ID
            stats: Statistics dictionary to update
            
        Returns:
            True if synced successfully
        """
        if not appointment.notion_page_id:
            logger.warning("Appointment has no notion_page_id, skipping sync")
            return False
        
        # Check if already synced by looking for SyncedToSharedId
        sync_id = await self._get_sync_tracking(private_service, appointment.notion_page_id)
        
        if sync_id:
            # Already synced, check if shared appointment still exists and update if needed
            try:
                shared_appointment = await shared_service.get_appointment_by_id(sync_id)
                if shared_appointment:
                    # Update shared appointment with current data
                    updated_appointment = self._prepare_appointment_for_shared(appointment, user_id)
                    await shared_service.update_appointment(sync_id, updated_appointment)
                    stats["updated"] += 1
                    logger.debug(f"Updated synced appointment {sync_id}")
                    return True
                else:
                    # Shared appointment was deleted, clear tracking and recreate
                    await self._clear_sync_tracking(private_service, appointment.notion_page_id)
                    sync_id = None
            except Exception as e:
                logger.warning(f"Error checking shared appointment {sync_id}: {e}")
                sync_id = None
        
        if not sync_id:
            # Not synced yet, create in shared database
            shared_appointment = self._prepare_appointment_for_shared(appointment, user_id)
            shared_page_id = await shared_service.create_appointment(shared_appointment)
            
            # Update private database with sync tracking
            await self._update_sync_tracking(private_service, appointment.notion_page_id, shared_page_id)
            
            stats["created"] += 1
            logger.debug(f"Created new synced appointment {shared_page_id}")
            return True
        
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
        # Create SharedAppointment (excludes PartnerRelevant property)
        shared_appointment = SharedAppointment(
            title=appointment.title,
            date=appointment.date,
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
            user_shared = [apt for apt in shared_appointments 
                         if hasattr(apt, 'source_user_id') and apt.source_user_id == user_id]
            
            # Get all partner-relevant appointments from private database
            private_appointments = await private_service.get_appointments(limit=500)
            partner_relevant_ids = {apt.notion_page_id for apt in private_appointments if apt.partner_relevant}
            
            # Remove appointments that are no longer partner-relevant
            for shared_apt in user_shared:
                if hasattr(shared_apt, 'source_private_id') and shared_apt.source_private_id not in partner_relevant_ids:
                    await shared_service.delete_appointment(shared_apt.notion_page_id)
                    stats["removed"] += 1
                    logger.debug(f"Removed non-partner-relevant appointment {shared_apt.notion_page_id}")
        
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
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
            
            shared_service = NotionService(
                notion_api_key=user_config.notion_api_key,
                database_id=user_config.shared_notion_database_id
            )
            
            # Get statistics
            private_appointments = await private_service.get_appointments(limit=200)
            partner_relevant_count = sum(1 for apt in private_appointments if apt.partner_relevant)
            
            shared_appointments = await shared_service.get_appointments(limit=200)
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