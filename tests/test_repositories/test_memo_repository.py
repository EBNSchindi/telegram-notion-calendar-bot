"""Unit tests for MemoRepository."""
import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime
from notion_client.errors import APIResponseError

from src.repositories.memo_repository import MemoRepository
from src.models.memo import Memo
from src.repositories.base_repository import PaginationParams
from src.utils.error_handler import BotError, ErrorType, ErrorSeverity


@pytest.fixture
def mock_notion_client():
    """Create a mock Notion client."""
    client = Mock()
    client.pages = Mock()
    client.databases = Mock()
    return client


@pytest.fixture
def repository(mock_notion_client):
    """Create a MemoRepository instance."""
    return MemoRepository(
        notion_client=mock_notion_client,
        database_id="test-memo-database-id"
    )


@pytest.fixture
def sample_memo():
    """Create a sample memo."""
    return Memo(
        title="Test Memo",
        content="This is a test memo content",
        tags=["test", "sample"],
        created_at=datetime.now()
    )


@pytest.fixture
def notion_memo_response():
    """Create a sample Notion page response for memo."""
    return {
        "id": "memo-123",
        "properties": {
            "Title": {
                "title": [
                    {
                        "text": {
                            "content": "Test Memo"
                        }
                    }
                ]
            },
            "Content": {
                "rich_text": [
                    {
                        "text": {
                            "content": "This is a test memo content"
                        }
                    }
                ]
            },
            "Tags": {
                "multi_select": [
                    {"name": "test"},
                    {"name": "sample"}
                ]
            },
            "Created": {
                "date": {
                    "start": "2024-01-15T10:00:00.000Z"
                }
            }
        }
    }


