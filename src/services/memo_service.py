import logging
from typing import List, Optional
from notion_client import Client
from notion_client.errors import APIResponseError
from src.models.memo import Memo
from config.user_config import UserConfig
from src.utils.error_handler import BotError, ErrorType, ErrorSeverity, handle_bot_error
from src.utils.security import InputSanitizer

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
        
        # Validate Notion IDs to prevent injection
        try:
            self.database_id = InputSanitizer.validate_notion_id(memo_database_id)
        except ValueError as e:
            raise BotError(
                str(e),
                ErrorType.VALIDATION,
                ErrorSeverity.HIGH
            )
        
        self.client = Client(auth=notion_api_key)
    
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
            # Sanitize memo content before sending to Notion
            sanitized_memo = Memo(
                aufgabe=InputSanitizer.sanitize_for_notion(memo.aufgabe),
                status=memo.status,  # Status is validated by model
                faelligkeitsdatum=memo.faelligkeitsdatum,
                bereich=InputSanitizer.sanitize_for_notion(memo.bereich) if memo.bereich else None,
                projekt=InputSanitizer.sanitize_for_notion(memo.projekt) if memo.projekt else None,
                notizen=InputSanitizer.sanitize_for_notion(memo.notizen) if memo.notizen else None
            )
            
            properties = sanitized_memo.to_notion_properties('Europe/Berlin')
            
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
    async def get_recent_memos(self, limit: int = 10, only_open: bool = True) -> List[Memo]:
        """
        Get recent memos from Notion database, sorted by creation date (newest first).
        
        Args:
            limit: Maximum number of memos to retrieve (default: 10)
            only_open: If True, only return non-completed memos (default: True)
            
        Returns:
            List[Memo]: List of recent memos
        """
        try:
            # Build filter for open memos if requested
            filter_dict = None
            if only_open:
                filter_dict = {
                    "or": [
                        {
                            "property": "Status",
                            "status": {
                                "equals": "Nicht begonnen"
                            }
                        },
                        {
                            "property": "Status", 
                            "status": {
                                "equals": "In Arbeit"
                            }
                        }
                    ]
                }
            
            query_params = {
                "database_id": self.database_id,
                "sorts": [
                    {
                        "timestamp": "created_time",
                        "direction": "descending"
                    }
                ],
                "page_size": limit
            }
            
            if filter_dict:
                query_params["filter"] = filter_dict
                
            response = self.client.databases.query(**query_params)
            
            # Defensive programming: handle corrupted API responses
            if not response:
                logger.error("Received null response from Notion API")
                raise BotError(
                    "Received invalid response from Notion API",
                    ErrorType.NOTION_API,
                    ErrorSeverity.MEDIUM,
                    user_message="📝 Fehler beim Laden der Memos. Ungültige API-Antwort."
                )
            
            if not isinstance(response, dict):
                logger.error(f"Response is not a dictionary: {type(response)}")
                raise BotError(
                    f"Invalid response format from Notion API: {type(response)}",
                    ErrorType.NOTION_API,
                    ErrorSeverity.MEDIUM,
                    user_message="📝 Fehler beim Laden der Memos. Ungültiges Antwortformat."
                )
            
            # Handle missing or malformed 'results' key
            results = response.get("results")
            if results is None:
                logger.error("Response missing 'results' key")
                raise BotError(
                    "Response missing 'results' key",
                    ErrorType.NOTION_API,
                    ErrorSeverity.MEDIUM,
                    user_message="📝 Fehler beim Laden der Memos. Unvollständige API-Antwort."
                )
            
            if not isinstance(results, list):
                logger.error(f"Results is not a list: {type(results)}")
                raise BotError(
                    f"Invalid results format from Notion API: {type(results)}",
                    ErrorType.NOTION_API,
                    ErrorSeverity.MEDIUM,
                    user_message="📝 Fehler beim Laden der Memos. Ungültiges Ergebnisformat."
                )
            
            memos = []
            corrupted_pages = 0
            
            for i, page in enumerate(results):
                try:
                    # Validate page structure
                    if not isinstance(page, dict):
                        logger.warning(f"Page {i} is not a dictionary: {type(page)}")
                        corrupted_pages += 1
                        continue
                    
                    if 'id' not in page:
                        logger.warning(f"Page {i} missing 'id' field")
                        corrupted_pages += 1
                        continue
                    
                    if 'properties' not in page:
                        logger.warning(f"Page {page.get('id', 'unknown')} missing 'properties' field")
                        corrupted_pages += 1
                        continue
                    
                    if not isinstance(page['properties'], dict):
                        logger.warning(f"Page {page['id']} has invalid properties type: {type(page['properties'])}")
                        corrupted_pages += 1
                        continue
                    
                    memo = Memo.from_notion_page(page)
                    memos.append(memo)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse memo from page {page.get('id', 'unknown')}: {e}")
                    corrupted_pages += 1
                    continue
            
            # Log corrupted pages for monitoring
            if corrupted_pages > 0:
                logger.warning(f"Encountered {corrupted_pages} corrupted pages out of {len(results)} total pages")
            
            logger.info(f"Retrieved {len(memos)} recent memos from Notion ({corrupted_pages} pages skipped)")
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
            
            # Defensive programming: handle corrupted API responses
            if not response:
                logger.error("Received null response from Notion API for status filter")
                raise BotError(
                    "Received invalid response from Notion API",
                    ErrorType.NOTION_API,
                    ErrorSeverity.MEDIUM,
                    user_message="📝 Fehler beim Filtern der Memos. Ungültige API-Antwort."
                )
            
            if not isinstance(response, dict):
                logger.error(f"Response is not a dictionary for status filter: {type(response)}")
                raise BotError(
                    f"Invalid response format from Notion API: {type(response)}",
                    ErrorType.NOTION_API,
                    ErrorSeverity.MEDIUM,
                    user_message="📝 Fehler beim Filtern der Memos. Ungültiges Antwortformat."
                )
            
            # Handle missing or malformed 'results' key
            results = response.get("results")
            if results is None:
                logger.error("Response missing 'results' key for status filter")
                raise BotError(
                    "Response missing 'results' key",
                    ErrorType.NOTION_API,
                    ErrorSeverity.MEDIUM,
                    user_message="📝 Fehler beim Filtern der Memos. Unvollständige API-Antwort."
                )
            
            if not isinstance(results, list):
                logger.error(f"Results is not a list for status filter: {type(results)}")
                raise BotError(
                    f"Invalid results format from Notion API: {type(results)}",
                    ErrorType.NOTION_API,
                    ErrorSeverity.MEDIUM,
                    user_message="📝 Fehler beim Filtern der Memos. Ungültiges Ergebnisformat."
                )
            
            memos = []
            corrupted_pages = 0
            
            for i, page in enumerate(results):
                try:
                    # Validate page structure
                    if not isinstance(page, dict):
                        logger.warning(f"Page {i} is not a dictionary: {type(page)}")
                        corrupted_pages += 1
                        continue
                    
                    if 'id' not in page:
                        logger.warning(f"Page {i} missing 'id' field")
                        corrupted_pages += 1
                        continue
                    
                    if 'properties' not in page:
                        logger.warning(f"Page {page.get('id', 'unknown')} missing 'properties' field")
                        corrupted_pages += 1
                        continue
                    
                    if not isinstance(page['properties'], dict):
                        logger.warning(f"Page {page['id']} has invalid properties type: {type(page['properties'])}")
                        corrupted_pages += 1
                        continue
                    
                    memo = Memo.from_notion_page(page)
                    memos.append(memo)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse memo from page {page.get('id', 'unknown')}: {e}")
                    corrupted_pages += 1
                    continue
            
            # Log corrupted pages for monitoring
            if corrupted_pages > 0:
                logger.warning(f"Encountered {corrupted_pages} corrupted pages out of {len(results)} total pages for status '{status}'")
            
            logger.info(f"Retrieved {len(memos)} memos with status '{status}' from Notion ({corrupted_pages} pages skipped)")
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