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
    
    @staticmethod
    def format_memo_list(memos: List[Dict[str, Any]], title: str = "Letzte Memos") -> str:
        """Format memos into a readable message."""
        if not memos:
            return f"*{title}*\n\n{StatusEmojis.INFO} Keine Memos gefunden."
        
        message_parts = [f"*{title}*\n"]
        
        for i, memo in enumerate(memos, 1):
            status = memo.get('status', 'Unbekannt')
            aufgabe = memo.get('aufgabe', 'Unbekannte Aufgabe')
            due_date = memo.get('faelligkeitsdatum')
            
            # Status emoji
            status_emoji = {
                'Nicht begonnen': '⚪',
                'In Arbeit': '🟡', 
                'Erledigt': '🟢'
            }.get(status, '⚪')
            
            # Due date formatting
            due_str = ""
            if due_date:
                if isinstance(due_date, str):
                    due_str = f" | Fällig: {due_date}"
                elif isinstance(due_date, datetime):
                    due_str = f" | Fällig: {due_date.strftime('%d.%m.%Y')}"
            
            message_parts.append(f"{i}. {status_emoji} {aufgabe}{due_str}")
        
        return "\n".join(message_parts)


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
    def create_partner_relevance_keyboard(user_id: int) -> InlineKeyboardMarkup:
        """Create partner relevance selection keyboard."""
        from src.constants import CallbackData
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Ja, für Partner relevant", 
                                   callback_data=f"{CallbackData.PARTNER_RELEVANT_YES}_{user_id}"),
                InlineKeyboardButton("❌ Nein, nur privat", 
                                   callback_data=f"{CallbackData.PARTNER_RELEVANT_NO}_{user_id}")
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


class DateTimeHelpers:
    """Helper functions for date and time operations."""
    
    @staticmethod
    def format_relative_date(target_date: date) -> str:
        """Format date relative to today (heute, morgen, etc.)."""
        today = date.today()
        diff = (target_date - today).days
        
        if diff == 0:
            return "heute"
        elif diff == 1:
            return "morgen"
        elif diff == 2:
            return "übermorgen"
        elif diff == -1:
            return "gestern"
        elif diff > 0 and diff <= 7:
            return f"in {diff} Tagen"
        elif diff < 0 and diff >= -7:
            return f"vor {abs(diff)} Tagen"
        else:
            return target_date.strftime("%d.%m.%Y")
    
    @staticmethod
    def is_business_hours(dt: datetime) -> bool:
        """Check if datetime falls within business hours (8-18, Mon-Fri)."""
        # Monday is 0, Sunday is 6
        if dt.weekday() >= 5:  # Saturday or Sunday
            return False
        
        return 8 <= dt.hour < 18