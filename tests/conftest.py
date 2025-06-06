import os
import pytest
from unittest.mock import Mock, AsyncMock
from config.settings import Settings

# Set test environment
os.environ['ENVIRONMENT'] = 'testing'
os.environ['TELEGRAM_BOT_TOKEN'] = 'test_telegram_token'
os.environ['NOTION_API_KEY'] = 'test_notion_api_key'
os.environ['NOTION_DATABASE_ID'] = 'test_database_id'

@pytest.fixture
def settings():
    """Test settings fixture."""
    return Settings()

@pytest.fixture
def mock_telegram_update():
    """Mock Telegram update."""
    update = Mock()
    update.effective_user = Mock()
    update.effective_user.id = 123456789
    update.effective_user.first_name = "Test"
    update.effective_user.mention_html.return_value = "<a href='tg://user?id=123456789'>Test</a>"
    
    update.message = Mock()
    update.message.reply_text = AsyncMock()
    update.message.reply_html = AsyncMock()
    
    return update

@pytest.fixture
def mock_telegram_context():
    """Mock Telegram context."""
    context = Mock()
    context.args = []
    return context

@pytest.fixture
def mock_notion_client():
    """Mock Notion client."""
    return Mock()