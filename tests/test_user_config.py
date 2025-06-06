"""Tests for user configuration management."""
import pytest
import json
import os
from config.user_config import UserConfig, UserConfigManager


class TestUserConfig:
    """Test cases for UserConfig dataclass."""
    
    def test_user_config_creation(self):
        """Test creating a UserConfig object."""
        config = UserConfig(
            telegram_user_id=123456,
            telegram_username="testuser",
            notion_api_key="secret_test_key",
            notion_database_id="test_db_id"
        )
        
        assert config.telegram_user_id == 123456
        assert config.telegram_username == "testuser"
        assert config.notion_api_key == "secret_test_key"
        assert config.notion_database_id == "test_db_id"
        assert config.timezone == "Europe/Berlin"  # Default
        assert config.language == "de"  # Default
        assert config.reminder_time == "08:00"  # Default
        assert config.reminder_enabled is True  # Default
    
    def test_user_config_custom_values(self):
        """Test UserConfig with custom values."""
        config = UserConfig(
            telegram_user_id=123456,
            telegram_username="testuser",
            notion_api_key="secret_test_key",
            notion_database_id="test_db_id",
            timezone="America/New_York",
            language="en",
            reminder_time="09:30",
            reminder_enabled=False
        )
        
        assert config.timezone == "America/New_York"
        assert config.language == "en"
        assert config.reminder_time == "09:30"
        assert config.reminder_enabled is False


class TestUserConfigManager:
    """Test cases for UserConfigManager."""
    
    @pytest.fixture
    def temp_config_file(self, tmp_path):
        """Create a temporary config file."""
        config_file = tmp_path / "test_users_config.json"
        return str(config_file)
    
    @pytest.fixture
    def sample_config_data(self):
        """Sample configuration data."""
        return {
            "users": [
                {
                    "telegram_user_id": 123456,
                    "telegram_username": "user1",
                    "notion_api_key": "secret_key_1",
                    "notion_database_id": "db_id_1",
                    "timezone": "Europe/Berlin",
                    "language": "de",
                    "reminder_time": "08:00",
                    "reminder_enabled": True
                },
                {
                    "telegram_user_id": 789012,
                    "telegram_username": "user2",
                    "notion_api_key": "secret_key_2",
                    "notion_database_id": "db_id_2",
                    "timezone": "America/New_York",
                    "language": "en",
                    "reminder_time": "09:00",
                    "reminder_enabled": False
                }
            ]
        }
    
    def test_load_from_file(self, temp_config_file, sample_config_data):
        """Test loading configuration from file."""
        # Write sample data
        with open(temp_config_file, 'w') as f:
            json.dump(sample_config_data, f)
        
        # Load configuration
        manager = UserConfigManager(temp_config_file)
        
        # Check loaded users
        all_users = manager.get_all_users()
        assert len(all_users) == 2
        
        # Check first user
        user1 = manager.get_user_config(123456)
        assert user1 is not None
        assert user1.telegram_username == "user1"
        assert user1.notion_api_key == "secret_key_1"
        assert user1.timezone == "Europe/Berlin"
        
        # Check second user
        user2 = manager.get_user_config(789012)
        assert user2 is not None
        assert user2.telegram_username == "user2"
        assert user2.notion_api_key == "secret_key_2"
        assert user2.timezone == "America/New_York"
    
    def test_add_user(self, temp_config_file):
        """Test adding a new user."""
        manager = UserConfigManager(temp_config_file)
        
        # Add new user
        new_user = UserConfig(
            telegram_user_id=555555,
            telegram_username="newuser",
            notion_api_key="new_secret_key",
            notion_database_id="new_db_id"
        )
        manager.add_user(new_user)
        
        # Check user was added
        retrieved_user = manager.get_user_config(555555)
        assert retrieved_user is not None
        assert retrieved_user.telegram_username == "newuser"
        
        # Check file was updated
        with open(temp_config_file, 'r') as f:
            data = json.load(f)
            assert len(data['users']) == 1
            assert data['users'][0]['telegram_user_id'] == 555555
    
    def test_remove_user(self, temp_config_file, sample_config_data):
        """Test removing a user."""
        # Write sample data
        with open(temp_config_file, 'w') as f:
            json.dump(sample_config_data, f)
        
        manager = UserConfigManager(temp_config_file)
        
        # Remove user
        manager.remove_user(123456)
        
        # Check user was removed
        assert manager.get_user_config(123456) is None
        
        # Check other user still exists
        assert manager.get_user_config(789012) is not None
        
        # Check file was updated
        with open(temp_config_file, 'r') as f:
            data = json.load(f)
            assert len(data['users']) == 1
            assert data['users'][0]['telegram_user_id'] == 789012
    
    def test_get_users_for_reminders(self, temp_config_file, sample_config_data):
        """Test getting users for reminders at specific time."""
        # Write sample data
        with open(temp_config_file, 'w') as f:
            json.dump(sample_config_data, f)
        
        manager = UserConfigManager(temp_config_file)
        
        # Get users for 08:00
        users_8 = manager.get_users_for_reminders("08:00")
        assert len(users_8) == 1
        assert users_8[0].telegram_user_id == 123456
        
        # Get users for 09:00 (disabled user)
        users_9 = manager.get_users_for_reminders("09:00")
        assert len(users_9) == 0  # User 2 has reminders disabled
        
        # Get users for 10:00 (no users)
        users_10 = manager.get_users_for_reminders("10:00")
        assert len(users_10) == 0
    
    def test_backward_compatibility_env(self, temp_config_file, monkeypatch):
        """Test backward compatibility with environment variables."""
        # Set environment variables
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("NOTION_API_KEY", "test_notion_key")
        monkeypatch.setenv("NOTION_DATABASE_ID", "test_db_id")
        monkeypatch.setenv("TIMEZONE", "Europe/London")
        
        manager = UserConfigManager(temp_config_file)
        
        # Check default user was created
        default_user = manager.get_user_config(0)
        assert default_user is None  # Should be None since it gets reassigned
        
        # When a real user ID is requested, default should be reassigned
        user_config = manager.get_user_config(999999)
        assert user_config is not None
        assert user_config.notion_api_key == "test_notion_key"
        assert user_config.notion_database_id == "test_db_id"
        assert user_config.timezone == "Europe/London"
        assert user_config.telegram_user_id == 999999
    
    def test_save_to_file_creates_directory(self, tmp_path):
        """Test that save_to_file creates directory if needed."""
        config_file = tmp_path / "subdir" / "users_config.json"
        manager = UserConfigManager(str(config_file))
        
        # Add user and save
        user = UserConfig(
            telegram_user_id=111111,
            telegram_username="testuser",
            notion_api_key="key",
            notion_database_id="db_id"
        )
        manager.add_user(user)
        
        # Check file was created
        assert config_file.exists()
        
        # Check content
        with open(config_file, 'r') as f:
            data = json.load(f)
            assert len(data['users']) == 1
            assert data['users'][0]['telegram_user_id'] == 111111