import os
from dotenv import load_dotenv
from typing import Optional

# Load environment variables from .env file
load_dotenv()

class Settings:
    def __init__(self):
        # Telegram Bot Configuration
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        
        # Notion Configuration
        self.notion_api_key = os.getenv('NOTION_API_KEY', '')
        self.notion_database_id = os.getenv('NOTION_DATABASE_ID', '')
        
        # Application Settings
        self.timezone = os.getenv('TIMEZONE', 'Europe/Berlin')
        self.language = os.getenv('LANGUAGE', 'de')
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        self.environment = os.getenv('ENVIRONMENT', 'production')
        
        # Validate required settings
        self._validate()
    
    def _validate(self):
        """Validate required configuration."""
        errors = []
        
        if not self.telegram_token:
            errors.append("TELEGRAM_BOT_TOKEN is required")
            
        if not self.notion_api_key:
            errors.append("NOTION_API_KEY is required")
            
        if not self.notion_database_id:
            errors.append("NOTION_DATABASE_ID is required")
            
        if errors and self.environment != 'testing':
            raise ValueError(f"Configuration errors: {', '.join(errors)}")
    
    @property
    def is_development(self) -> bool:
        return self.environment == 'development'
    
    @property
    def is_testing(self) -> bool:
        return self.environment == 'testing'