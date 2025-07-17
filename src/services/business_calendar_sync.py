"""Business calendar synchronization service for processing email-based calendar events."""
import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Dict, Set
from datetime import datetime, timedelta

from config.user_config import UserConfig
from src.services.email_processor import EmailProcessor, create_email_processor_from_config
from src.services.json_parser import BusinessEventParser, BusinessEvent
from src.services.notion_service import NotionService
from src.models.appointment import Appointment

logger = logging.getLogger(__name__)


class BusinessCalendarSync:
    """Main service for synchronizing business calendar events from emails to Notion."""
    
    def __init__(self, user_config: UserConfig, global_config: Dict = None):
        """
        Initialize business calendar sync.
        
        Args:
            user_config: User configuration with email and Notion settings
            global_config: Global configuration options
        """
        self.user_config = user_config
        self.global_config = global_config or {}
        
        # Initialize services
        self.event_parser = BusinessEventParser()
        self.processed_outlook_ids: Set[str] = set()
        
        # Sync settings
        self.check_interval = self.global_config.get('email_check_interval', 300)  # 5 minutes
        self.delete_after_processing = self.global_config.get('delete_after_processing', True)  # Default to True
        
        # Email configuration from global config or user config
        self._setup_email_processor()
        self._setup_notion_services()
        
        # Processing statistics
        self.stats = {
            'emails_processed': 0,
            'events_created': 0,
            'events_updated': 0,
            'events_deleted': 0,
            'errors': 0,
            'last_sync': None
        }
    
    def _setup_email_processor(self):
        """Setup email processor from configuration."""
        try:
            email_config = self.global_config
            
            if not all([
                email_config.get('email_address'),
                email_config.get('email_password')
            ]):
                logger.warning(f"Email configuration incomplete for user {self.user_config.telegram_user_id}")
                self.email_processor = None
                return
            
            self.email_processor = create_email_processor_from_config(
                email_address=email_config['email_address'],
                email_password=email_config['email_password'],
                imap_server=email_config.get('imap_server', 'imap.gmail.com'),
                imap_port=email_config.get('imap_port', 993),
                delete_after_processing=self.delete_after_processing
            )
            
            logger.info(f"Email processor configured for {email_config['email_address']}")
            
        except Exception as e:
            logger.error(f"Error setting up email processor: {e}")
            self.email_processor = None
    
    def _setup_notion_services(self):
        """Setup Notion services for business and shared calendars."""
        try:
            # 1. Setup Business Database (individual per user if configured)
            if (hasattr(self.user_config, 'business_notion_api_key') and
                hasattr(self.user_config, 'business_notion_database_id') and
                self.user_config.business_notion_api_key and
                self.user_config.business_notion_database_id):
                
                # User has individual business database
                self.business_notion = NotionService(
                    notion_api_key=self.user_config.business_notion_api_key,
                    database_id=self.user_config.business_notion_database_id
                )
                logger.info(f"Using user's business database: {self.user_config.business_notion_database_id}")
                
            elif self.global_config.get('business_notion_database_id'):
                # Fall back to global business database
                business_api_key = (self.user_config.shared_notion_api_key or 
                                  self.user_config.notion_api_key)
                self.business_notion = NotionService(
                    notion_api_key=business_api_key,
                    database_id=self.global_config['business_notion_database_id']
                )
                logger.info(f"Using global business database: {self.global_config['business_notion_database_id']}")
                
            else:
                # No business database - use private database
                self.business_notion = NotionService(
                    notion_api_key=self.user_config.notion_api_key,
                    database_id=self.user_config.notion_database_id
                )
                logger.info("Using private database for business events (no business DB configured)")
            
            # 2. Setup Shared Database (global - used by all users)
            shared_api_key = (self.global_config.get('shared_notion_api_key') or
                            self.user_config.shared_notion_api_key)
            shared_db_id = (self.global_config.get('shared_notion_database_id') or
                          self.user_config.shared_notion_database_id)
            
            if shared_api_key and shared_db_id:
                self.shared_notion = NotionService(
                    notion_api_key=shared_api_key,
                    database_id=shared_db_id
                )
                logger.info(f"Shared calendar configured: {shared_db_id}")
            else:
                self.shared_notion = None
                logger.warning("Shared calendar not configured")
                
        except Exception as e:
            logger.error(f"Error setting up Notion services: {e}")
            self.business_notion = None
            self.shared_notion = None
    
    async def start_sync_loop(self):
        """Start the main synchronization loop."""
        if not self.email_processor:
            logger.error("Email processor not configured, cannot start sync")
            return
        
        if not self.business_notion:
            logger.error("Business Notion service not configured, cannot start sync")
            return
        
        logger.info(f"Starting business calendar sync for user {self.user_config.telegram_user_id}")
        logger.info(f"Check interval: {self.check_interval} seconds")
        
        # Initial sync with up to 500 emails
        logger.info("Running initial sync to process up to 500 emails")
        await self.sync_business_calendars(is_initial=True)
        
        # Then continue with regular sync loop
        while True:
            try:
                await self.sync_business_calendars(is_initial=False)
                await asyncio.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                logger.info("Sync loop interrupted by user")
                break
            except Exception as e:
                logger.error(f"Error in sync loop: {e}")
                self.stats['errors'] += 1
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def sync_business_calendars(self, is_initial: bool = False):
        """Main synchronization method."""
        try:
            logger.info(f"Starting business calendar sync (initial={is_initial})")
            
            # Create thread pool for email operations
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=1, thread_name_prefix="email-sync") as executor:
                # Determine email fetch limit based on initial or regular run
                # Increased limits for 30-day processing window
                fetch_limit = 1000 if is_initial else 200
                
                # Fetch emails in thread to avoid blocking
                emails = await loop.run_in_executor(
                    executor,
                    lambda: self.email_processor.fetch_emails(limit=fetch_limit, is_initial=is_initial)
                )
                
                if not emails:
                    logger.debug("No emails found")
                    return
                
                logger.info(f"Processing {len(emails)} emails")
                
                for email_msg in emails:
                    try:
                        await self._process_single_email(email_msg, executor)
                    except Exception as e:
                        logger.error(f"Error processing email {email_msg.uid}: {e}")
                        self.stats['errors'] += 1
                        continue
                
            self.stats['last_sync'] = datetime.now()
            logger.info(f"Sync completed. Stats: {self.stats}")
            
        except Exception as e:
            logger.error(f"Error in business calendar sync: {e}")
            self.stats['errors'] += 1
    
    async def _process_single_email(self, email_msg, executor):
        """
        Process a single email message.
        
        Args:
            email_msg: EmailMessage object to process
            executor: ThreadPoolExecutor for running blocking operations
        """
        logger.info(f"Processing email: {email_msg.subject} from {email_msg.sender}")
        
        # Check if this is a calendar forwarding email
        if not self._is_calendar_email(email_msg):
            logger.debug(f"Email {email_msg.uid} is not a calendar email, skipping")
            return
        
        # Extract business event from email
        business_event = self.event_parser.parse_email_content(email_msg.body)
        
        if not business_event:
            logger.warning(f"Failed to parse business event from email {email_msg.uid}")
            # Mark as read but don't delete - might need manual review
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                executor,
                self.email_processor.mark_email_as_read,
                email_msg.uid
            )
            return
        
        logger.info(f"Parsed event: {business_event.event_title} ({business_event.action})")
        
        # Check for duplicate processing
        if business_event.outlook_ical_id in self.processed_outlook_ids:
            logger.info(f"Event {business_event.outlook_ical_id} already processed, skipping")
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                executor,
                self.email_processor.process_email_after_success,
                email_msg.uid
            )
            return
        
        # Process the business event
        success = await self._process_business_event(business_event)
        
        if success:
            # Mark as processed
            self.processed_outlook_ids.add(business_event.outlook_ical_id)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                executor,
                self.email_processor.process_email_after_success,
                email_msg.uid
            )
            self.stats['emails_processed'] += 1
            logger.info(f"Successfully processed email {email_msg.uid}")
        else:
            # Mark as read but don't delete on error
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                executor,
                self.email_processor.mark_email_as_read,
                email_msg.uid
            )
            logger.error(f"Failed to process email {email_msg.uid}")
    
    def _is_calendar_email(self, email_msg) -> bool:
        """
        Check if email is a calendar forwarding email.
        
        Args:
            email_msg: EmailMessage to check
            
        Returns:
            True if this is a calendar email
        """
        # Check subject
        calendar_subjects = ['terminweiterleitung', 'calendar forward', 'termin', 'meeting']
        subject_lower = email_msg.subject.lower()
        
        if any(keyword in subject_lower for keyword in calendar_subjects):
            return True
        
        # Check if body contains JSON-like structure
        if '{' in email_msg.body and '"Action"' in email_msg.body:
            return True
        
        # Check authorized senders
        authorized_senders = self.global_config.get('outlook_sender_whitelist', '').split(',')
        if authorized_senders:
            sender_email = email_msg.sender.lower()
            if any(sender.strip().lower() in sender_email for sender in authorized_senders if sender.strip()):
                return True
        
        return False
    
    async def _process_business_event(self, business_event: BusinessEvent) -> bool:
        """
        Process a business event and save to appropriate Notion databases.
        
        Args:
            business_event: BusinessEvent to process
            
        Returns:
            True if processing successful, False otherwise
        """
        try:
            if business_event.action == 'Delete':
                return await self._delete_business_event(business_event)
            elif business_event.action in ['Create', 'Update']:
                return await self._create_or_update_business_event(business_event)
            else:
                logger.error(f"Unknown action: {business_event.action}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing business event: {e}")
            return False
    
    async def _create_or_update_business_event(self, business_event: BusinessEvent) -> bool:
        """Create or update business event in Notion."""
        try:
            # Convert to Appointment object
            appointment = Appointment(
                title=business_event.event_title,
                date=business_event.event_start,
                description=f"Organizer: {business_event.organizer}",
                outlook_id=business_event.outlook_ical_id,
                organizer=business_event.organizer,
                is_business_event=True
            )
            
            # Set end time if different from start
            if business_event.event_end != business_event.event_start:
                duration = business_event.event_end - business_event.event_start
                appointment.duration_minutes = int(duration.total_seconds() / 60)
            
            # Save to business database
            if business_event.action == 'Update':
                # Try to update existing appointment
                updated = await self._update_existing_appointment(appointment)
                if updated:
                    self.stats['events_updated'] += 1
                else:
                    # If update failed, create new
                    await self.business_notion.create_appointment(appointment)
                    self.stats['events_created'] += 1
            else:
                # Create new appointment
                await self.business_notion.create_appointment(appointment)
                self.stats['events_created'] += 1
            
            logger.info(f"Saved business event to business database: {appointment.title}")
            
            # Save to shared database if team event
            if business_event.is_team_event() and self.shared_notion:
                try:
                    if business_event.action == 'Update':
                        updated = await self._update_existing_appointment(appointment, use_shared=True)
                        if not updated:
                            await self.shared_notion.create_appointment(appointment)
                    else:
                        await self.shared_notion.create_appointment(appointment)
                    
                    logger.info(f"Also saved team event to shared database: {appointment.title}")
                except Exception as e:
                    logger.warning(f"Failed to save to shared database: {e}")
                    # Don't fail the whole operation if shared save fails
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating/updating business event: {e}")
            return False
    
    async def _update_existing_appointment(self, appointment: Appointment, use_shared: bool = False) -> bool:
        """Update existing appointment by Outlook ID."""
        try:
            notion_service = self.shared_notion if use_shared else self.business_notion
            
            # Find existing appointment by outlook_id
            page_id = notion_service.find_appointment_by_outlook_id(appointment.outlook_id)
            
            if page_id:
                # Update the existing appointment
                success = await notion_service.update_appointment(page_id, appointment)
                if success:
                    logger.info(f"Updated appointment with OutlookID {appointment.outlook_id}")
                    return True
                else:
                    logger.error(f"Failed to update appointment with OutlookID {appointment.outlook_id}")
                    return False
            else:
                logger.info(f"No existing appointment found with OutlookID {appointment.outlook_id}, will create new")
                return False
            
        except Exception as e:
            logger.error(f"Error updating existing appointment: {e}")
            return False
    
    async def _delete_business_event(self, business_event: BusinessEvent) -> bool:
        """Delete business event from Notion databases."""
        try:
            # Delete from business database
            deleted_business = self.business_notion.delete_appointment_by_outlook_id(
                business_event.outlook_ical_id
            )
            
            # If it's a team event, also delete from shared database
            if business_event.is_team_event and self.shared_notion:
                deleted_shared = self.shared_notion.delete_appointment_by_outlook_id(
                    business_event.outlook_ical_id
                )
                logger.info(f"Deleted team event from both databases: {business_event.outlook_ical_id}")
            
            if deleted_business:
                logger.info(f"Deleted business event: {business_event.outlook_ical_id}")
                self.stats['events_deleted'] += 1
                return True
            else:
                logger.warning(f"No event found to delete with OutlookID: {business_event.outlook_ical_id}")
                return True  # Still return True as the event doesn't exist
            
        except Exception as e:
            logger.error(f"Error deleting business event: {e}")
            return False
    
    def get_sync_stats(self) -> Dict:
        """Get synchronization statistics."""
        return self.stats.copy()
    
    def stop_sync(self):
        """Stop the synchronization process."""
        logger.info("Stopping business calendar sync")


