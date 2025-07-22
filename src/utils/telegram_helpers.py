"""Utility functions for common Telegram bot operations."""

from typing import List, Optional, Dict, Any
from datetime import datetime, date
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from src.constants import StatusEmojis, DEFAULT_APPOINTMENTS_LIMIT
from src.models.appointment import Appointment


class TelegramFormatter:
    """Formatter for Telegram messages with consistent styling."""
    
    @staticmethod
    def format_appointment_list(
        appointments: List[Appointment], 
        title: str,
        show_database_source: bool = True,
        limit: int = DEFAULT_APPOINTMENTS_LIMIT
    ) -> str:
        """Format appointments into a readable message."""
        if not appointments:
            return f"*{title}*\n\n{StatusEmojis.INFO} Keine Termine gefunden."
        
        # Limit appointments if necessary
        display_appointments = appointments[:limit]
        has_more = len(appointments) > limit
        
        message_parts = [f"*{title}*"]
        
        if show_database_source:
            message_parts.append("")  # Empty line
        
        for appointment in display_appointments:
            formatted_appointment = TelegramFormatter._format_single_appointment(
                appointment, show_database_source
            )
            message_parts.append(formatted_appointment)
        
        if has_more:
            remaining = len(appointments) - limit
            message_parts.append(f"\n... und {remaining} weitere Termine")
        
        return "\n\n".join(message_parts)
    
    @staticmethod
    def _format_single_appointment(appointment: Appointment, show_source: bool = True) -> str:
        """Format a single appointment."""
        # Date formatting
        if appointment.start_datetime:
            date_str = appointment.start_datetime.strftime("%d.%m.%Y")
            time_str = appointment.start_datetime.strftime("%H:%M")
            
            if appointment.end_datetime:
                end_time = appointment.end_datetime.strftime("%H:%M")
                time_part = f"{time_str}-{end_time}"
            else:
                time_part = time_str
        else:
            date_str = "Unbekannt"
            time_part = "Ganztägig"
        
        # Source indicator
        source_indicator = ""
        if show_source:
            if hasattr(appointment, 'database_source'):
                source_indicator = f" {StatusEmojis.PRIVATE if appointment.database_source == 'private' else StatusEmojis.SHARED}"
        
        return f"📅 *{date_str}* um {time_part}{source_indicator}\n{appointment.title}"
    
    @staticmethod
    def format_status_message(
        private_status: bool, 
        shared_status: Optional[bool],
        user_name: str
    ) -> str:
        """Format database connection status message."""
        private_emoji = StatusEmojis.SUCCESS if private_status else StatusEmojis.ERROR
        
        if shared_status is None:
            shared_emoji = StatusEmojis.WARNING
            shared_text = "Nicht konfiguriert"
        else:
            shared_emoji = StatusEmojis.SUCCESS if shared_status else StatusEmojis.ERROR
            shared_text = "Verfügbar" if shared_status else "Fehler"
        
        return (
            f"Hallo *{user_name}*! 👋\n\n"
            f"*{StatusEmojis.INFO} Datenbankstatus:*\n"
            f"👤 Private DB: {private_emoji}\n"
            f"🌐 Gemeinsame DB: {shared_emoji} {shared_text}\n\n"
            f"Wähle eine Option:"
        )
    


class KeyboardBuilder:
    """Builder for common keyboard layouts."""
    
    @staticmethod
    def create_main_menu() -> InlineKeyboardMarkup:
        """Create the main menu keyboard."""
        from src.constants import MenuButtons, CallbackData
        
        keyboard = [
            [
                InlineKeyboardButton(MenuButtons.TODAY_TOMORROW, callback_data=CallbackData.TODAY_TOMORROW),
                InlineKeyboardButton(MenuButtons.RECENT_MEMOS, callback_data=CallbackData.RECENT_MEMOS)
            ],
            [
                InlineKeyboardButton(MenuButtons.NEW_APPOINTMENT, callback_data=CallbackData.ADD_APPOINTMENT),
                InlineKeyboardButton(MenuButtons.NEW_MEMO, callback_data=CallbackData.ADD_MEMO)
            ],
            [
                InlineKeyboardButton(MenuButtons.HELP, callback_data=CallbackData.HELP)
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    
    @staticmethod
    def create_back_to_menu_keyboard() -> InlineKeyboardMarkup:
        """Create a simple back to menu keyboard."""
        keyboard = [
            [InlineKeyboardButton("🔙 Zurück zum Hauptmenü", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)
