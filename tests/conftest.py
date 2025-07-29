import os
import sys
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import pytz
from typing import Dict, List, Any

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.settings import Settings
from tests.factories import (
    AppointmentFactory, MemoFactory, SharedAppointmentFactory,
    TelegramUpdateFactory, TelegramContextFactory, NotionPageFactory,
    UserConfigFactory
)

# Set test environment
os.environ['ENVIRONMENT'] = 'testing'
os.environ['TELEGRAM_BOT_TOKEN'] = 'test_telegram_token'
os.environ['NOTION_API_KEY'] = 'test_notion_api_key'
os.environ['NOTION_DATABASE_ID'] = 'test_database_id'
os.environ['OPENAI_API_KEY'] = 'test_openai_api_key'
os.environ['SHARED_NOTION_DATABASE_ID'] = 'test_shared_database_id'

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)


@pytest.fixture(scope='session')
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def settings():
    """Test settings fixture."""
    return Settings()


@pytest.fixture
def mock_telegram_update():
    """Mock Telegram update using factory."""
    return TelegramUpdateFactory()


@pytest.fixture
def mock_telegram_context():
    """Mock Telegram context using factory."""
    return TelegramContextFactory()


@pytest.fixture
def mock_notion_client():
    """Mock Notion client with common methods."""
    client = Mock()
    client.pages = Mock()
    client.pages.create = AsyncMock()
    client.pages.update = AsyncMock()
    client.pages.retrieve = AsyncMock()
    client.databases = Mock()
    client.databases.query = AsyncMock()
    client.databases.retrieve = AsyncMock()
    client.blocks = Mock()
    client.blocks.children = Mock()
    client.blocks.children.list = AsyncMock()
    return client


@pytest.fixture
def sample_appointment():
    """Create a sample appointment using factory."""
    return AppointmentFactory()


@pytest.fixture
def sample_memo():
    """Create a sample memo using factory."""
    return MemoFactory()


@pytest.fixture
def sample_shared_appointment():
    """Create a sample shared appointment using factory."""
    return SharedAppointmentFactory()


@pytest.fixture
def sample_notion_page():
    """Create a sample Notion page using factory."""
    return NotionPageFactory()


@pytest.fixture
def sample_user_config():
    """Create a sample user configuration using factory."""
    return UserConfigFactory()


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for AI assistant tests."""
    client = Mock()
    client.chat = Mock()
    client.chat.completions = Mock()
    client.chat.completions.create = Mock()
    
    # Sample AI response
    response = Mock()
    response.choices = [Mock()]
    response.choices[0].message = Mock()
    response.choices[0].message.content = '{"appointments": []}'
    client.chat.completions.create.return_value = response
    
    return client


@pytest.fixture
def mock_rate_limiter():
    """Mock rate limiter that always allows requests."""
    limiter = Mock()
    limiter.check_rate_limit = Mock(return_value=True)
    limiter.get_remaining_requests = Mock(return_value=10)
    return limiter


@pytest.fixture
def mock_email_validator():
    """Mock email validator."""
    validator = Mock()
    validator.validate = Mock(return_value=True)
    validator.normalize = Mock(side_effect=lambda x: x.lower())
    return validator


@pytest.fixture
def mock_cache():
    """Mock cache for testing caching functionality."""
    cache_data = {}
    
    cache = Mock()
    cache.get = Mock(side_effect=lambda k: cache_data.get(k))
    cache.set = Mock(side_effect=lambda k, v, ttl=None: cache_data.update({k: v}))
    cache.delete = Mock(side_effect=lambda k: cache_data.pop(k, None))
    cache.clear = Mock(side_effect=cache_data.clear)
    cache.data = cache_data  # For test inspection
    
    return cache


@pytest.fixture
def mock_scheduler():
    """Mock scheduler for reminder service tests."""
    scheduler = Mock()
    scheduler.add_job = Mock()
    scheduler.remove_job = Mock()
    scheduler.get_job = Mock()
    scheduler.get_jobs = Mock(return_value=[])
    scheduler.start = Mock()
    scheduler.shutdown = Mock()
    scheduler.running = True
    return scheduler


@pytest.fixture
def time_machine():
    """Fixture for time manipulation using freezegun."""
    from freezegun import freeze_time
    return freeze_time


@pytest.fixture
def mock_logger():
    """Mock logger for testing logging functionality."""
    logger = Mock()
    logger.debug = Mock()
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    logger.exception = Mock()
    return logger


@pytest.fixture
def performance_timer():
    """Fixture for measuring test performance."""
    import time
    
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            
        def start(self):
            self.start_time = time.time()
            
        def stop(self):
            self.end_time = time.time()
            
        @property
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None
    
    return Timer()


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances between tests."""
    # Reset any singleton instances that might persist between tests
    from src.services.notion_service import NotionService
    if hasattr(NotionService, '_instance'):
        delattr(NotionService, '_instance')


@pytest.fixture
def mock_environment_vars():
    """Fixture to temporarily set environment variables."""
    original_env = os.environ.copy()
    
    def _set_env(**kwargs):
        for key, value in kwargs.items():
            os.environ[key] = str(value)
    
    yield _set_env
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def capture_async_exceptions():
    """Fixture to capture exceptions in async code."""
    exceptions = []
    
    def exception_handler(loop, context):
        exceptions.append(context)
    
    loop = asyncio.get_event_loop()
    old_handler = loop.get_exception_handler()
    loop.set_exception_handler(exception_handler)
    
    yield exceptions
    
    loop.set_exception_handler(old_handler)


# Markers for test organization
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "security: Security tests")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "requires_api_key: Tests requiring API keys")
    config.addinivalue_line("markers", "flaky: Flaky tests that may fail intermittently")