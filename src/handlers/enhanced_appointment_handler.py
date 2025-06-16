"""Enhanced appointment handler with combined database support."""
import logging
from datetime import datetime, timedelta, date
from typing import List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from telegram.ext import ContextTypes
import pytz

from src.models.appointment import Appointment
from src.services.combined_appointment_service import CombinedAppointmentService
from config.user_config import UserConfig
from src.utils.robust_time_parser import RobustTimeParser
from src.utils.rate_limiter import rate_limit
from src.utils.input_validator import InputValidator
from pydantic.error_wrappers import ValidationError

logger = logging.getLogger(__name__)


class EnhancedAppointmentHandler:
    """Enhanced handler for appointment-related Telegram commands with combined database support."""
    
    def __init__(self, user_config: UserConfig):
        self.user_config = user_config
        self.combined_service = CombinedAppointmentService(user_config)
        
        # Handle timezone with fallback
        timezone_str = user_config.timezone if user_config.timezone else 'Europe/Berlin'
        try:
            self.timezone = pytz.timezone(timezone_str)
        except Exception as e:
            logger.warning(f"Invalid timezone '{timezone_str}', falling back to Europe/Berlin: {e}")
            self.timezone = pytz.timezone('Europe/Berlin')
    
    @rate_limit(max_requests=20, time_window=60)  # 20 requests per minute for menu
    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show the main menu with inline buttons."""
        user = update.effective_user
        
        # Test database connections
        private_ok, shared_ok = await self.combined_service.test_connections()
        
        # Create status message
        private_status = "✅" if private_ok else "❌"
        if shared_ok is None:
            shared_status = "⚠️ Nicht konfiguriert"
        else:
            shared_status = "✅" if shared_ok else "❌"
        
        status_text = (
            f"Hallo {user.first_name}! 👋\n\n"
            f"🗓 *Dein Kalender-Bot*\n\n"
            f"*Datenbankstatus:*\n"
            f"👤 Private Datenbank: {private_status}\n"
            f"🌐 Gemeinsame Datenbank: {shared_status}\n\n"
            f"*Wähle eine Aktion:*"
        )
        
        # Create inline keyboard
        keyboard = [
            [
                InlineKeyboardButton("📅 Heutige Termine", callback_data="today"),
                InlineKeyboardButton("🗓️ Termine für morgen", callback_data="tomorrow")
            ],
            [
                InlineKeyboardButton("📋 Alle anstehenden Termine", callback_data="list"),
                InlineKeyboardButton("➕ Neuen Termin hinzufügen", callback_data="add")
            ],
            [
                InlineKeyboardButton("⚙️ Erinnerungen", callback_data="reminder"),
                InlineKeyboardButton("❓ Hilfe", callback_data="help")
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
        """Handle inline keyboard callbacks."""
        query = update.callback_query
        await query.answer()
        
        if query.data == "today":
            await self.today_appointments_callback(update, context)
        elif query.data == "tomorrow":
            await self.tomorrow_appointments_callback(update, context)
        elif query.data == "list":
            await self.list_appointments_callback(update, context)
        elif query.data == "add":
            await self.add_appointment_callback(update, context)
        elif query.data == "reminder":
            await self.reminder_callback(update, context)
        elif query.data == "help":
            await self.help_callback(update, context)
        elif query.data == "back_to_menu":
            await self.show_main_menu(update, context)
    
    async def today_appointments_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle today appointments callback."""
        try:
            appointments = await self.combined_service.get_today_appointments()
            
            today = datetime.now(self.timezone).date()
            title = f"Termine für heute ({today.strftime('%d.%m.%Y')})"
            
            message = self.combined_service.format_appointments_for_telegram(appointments, title)
            
            # Add back button
            keyboard = [[InlineKeyboardButton("🔙 Zurück zum Menü", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
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
            keyboard = [[InlineKeyboardButton("🔙 Zurück zum Menü", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
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
            keyboard = [[InlineKeyboardButton("🔙 Zurück zum Menü", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
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
        help_text = """
❓ *Hilfe - Kalender-Bot*

*Verfügbare Befehle:*
• `/start` - Hauptmenü anzeigen
• `/today` - Heutige Termine
• `/tomorrow` - Morgige Termine
• `/list` - Kommende Termine
• `/add` - Neuen Termin hinzufügen
• `/reminder` - Erinnerungen verwalten

*Datenbanken:*
👤 *Private Datenbank* - Nur deine Termine
🌐 *Gemeinsame Datenbank* - Termine aller Nutzer

*Zeitformate:*
• Standard: `14:00`, `14.30`
• Deutsch: `16 Uhr`, `halb 3`
• English: `4 PM`, `quarter past 2`

*Besonderheiten:*
• Termine werden aus beiden Datenbanken kombiniert angezeigt
• Tägliche Erinnerungen um die eingestellte Zeit
• Intuitive Menüführung mit Buttons
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
            await update.message.reply_text("❌ Ungültige Eingabe. Bitte versuche es erneut.")
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
                parse_mode='Markdown'
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
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Failed to get today's appointments: {e}")
            await update.message.reply_text(
                "❌ Fehler beim Abrufen der heutigen Termine. Bitte versuche es erneut."
            )
    
    @rate_limit(max_requests=15, time_window=60)  # 15 queries per minute
    async def tomorrow_appointments(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /tomorrow command."""
        try:
            appointments = await self.combined_service.get_tomorrow_appointments()
            
            tomorrow = (datetime.now(self.timezone) + timedelta(days=1)).date()
            title = f"Termine für morgen ({tomorrow.strftime('%d.%m.%Y')})"
            
            message = self.combined_service.format_appointments_for_telegram(appointments, title)
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Failed to get tomorrow's appointments: {e}")
            await update.message.reply_text(
                "❌ Fehler beim Abrufen der morgigen Termine. Bitte versuche es erneut."
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
                "❌ Fehler beim Abrufen der Termine. Bitte versuche es erneut."
            )
    
    def _parse_add_command(self, args: List[str]) -> tuple[datetime, str, str]:
        """Parse arguments for add command with smart time parsing."""
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