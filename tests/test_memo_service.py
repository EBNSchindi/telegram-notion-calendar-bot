"""Unit tests for MemoService."""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch
from src.services.memo_service import MemoService
from src.models.memo import Memo
from config.user_config import UserConfig


@pytest.fixture
def user_config():
    """Create a test user configuration."""
    return UserConfig(
        user_id=123456,
        private_api_key="test_private_key",
        private_database_id="12345678901234567890123456789012",
        memo_database_id="98765432109876543210987654321098",
        shared_api_key="test_shared_key",
        shared_database_id="11111111222222223333333344444444",
        timezone="Europe/Berlin"
    )


@pytest.fixture
def memo_service(user_config):
    """Create a MemoService instance with mocked NotionService."""
    with patch('src.services.memo_service.NotionService') as mock_notion:
        service = MemoService.from_user_config(user_config)
        service.notion_service = mock_notion.return_value
        return service


@pytest.fixture
def sample_memo():
    """Create a sample memo for testing."""
    return Memo(
        aufgabe="Test Aufgabe",
        status="Nicht begonnen",
        faelligkeitsdatum=datetime.now(timezone.utc) + timedelta(days=7),
        bereich="Arbeit",
        projekt="Test Projekt",
        notizen="Test Notizen"
    )


@pytest.fixture
def notion_page_data():
    """Create sample Notion page data."""
    return {
        'id': 'page-123',
        'created_time': '2024-01-15T10:00:00.000Z',
        'properties': {
            'Aufgabe': {
                'title': [{'text': {'content': 'Test Aufgabe'}}]
            },
            'Status': {
                'select': {'name': 'Nicht begonnen'}
            },
            'Fälligkeitsdatum': {
                'date': {'start': '2024-01-22'}
            },
            'Bereich': {
                'select': {'name': 'Arbeit'}
            },
            'Projekt': {
                'rich_text': [{'text': {'content': 'Test Projekt'}}]
            },
            'Notizen': {
                'rich_text': [{'text': {'content': 'Test Notizen'}}]
            }
        }
    }