class BusinessCalendarSyncManager:
    """Manager for multiple user business calendar syncs."""
    
    def __init__(self, global_config: Dict):
        """
        Initialize sync manager.
        
        Args:
            global_config: Global configuration options
        """
        self.global_config = global_config
        self.user_syncs: Dict[int, BusinessCalendarSync] = {}
        self.running = False
    
    def add_user(self, user_config: UserConfig):
        """Add user to sync management."""
        if not self.global_config.get('email_sync_enabled', False):
            logger.info("Email sync disabled in configuration")
            return
        
        sync = BusinessCalendarSync(user_config, self.global_config)
        self.user_syncs[user_config.telegram_user_id] = sync
        logger.info(f"Added user {user_config.telegram_user_id} to business calendar sync")
    
    async def start_all_syncs(self):
        """Start sync loops for all users."""
        if not self.user_syncs:
            logger.info("No users configured for business calendar sync")
            return
        
        self.running = True
        logger.info(f"Starting business calendar sync for {len(self.user_syncs)} users")
        
        # Start sync tasks for all users
        tasks = []
        for user_id, sync in self.user_syncs.items():
            task = asyncio.create_task(sync.start_sync_loop())
            tasks.append(task)
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Error in sync manager: {e}")
        finally:
            self.running = False
    
    def stop_all_syncs(self):
        """Stop all sync processes."""
        self.running = False
        for sync in self.user_syncs.values():
            sync.stop_sync()
        logger.info("Stopped all business calendar syncs")
    
    def get_all_stats(self) -> Dict[int, Dict]:
        """Get stats for all user syncs."""
        return {
            user_id: sync.get_sync_stats() 
            for user_id, sync in self.user_syncs.items()
        }


