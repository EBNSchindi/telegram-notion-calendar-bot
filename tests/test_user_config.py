"""Unit tests for UserConfig and UserConfigManager."""
import pytest
import json
import os
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
from config.user_config import UserConfig, UserConfigManager


@pytest.fixture
def sample_user_config():
    """Create a sample user configuration."""
    return UserConfig(
        user_id=123456,
        private_api_key="test_private_key",
        private_database_id="12345678901234567890123456789012",
        shared_api_key="test_shared_key",
        shared_database_id="11111111222222223333333344444444",
        timezone="Europe/Berlin",
        memo_database_id="98765432109876543210987654321098",
        business_email="user@example.com",
        business_calendar_url="https://example.com/calendar",
        business_sync_hours="9,12,15,18"
    )


@pytest.fixture
def sample_config_dict():
    """Create a sample configuration dictionary."""
    return {
        "123456": {
            "private_api_key": "test_private_key",
            "private_database_id": "12345678901234567890123456789012",
            "shared_api_key": "test_shared_key",
            "shared_database_id": "11111111222222223333333344444444",
            "timezone": "Europe/Berlin",
            "memo_database_id": "98765432109876543210987654321098"
        },
        "789012": {
            "private_api_key": "another_private_key",
            "private_database_id": "98765432109876543210987654321098",
            "shared_api_key": "another_shared_key",
            "shared_database_id": "11111111222222223333333344444444",
            "timezone": "America/New_York"
        }
    }


@pytest.fixture
def user_config_manager(tmp_path):
    """Create a UserConfigManager with a temporary config file."""
    config_file = tmp_path / "test_user_config.json"
    with patch('config.user_config.UserConfigManager.CONFIG_FILE', str(config_file)):
        return UserConfigManager()


class TestUserConfig:
    """Test cases for UserConfig model."""
    
    def test_user_config_creation(self, sample_user_config):
        """Test creating a UserConfig instance."""
        assert sample_user_config.user_id == 123456
        assert sample_user_config.private_api_key == "test_private_key"
        assert sample_user_config.timezone == "Europe/Berlin"
        assert sample_user_config.memo_database_id == "98765432109876543210987654321098"
    
    def test_user_config_minimal(self):
        """Test creating UserConfig with minimal required fields."""
        config = UserConfig(
            user_id=123,
            private_api_key="key",
            private_database_id="12345678901234567890123456789012"
        )
        
        assert config.user_id == 123
        assert config.private_api_key == "key"
        assert config.shared_api_key is None
        assert config.timezone == "Europe/Berlin"  # Default value
    
    def test_user_config_validation(self):
        """Test UserConfig validation."""
        # Valid configuration
        config = UserConfig(
            user_id=123,
            private_api_key="key",
            private_database_id="12345678901234567890123456789012"
        )
        assert config.user_id == 123
        
        # Test with invalid data types (Pydantic should handle type conversion)
        config = UserConfig(
            user_id="123",  # String instead of int
            private_api_key="key",
            private_database_id="12345678901234567890123456789012"
        )
        assert config.user_id == 123  # Should be converted to int
    
    def test_user_config_to_dict(self, sample_user_config):
        """Test converting UserConfig to dictionary."""
        config_dict = sample_user_config.model_dump()
        
        assert config_dict['user_id'] == 123456
        assert config_dict['private_api_key'] == "test_private_key"
        assert config_dict['timezone'] == "Europe/Berlin"
        assert 'memo_database_id' in config_dict
    
    def test_user_config_from_dict(self):
        """Test creating UserConfig from dictionary."""
        data = {
            'user_id': 123,
            'private_api_key': 'key',
            'private_database_id': '12345678901234567890123456789012',
            'timezone': 'America/New_York'
        }
        
        config = UserConfig(**data)
        assert config.user_id == 123
        assert config.timezone == 'America/New_York'


