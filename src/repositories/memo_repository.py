"""Repository implementation for Memo entities."""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from notion_client import Client
from notion_client.errors import APIResponseError

from src.repositories.base_repository import BaseRepository, PaginationParams, PaginatedResult
from src.models.memo import Memo
from src.utils.error_handler import BotError, ErrorType, ErrorSeverity


logger = logging.getLogger(__name__)


class MemoRepository(BaseRepository[Memo]):
    """
    Repository for managing memo data in Notion.
    
    Handles data access for memo/note entities with proper error handling.
    """
    
    def __init__(self, notion_client: Client, database_id: str):
        """
        Initialize MemoRepository.
        
        Args:
            notion_client: Initialized Notion client
            database_id: Notion database ID for memos
        """
        self.client = notion_client
        self.database_id = database_id
        self._cache: Dict[str, Memo] = {}
        self._cache_ttl = 300  # 5 minutes cache TTL
        self._cache_timestamps: Dict[str, datetime] = {}
    
    async def create(self, memo: Memo) -> str:
        """Create a new memo in Notion database."""
        try:
            properties = {
                "Title": {
                    "title": [
                        {
                            "text": {
                                "content": memo.title or "Untitled Memo"
                            }
                        }
                    ]
                },
                "Content": {
                    "rich_text": [
                        {
                            "text": {
                                "content": memo.content or ""
                            }
                        }
                    ]
                }
            }
            
            # Add tags if present
            if memo.tags:
                properties["Tags"] = {
                    "multi_select": [{"name": tag} for tag in memo.tags]
                }
            
            # Add created date
            if memo.created_at:
                properties["Created"] = {
                    "date": {
                        "start": memo.created_at.isoformat()
                    }
                }
            
            response = self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties
            )
            
            page_id = response["id"]
            logger.info(f"Created memo in Notion: {page_id}")
            
            # Update memo with ID and cache it
            memo.notion_id = page_id
            self._update_cache(page_id, memo)
            
            return page_id
            
        except APIResponseError as e:
            logger.error(f"Failed to create memo in Notion: {e}")
            raise BotError(
                f"Failed to create memo in Notion: {str(e)}",
                ErrorType.NOTION_API,
                ErrorSeverity.HIGH,
                user_message="📝 Fehler beim Erstellen der Notiz in Notion. Bitte versuche es erneut."
            )
    
    async def get_by_id(self, entity_id: str) -> Optional[Memo]:
        """Get memo by Notion page ID."""
        # Check cache first
        cached = self._get_from_cache(entity_id)
        if cached:
            return cached
        
        try:
            response = self.client.pages.retrieve(page_id=entity_id)
            memo = self._parse_notion_page_to_memo(response)
            
            # Update cache
            self._update_cache(entity_id, memo)
            
            return memo
            
        except APIResponseError as e:
            if e.code == "object_not_found":
                return None
            logger.error(f"Failed to retrieve memo: {e}")
            raise BotError(
                f"Failed to retrieve memo: {str(e)}",
                ErrorType.NOTION_API,
                ErrorSeverity.MEDIUM
            )
    
    async def get_all(self, pagination: Optional[PaginationParams] = None) -> PaginatedResult[Memo]:
        """Get all memos with pagination."""
        if pagination is None:
            pagination = PaginationParams()
        
        try:
            query_params = {
                "database_id": self.database_id,
                "page_size": pagination.page_size,
                "sorts": [{"property": "Created", "direction": "descending"}]
            }
            
            if pagination.start_cursor:
                query_params["start_cursor"] = pagination.start_cursor
            
            response = self.client.databases.query(**query_params)
            
            memos = []
            for page in response["results"]:
                try:
                    memo = self._parse_notion_page_to_memo(page)
                    memos.append(memo)
                    # Cache each memo
                    self._update_cache(page["id"], memo)
                except Exception as e:
                    logger.warning(f"Failed to parse memo page {page.get('id')}: {e}")
            
            return PaginatedResult(
                items=memos,
                has_more=response.get("has_more", False),
                next_cursor=response.get("next_cursor")
            )
            
        except APIResponseError as e:
            logger.error(f"Failed to query memos: {e}")
            raise BotError(
                f"Failed to query memos: {str(e)}",
                ErrorType.NOTION_API,
                ErrorSeverity.MEDIUM
            )
    
    async def update(self, entity_id: str, memo: Memo) -> bool:
        """Update an existing memo."""
        try:
            properties = {
                "Title": {
                    "title": [
                        {
                            "text": {
                                "content": memo.title or "Untitled Memo"
                            }
                        }
                    ]
                },
                "Content": {
                    "rich_text": [
                        {
                            "text": {
                                "content": memo.content or ""
                            }
                        }
                    ]
                }
            }
            
            # Update tags if present
            if memo.tags:
                properties["Tags"] = {
                    "multi_select": [{"name": tag} for tag in memo.tags]
                }
            
            self.client.pages.update(
                page_id=entity_id,
                properties=properties
            )
            
            # Update cache
            memo.notion_id = entity_id
            self._update_cache(entity_id, memo)
            
            logger.info(f"Updated memo: {entity_id}")
            return True
            
        except APIResponseError as e:
            logger.error(f"Failed to update memo: {e}")
            if e.code == "object_not_found":
                return False
            raise BotError(
                f"Failed to update memo: {str(e)}",
                ErrorType.NOTION_API,
                ErrorSeverity.MEDIUM
            )
    
    async def delete(self, entity_id: str) -> bool:
        """Archive a memo (Notion doesn't support hard delete)."""
        try:
            self.client.pages.update(
                page_id=entity_id,
                archived=True
            )
            
            # Remove from cache
            self._invalidate_cache(entity_id)
            
            logger.info(f"Archived memo: {entity_id}")
            return True
            
        except APIResponseError as e:
            logger.error(f"Failed to archive memo: {e}")
            if e.code == "object_not_found":
                return False
            raise BotError(
                f"Failed to archive memo: {str(e)}",
                ErrorType.NOTION_API,
                ErrorSeverity.MEDIUM
            )
    
    async def find_by_criteria(self, criteria: Dict[str, Any], 
                             pagination: Optional[PaginationParams] = None) -> PaginatedResult[Memo]:
        """Find memos by criteria."""
        if pagination is None:
            pagination = PaginationParams()
        
        filter_conditions = []
        
        # Build filters based on criteria
        if "title_contains" in criteria:
            filter_conditions.append({
                "property": "Title",
                "title": {
                    "contains": criteria["title_contains"]
                }
            })
        
        if "content_contains" in criteria:
            filter_conditions.append({
                "property": "Content",
                "rich_text": {
                    "contains": criteria["content_contains"]
                }
            })
        
        if "tags" in criteria and isinstance(criteria["tags"], list):
            tag_filters = []
            for tag in criteria["tags"]:
                tag_filters.append({
                    "property": "Tags",
                    "multi_select": {
                        "contains": tag
                    }
                })
            if tag_filters:
                filter_conditions.extend(tag_filters)
        
        if "created_after" in criteria:
            filter_conditions.append({
                "property": "Created",
                "date": {
                    "after": criteria["created_after"].isoformat()
                }
            })
        
        # Build query
        query_params = {
            "database_id": self.database_id,
            "page_size": pagination.page_size,
            "sorts": [{"property": "Created", "direction": "descending"}]
        }
        
        if filter_conditions:
            if len(filter_conditions) == 1:
                query_params["filter"] = filter_conditions[0]
            else:
                query_params["filter"] = {
                    "and": filter_conditions
                }
        
        if pagination.start_cursor:
            query_params["start_cursor"] = pagination.start_cursor
        
        try:
            response = self.client.databases.query(**query_params)
            
            memos = []
            for page in response["results"]:
                try:
                    memo = self._parse_notion_page_to_memo(page)
                    memos.append(memo)
                    self._update_cache(page["id"], memo)
                except Exception as e:
                    logger.warning(f"Failed to parse memo page {page.get('id')}: {e}")
            
            return PaginatedResult(
                items=memos,
                has_more=response.get("has_more", False),
                next_cursor=response.get("next_cursor")
            )
            
        except APIResponseError as e:
            logger.error(f"Failed to query memos with criteria: {e}")
            raise BotError(
                f"Failed to query memos: {str(e)}",
                ErrorType.NOTION_API,
                ErrorSeverity.MEDIUM
            )
    
    async def exists(self, entity_id: str) -> bool:
        """Check if memo exists."""
        try:
            await self.get_by_id(entity_id)
            return True
        except:
            return False
    
    async def search_memos(self, search_term: str, limit: int = 10) -> List[Memo]:
        """Search memos by title or content."""
        criteria = {
            "title_contains": search_term
        }
        
        # First search by title
        result = await self.find_by_criteria(criteria, PaginationParams(page_size=limit))
        memos = result.items
        
        # If not enough results, also search by content
        if len(memos) < limit:
            criteria = {
                "content_contains": search_term
            }
            content_result = await self.find_by_criteria(
                criteria, 
                PaginationParams(page_size=limit - len(memos))
            )
            
            # Add unique memos from content search
            existing_ids = {m.notion_id for m in memos}
            for memo in content_result.items:
                if memo.notion_id not in existing_ids:
                    memos.append(memo)
        
        return memos[:limit]
    
    async def get_recent_memos(self, limit: int = 10) -> List[Memo]:
        """Get most recent memos."""
        result = await self.get_all(PaginationParams(page_size=limit))
        return result.items
    
    def _parse_notion_page_to_memo(self, page: Dict[str, Any]) -> Memo:
        """Parse Notion page response to Memo object."""
        properties = page.get("properties", {})
        
        # Extract title
        title = ""
        title_prop = properties.get("Title", {}).get("title", [])
        if title_prop:
            title = title_prop[0].get("text", {}).get("content", "")
        
        # Extract content
        content = ""
        content_prop = properties.get("Content", {}).get("rich_text", [])
        if content_prop:
            content = content_prop[0].get("text", {}).get("content", "")
        
        # Extract tags
        tags = []
        tags_prop = properties.get("Tags", {}).get("multi_select", [])
        for tag in tags_prop:
            tags.append(tag.get("name", ""))
        
        # Extract created date
        created_at = None
        created_prop = properties.get("Created", {}).get("date", {})
        if created_prop and created_prop.get("start"):
            try:
                created_at = datetime.fromisoformat(
                    created_prop["start"].replace("Z", "+00:00")
                )
            except:
                pass
        
        return Memo(
            notion_id=page["id"],
            title=title,
            content=content,
            tags=tags,
            created_at=created_at or datetime.now()
        )
    
    def _get_from_cache(self, entity_id: str) -> Optional[Memo]:
        """Get memo from cache if not expired."""
        if entity_id not in self._cache:
            return None
        
        # Check if cache entry is expired
        timestamp = self._cache_timestamps.get(entity_id)
        if timestamp and (datetime.now() - timestamp).seconds > self._cache_ttl:
            self._invalidate_cache(entity_id)
            return None
        
        return self._cache.get(entity_id)
    
    def _update_cache(self, entity_id: str, memo: Memo):
        """Update cache with memo."""
        self._cache[entity_id] = memo
        self._cache_timestamps[entity_id] = datetime.now()
    
    def _invalidate_cache(self, entity_id: str):
        """Remove memo from cache."""
        self._cache.pop(entity_id, None)
        self._cache_timestamps.pop(entity_id, None)
    
    def clear_cache(self):
        """Clear all cached memos."""
        self._cache.clear()
        self._cache_timestamps.clear()