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
        telegram_user_id=123456,
        telegram_username="testuser",
        notion_api_key="test_private_key",
        notion_database_id="12345678901234567890123456789012",
        memo_database_id="98765432109876543210987654321098",
        shared_notion_database_id="11111111222222223333333344444444",
        timezone="Europe/Berlin"
    )


@pytest.fixture
def memo_service(user_config):
    """Create a MemoService instance with mocked Client."""
    with patch('src.services.memo_service.Client') as mock_client:
        # Mock the client instance
        mock_instance = Mock()
        mock_client.return_value = mock_instance
        
        # Create service
        service = MemoService.from_user_config(user_config)
        
        # Add mock instance to service for tests
        service.mock_client = mock_instance
        
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
                'status': {'name': 'Nicht begonnen'}
            },
            'Fälligkeitsdatum': {
                'date': {'start': '2024-01-22'}
            },
            'Bereich': {
                'multi_select': [{'name': 'Arbeit'}]
            },
            'Projekt': {
                'multi_select': [{'name': 'Test Projekt'}]
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
        # Mock Notion client response
        memo_service.mock_client.pages.create.return_value = {'id': 'page-123'}
        
        # Create memo
        page_id = await memo_service.create_memo(sample_memo)
        
        # Verify
        assert page_id == 'page-123'
        memo_service.mock_client.pages.create.assert_called_once()
        
        # Check the properties passed to Notion
        call_args = memo_service.mock_client.pages.create.call_args
        properties = call_args[1]['properties']
        
        assert properties['Aufgabe']['title'][0]['text']['content'] == 'Test Aufgabe'
        assert properties['Status']['status']['name'] == 'Nicht begonnen'
        assert 'Fälligkeitsdatum' in properties
        assert properties['Bereich']['multi_select'][0]['name'] == 'Arbeit'
        assert properties['Projekt']['multi_select'][0]['name'] == 'Test Projekt'
        assert properties['Notizen']['rich_text'][0]['text']['content'] == 'Test Notizen'
    
    @pytest.mark.asyncio
    async def test_create_memo_minimal(self, memo_service):
        """Test creating a memo with minimal fields."""
        minimal_memo = Memo(aufgabe="Minimal Task", status="Nicht begonnen")
        
        memo_service.mock_client.pages.create.return_value = {'id': 'page-456'}
        
        page_id = await memo_service.create_memo(minimal_memo)
        
        assert page_id == 'page-456'
        
        # Check that only required fields are set
        call_args = memo_service.mock_client.pages.create.call_args
        properties = call_args[1]['properties']
        
        assert properties['Aufgabe']['title'][0]['text']['content'] == 'Minimal Task'
        assert properties['Status']['status']['name'] == 'Nicht begonnen'
        # Notizen field should always be present (even if empty) after Issue #13 fix
        assert 'Notizen' in properties
        assert properties['Notizen']['rich_text'] == []
    
    @pytest.mark.asyncio
    async def test_create_memo_empty_description_issue_13(self, memo_service):
        """Test Issue #13: Creating memos with empty description field."""
        # Test memo with None description (notizen=None)
        memo_none = Memo(aufgabe="Quick task - no description", notizen=None)
        memo_service.mock_client.pages.create.return_value = {'id': 'page-issue13-none'}
        
        page_id = await memo_service.create_memo(memo_none)
        assert page_id == 'page-issue13-none'
        
        call_args = memo_service.mock_client.pages.create.call_args
        properties = call_args[1]['properties']
        
        # Verify Notizen field is present but empty
        assert 'Notizen' in properties
        assert properties['Notizen']['rich_text'] == []
        
        # Reset mock for next test
        memo_service.mock_client.reset_mock()
        
        # Test memo with empty string description (notizen="")
        memo_empty = Memo(aufgabe="Quick task - empty description", notizen="")
        memo_service.mock_client.pages.create.return_value = {'id': 'page-issue13-empty'}
        
        page_id = await memo_service.create_memo(memo_empty)
        assert page_id == 'page-issue13-empty'
        
        call_args = memo_service.mock_client.pages.create.call_args
        properties = call_args[1]['properties']
        
        # Verify Notizen field is present but empty
        assert 'Notizen' in properties
        assert properties['Notizen']['rich_text'] == []
    
    @pytest.mark.asyncio
    async def test_get_recent_memos(self, memo_service, notion_page_data):
        """Test retrieving recent memos."""
        # Mock Notion query response
        memo_service.mock_client.databases.query.return_value = {'results': [notion_page_data]}
        
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
        memo_service.mock_client.databases.query.return_value = {'results': []}
        
        memos = await memo_service.get_recent_memos()
        
        assert memos == []
    
    @pytest.mark.asyncio
    async def test_update_memo_status(self, memo_service):
        """Test updating memo status."""
        memo_service.mock_client.pages.update.return_value = {'id': 'page-123'}
        
        success = await memo_service.update_memo_status('page-123', 'Erledigt')
        
        assert success is True
        memo_service.mock_client.pages.update.assert_called_once()
        call_args = memo_service.mock_client.pages.update.call_args
        assert call_args[1]['properties']['Status']['status']['name'] == 'Erledigt'
    
    @pytest.mark.asyncio
    async def test_delete_memo(self, memo_service):
        """Test deleting a memo."""
        memo_service.mock_client.pages.update.return_value = {'archived': True}
        
        success = await memo_service.delete_memo('page-123')
        
        assert success is True
        memo_service.mock_client.pages.update.assert_called_once()
        call_args = memo_service.mock_client.pages.update.call_args
        assert call_args[1]['archived'] is True
    
    @pytest.mark.asyncio
    async def test_get_memos_by_status(self, memo_service, notion_page_data):
        """Test getting memos by status."""
        memo_service.mock_client.databases.query.return_value = {'results': [notion_page_data]}
        
        memos = await memo_service.get_memos_by_status('Nicht begonnen')
        
        assert len(memos) == 1
        assert memos[0].status == 'Nicht begonnen'
        
        # Verify the filter was applied
        call_args = memo_service.mock_client.databases.query.call_args
        filter_data = call_args[1]['filter']
        assert filter_data['property'] == 'Status'
        assert filter_data['status']['equals'] == 'Nicht begonnen'
    
    @pytest.mark.asyncio
    async def test_update_memo(self, memo_service, sample_memo):
        """Test updating an existing memo."""
        memo_service.mock_client.pages.update.return_value = {'id': 'page-123'}
        
        success = await memo_service.update_memo('page-123', sample_memo)
        
        assert success is True
        memo_service.mock_client.pages.update.assert_called_once()
        
        # Verify all properties were updated
        call_args = memo_service.mock_client.pages.update.call_args
        properties = call_args[1]['properties']
        assert properties['Aufgabe']['title'][0]['text']['content'] == 'Test Aufgabe'
        assert properties['Status']['status']['name'] == 'Nicht begonnen'
    
    @pytest.mark.asyncio
    async def test_test_connection(self, memo_service):
        """Test database connection test."""
        memo_service.mock_client.databases.retrieve.return_value = {'id': 'test-db'}
        
        result = await memo_service.test_connection()
        
        assert result is True
        memo_service.mock_client.databases.retrieve.assert_called_once_with(
            database_id=memo_service.database_id
        )
    
    @pytest.mark.asyncio
    async def test_error_handling_create(self, memo_service, sample_memo):
        """Test error handling during memo creation."""
        from notion_client.errors import APIResponseError
        
        # Create a mock httpx Response
        import httpx
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 400
        mock_response.text = "API Error"
        mock_response.headers = {}
        mock_response.json.return_value = {"code": "bad_request", "message": "API Error"}
        
        # Create APIResponseError with the mocked response
        api_error = APIResponseError(
            response=mock_response,
            message="API Error", 
            code="bad_request"
        )
        
        memo_service.mock_client.pages.create.side_effect = api_error
        
        # The @handle_bot_error decorator catches the error and returns None for HIGH severity
        # So we test that None is returned and the error was logged
        result = await memo_service.create_memo(sample_memo)
        
        # Should return None since error was handled
        assert result is None
        
        # Verify that the Notion client was called
        memo_service.mock_client.pages.create.assert_called_once()
    
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
                    'status': {'name': 'In Bearbeitung'}
                }
            }
        }
        
        memo = Memo.from_notion_page(minimal_page_data)
        
        assert memo.aufgabe == 'Minimal Task'
        assert memo.status == 'In Bearbeitung'
        assert memo.faelligkeitsdatum is None
        assert memo.bereich is None
        assert memo.projekt is None
        assert memo.notizen is None


class TestMemoServiceInitialization:
    """Test MemoService initialization."""
    
    def test_from_user_config_success(self, user_config):
        """Test successful initialization from user config."""
        with patch('src.services.memo_service.Client') as mock_client:
            service = MemoService.from_user_config(user_config)
            
            assert service.database_id == user_config.memo_database_id
            mock_client.assert_called_once_with(
                auth=user_config.notion_api_key
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
        
        from src.utils.error_handler import BotError
        with pytest.raises(BotError) as exc_info:
            MemoService.from_user_config(config)
        
        assert "missing memo_database_id" in str(exc_info.value)