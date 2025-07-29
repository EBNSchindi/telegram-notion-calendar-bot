"""User configuration management for multi-user support."""
import os
import json
from typing import Dict, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class UserConfig:
    """Configuration for a single user."""
    telegram_user_id: int
    telegram_username: str
    notion_api_key: str  # User's own API key for private/memo databases
    notion_database_id: str  # Private database (individual per user)
    shared_notion_database_id: str = None  # Shared database ID (same for all users)
    business_notion_database_id: str = None  # Business database ID (optional, individual)
    memo_database_id: str = None  # Memo database ID (individual per user)
    teamspace_owner_api_key: str = None  # Owner API key for shared database in Teamspace
    is_owner: bool = False  # Flag to identify if user is the Teamspace owner
    timezone: str = 'Europe/Berlin'
    language: str = 'de'
    reminder_time: str = '08:00'  # Time for daily reminders
    reminder_enabled: bool = True


class UserConfigManager:
    """Manages user configurations for multi-user support."""
    
    def __init__(self, config_file: str = 'users_config.json'):
        self.config_file = config_file
        self._users: Dict[int, UserConfig] = {}
        self._load_from_env()  # Load from environment for backward compatibility
        self._load_from_file()
    
    def _load_from_env(self):
        """Load configuration from environment variables for backward compatibility."""
        # Skip loading from environment if users_config.json exists
        if os.path.exists(self.config_file):
            logger.info("users_config.json found - skipping environment variable loading")
            return
            
        # Only load from env if no users_config.json exists (backward compatibility)
        if os.getenv('NOTION_API_KEY') and os.getenv('NOTION_DATABASE_ID'):
            # Create default user config from env
            default_user = UserConfig(
                telegram_user_id=0,  # Will be updated on first message
                telegram_username='default',
                notion_api_key=os.getenv('NOTION_API_KEY', ''),
                notion_database_id=os.getenv('NOTION_DATABASE_ID', ''),
                teamspace_owner_api_key=os.getenv('TEAMSPACE_OWNER_API_KEY', ''),
                is_owner=os.getenv('IS_TEAMSPACE_OWNER', 'false').lower() == 'true',
                timezone=os.getenv('TIMEZONE', 'Europe/Berlin'),
                language=os.getenv('LANGUAGE', 'de'),
                reminder_time=os.getenv('REMINDER_TIME', '08:00'),
                reminder_enabled=os.getenv('REMINDER_ENABLED', 'true').lower() == 'true'
            )
            self._users[0] = default_user
            logger.info("Loaded default user config from environment variables")
    
    def _load_from_file(self):
        """Load user configurations from JSON file."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    for user_data in data.get('users', []):
                        # Filter out comment fields that start with underscore
                        filtered_data = {k: v for k, v in user_data.items() if not k.startswith('_')}
                        user = UserConfig(**filtered_data)
                        self._users[user.telegram_user_id] = user
                logger.info(f"Loaded {len(self._users)} user configurations")
            except Exception as e:
                logger.error(f"Error loading user config: {e}")
    
    def save_to_file(self):
        """Save current user configurations to file."""
        try:
            data = {
                'users': [
                    {
                        'telegram_user_id': user.telegram_user_id,
                        'telegram_username': user.telegram_username,
                        'notion_api_key': user.notion_api_key,
                        'notion_database_id': user.notion_database_id,
                        'shared_notion_database_id': user.shared_notion_database_id,
                        'business_notion_database_id': user.business_notion_database_id,
                        'memo_database_id': user.memo_database_id,
                        'teamspace_owner_api_key': user.teamspace_owner_api_key,
                        'is_owner': user.is_owner,
                        'timezone': user.timezone,
                        'language': user.language,
                        'reminder_time': user.reminder_time,
                        'reminder_enabled': user.reminder_enabled
                    }
                    for user in self._users.values()
                    if user.telegram_user_id != 0  # Skip default user
                ]
            }
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(data['users'])} user configurations")
        except Exception as e:
            logger.error(f"Error saving user config: {e}")
    
    def get_user_config(self, telegram_user_id: int) -> Optional[UserConfig]:
        """Get configuration for a specific user."""
        # First check if we have a specific config for this user
        if telegram_user_id in self._users:
            return self._users[telegram_user_id]
        
        # If not, check if we have a default config (backward compatibility)
        if 0 in self._users:
            # Create a new config based on the default one
            default = self._users[0]
            new_user_config = UserConfig(
                telegram_user_id=telegram_user_id,
                telegram_username=f'user_{telegram_user_id}',
                notion_api_key=default.notion_api_key,
                notion_database_id=default.notion_database_id,
                shared_notion_database_id=getattr(default, 'shared_notion_database_id', None),
                business_notion_database_id=getattr(default, 'business_notion_database_id', None),
                memo_database_id=getattr(default, 'memo_database_id', None),
                teamspace_owner_api_key=getattr(default, 'teamspace_owner_api_key', None),
                is_owner=getattr(default, 'is_owner', False),
                timezone=getattr(default, 'timezone', 'Europe/Berlin'),
                language=getattr(default, 'language', 'de'),
                reminder_time=getattr(default, 'reminder_time', '08:00'),
                reminder_enabled=getattr(default, 'reminder_enabled', True)
            )
            self._users[telegram_user_id] = new_user_config
            del self._users[0]
            self.save_to_file()
            return new_user_config
        
        return None
    
    def add_user(self, user_config: UserConfig):
        """Add or update a user configuration."""
        self._users[user_config.telegram_user_id] = user_config
        self.save_to_file()
    
    def remove_user(self, telegram_user_id: int):
        """Remove a user configuration."""
        if telegram_user_id in self._users:
            del self._users[telegram_user_id]
            self.save_to_file()
    
    def get_all_users(self) -> Dict[int, UserConfig]:
        """Get all user configurations."""
        return self._users.copy()
    
    def is_valid_notion_key(self, api_key: str) -> bool:
        """Check if a Notion API key is valid (not a placeholder)."""
        if not api_key:
            return False
        
        # Check for common placeholder patterns
        placeholder_patterns = [
            'secret_xxx_',
            'your_notion_',
            'your_private_',
            'your_shared_',
            'your_business_',
            'secret_your_',
            'your_global_'
        ]
        
        api_key_lower = api_key.lower()
        for pattern in placeholder_patterns:
            if pattern in api_key_lower:
                return False
        
        # Valid Notion API keys should start with 'secret_' or 'ntn_'
        return api_key.startswith(('secret_', 'ntn_'))
    
    def is_valid_database_id(self, database_id: str) -> bool:
        """Check if a database ID is valid (not a placeholder)."""
        if not database_id:
            return False
        
        # Check for common placeholder patterns
        placeholder_patterns = [
            'your_notion_',
            'your_private_',
            'your_shared_',
            'your_business_',
            'your_global_'
        ]
        
        database_id_lower = database_id.lower()
        for pattern in placeholder_patterns:
            if pattern in database_id_lower:
                return False
        
        # Valid database IDs should be hexadecimal and reasonably long (at least 30 chars)
        # Notion database IDs can vary in length but are typically 31-32 characters
        clean_id = database_id.replace('-', '').replace('_', '')
        return len(clean_id) >= 30 and all(c in '0123456789abcdef' for c in clean_id.lower())
    
    def is_user_config_valid(self, user_config: UserConfig) -> bool:
        """Check if a user configuration has valid Notion credentials."""
        # Check required fields
        if not self.is_valid_notion_key(user_config.notion_api_key):
            return False
        
        if not self.is_valid_database_id(user_config.notion_database_id):
            return False
        
        # Check optional databases if configured
        if user_config.shared_notion_database_id:
            if not self.is_valid_database_id(user_config.shared_notion_database_id):
                return False
        
        if user_config.business_notion_database_id:
            if not self.is_valid_database_id(user_config.business_notion_database_id):
                return False
                
        if user_config.memo_database_id:
            if not self.is_valid_database_id(user_config.memo_database_id):
                return False
        
        return True
    
    def get_valid_users(self) -> Dict[int, UserConfig]:
        """Get only users with valid Notion configurations."""
        valid_users = {}
        for user_id, user_config in self._users.items():
            if user_config.telegram_user_id != 0 and self.is_user_config_valid(user_config):
                valid_users[user_id] = user_config
            elif user_config.telegram_user_id != 0:
                logger.warning(f"User {user_id} has invalid Notion configuration, skipping")
        
        return valid_users
    
    def get_users_for_reminders(self, current_time: str) -> list[UserConfig]:
        """Get users who should receive reminders at the current time."""
        users = []
        valid_users = self.get_valid_users()
        for user in valid_users.values():
            if user.reminder_enabled and user.reminder_time == current_time:
                users.append(user)
        return users
    
    def get_shared_database_api_key(self, user_config: UserConfig) -> str:
        """
        Get the appropriate API key for accessing the shared database.
        
        For Teamspace shared databases:
        - If user is the owner, use their own API key
        - If user is not the owner, use the teamspace_owner_api_key
        
        Args:
            user_config: User configuration
            
        Returns:
            str: API key to use for shared database access
        """
        if user_config.is_owner or not user_config.teamspace_owner_api_key:
            # Owner uses their own key, or fallback if no owner key configured
            return user_config.notion_api_key
        else:
            # Non-owners use the teamspace owner's API key for shared DB
            return user_config.teamspace_owner_api_key