# Factory function for creating sync manager from environment
def create_sync_manager_from_env() -> BusinessCalendarSyncManager:
    """Create BusinessCalendarSyncManager from environment configuration."""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    global_config = {
        'email_sync_enabled': os.getenv('EMAIL_SYNC_ENABLED', 'false').lower() == 'true',
        'email_address': os.getenv('EMAIL_ADDRESS', ''),
        'email_password': os.getenv('EMAIL_PASSWORD', ''),
        'imap_server': os.getenv('IMAP_SERVER', 'imap.gmail.com'),
        'imap_port': int(os.getenv('IMAP_PORT', '993')),
        'email_check_interval': int(os.getenv('EMAIL_CHECK_INTERVAL', '300')),
        'business_notion_database_id': os.getenv('BUSINESS_NOTION_DATABASE_ID', ''),
        'delete_after_processing': os.getenv('DELETE_AFTER_PROCESSING', 'false').lower() == 'true',
        'outlook_sender_whitelist': os.getenv('OUTLOOK_SENDER_WHITELIST', ''),
    }
    
    return BusinessCalendarSyncManager(global_config)


if __name__ == "__main__":
    # Test the business calendar sync
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    
    from config.user_config import UserConfig
    
    # Test configuration
    test_user_config = UserConfig(
        telegram_user_id=123456789,
        telegram_username="test_user",
        notion_api_key="test_api_key",
        notion_database_id="test_db_id",
        shared_notion_api_key="shared_api_key",
        shared_notion_database_id="shared_db_id"
    )
    
    sync_manager = create_sync_manager_from_env()
    sync_manager.add_user(test_user_config)
    
    print("Business Calendar Sync Manager created successfully")
    print(f"Configuration: {sync_manager.global_config}")