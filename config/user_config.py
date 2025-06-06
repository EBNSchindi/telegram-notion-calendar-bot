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
    notion_api_key: str
    notion_database_id: str  # Private database
    shared_notion_api_key: str = None  # API key for shared database (can be same as private)
    shared_notion_database_id: str = None  # Shared database ID
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
        # Check if we have notion API config (TELEGRAM_BOT_TOKEN is handled by the bot itself)
        if os.getenv('NOTION_API_KEY') and os.getenv('NOTION_DATABASE_ID'):
            # Create default user config from env
            default_user = UserConfig(
                telegram_user_id=0,  # Will be updated on first message
                telegram_username='default',
                notion_api_key=os.getenv('NOTION_API_KEY', ''),
                notion_database_id=os.getenv('NOTION_DATABASE_ID', ''),
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
                        user = UserConfig(**user_data)
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
                shared_notion_api_key=getattr(default, 'shared_notion_api_key', None),
                shared_notion_database_id=getattr(default, 'shared_notion_database_id', None),
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
    
    def get_users_for_reminders(self, current_time: str) -> list[UserConfig]:
        """Get users who should receive reminders at the current time."""
        users = []
        for user in self._users.values():
            if user.reminder_enabled and user.reminder_time == current_time:
                users.append(user)
        return users