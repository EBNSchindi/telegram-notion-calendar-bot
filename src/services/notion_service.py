import logging
from typing import List, Optional
from notion_client import Client
from notion_client.errors import APIResponseError
from src.models.appointment import Appointment
from config.settings import Settings

logger = logging.getLogger(__name__)


class NotionService:
    """Service for interacting with Notion API."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = Client(auth=settings.notion_api_key)
        self.database_id = settings.notion_database_id
    
    async def create_appointment(self, appointment: Appointment) -> str:
        """
        Create a new appointment in Notion database.
        
        Args:
            appointment: Appointment object to create
            
        Returns:
            str: Notion page ID of created appointment
            
        Raises:
            APIResponseError: If Notion API request fails
        """
        try:
            properties = appointment.to_notion_properties(self.settings.timezone)
            
            response = self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties
            )
            
            page_id = response["id"]
            logger.info(f"Created appointment in Notion: {page_id}")
            
            return page_id
            
        except APIResponseError as e:
            logger.error(f"Failed to create appointment in Notion: {e}")
            raise
    
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
            raise
    
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
            properties = appointment.to_notion_properties(self.settings.timezone)
            
            self.client.pages.update(
                page_id=page_id,
                properties=properties
            )
            
            logger.info(f"Updated appointment in Notion: {page_id}")
            return True
            
        except APIResponseError as e:
            logger.error(f"Failed to update appointment in Notion: {e}")
            raise
    
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
            raise
    
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