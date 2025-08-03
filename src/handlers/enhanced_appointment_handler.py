"""Enhanced appointment handler with combined database support."""
import logging
from datetime import datetime, timedelta, date
from typing import List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from telegram.ext import ContextTypes
import pytz

from src.models.appointment import Appointment
from src.services.combined_appointment_service import CombinedAppointmentService
from src.services.ai_assistant_service import AIAssistantService
from src.handlers.memo_handler import MemoHandler
from config.user_config import UserConfig, UserConfigManager
from src.utils.robust_time_parser import RobustTimeParser
from src.utils.rate_limiter import rate_limit
from src.utils.input_validator import InputValidator
from pydantic import ValidationError
from src.constants import (
    DEFAULT_RATE_LIMIT_REQUESTS,
    DEFAULT_RATE_LIMIT_WINDOW,
    AI_RATE_LIMIT_REQUESTS,
    AI_RATE_LIMIT_WINDOW,
    DEFAULT_APPOINTMENTS_LIMIT,
    MAX_ERROR_MESSAGE_LENGTH,
    MenuButtons,
    CallbackData
)
from src.constants import (
    DATABASE_STATUS_HEADER,
    DATABASE_PRIVATE,
    DATABASE_SHARED,
    MENU_CHOOSE_ACTION,
    WELCOME_MESSAGE,
    WELCOME_CALENDAR_BOT,
    ERROR_NOT_CONFIGURED_FULL
)

# Define missing constants locally
ERROR_INVALID_INPUT = "❌ Ungültige Eingabe. Bitte versuche es erneut."
AI_ANALYZING_APPOINTMENT = "🤖 KI analysiert deinen Termin..."
STATUS_NOT_CONFIGURED = "❌ Nicht konfiguriert"

logger = logging.getLogger(__name__)


