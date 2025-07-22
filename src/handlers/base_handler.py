"""Base handler class with common functionality for all Telegram handlers."""

import logging
from typing import Optional, List, Union
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from telegram.ext import ContextTypes
import pytz

from config.user_config import UserConfig
from src.constants import DEFAULT_TIMEZONE, MAX_TELEGRAM_MESSAGE_LENGTH, StatusEmojis

logger = logging.getLogger(__name__)


class BaseHandler:
    """Base class for all Telegram bot handlers with common functionality."""
    
    def __init__(self, user_config: UserConfig):
        self.user_config = user_config
        self.timezone = self._setup_timezone(user_config.timezone)
    
    def _setup_timezone(self, timezone_str: Optional[str] = None) -> pytz.BaseTzInfo:
        """Setup timezone with fallback to default."""
        timezone_str = timezone_str or DEFAULT_TIMEZONE
        try:
            return pytz.timezone(timezone_str)
        except Exception as e:
            logger.warning(f"Invalid timezone '{timezone_str}', falling back to {DEFAULT_TIMEZONE}: {e}")
            return pytz.timezone(DEFAULT_TIMEZONE)
    
    async def answer_callback_query(
        self, 
        update: Update, 
        text: Optional[str] = None,
        show_alert: bool = False
    ) -> None:
        """Answer callback query with standardized handling."""
        try:
            await update.callback_query.answer(text=text, show_alert=show_alert)
        except Exception as e:
            logger.error(f"Failed to answer callback query: {e}")
    
    def create_inline_keyboard(
        self, 
        buttons: List[List[tuple[str, str]]]
    ) -> InlineKeyboardMarkup:
        """Create inline keyboard from button data.
        
        Args:
            buttons: List of button rows, each containing (text, callback_data) tuples
            
        Returns:
            InlineKeyboardMarkup object
        """
        keyboard = []
        for row in buttons:
            keyboard_row = []
            for text, callback_data in row:
                keyboard_row.append(InlineKeyboardButton(text, callback_data=callback_data))
            keyboard.append(keyboard_row)
        
        return InlineKeyboardMarkup(keyboard)
    
    def create_force_reply(self, placeholder: str) -> ForceReply:
        """Create a ForceReply with placeholder text."""
        return ForceReply(input_field_placeholder=placeholder, selective=True)
    
    def truncate_message(self, message: str, max_length: int = MAX_TELEGRAM_MESSAGE_LENGTH) -> str:
        """Truncate message to Telegram limits."""
        if len(message) <= max_length:
            return message
        
        truncated = message[:max_length - 4]  # Reserve space for "..."
        # Try to truncate at word boundary
        last_space = truncated.rfind(' ')
        if last_space > max_length * 0.8:  # Only if we don't lose too much content
            truncated = truncated[:last_space]
        
        return truncated + "..."
    
    def format_error_message(self, error: str, context: Optional[str] = None) -> str:
        """Format standardized error message."""
        base_msg = f"{StatusEmojis.ERROR} {error}"
        if context:
            base_msg += f"\n\n💡 {context}"
        return base_msg
    
    def format_success_message(self, message: str) -> str:
        """Format standardized success message."""
        return f"{StatusEmojis.SUCCESS} {message}"
    
    def format_warning_message(self, message: str) -> str:
        """Format standardized warning message."""
        return f"{StatusEmojis.WARNING} {message}"
    
    def format_info_message(self, message: str) -> str:
        """Format standardized info message."""
        return f"{StatusEmojis.INFO} {message}"
    
    async def send_message_safe(
        self, 
        update: Update, 
        text: str,
        parse_mode: Optional[str] = None,
        reply_markup: Optional[Union[InlineKeyboardMarkup, ForceReply]] = None,
        edit_message: bool = False
    ) -> None:
        """Send message with error handling and truncation."""
        try:
            text = self.truncate_message(text)
            
            if edit_message and update.callback_query:
                await update.callback_query.edit_message_text(
                    text=text,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup
                )
            else:
                message_obj = update.effective_message
                if not message_obj:
                    logger.error("No effective message found for sending")
                    return
                    
                await message_obj.reply_text(
                    text=text,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup
                )
                
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            # Fallback: try to send a simple error message
            try:
                if update.effective_message:
                    await update.effective_message.reply_text(
                        f"{StatusEmojis.ERROR} Ein Fehler ist aufgetreten."
                    )
            except Exception as fallback_error:
                logger.error(f"Failed to send fallback message: {fallback_error}")
    
    def validate_user_input(self, input_text: str, max_length: int = 1000) -> bool:
        """Validate user input for basic security and length."""
        if not input_text or not input_text.strip():
            return False
        
        if len(input_text) > max_length:
            return False
        
        # Basic security: no script tags or suspicious patterns
        suspicious_patterns = ['<script', 'javascript:', 'data:', 'vbscript:']
        input_lower = input_text.lower()
        
        return not any(pattern in input_lower for pattern in suspicious_patterns)
    
    def get_user_mention(self, update: Update) -> str:
        """Get safe user mention for logging/display."""
        user = update.effective_user
        if not user:
            return "Unknown User"
        
        # Use first name and ID for identification
        return f"{user.first_name or 'User'} ({user.id})"