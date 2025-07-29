"""Unit tests for AppointmentRepository."""
import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime, timedelta
import pytz
from notion_client.errors import APIResponseError

from src.repositories.appointment_repository import AppointmentRepository
from src.models.appointment import Appointment
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
    """Create an AppointmentRepository instance."""
    return AppointmentRepository(
        notion_client=mock_notion_client,
        database_id="test-database-id",
        timezone="Europe/Berlin"
    )


@pytest.fixture
def sample_appointment():
    """Create a sample appointment."""
    tz = pytz.timezone("Europe/Berlin")
    return Appointment(
        title="Test Appointment",
        date=datetime.now(tz) + timedelta(days=1),
        memo="Test memo",
        is_partner_relevant=True,
        is_business=False
    )


@pytest.fixture
def notion_page_response():
    """Create a sample Notion page response."""
    return {
        "id": "page-123",
        "properties": {
            "Title": {
                "title": [
                    {
                        "text": {
                            "content": "Test Appointment"
                        }
                    }
                ]
            },
            "📅 Date": {
                "date": {
                    "start": "2024-01-15T14:00:00.000+01:00"
                }
            },
            "📝 Memo": {
                "rich_text": [
                    {
                        "text": {
                            "content": "Test memo"
                        }
                    }
                ]
            },
            "💑 Partner Relevant": {
                "checkbox": True
            },
            "👔 Business": {
                "checkbox": False
            }
        }
    }