class EnhancedAppointmentHandler:
    """Enhanced handler for appointment-related Telegram commands with combined database support."""
    
    def __init__(self, user_config: UserConfig, user_config_manager: Optional[UserConfigManager] = None):
        self.user_config = user_config
        self.user_config_manager = user_config_manager
        self.combined_service = CombinedAppointmentService(user_config, user_config_manager)
        self.ai_service = AIAssistantService()
        self.memo_handler = MemoHandler(user_config)
        
        # Handle timezone with fallback
        timezone_str = user_config.timezone if user_config.timezone else 'Europe/Berlin'
        try:
            self.timezone = pytz.timezone(timezone_str)
        except Exception as e:
            logger.warning(f"Invalid timezone '{timezone_str}', falling back to Europe/Berlin: {e}")
            self.timezone = pytz.timezone('Europe/Berlin')
    
    def get_back_to_menu_keyboard(self) -> InlineKeyboardMarkup:
        """Get a keyboard with only the 'Back to Menu' button."""
        keyboard = [[InlineKeyboardButton("🔙 Zurück zum Hauptmenü", callback_data="back_to_menu")]]
        return InlineKeyboardMarkup(keyboard)
    
    @rate_limit(max_requests=DEFAULT_RATE_LIMIT_REQUESTS, time_window=DEFAULT_RATE_LIMIT_WINDOW)
    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show the main menu with inline buttons."""
        user = update.effective_user
        
        # Test database connections
        private_ok, shared_ok = await self.combined_service.test_connections()
        
        # Test memo database connection
        memo_ok = False
        if self.memo_handler.is_memo_service_available():
            try:
                memo_ok = await self.memo_handler.memo_service.test_connection()
            except Exception as e:
                logger.error(f"Memo database connection test failed: {e}")
                memo_ok = False
        
        # Create status message
        private_status = "✅" if private_ok else "❌"
        if shared_ok is None:
            shared_status = STATUS_NOT_CONFIGURED
        else:
            shared_status = "✅" if shared_ok else "❌"
        
        # Memo status
        if not self.memo_handler.is_memo_service_available():
            memo_status = STATUS_NOT_CONFIGURED
        else:
            memo_status = "✅" if memo_ok else "❌"
        
        status_text = (
            f"{WELCOME_MESSAGE}\n\n"
            f"{WELCOME_CALENDAR_BOT}\n\n"
            f"{DATABASE_STATUS_HEADER}\n"
            f"{DATABASE_PRIVATE}: {private_status}\n"
            f"{DATABASE_SHARED}: {shared_status}\n"
            f"📝 Memo Datenbank: {memo_status}\n\n"
            f"{MENU_CHOOSE_ACTION}"
        )
        
        # Create simplified inline keyboard (2x2 + 1)
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
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send or edit message depending on whether this is a callback or new message
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=status_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                text=status_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle inline keyboard callbacks.
        
        Routes callback queries to appropriate handler methods based on the
        callback data. Supports both new simplified menu and legacy menu items.
        
        Args:
            update: Telegram update containing the callback query
            context: Telegram context for the update
        """
        query = update.callback_query
        await query.answer()
        
        if query.data == CallbackData.TODAY_TOMORROW:
            await self.today_tomorrow_appointments_callback(update, context)
        elif query.data == CallbackData.RECENT_MEMOS:
            await self.memo_handler.show_recent_memos(update, context)
        elif query.data == CallbackData.ADD_APPOINTMENT:
            await self.add_appointment_callback(update, context)
        elif query.data == CallbackData.ADD_MEMO:
            await self.memo_handler.prompt_for_new_memo(update, context)
        elif query.data == CallbackData.HELP:
            await self.help_callback(update, context)
        elif query.data == "main_menu" or query.data == "back_to_menu":
            await self.show_main_menu(update, context)
        elif query.data.startswith("partner_relevant_"):
            await self.handle_partner_relevance_callback(update, context)
        # Legacy support for old menu items
        elif query.data == "today":
            await self.today_appointments_callback(update, context)
        elif query.data == "tomorrow":
            await self.tomorrow_appointments_callback(update, context)
        elif query.data == "list":
            await self.list_appointments_callback(update, context)
        elif query.data == "add":
            await self.add_appointment_callback(update, context)
    
    async def today_tomorrow_appointments_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle combined today and tomorrow appointments callback."""
        try:
            # Get appointments for today and tomorrow
            today_appointments = await self.combined_service.get_today_appointments()
            tomorrow_appointments = await self.combined_service.get_tomorrow_appointments()
            
            today = datetime.now(self.timezone).date()
            tomorrow = (datetime.now(self.timezone) + timedelta(days=1)).date()
            
            message = "📅 *Termine für Heute & Morgen*\n\n"
            
            # Today's appointments
            if today_appointments:
                message += f"*Heute ({today.strftime('%d.%m.%Y')}):*\n"
                for i, apt_src in enumerate(today_appointments, 1):
                    apt = apt_src.appointment
                    source_icon = "🌐" if apt_src.is_shared else "👤"
                    local_date = apt.date.astimezone(self.timezone) if apt.date.tzinfo else self.timezone.localize(apt.date)
                    message += f"{i}. {source_icon} *{local_date.strftime('%H:%M')}* - {apt.title}"
                    if apt.location:
                        message += f" (📍 {apt.location})"
                    message += "\n"
                    if apt.description:
                        message += f"   📝 _{apt.description}_\n"
                message += "\n"
            else:
                message += f"*Heute ({today.strftime('%d.%m.%Y')}):*\nKeine Termine! 🎉\n\n"
            
            # Tomorrow's appointments
            if tomorrow_appointments:
                message += f"*Morgen ({tomorrow.strftime('%d.%m.%Y')}):*\n"
                for i, apt_src in enumerate(tomorrow_appointments, 1):
                    apt = apt_src.appointment
                    source_icon = "🌐" if apt_src.is_shared else "👤"
                    local_date = apt.date.astimezone(self.timezone) if apt.date.tzinfo else self.timezone.localize(apt.date)
                    message += f"{i}. {source_icon} *{local_date.strftime('%H:%M')}* - {apt.title}"
                    if apt.location:
                        message += f" (📍 {apt.location})"
                    message += "\n"
                    if apt.description:
                        message += f"   📝 _{apt.description}_\n"
            else:
                message += f"*Morgen ({tomorrow.strftime('%d.%m.%Y')}):*\nKeine Termine! 🎉"
            
            if not today_appointments and not tomorrow_appointments:
                message += "\nPerfekt für eine entspannte Zeit! 🌟"
            
            # Add back button
            reply_markup = self.get_back_to_menu_keyboard()
            
            await update.callback_query.edit_message_text(
                text=message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error getting today/tomorrow appointments: {e}")
            await update.callback_query.edit_message_text(
                "❌ Fehler beim Abrufen der Termine für heute und morgen."
            )
    
    async def today_appointments_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle today appointments callback."""
        try:
            appointments = await self.combined_service.get_today_appointments()
            
            today = datetime.now(self.timezone).date()
            title = f"Termine für heute ({today.strftime('%d.%m.%Y')})"
            
            message = self.combined_service.format_appointments_for_telegram(appointments, title)
            
            # Add back button
            reply_markup = self.get_back_to_menu_keyboard()
            
            await update.callback_query.edit_message_text(
                text=message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error getting today's appointments: {e}")
            await update.callback_query.edit_message_text(
                "❌ Fehler beim Abrufen der heutigen Termine."
            )
    
    async def tomorrow_appointments_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle tomorrow appointments callback."""
        try:
            appointments = await self.combined_service.get_tomorrow_appointments()
            
            tomorrow = (datetime.now(self.timezone) + timedelta(days=1)).date()
            title = f"Termine für morgen ({tomorrow.strftime('%d.%m.%Y')})"
            
            message = self.combined_service.format_appointments_for_telegram(appointments, title)
            
            # Add back button
            reply_markup = self.get_back_to_menu_keyboard()
            
            await update.callback_query.edit_message_text(
                text=message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error getting tomorrow's appointments: {e}")
            await update.callback_query.edit_message_text(
                "❌ Fehler beim Abrufen der morgigen Termine."
            )
    
    async def list_appointments_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle list appointments callback."""
        try:
            appointments = await self.combined_service.get_upcoming_appointments()
            
            # Limit to next 10 appointments
            appointments = appointments[:10]
            
            message = self.combined_service.format_appointments_for_telegram(
                appointments, "Kommende Termine"
            )
            
            if len(appointments) == 10:
                message += "\n\n_Nur die nächsten 10 Termine werden angezeigt._"
            
            # Add back button
            reply_markup = self.get_back_to_menu_keyboard()
            
            await update.callback_query.edit_message_text(
                text=message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error getting appointments: {e}")
            await update.callback_query.edit_message_text(
                "❌ Fehler beim Abrufen der Termine."
            )
    
    async def add_appointment_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle add appointment callback."""
        help_text = (
            "➕ *Neuen Termin hinzufügen*\n\n"
            "*Beispiele:*\n"
            "• `morgen 14:00 Meeting`\n"
            "• `heute 4 PM Arzttermin`\n"
            "• `25.12.2024 18 Uhr Weihnachtsfeier`\n"
            "• `morgen halb 10 Frühstück`\n\n"
            "*Unterstützte Zeitformate:*\n"
            "• `14:00`, `14.00`, `1430`\n"
            "• `16 Uhr`, `4 PM`, `4 pm`\n"
            "• `halb 3`, `quarter past 2`\n"
            "• `viertel vor 5`, `quarter to 5`\n\n"
            "*Datum-Formate:*\n"
            "• `heute`, `morgen`\n"
            "• `25.12.2024`, `2024-12-25`\n\n"
            "💡 *Gib deinen Termin ein (ohne /add):*"
        )
        
        # Answer the callback query first
        await update.callback_query.answer()
        
        # Use ForceReply with placeholder text (must be a new message, not edit)
        reply_markup = ForceReply(
            selective=True,
            input_field_placeholder="morgen 14:00 Meeting mit Team"
        )
        
        await update.callback_query.message.reply_text(
            text=help_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def reminder_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle reminder settings callback."""
        status = "✅ Aktiv" if self.user_config.reminder_enabled else "❌ Deaktiviert"
        
        reminder_text = (
            "⚙️ *Erinnerungseinstellungen*\n\n"
            f"*Status:* {status}\n"
            f"*Zeit:* {self.user_config.reminder_time}\n\n"
            "*Befehle:*\n"
            "• `/reminder on` - Aktivieren\n"
            "• `/reminder off` - Deaktivieren\n"
            "• `/reminder time HH:MM` - Zeit ändern\n"
            "• `/reminder test` - Test senden"
        )
        
        # Add back button
        keyboard = [[InlineKeyboardButton("🔙 Zurück zum Menü", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            text=reminder_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def help_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle help callback."""
        reminder_time = self.user_config.reminder_time
        help_text = f"""
❓ *Hilfe - Kalender & Memo Bot*

*📅 Termine erstellen:*
Schreibe einfach deinen Termin:
• "morgen 15 Uhr Zahnarzttermin"
• "Montag 9 Uhr Meeting im Büro"
• "25.12. 18:30 Weihnachtsessen bei Oma"

*📝 Memos erstellen:*
Schreibe deine Aufgabe oder Notiz:
• "Präsentation vorbereiten bis Freitag"
• "Einkaufsliste: Milch, Brot, Butter"
• "Website Projekt: Client Feedback einholen"

*⏰ Erinnerungen:*
Täglich um {reminder_time} Uhr erhältst du eine Übersicht
deiner Termine für heute und morgen.

*🎯 Hauptfunktionen:*
📅 *Termine Heute & Morgen* - Schnellübersicht
📝 *Letzte 10 Memos* - Deine aktuellen Aufgaben
➕ *Neuer Termin* - Termin mit KI-Unterstützung erstellen
➕ *Neues Memo* - Aufgabe mit KI-Unterstützung erstellen

*🤖 KI-Unterstützung:*
Der Bot versteht natürliche Sprache! Schreibe einfach
wie du sprechen würdest:
• "Zahnarzt morgen um 3" → Termin am nächsten Tag 15:00
• "Einkaufen bis Freitag" → Memo mit Fälligkeitsdatum

*🗄️ Datenbanken:*
👤 *Private Termine* - Nur deine Termine
🌐 *Gemeinsame Termine* - Geteilte Termine
💼 *Business Termine* - Automatisch aus E-Mails
📝 *Memos* - Deine Aufgaben und Notizen

*💡 Tipp:*
Verwende das Hauptmenü für schnellen Zugriff auf alle
Funktionen. Der Bot lernt aus deinen Eingaben!
        """
        
        # Add back button
        keyboard = [[InlineKeyboardButton("🔙 Zurück zum Menü", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            text=help_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    # Legacy command methods for backward compatibility
    @rate_limit(max_requests=10, time_window=60)  # 10 appointments per minute
    async def add_appointment(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /add command to create new appointment."""
        user_id = update.effective_user.id
        logger.info(f"Received /add command from user {user_id} with args: {context.args}")
        
        # Validate Telegram input
        try:
            InputValidator.validate_telegram_input(
                user_id=user_id,
                username=update.effective_user.username,
                message_text=update.message.text or ""
            )
        except ValidationError as e:
            await update.message.reply_text(ERROR_INVALID_INPUT)
            logger.warning(f"Invalid Telegram input from user {user_id}: {e}")
            return
        
        if not context.args:
            await update.message.reply_text(
                "❌ Bitte gib einen Termin an.\n\n"
                "*Format:* `/add <Datum> <Zeit> <Titel> [Beschreibung]`\n\n"
                "*Beispiele:*\n"
                "• `/add morgen 14:00 Meeting`\n"
                "• `/add 25.12.2024 18:00 Weihnachtsfeier`\n"
                "• `/add heute 4 PM Arzttermin Wichtiger Termin`",
                parse_mode='Markdown'
            )
            return
        
        try:
            # Parse command arguments
            date_time, title, description = self._parse_add_command(context.args)
            
            # Validate appointment input
            try:
                validated_input = InputValidator.validate_appointment_input(
                    title=title,
                    description=description
                )
                title = validated_input.get('title', title)
                description = validated_input.get('description', description)
            except ValidationError as e:
                await update.message.reply_text(
                    f"❌ Ungültige Termindaten: {e.errors()[0]['msg']}\n"
                    "Bitte überprüfe deine Eingabe."
                )
                return
            
            # Create appointment
            appointment = Appointment(
                title=title,
                date=date_time,
                description=description
            )
            
            # Save to private database by default
            page_id = await self.combined_service.create_appointment(appointment, use_shared=False)
            appointment.notion_page_id = page_id
            
            # Send confirmation
            timezone_str = self.user_config.timezone if self.user_config.timezone else 'Europe/Berlin'
            formatted_appointment = appointment.format_for_telegram(timezone_str)
            await update.message.reply_text(
                f"✅ Termin erfolgreich erstellt!\n\n{formatted_appointment}",
                parse_mode='Markdown',
                reply_markup=self.get_back_to_menu_keyboard()
            )
            
            logger.info(f"Created appointment: {title} at {date_time}")
            
        except ValueError as e:
            await update.message.reply_text(f"❌ Eingabefehler: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to create appointment: {e}", exc_info=True)
            
            # Provide more specific error messages
            error_msg = str(e).lower()
            if "notion" in error_msg:
                await update.message.reply_text(
                    f"❌ Notion-Fehler: {str(e)}\n\n"
                    "💡 Mögliche Ursachen:\n"
                    "• Notion API Key ungültig\n"
                    "• Datenbank nicht gefunden\n"
                    "• Keine Berechtigung für Datenbank\n"
                    "• Datenbank-Schema inkorrekt"
                )
            elif "connection" in error_msg or "timeout" in error_msg:
                await update.message.reply_text(
                    "❌ Verbindungsfehler zur Notion API.\n\n"
                    "Bitte versuche es in ein paar Sekunden erneut."
                )
            else:
                await update.message.reply_text(
                    f"❌ Unbekannter Fehler beim Erstellen des Termins:\n\n"
                    f"`{str(e)}`\n\n"
                    "Bitte kontaktiere den Administrator."
                )
    
    @rate_limit(max_requests=15, time_window=60)  # 15 queries per minute
    async def today_appointments(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /today command."""
        try:
            appointments = await self.combined_service.get_today_appointments()
            
            today = datetime.now(self.timezone).date()
            title = f"Termine für heute ({today.strftime('%d.%m.%Y')})"
            
            message = self.combined_service.format_appointments_for_telegram(appointments, title)
            await update.message.reply_text(message, parse_mode='Markdown', reply_markup=self.get_back_to_menu_keyboard())
            
        except Exception as e:
            logger.error(f"Failed to get today's appointments: {e}")
            await update.message.reply_text(
                "❌ Fehler beim Abrufen der heutigen Termine. Bitte versuche es erneut.",
                reply_markup=self.get_back_to_menu_keyboard()
            )
    
    @rate_limit(max_requests=15, time_window=60)  # 15 queries per minute
    async def tomorrow_appointments(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /tomorrow command."""
        try:
            appointments = await self.combined_service.get_tomorrow_appointments()
            
            tomorrow = (datetime.now(self.timezone) + timedelta(days=1)).date()
            title = f"Termine für morgen ({tomorrow.strftime('%d.%m.%Y')})"
            
            message = self.combined_service.format_appointments_for_telegram(appointments, title)
            await update.message.reply_text(message, parse_mode='Markdown', reply_markup=self.get_back_to_menu_keyboard())
            
        except Exception as e:
            logger.error(f"Failed to get tomorrow's appointments: {e}")
            await update.message.reply_text(
                "❌ Fehler beim Abrufen der morgigen Termine. Bitte versuche es erneut.",
                reply_markup=self.get_back_to_menu_keyboard()
            )
    
    @rate_limit(max_requests=15, time_window=60)  # 15 queries per minute
    async def list_appointments(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /list command."""
        try:
            appointments = await self.combined_service.get_upcoming_appointments()
            
            # Limit to next 10 appointments
            appointments = appointments[:10]
            
            message = self.combined_service.format_appointments_for_telegram(
                appointments, "Kommende Termine"
            )
            
            if len(appointments) == 10:
                message += "\n\n_Nur die nächsten 10 Termine werden angezeigt._"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Failed to list appointments: {e}")
            await update.message.reply_text(
                "❌ Fehler beim Abrufen der Termine. Bitte versuche es erneut.",
                reply_markup=self.get_back_to_menu_keyboard()
            )
    
    def _parse_add_command(self, args: List[str]) -> tuple[datetime, str, str]:
        """Parse arguments for add command with smart time parsing.
        
        Handles various German and English time formats including:
        - Standard: "14:00", "2:30 PM"
        - German colloquial: "14 Uhr", "halb 6", "viertel vor 5"
        - English colloquial: "half past 3", "quarter to 5"
        
        Args:
            args: List of command arguments [date, time, title, ...description]
            
        Returns:
            tuple: (datetime, title, description)
            
        Raises:
            ValueError: If arguments are insufficient or invalid
            
        Examples:
            - ["morgen", "14:00", "Meeting"] -> (tomorrow 14:00, "Meeting", None)
            - ["morgen", "halb", "6", "Dinner"] -> (tomorrow 17:30, "Dinner", None)
            - ["heute", "4", "PM", "Arzt", "Checkup"] -> (today 16:00, "Arzt", "Checkup")
        """
        if len(args) < 3:
            raise ValueError("Mindestens Datum, Zeit und Titel sind erforderlich")
        
        date_str = args[0]
        
        # Smart parsing for German time formats
        if len(args) >= 3 and args[2].lower() == "uhr":
            # "morgen 14 Uhr kicken" -> time_str = "14 Uhr"
            time_str = f"{args[1]} {args[2]}"
            title_and_desc = args[3:]
        elif len(args) >= 3 and args[1].lower() in ["halb", "viertel"]:
            # "morgen halb 6 kicken" -> time_str = "halb 6"
            # "morgen viertel vor 5 kicken" -> time_str = "viertel vor 5" (needs more args)
            if args[1].lower() == "viertel" and len(args) >= 5:
                # "viertel vor/nach X"
                time_str = f"{args[1]} {args[2]} {args[3]}"
                title_and_desc = args[4:]
            else:
                # "halb X"
                time_str = f"{args[1]} {args[2]}"
                title_and_desc = args[3:]
        else:
            # Normal parsing: "morgen 14:00 kicken"
            time_str = args[1]
            title_and_desc = args[2:]
        
        if not title_and_desc:
            raise ValueError("Titel ist erforderlich")
        
        # Parse date and time
        date_time = self._parse_date_time(date_str, time_str)
        
        # Split title and description
        if len(title_and_desc) == 1:
            title = title_and_desc[0]
            description = None
        else:
            title = title_and_desc[0]
            description = " ".join(title_and_desc[1:]) if len(title_and_desc) > 1 else None
        
        if not title.strip():
            raise ValueError("Titel darf nicht leer sein")
        
        return date_time, title.strip(), description
    
    def _parse_date_time(self, date_str: str, time_str: str) -> datetime:
        """Parse date and time strings into datetime object."""
        now = datetime.now(self.timezone)
        
        # Handle relative dates
        if date_str.lower() in ['heute', 'today']:
            target_date = now.date()
        elif date_str.lower() in ['morgen', 'tomorrow']:
            target_date = (now + timedelta(days=1)).date()
        elif date_str.lower() in ['übermorgen', 'day after tomorrow']:
            target_date = (now + timedelta(days=2)).date()
        else:
            # Try to parse as weekday name first
            target_date = self._parse_weekday(date_str, now)
            if target_date is None:
                # Parse absolute date
                try:
                    for fmt in ['%d.%m.%Y', '%d.%m.%y', '%Y-%m-%d']:
                        try:
                            target_date = datetime.strptime(date_str, fmt).date()
                            break
                        except ValueError:
                            continue
                    else:
                        raise ValueError(f"Ungültiges Datumsformat: {date_str}")
                except ValueError:
                    raise ValueError(f"Ungültiges Datum: {date_str}")
        
        # Parse time using robust time parser
        try:
            time_obj = RobustTimeParser.parse_time(time_str)
        except ValueError as e:
            raise ValueError(str(e))
        
        # Combine date and time
        date_time = datetime.combine(target_date, time_obj)
        
        # Localize to timezone
        date_time = self.timezone.localize(date_time)
        
        # Validate that appointment is in the future
        if date_time <= now:
            raise ValueError("Termin muss in der Zukunft liegen")
        
        return date_time
    
    def _parse_weekday(self, date_str: str, now: datetime) -> Optional[date]:
        """Parse weekday names and return next occurrence, or None if not a weekday."""
        weekday_names = {
            'montag': 0, 'monday': 0,
            'dienstag': 1, 'tuesday': 1,
            'mittwoch': 2, 'wednesday': 2,
            'donnerstag': 3, 'thursday': 3,
            'freitag': 4, 'friday': 4,
            'samstag': 5, 'saturday': 5,
            'sonntag': 6, 'sunday': 6,
        }
        
        date_str_lower = date_str.lower().strip()
        
        if date_str_lower in weekday_names:
            target_weekday = weekday_names[date_str_lower]
            current_weekday = now.weekday()
            
            # Calculate days until next occurrence of this weekday
            days_ahead = target_weekday - current_weekday
            if days_ahead <= 0:  # Target day already happened this week
                days_ahead += 7  # Take next week
            
            return (now + timedelta(days=days_ahead)).date()
        
        return None
    
    async def process_ai_appointment_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Process a message using AI to extract appointment information.
        
        This method handles natural language appointment creation with AI assistance.
        It extracts appointment details including duration, then prompts for partner relevance.
        
        Flow:
        1. Validates user input and checks AI service availability
        2. Uses AI to extract appointment data from natural language
        3. Displays extracted information for user confirmation
        4. Prompts for partner relevance with inline buttons
        5. Stores pending appointment in context for callback handling
        
        Args:
            update: Telegram update containing the user's message
            context: Telegram context for storing temporary data
            
        Notes:
            - Falls back to manual creation if AI is unavailable
            - Supports duration extraction from natural language
            - Partner relevance is asked via inline keyboard
        """
        user_id = update.effective_user.id
        message_text = update.message.text
        
        # Check if AI service is available
        if not self.ai_service.is_available():
            logger.warning("AI service not available, falling back to manual appointment creation")
            await update.message.reply_text(
                "🤖 KI-Assistent ist derzeit nicht verfügbar.\n"
                "Bitte nutze das Format: `/add <Datum> <Zeit> <Titel>`\n\n"
                "Beispiel: `/add morgen 14:00 Zahnarzttermin`"
            )
            return
        
        # Validate input
        try:
            InputValidator.validate_telegram_input(
                user_id=user_id,
                username=update.effective_user.username,
                message_text=message_text
            )
        except ValidationError as e:
            await update.message.reply_text(ERROR_INVALID_INPUT)
            logger.warning(f"Invalid input from user {user_id}: {e}")
            return
        
        # Show processing message
        processing_msg = await update.message.reply_text(AI_ANALYZING_APPOINTMENT)
        
        try:
            # Extract appointment data using AI
            appointment_data = await self.ai_service.extract_appointment_from_text(
                message_text, 
                self.timezone.zone
            )
            
            if not appointment_data:
                await processing_msg.delete()
                await update.message.reply_text(
                    "❌ Ich konnte leider keine Termininformationen aus deiner Nachricht extrahieren.\n\n"
                    "Bitte versuche es mit einem klareren Format:\n"
                    "• `morgen 14:00 Zahnarzttermin`\n"
                    "• `25.12.2024 18:00 Weihnachtsfeier`\n"
                    "• `heute 16 Uhr Meeting mit Team`",
                    reply_markup=self.get_back_to_menu_keyboard()
                )
                return
            
            # Validate extracted data
            appointment_data = await self.ai_service.validate_appointment_data(appointment_data)
            
            # Format the extracted information for user confirmation
            from datetime import datetime
            date_obj = datetime.strptime(appointment_data['date'], '%Y-%m-%d')
            formatted_date = date_obj.strftime('%d.%m.%Y')
            time_str = appointment_data.get('time', 'Ganztägig')
            
            confirmation_text = (
                f"🤖 Ich habe folgende Termindaten erkannt:\n\n"
                f"📅 **Datum:** {formatted_date}\n"
                f"⏰ **Zeit:** {time_str}\n"
                f"📝 **Titel:** {appointment_data['title']}\n"
            )
            
            if appointment_data.get('description'):
                confirmation_text += f"📄 **Beschreibung:** {appointment_data['description']}\n"
            
            if appointment_data.get('location'):
                confirmation_text += f"📍 **Ort:** {appointment_data['location']}\n"
            
            confirmation_text += f"\n**Ist dieser Termin auch für deine Partnerin relevant?**"
            
            # Create inline keyboard for partner relevance
            keyboard = [
                [
                    InlineKeyboardButton("✅ Ja", callback_data=f"partner_relevant_yes_{user_id}"),
                    InlineKeyboardButton("❌ Nein", callback_data=f"partner_relevant_no_{user_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Store appointment data in context for callback
            context.user_data['pending_appointment'] = appointment_data
            
            await processing_msg.edit_text(
                text=confirmation_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error processing AI appointment: {e}", exc_info=True)
            await processing_msg.delete()
            await update.message.reply_text(
                f"❌ Es ist ein Fehler bei der Verarbeitung aufgetreten.\n"
                f"Fehler: {str(e)[:100]}...\n\n"
                f"Bitte versuche es später erneut oder nutze das manuelle Format.",
                reply_markup=self.get_back_to_menu_keyboard()
            )
    
    async def handle_partner_relevance_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle partner relevance callback from inline keyboard."""
        query = update.callback_query
        await query.answer()
        
        try:
            # Parse callback data
            callback_parts = query.data.split('_')
            if len(callback_parts) < 4:
                await query.edit_message_text("❌ Ungültige Callback-Daten.")
                return
            
            partner_relevant = callback_parts[2] == "yes"
            user_id = int(callback_parts[3])
            
            # Verify user match
            if user_id != update.effective_user.id:
                await query.edit_message_text("❌ Nicht autorisiert.")
                return
            
            # Get pending appointment data
            appointment_data = context.user_data.get('pending_appointment')
            if not appointment_data:
                await query.edit_message_text("❌ Termindaten nicht gefunden. Bitte versuche es erneut.")
                return
            
            # Create appointment with partner relevance
            from datetime import datetime
            import pytz
            
            # Parse date and time
            date_obj = datetime.strptime(appointment_data['date'], '%Y-%m-%d')
            
            # Add time if provided
            if appointment_data.get('time'):
                time_parts = appointment_data['time'].split(':')
                date_obj = date_obj.replace(hour=int(time_parts[0]), minute=int(time_parts[1]))
            
            # Localize to user's timezone
            user_tz = pytz.timezone(self.timezone.zone)
            date_obj = user_tz.localize(date_obj)
            
            # Create appointment with extracted duration
            # The 'date' field is used for backward compatibility
            # The model's __init__ will automatically set start_date and end_date
            appointment = Appointment(
                title=appointment_data['title'],
                date=date_obj,  # This will trigger migration logic in __init__
                description=appointment_data.get('description'),
                location=appointment_data.get('location'),
                partner_relevant=partner_relevant,
                duration_minutes=appointment_data.get('duration_minutes', 60)  # Extracted duration or default
            )
            
            # Validate appointment
            try:
                validated_input = InputValidator.validate_appointment_input(
                    title=appointment.title,
                    description=appointment.description
                )
                appointment.title = validated_input.get('title', appointment.title)
                appointment.description = validated_input.get('description', appointment.description)
            except ValidationError as e:
                await query.edit_message_text(f"❌ Ungültige Termindaten: {e.errors()[0]['msg']}")
                return
            
            # Create appointment in Notion
            try:
                created_appointment = await self.combined_service.create_appointment(appointment)
                logger.info(f"Successfully created appointment: {appointment.title}")
            except Exception as e:
                logger.error(f"Failed to create appointment in Notion: {e}")
                await query.edit_message_text(
                    f"❌ Fehler beim Speichern in Notion: {str(e)[:100]}...\n\n"
                    f"Termin: {appointment.title}\n"
                    f"Datum: {appointment.date.strftime('%d.%m.%Y um %H:%M')}\n"
                    f"Partner-relevant: {'✅ Ja' if appointment.partner_relevant else '❌ Nein'}"
                )
                return
            
            # Success message
            partner_status = "✅ Ja" if partner_relevant else "❌ Nein"
            success_text = (
                f"✅ **Termin wurde erfolgreich erstellt!**\n\n"
                f"📅 {appointment.title}\n"
                f"🗓️ {appointment.date.strftime('%d.%m.%Y um %H:%M')}\n"
                f"💑 Partner-relevant: {partner_status}\n\n"
                f"_Termin wurde in Notion gespeichert._"
            )
            
            await query.edit_message_text(
                text=success_text,
                parse_mode='Markdown'
            )
            
            # Clean up context
            if 'pending_appointment' in context.user_data:
                del context.user_data['pending_appointment']
            
        except Exception as e:
            logger.error(f"Error handling partner relevance callback: {e}", exc_info=True)
            await query.edit_message_text(
                f"❌ Es ist ein Fehler aufgetreten.\n"
                f"Fehler: {str(e)[:100]}...\n\n"
                f"Bitte versuche es erneut oder nutze /start für das Hauptmenü."
            )