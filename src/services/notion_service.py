import logging
from typing import List, Optional, Union
from notion_client import Client
from notion_client.errors import APIResponseError
from src.models.appointment import Appointment
from config.settings import Settings
from config.user_config import UserConfig
from src.utils.error_handler import BotError, ErrorType, ErrorSeverity, handle_bot_error

logger = logging.getLogger(__name__)


class NotionService:
    """Service for interacting with Notion API."""
    
    def __init__(self, settings: Optional[Settings] = None, 
                 notion_api_key: Optional[str] = None,
                 database_id: Optional[str] = None):
        """
        Initialize NotionService with either Settings object or direct parameters.
        
        Args:
            settings: Settings object (for backward compatibility)
            notion_api_key: Direct API key (for multi-user support)
            database_id: Direct database ID (for multi-user support)
        """
        if settings:
            # Backward compatibility
            self.settings = settings
            self.client = Client(auth=settings.notion_api_key)
            self.database_id = settings.notion_database_id
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
    
    @classmethod
    def from_user_config(cls, user_config: UserConfig) -> 'NotionService':
        """Create NotionService from UserConfig."""
        return cls(
            notion_api_key=user_config.notion_api_key,
            database_id=user_config.notion_database_id
        )
    
    @handle_bot_error(ErrorType.NOTION_API, ErrorSeverity.HIGH)
    async def create_appointment(self, appointment: Appointment) -> str:
        """
        Create a new appointment in Notion database.
        
        Args:
            appointment: Appointment object to create
            
        Returns:
            str: Notion page ID of created appointment
            
        Raises:
            BotError: If Notion API request fails
        """
        try:
            properties = appointment.to_notion_properties(self.settings.timezone if self.settings else 'Europe/Berlin')
            
            response = self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties
            )
            
            page_id = response["id"]
            logger.info(f"Created appointment in Notion: {page_id}")
            
            return page_id
            
        except APIResponseError as e:
            logger.error(f"Failed to create appointment in Notion: {e}")
            raise BotError(
                f"Failed to create appointment in Notion: {str(e)}",
                ErrorType.NOTION_API,
                ErrorSeverity.HIGH,
                user_message="📝 Fehler beim Erstellen des Termins in Notion. Bitte versuche es erneut."
            )
    
    @handle_bot_error(ErrorType.NOTION_API, ErrorSeverity.MEDIUM)
    async def get_appointments(self, limit: int = 10) -> List[Appointment]:
        """
        Get appointments from Notion database.
        
        Args:
            limit: Maximum number of appointments to retrieve
            
        Returns:
            List[Appointment]: List of appointments
        """
        try:
            response = self.client.databases.query(
                database_id=self.database_id,
                sorts=[
                    {
                        "property": "Datum",  # Updated to match your database field
                        "direction": "ascending"
                    }
                ],
                page_size=limit
            )
            
            appointments = []
            for page in response["results"]:
                try:
                    appointment = Appointment.from_notion_page(page)
                    appointments.append(appointment)
                except Exception as e:
                    logger.warning(f"Failed to parse appointment from page {page['id']}: {e}")
                    continue
            
            logger.info(f"Retrieved {len(appointments)} appointments from Notion")
            return appointments
            
        except APIResponseError as e:
            logger.error(f"Failed to retrieve appointments from Notion: {e}")
            raise BotError(
                f"Failed to retrieve appointments from Notion: {str(e)}",
                ErrorType.NOTION_API,
                ErrorSeverity.MEDIUM,
                user_message="📝 Fehler beim Laden der Termine aus Notion. Bitte versuche es später erneut."
            )
    
    async def get_appointment_by_id(self, page_id: str) -> Optional[Appointment]:
        """
        Get a specific appointment by its Notion page ID.
        
        Args:
            page_id: Notion page ID
            
        Returns:
            Appointment object if found, None otherwise
        """
        try:
            response = self.client.pages.retrieve(page_id=page_id)
            
            if response and not response.get('archived', False):
                appointment = Appointment.from_notion_page(response)
                logger.info(f"Retrieved appointment by ID: {page_id}")
                return appointment
            else:
                logger.warning(f"Appointment {page_id} not found or archived")
                return None
                
        except APIResponseError as e:
            logger.error(f"Failed to retrieve appointment by ID {page_id}: {e}")
            return None
        except Exception as e:
            logger.warning(f"Failed to parse appointment from page {page_id}: {e}")
            return None
    
    @handle_bot_error(ErrorType.NOTION_API, ErrorSeverity.HIGH)
    async def update_appointment(self, page_id: str, appointment: Appointment) -> bool:
        """
        Update an existing appointment in Notion.
        
        Args:
            page_id: Notion page ID
            appointment: Updated appointment data
            
        Returns:
            bool: True if successful
        """
        try:
            properties = appointment.to_notion_properties(self.settings.timezone if self.settings else 'Europe/Berlin')
            
            self.client.pages.update(
                page_id=page_id,
                properties=properties
            )
            
            logger.info(f"Updated appointment in Notion: {page_id}")
            return True
            
        except APIResponseError as e:
            logger.error(f"Failed to update appointment in Notion: {e}")
            raise BotError(
                f"Failed to update appointment in Notion: {str(e)}",
                ErrorType.NOTION_API,
                ErrorSeverity.HIGH,
                user_message="📝 Fehler beim Aktualisieren des Termins in Notion. Bitte versuche es erneut."
            )
    
    @handle_bot_error(ErrorType.NOTION_API, ErrorSeverity.HIGH)
    async def delete_appointment(self, page_id: str) -> bool:
        """
        Delete an appointment from Notion (archive it).
        
        Args:
            page_id: Notion page ID
            
        Returns:
            bool: True if successful
        """
        try:
            self.client.pages.update(
                page_id=page_id,
                archived=True
            )
            
            logger.info(f"Deleted appointment in Notion: {page_id}")
            return True
            
        except APIResponseError as e:
            logger.error(f"Failed to delete appointment in Notion: {e}")
            raise BotError(
                f"Failed to delete appointment in Notion: {str(e)}",
                ErrorType.NOTION_API,
                ErrorSeverity.HIGH,
                user_message="📝 Fehler beim Löschen des Termins in Notion. Bitte versuche es erneut."
            )
    
    def find_appointment_by_outlook_id(self, outlook_id: str) -> Optional[str]:
        """
        Find an appointment by its Outlook ID.
        
        Args:
            outlook_id: The Outlook ID to search for
        
        Returns:
            Page ID if found, None otherwise
        """
        try:
            # Query the database for the specific OutlookID
            response = self.client.databases.query(
                database_id=self.database_id,
                filter={
                    "property": "OutlookID",
                    "rich_text": {
                        "equals": outlook_id
                    }
                }
            )
            
            if response['results']:
                page_id = response['results'][0]['id']
                logger.info(f"Found appointment with OutlookID {outlook_id}: {page_id}")
                return page_id
            
            logger.debug(f"No appointment found with OutlookID: {outlook_id}")
            return None
            
        except APIResponseError as e:
            logger.error(f"Failed to search by OutlookID: {e}")
            return None
    
    def delete_appointment_by_outlook_id(self, outlook_id: str) -> bool:
        """
        Delete an appointment by its Outlook ID.
        
        Args:
            outlook_id: The Outlook ID of the appointment to delete
        
        Returns:
            bool: True if deleted successfully, False otherwise
        """
        try:
            page_id = self.find_appointment_by_outlook_id(outlook_id)
            if page_id:
                return self.delete_appointment(page_id)
            
            logger.warning(f"No appointment found to delete with OutlookID: {outlook_id}")
            return False
            
        except Exception as e:
            logger.error(f"Error deleting by OutlookID: {e}")
            return False
    
    async def test_connection(self) -> bool:
        """
        Test connection to Notion API and database.
        
        Returns:
            bool: True if connection is successful
        """
        try:
            # Test database access
            response = self.client.databases.retrieve(database_id=self.database_id)
            
            logger.info("Notion connection test successful")
            return True
            
        except APIResponseError as e:
            logger.error(f"Notion connection test failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during connection test: {e}")
            return False