class TestAppointmentRepository:
    """Test cases for AppointmentRepository."""
    
    @pytest.mark.asyncio
    async def test_create_appointment_success(self, repository, mock_notion_client, sample_appointment):
        """Test successful appointment creation."""
        mock_notion_client.pages.create.return_value = {"id": "new-page-id"}
        
        result = await repository.create(sample_appointment)
        
        assert result == "new-page-id"
        mock_notion_client.pages.create.assert_called_once()
        
        # Verify the appointment was cached
        cached = repository._get_from_cache("new-page-id")
        assert cached == sample_appointment
    
    @pytest.mark.asyncio
    async def test_create_appointment_api_error(self, repository, mock_notion_client, sample_appointment):
        """Test appointment creation with API error."""
        mock_notion_client.pages.create.side_effect = APIResponseError(
            {"code": "invalid_request", "message": "Invalid request"},
            400,
            "Invalid request",
            {}
        )
        
        with pytest.raises(BotError) as exc_info:
            await repository.create(sample_appointment)
        
        assert exc_info.value.error_type == ErrorType.NOTION_API
        assert exc_info.value.severity == ErrorSeverity.HIGH
    
    @pytest.mark.asyncio
    async def test_get_by_id_success(self, repository, mock_notion_client, notion_page_response):
        """Test successful appointment retrieval by ID."""
        mock_notion_client.pages.retrieve.return_value = notion_page_response
        
        result = await repository.get_by_id("page-123")
        
        assert result is not None
        assert result.title == "Test Appointment"
        assert result.memo == "Test memo"
        assert result.is_partner_relevant is True
        assert result.is_business is False
        
        # Verify caching
        cached = repository._get_from_cache("page-123")
        assert cached == result
    
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repository, mock_notion_client):
        """Test appointment retrieval when not found."""
        mock_notion_client.pages.retrieve.side_effect = APIResponseError(
            {"code": "object_not_found", "message": "Not found"},
            404,
            "Not found",
            {}
        )
        
        result = await repository.get_by_id("non-existent")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_all_with_pagination(self, repository, mock_notion_client, notion_page_response):
        """Test getting all appointments with pagination."""
        mock_notion_client.databases.query.return_value = {
            "results": [notion_page_response],
            "has_more": True,
            "next_cursor": "next-cursor-123"
        }
        
        pagination = PaginationParams(page_size=10)
        result = await repository.get_all(pagination)
        
        assert len(result.items) == 1
        assert result.has_more is True
        assert result.next_cursor == "next-cursor-123"
        
        mock_notion_client.databases.query.assert_called_once_with(
            database_id="test-database-id",
            page_size=10,
            sorts=[{"property": "📅 Date", "direction": "ascending"}]
        )
    
    @pytest.mark.asyncio
    async def test_update_appointment_success(self, repository, mock_notion_client, sample_appointment):
        """Test successful appointment update."""
        mock_notion_client.pages.update.return_value = {"id": "page-123"}
        
        result = await repository.update("page-123", sample_appointment)
        
        assert result is True
        mock_notion_client.pages.update.assert_called_once()
        
        # Verify cache update
        cached = repository._get_from_cache("page-123")
        assert cached == sample_appointment
    
    @pytest.mark.asyncio
    async def test_update_appointment_not_found(self, repository, mock_notion_client, sample_appointment):
        """Test updating non-existent appointment."""
        mock_notion_client.pages.update.side_effect = APIResponseError(
            {"code": "object_not_found", "message": "Not found"},
            404,
            "Not found",
            {}
        )
        
        result = await repository.update("non-existent", sample_appointment)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_delete_appointment_success(self, repository, mock_notion_client):
        """Test successful appointment deletion (archiving)."""
        # First cache an appointment
        repository._update_cache("page-123", Mock())
        
        mock_notion_client.pages.update.return_value = {"id": "page-123", "archived": True}
        
        result = await repository.delete("page-123")
        
        assert result is True
        mock_notion_client.pages.update.assert_called_once_with(
            page_id="page-123",
            archived=True
        )
        
        # Verify cache invalidation
        cached = repository._get_from_cache("page-123")
        assert cached is None
    
    @pytest.mark.asyncio
    async def test_find_by_criteria_with_filters(self, repository, mock_notion_client, notion_page_response):
        """Test finding appointments by criteria."""
        mock_notion_client.databases.query.return_value = {
            "results": [notion_page_response],
            "has_more": False
        }
        
        criteria = {
            "date_from": datetime.now(),
            "title_contains": "Test",
            "is_business": False
        }
        
        result = await repository.find_by_criteria(criteria)
        
        assert len(result.items) == 1
        
        # Verify the filter was built correctly
        call_args = mock_notion_client.databases.query.call_args[1]
        assert "filter" in call_args
        assert "and" in call_args["filter"]
    
    @pytest.mark.asyncio
    async def test_get_todays_appointments(self, repository, mock_notion_client, notion_page_response):
        """Test getting today's appointments."""
        mock_notion_client.databases.query.return_value = {
            "results": [notion_page_response],
            "has_more": False
        }
        
        result = await repository.get_todays_appointments()
        
        assert isinstance(result, list)
        
        # Verify date filter was applied
        call_args = mock_notion_client.databases.query.call_args[1]
        assert "filter" in call_args
    
    @pytest.mark.asyncio
    async def test_find_duplicates(self, repository, mock_notion_client, sample_appointment):
        """Test finding duplicate appointments."""
        # Create a duplicate appointment
        duplicate_response = {
            "id": "duplicate-123",
            "properties": {
                "Title": {
                    "title": [{"text": {"content": "Test Appointment"}}]
                },
                "📅 Date": {
                    "date": {"start": sample_appointment.date.isoformat()}
                }
            }
        }
        
        mock_notion_client.databases.query.return_value = {
            "results": [duplicate_response],
            "has_more": False
        }
        
        duplicates = await repository.find_duplicates(sample_appointment)
        
        assert len(duplicates) == 1
        assert duplicates[0].title == sample_appointment.title
    
    def test_cache_operations(self, repository, sample_appointment):
        """Test cache operations."""
        # Test cache update
        repository._update_cache("test-id", sample_appointment)
        cached = repository._get_from_cache("test-id")
        assert cached == sample_appointment
        
        # Test cache invalidation
        repository._invalidate_cache("test-id")
        cached = repository._get_from_cache("test-id")
        assert cached is None
        
        # Test clear cache
        repository._update_cache("id1", sample_appointment)
        repository._update_cache("id2", sample_appointment)
        repository.clear_cache()
        
        assert repository._get_from_cache("id1") is None
        assert repository._get_from_cache("id2") is None
    
    def test_cache_ttl(self, repository, sample_appointment):
        """Test cache TTL expiration."""
        repository._cache_ttl = 0  # Set TTL to 0 seconds
        
        repository._update_cache("test-id", sample_appointment)
        
        # Wait a moment to ensure TTL expires
        import time
        time.sleep(0.1)
        
        cached = repository._get_from_cache("test-id")
        assert cached is None
    
    def test_title_similarity_calculation(self, repository):
        """Test title similarity calculation."""
        # Exact match
        assert repository._calculate_title_similarity("test", "test") == 1.0
        
        # One contains the other
        assert repository._calculate_title_similarity("test", "test appointment") == 0.9
        
        # Common characters
        similarity = repository._calculate_title_similarity("hello", "hallo")
        assert 0.5 < similarity < 1.0
        
        # No common characters
        assert repository._calculate_title_similarity("abc", "xyz") < 0.5