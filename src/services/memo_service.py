import logging
from typing import List, Optional
from notion_client import Client
from notion_client.errors import APIResponseError
from src.models.memo import Memo
from config.user_config import UserConfig
from src.utils.error_handler import BotError, ErrorType, ErrorSeverity, handle_bot_error

logger = logging.getLogger(__name__)


class MemoService:
    """Service for interacting with Notion API for memos/tasks."""
    
    def __init__(self, notion_api_key: str, memo_database_id: str):
        """
        Initialize MemoService with API key and database ID.
        
        Args:
            notion_api_key: Notion API key
            memo_database_id: Notion memo database ID
        """
        if not notion_api_key or not memo_database_id:
            raise BotError(
                "notion_api_key and memo_database_id are required",
                ErrorType.VALIDATION,
                ErrorSeverity.HIGH
            )
        
        self.client = Client(auth=notion_api_key)
        self.database_id = memo_database_id
    
    @classmethod
    def from_user_config(cls, user_config: UserConfig) -> 'MemoService':
        """Create MemoService from UserConfig."""
        if not user_config.memo_database_id:
            raise BotError(
                "User config missing memo_database_id",
                ErrorType.VALIDATION,
                ErrorSeverity.HIGH,
                user_message="📝 Memo-Datenbank ist nicht konfiguriert. Bitte wende dich an den Administrator."
            )
        
        return cls(
            notion_api_key=user_config.notion_api_key,
            memo_database_id=user_config.memo_database_id
        )
    
    @handle_bot_error(ErrorType.NOTION_API, ErrorSeverity.HIGH)
    async def create_memo(self, memo: Memo) -> str:
        """
        Create a new memo in Notion database.
        
        Args:
            memo: Memo object to create
            
        Returns:
            str: Notion page ID of created memo
            
        Raises:
            BotError: If Notion API request fails
        """
        try:
            properties = memo.to_notion_properties('Europe/Berlin')
            
            response = self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties
            )
            
            page_id = response["id"]
            logger.info(f"Created memo in Notion: {page_id}")
            
            return page_id
            
        except APIResponseError as e:
            logger.error(f"Failed to create memo in Notion: {e}")
            raise BotError(
                f"Failed to create memo in Notion: {str(e)}",
                ErrorType.NOTION_API,
                ErrorSeverity.HIGH,
                user_message="📝 Fehler beim Erstellen des Memos in Notion. Bitte versuche es erneut."
            )
    
    @handle_bot_error(ErrorType.NOTION_API, ErrorSeverity.MEDIUM)
    async def get_recent_memos(self, limit: int = 10) -> List[Memo]:
        """
        Get recent memos from Notion database, sorted by creation date (newest first).
        
        Args:
            limit: Maximum number of memos to retrieve (default: 10)
            
        Returns:
            List[Memo]: List of recent memos
        """
        try:
            response = self.client.databases.query(
                database_id=self.database_id,
                sorts=[
                    {
                        "timestamp": "created_time",
                        "direction": "descending"
                    }
                ],
                page_size=limit
            )
            
            memos = []
            for page in response["results"]:
                try:
                    memo = Memo.from_notion_page(page)
                    memos.append(memo)
                except Exception as e:
                    logger.warning(f"Failed to parse memo from page {page['id']}: {e}")
                    continue
            
            logger.info(f"Retrieved {len(memos)} recent memos from Notion")
            return memos
            
        except APIResponseError as e:
            logger.error(f"Failed to retrieve memos from Notion: {e}")
            raise BotError(
                f"Failed to retrieve memos from Notion: {str(e)}",
                ErrorType.NOTION_API,
                ErrorSeverity.MEDIUM,
                user_message="📝 Fehler beim Laden der Memos aus Notion. Bitte versuche es später erneut."
            )
    
    @handle_bot_error(ErrorType.NOTION_API, ErrorSeverity.MEDIUM)
    async def get_memos_by_status(self, status: str, limit: int = 20) -> List[Memo]:
        """
        Get memos filtered by status.
        
        Args:
            status: Status to filter by ("Nicht begonnen", "In Arbeit", "Erledigt")
            limit: Maximum number of memos to retrieve
            
        Returns:
            List[Memo]: List of memos with specified status
        """
        try:
            response = self.client.databases.query(
                database_id=self.database_id,
                filter={
                    "property": "Status",
                    "status": {
                        "equals": status
                    }
                },
                sorts=[
                    {
                        "timestamp": "created_time",
                        "direction": "descending"
                    }
                ],
                page_size=limit
            )
            
            memos = []
            for page in response["results"]:
                try:
                    memo = Memo.from_notion_page(page)
                    memos.append(memo)
                except Exception as e:
                    logger.warning(f"Failed to parse memo from page {page['id']}: {e}")
                    continue
            
            logger.info(f"Retrieved {len(memos)} memos with status '{status}' from Notion")
            return memos
            
        except APIResponseError as e:
            logger.error(f"Failed to retrieve memos by status from Notion: {e}")
            raise BotError(
                f"Failed to retrieve memos by status from Notion: {str(e)}",
                ErrorType.NOTION_API,
                ErrorSeverity.MEDIUM,
                user_message="📝 Fehler beim Filtern der Memos. Bitte versuche es später erneut."
            )
    
    @handle_bot_error(ErrorType.NOTION_API, ErrorSeverity.HIGH)
    async def update_memo(self, page_id: str, memo: Memo) -> bool:
        """
        Update an existing memo in Notion.
        
        Args:
            page_id: Notion page ID
            memo: Updated memo data
            
        Returns:
            bool: True if successful
        """
        try:
            properties = memo.to_notion_properties('Europe/Berlin')
            
            response = self.client.pages.update(
                page_id=page_id,
                properties=properties
            )
            
            logger.info(f"Updated memo in Notion: {page_id}")
            return True
            
        except APIResponseError as e:
            logger.error(f"Failed to update memo in Notion: {e}")
            raise BotError(
                f"Failed to update memo in Notion: {str(e)}",
                ErrorType.NOTION_API,
                ErrorSeverity.HIGH,
                user_message="📝 Fehler beim Aktualisieren des Memos. Bitte versuche es erneut."
            )
    
    @handle_bot_error(ErrorType.NOTION_API, ErrorSeverity.MEDIUM)
    async def update_memo_status(self, page_id: str, status: str) -> bool:
        """
        Update only the status of a memo.
        
        Args:
            page_id: Notion page ID
            status: New status ("Nicht begonnen", "In Arbeit", "Erledigt")
            
        Returns:
            bool: True if successful
        """
        try:
            properties = {
                "Status": {
                    "status": {
                        "name": status
                    }
                }
            }
            
            response = self.client.pages.update(
                page_id=page_id,
                properties=properties
            )
            
            logger.info(f"Updated memo status to '{status}' in Notion: {page_id}")
            return True
            
        except APIResponseError as e:
            logger.error(f"Failed to update memo status in Notion: {e}")
            raise BotError(
                f"Failed to update memo status in Notion: {str(e)}",
                ErrorType.NOTION_API,
                ErrorSeverity.MEDIUM,
                user_message="📝 Fehler beim Aktualisieren des Memo-Status. Bitte versuche es erneut."
            )
    
    @handle_bot_error(ErrorType.NOTION_API, ErrorSeverity.HIGH)
    async def delete_memo(self, page_id: str) -> bool:
        """
        Archive (delete) a memo in Notion.
        
        Args:
            page_id: Notion page ID
            
        Returns:
            bool: True if successful
        """
        try:
            response = self.client.pages.update(
                page_id=page_id,
                archived=True
            )
            
            logger.info(f"Archived memo in Notion: {page_id}")
            return True
            
        except APIResponseError as e:
            logger.error(f"Failed to archive memo in Notion: {e}")
            raise BotError(
                f"Failed to archive memo in Notion: {str(e)}",
                ErrorType.NOTION_API,
                ErrorSeverity.HIGH,
                user_message="📝 Fehler beim Löschen des Memos. Bitte versuche es erneut."
            )
    
    async def test_connection(self) -> bool:
        """
        Test connection to the memo database.
        
        Returns:
            bool: True if connection successful
        """
        try:
            response = self.client.databases.retrieve(database_id=self.database_id)
            logger.info("Successfully connected to memo database")
            return True
        except APIResponseError as e:
            logger.error(f"Failed to connect to memo database: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error testing memo database connection: {e}")
            return False