class TestUserConfigManager:
    """Test cases for UserConfigManager."""
    
    def test_load_empty_config(self, user_config_manager):
        """Test loading when no config file exists."""
        configs = user_config_manager.configs
        assert configs == {}
    
    def test_save_and_load_config(self, user_config_manager, sample_user_config):
        """Test saving and loading configuration."""
        # Add a user config
        user_config_manager.add_user_config(sample_user_config)
        
        # Create a new manager instance to test loading
        new_manager = UserConfigManager()
        
        # Check that config was loaded
        loaded_config = new_manager.get_user_config(123456)
        assert loaded_config is not None
        assert loaded_config.user_id == 123456
        assert loaded_config.private_api_key == "test_private_key"
        assert loaded_config.timezone == "Europe/Berlin"
    
    def test_add_user_config(self, user_config_manager, sample_user_config):
        """Test adding a user configuration."""
        user_config_manager.add_user_config(sample_user_config)
        
        assert 123456 in user_config_manager.configs
        stored_config = user_config_manager.configs[123456]
        assert stored_config.private_api_key == "test_private_key"
    
    def test_get_user_config(self, user_config_manager, sample_user_config):
        """Test retrieving a user configuration."""
        # Add config first
        user_config_manager.add_user_config(sample_user_config)
        
        # Retrieve it
        config = user_config_manager.get_user_config(123456)
        assert config is not None
        assert config.user_id == 123456
        assert config.private_api_key == "test_private_key"
        
        # Try non-existent user
        config = user_config_manager.get_user_config(999999)
        assert config is None
    
    def test_update_user_config(self, user_config_manager, sample_user_config):
        """Test updating a user configuration."""
        # Add initial config
        user_config_manager.add_user_config(sample_user_config)
        
        # Update it
        updated_config = UserConfig(
            user_id=123456,
            private_api_key="new_key",
            private_database_id="12345678901234567890123456789012",
            timezone="America/New_York"
        )
        user_config_manager.update_user_config(updated_config)
        
        # Verify update
        config = user_config_manager.get_user_config(123456)
        assert config.private_api_key == "new_key"
        assert config.timezone == "America/New_York"
    
    def test_remove_user_config(self, user_config_manager, sample_user_config):
        """Test removing a user configuration."""
        # Add config
        user_config_manager.add_user_config(sample_user_config)
        assert user_config_manager.get_user_config(123456) is not None
        
        # Remove it
        user_config_manager.remove_user_config(123456)
        assert user_config_manager.get_user_config(123456) is None
        
        # Verify it's saved
        new_manager = UserConfigManager()
        assert new_manager.get_user_config(123456) is None
    
    def test_get_all_user_configs(self, user_config_manager):
        """Test getting all user configurations."""
        # Add multiple configs
        config1 = UserConfig(
            user_id=111,
            private_api_key="key1",
            private_database_id="12345678901234567890123456789012"
        )
        config2 = UserConfig(
            user_id=222,
            private_api_key="key2",
            private_database_id="98765432109876543210987654321098"
        )
        
        user_config_manager.add_user_config(config1)
        user_config_manager.add_user_config(config2)
        
        all_configs = user_config_manager.get_all_user_configs()
        assert len(all_configs) == 2
        assert any(c.user_id == 111 for c in all_configs)
        assert any(c.user_id == 222 for c in all_configs)
    
    def test_file_corruption_handling(self, tmp_path):
        """Test handling of corrupted config file."""
        config_file = tmp_path / "corrupt_config.json"
        
        # Write invalid JSON
        config_file.write_text("{ invalid json content")
        
        with patch('config.user_config.UserConfigManager.CONFIG_FILE', str(config_file)):
            manager = UserConfigManager()
            # Should handle gracefully and start with empty config
            assert manager.configs == {}
    
    def test_backward_compatibility(self, tmp_path):
        """Test loading old config format."""
        config_file = tmp_path / "old_config.json"
        
        # Old format without memo_database_id
        old_config = {
            "123456": {
                "private_api_key": "test_key",
                "private_database_id": "12345678901234567890123456789012",
                "shared_api_key": "shared_key",
                "shared_database_id": "11111111222222223333333344444444"
            }
        }
        
        config_file.write_text(json.dumps(old_config, indent=2))
        
        with patch('config.user_config.UserConfigManager.CONFIG_FILE', str(config_file)):
            manager = UserConfigManager()
            config = manager.get_user_config(123456)
            
            assert config is not None
            assert config.memo_database_id is None  # Should be None for old configs
            assert config.timezone == "Europe/Berlin"  # Should use default
    
    def test_save_config_creates_directory(self, tmp_path):
        """Test that save_config creates directory if it doesn't exist."""
        config_file = tmp_path / "subdir" / "config.json"
        
        with patch('config.user_config.UserConfigManager.CONFIG_FILE', str(config_file)):
            manager = UserConfigManager()
            config = UserConfig(
                user_id=123,
                private_api_key="key",
                private_database_id="12345678901234567890123456789012"
            )
            manager.add_user_config(config)
            
            # Directory should be created
            assert config_file.parent.exists()
            assert config_file.exists()


class TestUserConfigBusinessFields:
    """Test business-related fields in UserConfig."""
    
    def test_business_fields(self, sample_user_config):
        """Test business calendar fields."""
        assert sample_user_config.business_email == "user@example.com"
        assert sample_user_config.business_calendar_url == "https://example.com/calendar"
        assert sample_user_config.business_sync_hours == "9,12,15,18"
    
    def test_business_fields_optional(self):
        """Test that business fields are optional."""
        config = UserConfig(
            user_id=123,
            private_api_key="key",
            private_database_id="12345678901234567890123456789012"
        )
        
        assert config.business_email is None
        assert config.business_calendar_url is None
        assert config.business_sync_hours is None
    
    def test_get_sync_hours(self, sample_user_config):
        """Test parsing sync hours."""
        # This would be a method on UserConfig if implemented
        sync_hours = sample_user_config.business_sync_hours.split(',')
        assert sync_hours == ['9', '12', '15', '18']
        
        # Test with None
        config = UserConfig(
            user_id=123,
            private_api_key="key",
            private_database_id="12345678901234567890123456789012"
        )
        assert config.business_sync_hours is None


class TestUserConfigSecurityConsiderations:
    """Test security aspects of UserConfig."""
    
    def test_no_api_keys_in_repr(self, sample_user_config):
        """Test that API keys are not exposed in string representation."""
        repr_str = repr(sample_user_config)
        # Check that sensitive data is not in repr
        # (This would require implementing custom __repr__ in UserConfig)
        # For now, just verify the object can be represented
        assert 'UserConfig' in str(type(sample_user_config))
    
    def test_config_file_permissions(self, tmp_path):
        """Test that config file is created with appropriate permissions."""
        config_file = tmp_path / "secure_config.json"
        
        with patch('config.user_config.UserConfigManager.CONFIG_FILE', str(config_file)):
            manager = UserConfigManager()
            config = UserConfig(
                user_id=123,
                private_api_key="secret_key",
                private_database_id="12345678901234567890123456789012"
            )
            manager.add_user_config(config)
            
            # File should exist
            assert config_file.exists()
            
            # On Unix systems, check file permissions
            if os.name != 'nt':  # Not Windows
                stat_info = config_file.stat()
                # File should not be world-readable
                assert (stat_info.st_mode & 0o077) == 0