class TestMemoRepository:
    """Test cases for MemoRepository."""
    
    @pytest.mark.asyncio
    async def test_create_memo_success(self, repository, mock_notion_client, sample_memo):
        """Test successful memo creation."""
        mock_notion_client.pages.create.return_value = {"id": "new-memo-id"}
        
        result = await repository.create(sample_memo)
        
        assert result == "new-memo-id"
        assert sample_memo.notion_id == "new-memo-id"
        mock_notion_client.pages.create.assert_called_once()
        
        # Verify the memo was cached
        cached = repository._get_from_cache("new-memo-id")
        assert cached == sample_memo
    
    @pytest.mark.asyncio
    async def test_create_memo_api_error(self, repository, mock_notion_client, sample_memo):
        """Test memo creation with API error."""
        mock_notion_client.pages.create.side_effect = APIResponseError(
            {"code": "invalid_request", "message": "Invalid request"},
            400,
            "Invalid request",
            {}
        )
        
        with pytest.raises(BotError) as exc_info:
            await repository.create(sample_memo)
        
        assert exc_info.value.error_type == ErrorType.NOTION_API
        assert exc_info.value.severity == ErrorSeverity.HIGH
    
    @pytest.mark.asyncio
    async def test_get_by_id_success(self, repository, mock_notion_client, notion_memo_response):
        """Test successful memo retrieval by ID."""
        mock_notion_client.pages.retrieve.return_value = notion_memo_response
        
        result = await repository.get_by_id("memo-123")
        
        assert result is not None
        assert result.notion_id == "memo-123"
        assert result.title == "Test Memo"
        assert result.content == "This is a test memo content"
        assert result.tags == ["test", "sample"]
        
        # Verify caching
        cached = repository._get_from_cache("memo-123")
        assert cached.notion_id == result.notion_id
    
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repository, mock_notion_client):
        """Test memo retrieval when not found."""
        mock_notion_client.pages.retrieve.side_effect = APIResponseError(
            {"code": "object_not_found", "message": "Not found"},
            404,
            "Not found",
            {}
        )
        
        result = await repository.get_by_id("non-existent")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_all_with_pagination(self, repository, mock_notion_client, notion_memo_response):
        """Test getting all memos with pagination."""
        mock_notion_client.databases.query.return_value = {
            "results": [notion_memo_response],
            "has_more": True,
            "next_cursor": "next-cursor-456"
        }
        
        pagination = PaginationParams(page_size=5)
        result = await repository.get_all(pagination)
        
        assert len(result.items) == 1
        assert result.has_more is True
        assert result.next_cursor == "next-cursor-456"
        
        mock_notion_client.databases.query.assert_called_once_with(
            database_id="test-memo-database-id",
            page_size=5,
            sorts=[{"property": "Created", "direction": "descending"}]
        )
    
    @pytest.mark.asyncio
    async def test_update_memo_success(self, repository, mock_notion_client, sample_memo):
        """Test successful memo update."""
        mock_notion_client.pages.update.return_value = {"id": "memo-123"}
        
        result = await repository.update("memo-123", sample_memo)
        
        assert result is True
        assert sample_memo.notion_id == "memo-123"
        mock_notion_client.pages.update.assert_called_once()
        
        # Verify cache update
        cached = repository._get_from_cache("memo-123")
        assert cached == sample_memo
    
    @pytest.mark.asyncio
    async def test_delete_memo_success(self, repository, mock_notion_client):
        """Test successful memo deletion (archiving)."""
        # First cache a memo
        repository._update_cache("memo-123", Mock())
        
        mock_notion_client.pages.update.return_value = {"id": "memo-123", "archived": True}
        
        result = await repository.delete("memo-123")
        
        assert result is True
        mock_notion_client.pages.update.assert_called_once_with(
            page_id="memo-123",
            archived=True
        )
        
        # Verify cache invalidation
        cached = repository._get_from_cache("memo-123")
        assert cached is None
    
    @pytest.mark.asyncio
    async def test_find_by_criteria_with_filters(self, repository, mock_notion_client, notion_memo_response):
        """Test finding memos by criteria."""
        mock_notion_client.databases.query.return_value = {
            "results": [notion_memo_response],
            "has_more": False
        }
        
        criteria = {
            "title_contains": "Test",
            "tags": ["test", "sample"],
            "created_after": datetime.now()
        }
        
        result = await repository.find_by_criteria(criteria)
        
        assert len(result.items) == 1
        
        # Verify the filter was built correctly
        call_args = mock_notion_client.databases.query.call_args[1]
        assert "filter" in call_args
        assert "and" in call_args["filter"]
    
    @pytest.mark.asyncio
    async def test_search_memos(self, repository, mock_notion_client, notion_memo_response):
        """Test searching memos by title and content."""
        # First search by title
        mock_notion_client.databases.query.return_value = {
            "results": [notion_memo_response],
            "has_more": False
        }
        
        result = await repository.search_memos("Test", limit=5)
        
        assert len(result) == 1
        assert result[0].title == "Test Memo"
        
        # Verify both title and content searches were attempted if needed
        assert mock_notion_client.databases.query.called
    
    @pytest.mark.asyncio
    async def test_get_recent_memos(self, repository, mock_notion_client, notion_memo_response):
        """Test getting recent memos."""
        mock_notion_client.databases.query.return_value = {
            "results": [notion_memo_response, notion_memo_response],
            "has_more": False
        }
        
        result = await repository.get_recent_memos(limit=10)
        
        assert len(result) == 2
        
        # Verify sort order
        call_args = mock_notion_client.databases.query.call_args[1]
        assert call_args["sorts"][0]["direction"] == "descending"
    
    def test_parse_notion_page_to_memo(self, repository, notion_memo_response):
        """Test parsing Notion page response to Memo object."""
        memo = repository._parse_notion_page_to_memo(notion_memo_response)
        
        assert memo.notion_id == "memo-123"
        assert memo.title == "Test Memo"
        assert memo.content == "This is a test memo content"
        assert memo.tags == ["test", "sample"]
        assert isinstance(memo.created_at, datetime)
    
    def test_parse_notion_page_with_missing_fields(self, repository):
        """Test parsing Notion page with missing fields."""
        minimal_response = {
            "id": "memo-minimal",
            "properties": {}
        }
        
        memo = repository._parse_notion_page_to_memo(minimal_response)
        
        assert memo.notion_id == "memo-minimal"
        assert memo.title == ""
        assert memo.content == ""
        assert memo.tags == []
        assert isinstance(memo.created_at, datetime)
    
    def test_cache_operations(self, repository, sample_memo):
        """Test cache operations."""
        # Test cache update
        repository._update_cache("test-id", sample_memo)
        cached = repository._get_from_cache("test-id")
        assert cached == sample_memo
        
        # Test cache invalidation
        repository._invalidate_cache("test-id")
        cached = repository._get_from_cache("test-id")
        assert cached is None
        
        # Test clear cache
        repository._update_cache("id1", sample_memo)
        repository._update_cache("id2", sample_memo)
        repository.clear_cache()
        
        assert repository._get_from_cache("id1") is None
        assert repository._get_from_cache("id2") is None