class TestMemoService:
    """Test cases for MemoService."""
    
    @pytest.mark.asyncio
    async def test_create_memo_success(self, memo_service, sample_memo):
        """Test successful memo creation."""
        # Mock Notion service response
        memo_service.notion_service.create_page.return_value = AsyncMock(return_value='page-123')
        
        # Create memo
        page_id = await memo_service.create_memo(sample_memo)
        
        # Verify
        assert page_id == 'page-123'
        memo_service.notion_service.create_page.assert_called_once()
        
        # Check the properties passed to Notion
        call_args = memo_service.notion_service.create_page.call_args[0]
        properties = call_args[0]
        
        assert properties['Aufgabe']['title'][0]['text']['content'] == 'Test Aufgabe'
        assert properties['Status']['select']['name'] == 'Nicht begonnen'
        assert 'Fälligkeitsdatum' in properties
        assert properties['Bereich']['select']['name'] == 'Arbeit'
        assert properties['Projekt']['rich_text'][0]['text']['content'] == 'Test Projekt'
        assert properties['Notizen']['rich_text'][0]['text']['content'] == 'Test Notizen'
    
    @pytest.mark.asyncio
    async def test_create_memo_minimal(self, memo_service):
        """Test creating a memo with minimal fields."""
        minimal_memo = Memo(aufgabe="Minimal Task", status="Nicht begonnen")
        
        memo_service.notion_service.create_page.return_value = AsyncMock(return_value='page-456')
        
        page_id = await memo_service.create_memo(minimal_memo)
        
        assert page_id == 'page-456'
        
        # Check that only required fields are set
        call_args = memo_service.notion_service.create_page.call_args[0]
        properties = call_args[0]
        
        assert properties['Aufgabe']['title'][0]['text']['content'] == 'Minimal Task'
        assert properties['Status']['select']['name'] == 'Nicht begonnen'
        # Optional fields should not be in properties
        assert 'Fälligkeitsdatum' not in properties
        assert 'Bereich' not in properties
        assert 'Projekt' not in properties
        assert 'Notizen' not in properties
    
    @pytest.mark.asyncio
    async def test_get_recent_memos(self, memo_service, notion_page_data):
        """Test retrieving recent memos."""
        # Mock Notion query response
        memo_service.notion_service.query_database.return_value = AsyncMock(
            return_value={'results': [notion_page_data]}
        )
        
        memos = await memo_service.get_recent_memos(limit=10)
        
        assert len(memos) == 1
        assert memos[0].aufgabe == 'Test Aufgabe'
        assert memos[0].status == 'Nicht begonnen'
        assert memos[0].bereich == 'Arbeit'
        assert memos[0].projekt == 'Test Projekt'
        assert memos[0].notizen == 'Test Notizen'
        assert memos[0].notion_page_id == 'page-123'
    
    @pytest.mark.asyncio
    async def test_get_recent_memos_empty(self, memo_service):
        """Test retrieving memos when database is empty."""
        memo_service.notion_service.query_database.return_value = AsyncMock(
            return_value={'results': []}
        )
        
        memos = await memo_service.get_recent_memos()
        
        assert memos == []
    
    @pytest.mark.asyncio
    async def test_update_memo_status(self, memo_service):
        """Test updating memo status."""
        memo_service.notion_service.update_page.return_value = AsyncMock(return_value=True)
        
        success = await memo_service.update_memo_status('page-123', 'Erledigt')
        
        assert success is True
        memo_service.notion_service.update_page.assert_called_once_with(
            'page-123',
            {'Status': {'select': {'name': 'Erledigt'}}}
        )
    
    @pytest.mark.asyncio
    async def test_delete_memo(self, memo_service):
        """Test deleting a memo."""
        memo_service.notion_service.archive_page.return_value = AsyncMock(return_value=True)
        
        success = await memo_service.delete_memo('page-123')
        
        assert success is True
        memo_service.notion_service.archive_page.assert_called_once_with('page-123')
    
    @pytest.mark.asyncio
    async def test_search_memos(self, memo_service, notion_page_data):
        """Test searching memos."""
        memo_service.notion_service.query_database.return_value = AsyncMock(
            return_value={'results': [notion_page_data]}
        )
        
        memos = await memo_service.search_memos("Test")
        
        assert len(memos) == 1
        assert memos[0].aufgabe == 'Test Aufgabe'
        
        # Verify the filter was applied
        call_args = memo_service.notion_service.query_database.call_args
        assert 'filter' in call_args[1]
    
    @pytest.mark.asyncio
    async def test_get_memos_by_status(self, memo_service, notion_page_data):
        """Test getting memos by status."""
        memo_service.notion_service.query_database.return_value = AsyncMock(
            return_value={'results': [notion_page_data]}
        )
        
        memos = await memo_service.get_memos_by_status('Nicht begonnen')
        
        assert len(memos) == 1
        assert memos[0].status == 'Nicht begonnen'
        
        # Verify the filter was applied
        call_args = memo_service.notion_service.query_database.call_args
        filter_data = call_args[1]['filter']
        assert filter_data['property'] == 'Status'
        assert filter_data['select']['equals'] == 'Nicht begonnen'
    
    @pytest.mark.asyncio
    async def test_get_memos_by_project(self, memo_service, notion_page_data):
        """Test getting memos by project."""
        memo_service.notion_service.query_database.return_value = AsyncMock(
            return_value={'results': [notion_page_data]}
        )
        
        memos = await memo_service.get_memos_by_project('Test Projekt')
        
        assert len(memos) == 1
        assert memos[0].projekt == 'Test Projekt'
    
    @pytest.mark.asyncio
    async def test_error_handling_create(self, memo_service, sample_memo):
        """Test error handling during memo creation."""
        memo_service.notion_service.create_page.side_effect = Exception("API Error")
        
        with pytest.raises(Exception) as exc_info:
            await memo_service.create_memo(sample_memo)
        
        assert "API Error" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_memo_from_notion_page_missing_fields(self, memo_service):
        """Test creating memo from Notion page with missing optional fields."""
        minimal_page_data = {
            'id': 'page-789',
            'created_time': '2024-01-15T10:00:00.000Z',
            'properties': {
                'Aufgabe': {
                    'title': [{'text': {'content': 'Minimal Task'}}]
                },
                'Status': {
                    'select': {'name': 'In Arbeit'}
                }
            }
        }
        
        memo = Memo.from_notion_page(minimal_page_data)
        
        assert memo.aufgabe == 'Minimal Task'
        assert memo.status == 'In Arbeit'
        assert memo.faelligkeitsdatum is None
        assert memo.bereich is None
        assert memo.projekt is None
        assert memo.notizen is None


class TestMemoServiceInitialization:
    """Test MemoService initialization."""
    
    def test_from_user_config_success(self, user_config):
        """Test successful initialization from user config."""
        with patch('src.services.memo_service.NotionService') as mock_notion:
            service = MemoService.from_user_config(user_config)
            
            assert service.database_id == user_config.memo_database_id
            mock_notion.assert_called_once_with(
                user_config.private_api_key,
                user_config.memo_database_id
            )
    
    def test_from_user_config_no_memo_db(self):
        """Test initialization fails when no memo database configured."""
        config = UserConfig(
            telegram_user_id=123456,
            telegram_username="testuser",
            notion_api_key="test_key",
            notion_database_id="12345678901234567890123456789012"
            # No memo_database_id
        )
        
        with pytest.raises(ValueError) as exc_info:
            MemoService.from_user_config(config)
        
        assert "No memo database configured" in str(exc_info.value)