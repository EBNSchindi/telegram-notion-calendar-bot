"""Tests for Teamspace configuration functionality."""
import pytest
import tempfile
import json
import os
from config.user_config import UserConfig, UserConfigManager


class TestTeamspaceConfiguration:
    """Test cases for Teamspace API key management."""
    
    def test_user_config_new_fields(self):
        """Test that UserConfig includes new teamspace fields."""
        config = UserConfig(
            telegram_user_id=123,
            telegram_username="test_user",
            notion_api_key="personal_key",
            notion_database_id="personal_db",
            teamspace_owner_api_key="owner_key",
            is_owner=False
        )
        
        assert config.teamspace_owner_api_key == "owner_key"
        assert config.is_owner is False
    
    def test_owner_api_key_selection(self):
        """Test API key selection for owners."""
        # Create owner config
        owner_config = UserConfig(
            telegram_user_id=111,
            telegram_username="owner",
            notion_api_key="owner_personal_key",
            notion_database_id="owner_db",
            shared_notion_database_id="shared_db",
            is_owner=True
        )
        
        manager = UserConfigManager()
        api_key = manager.get_shared_database_api_key(owner_config)
        
        # Owner should use their own key
        assert api_key == "owner_personal_key"
    
    def test_member_api_key_selection(self):
        """Test API key selection for team members."""
        # Create member config
        member_config = UserConfig(
            telegram_user_id=222,
            telegram_username="member",
            notion_api_key="member_personal_key",
            notion_database_id="member_db",
            shared_notion_database_id="shared_db",
            teamspace_owner_api_key="owner_shared_key",
            is_owner=False
        )
        
        manager = UserConfigManager()
        api_key = manager.get_shared_database_api_key(member_config)
        
        # Member should use owner's key for shared DB
        assert api_key == "owner_shared_key"
    
    def test_fallback_without_owner_key(self):
        """Test fallback when no owner key is configured."""
        # Member without owner key configured
        member_config = UserConfig(
            telegram_user_id=333,
            telegram_username="member_no_owner",
            notion_api_key="member_key",
            notion_database_id="member_db",
            shared_notion_database_id="shared_db",
            teamspace_owner_api_key=None,
            is_owner=False
        )
        
        manager = UserConfigManager()
        api_key = manager.get_shared_database_api_key(member_config)
        
        # Should fallback to user's own key
        assert api_key == "member_key"
    
    def test_save_load_teamspace_config(self):
        """Test saving and loading config with teamspace fields."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_file = f.name
        
        try:
            # Create manager with test file
            manager = UserConfigManager(config_file=config_file)
            
            # Add users with teamspace config
            owner = UserConfig(
                telegram_user_id=100,
                telegram_username="owner",
                notion_api_key="owner_key",
                notion_database_id="owner_db",
                shared_notion_database_id="shared_db",
                teamspace_owner_api_key=None,
                is_owner=True
            )
            
            member = UserConfig(
                telegram_user_id=200,
                telegram_username="member",
                notion_api_key="member_key",
                notion_database_id="member_db",
                shared_notion_database_id="shared_db",
                teamspace_owner_api_key="owner_key",
                is_owner=False
            )
            
            manager.add_user(owner)
            manager.add_user(member)
            
            # Reload and verify
            new_manager = UserConfigManager(config_file=config_file)
            loaded_owner = new_manager.get_user_config(100)
            loaded_member = new_manager.get_user_config(200)
            
            assert loaded_owner.is_owner is True
            assert loaded_owner.teamspace_owner_api_key is None
            
            assert loaded_member.is_owner is False
            assert loaded_member.teamspace_owner_api_key == "owner_key"
            
        finally:
            os.unlink(config_file)
    
    def test_environment_variable_loading(self):
        """Test loading teamspace config from environment."""
        # Set environment variables
        os.environ['NOTION_API_KEY'] = 'env_api_key'
        os.environ['NOTION_DATABASE_ID'] = 'env_db_id'
        os.environ['TEAMSPACE_OWNER_API_KEY'] = 'env_owner_key'
        os.environ['IS_TEAMSPACE_OWNER'] = 'true'
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json') as f:
            # Use non-existent file to trigger env loading
            manager = UserConfigManager(config_file=f.name + '.notexist')
            
            default_config = manager.get_user_config(0)
            if default_config:
                assert default_config.teamspace_owner_api_key == 'env_owner_key'
                assert default_config.is_owner is True
        
        # Cleanup
        del os.environ['TEAMSPACE_OWNER_API_KEY']
        del os.environ['IS_TEAMSPACE_OWNER']
    
    def test_mixed_scenario(self):
        """Test a realistic mixed scenario with owner and members."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_file = f.name
        
        try:
            manager = UserConfigManager(config_file=config_file)
            
            # Teamspace owner (Dad)
            dad = UserConfig(
                telegram_user_id=1001,
                telegram_username="dad",
                notion_api_key="dad_personal_key",
                notion_database_id="dad_private_db",
                shared_notion_database_id="family_shared_db",
                memo_database_id="dad_memo_db",
                teamspace_owner_api_key=None,
                is_owner=True
            )
            
            # Team member (Mom)
            mom = UserConfig(
                telegram_user_id=1002,
                telegram_username="mom",
                notion_api_key="mom_personal_key",
                notion_database_id="mom_private_db",
                shared_notion_database_id="family_shared_db",
                memo_database_id="mom_memo_db",
                teamspace_owner_api_key="dad_personal_key",
                is_owner=False
            )
            
            # Team member (Kid)
            kid = UserConfig(
                telegram_user_id=1003,
                telegram_username="kid",
                notion_api_key="kid_personal_key",
                notion_database_id="kid_private_db",
                shared_notion_database_id="family_shared_db",
                memo_database_id="kid_memo_db",
                teamspace_owner_api_key="dad_personal_key",
                is_owner=False
            )
            
            manager.add_user(dad)
            manager.add_user(mom)
            manager.add_user(kid)
            
            # Test API key selection
            assert manager.get_shared_database_api_key(dad) == "dad_personal_key"
            assert manager.get_shared_database_api_key(mom) == "dad_personal_key"
            assert manager.get_shared_database_api_key(kid) == "dad_personal_key"
            
            # Verify each user uses their own key for private DBs
            assert dad.notion_api_key == "dad_personal_key"
            assert mom.notion_api_key == "mom_personal_key"
            assert kid.notion_api_key == "kid_personal_key"
            
        finally:
            os.unlink(config_file)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])