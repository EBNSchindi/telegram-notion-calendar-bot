#!/usr/bin/env python3
"""Enhanced multi-user calendar bot with visual menu and combined database support."""
import logging
import asyncio
import sys
import os
from functools import wraps
from typing import Callable

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram import Update, MenuButton, MenuButtonCommands, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from config.settings import Settings
from config.user_config import UserConfigManager, UserConfig
from src.handlers.enhanced_appointment_handler import EnhancedAppointmentHandler
from src.handlers.debug_handler import DebugHandler
from src.services.enhanced_reminder_service import EnhancedReminderService
from src.services.business_calendar_sync import create_sync_manager_from_env
from src.constants import (
    SUCCESS_REMINDER_ENABLED, SUCCESS_REMINDER_DISABLED,
    ERROR_REMINDER_SERVICE_NOT_ACTIVE, ERROR_TEST_REMINDER_FAILED,
    ERROR_CREATE_PREVIEW_FAILED, ERROR_UNKNOWN_COMMAND,
    STATUS_SENDING_TEST_REMINDER, WELCOME_MESSAGE,
    WELCOME_CALENDAR_BOT, DATABASE_STATUS_HEADER,
    DATABASE_PRIVATE, DATABASE_SHARED,
    MENU_CHOOSE_ACTION, STATUS_ACTIVE, STATUS_INACTIVE,
    REMINDER_SETTINGS_HEADER, REMINDER_STATUS, REMINDER_TIME,
    REMINDER_SHARED_DB, REMINDER_COMMANDS_HEADER,
    REMINDER_COMMAND_ON, REMINDER_COMMAND_OFF, REMINDER_COMMAND_TIME,
    REMINDER_COMMAND_TEST, REMINDER_COMMAND_PREVIEW
)

# Define missing constants locally
CONFIG_NO_VALID_USERS = "❌ Keine gültigen Benutzer in der Konfiguration gefunden"
SERVICE_REMINDER_STARTED = "✅ Erinnerungsdienst gestartet"
SERVICE_PARTNER_SYNC_STARTED = "✅ Partner-Synchronisation gestartet"
SERVICE_PARTNER_SYNC_DISABLED = "ℹ️ Partner-Synchronisation deaktiviert"
SERVICE_PARTNER_SYNC_FAILED = "❌ Partner-Synchronisation fehlgeschlagen"
BOT_COMMANDS_SET_SUCCESS = "✅ Bot-Befehle erfolgreich gesetzt"
BOT_COMMANDS_SET_FAILED = "❌ Bot-Befehle konnten nicht gesetzt werden"
HELP_HEADER = "❓ **Hilfe**"
HELP_COMMANDS = "📋 **Verfügbare Befehle:**"
HELP_DEBUG_COMMANDS = "🔧 **Debug-Befehle:**"
HELP_DATABASE_INFO = "💾 **Datenbank-Info:**"
HELP_TIME_FORMATS = "⏰ **Unterstützte Zeitformate:**"
HELP_DATE_FORMATS = "📅 **Unterstützte Datumsformate:**"
HELP_TIPS = "💡 **Tipps:**"
from src.constants import PARTNER_SYNC_INTERVAL_HOURS
PARTNER_SYNC_INTERVAL = PARTNER_SYNC_INTERVAL_HOURS * 3600  # Convert to seconds
from src.constants import StatusEmojis, BOT_COMMANDS
from src.utils.telegram_helpers import get_back_to_menu_keyboard

# Enable secure logging with data sanitization
from utils.log_sanitizer import setup_secure_logging
# Enable debug mode if DEBUG env var is set
debug_mode = os.getenv('DEBUG', 'false').lower() == 'true'
log_level = os.getenv('LOG_LEVEL', 'INFO')
setup_secure_logging('bot.log', log_level, enable_debug=debug_mode)
logger = logging.getLogger(__name__)


def require_authorized_user(func: Callable) -> Callable:
    """Decorator to check if user is authorized before processing commands.
    
    This decorator implements a two-tier authorization system:
    1. If ALLOWED_USER_IDS environment variable is set, only users in that whitelist can access
    2. If no whitelist is configured, falls back to checking if user has valid configuration
    
    Args:
        func: The async function to be decorated (bot command handler)
        
    Returns:
        Wrapped function that performs authorization check before execution
        
    Environment Variables:
        ALLOWED_USER_IDS: Comma-separated list of Telegram user IDs (e.g., "123456789,987654321")
        
    Raises:
        No exceptions raised - unauthorized users receive error message instead
        
    Example:
        @require_authorized_user
        async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            # Handler code here
    """
    @wraps(func)
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        
        # Get allowed user IDs from environment variable
        allowed_users_str = os.getenv('ALLOWED_USER_IDS', '')
        if not allowed_users_str:
            # If no whitelist is configured, check if user has valid config
            user_config = self.user_config_manager.get_user_config(user_id)
            if not user_config:
                # Use appropriate reply method based on update type
                if update.message:
                    await update.message.reply_text(
                        "❌ Unauthorized access. Please contact the administrator."
                    )
                elif update.callback_query:
                    await update.callback_query.answer(
                        "❌ Unauthorized access.", show_alert=True
                    )
                logger.warning(f"Unauthorized access attempt by user {user_id}")
                return
        else:
            # Check against whitelist
            allowed_user_ids = [uid.strip() for uid in allowed_users_str.split(',') if uid.strip()]
            if str(user_id) not in allowed_user_ids:
                # Use appropriate reply method based on update type
                if update.message:
                    await update.message.reply_text(
                        "❌ Unauthorized access. You are not in the allowed users list."
                    )
                elif update.callback_query:
                    await update.callback_query.answer(
                        "❌ Unauthorized access.", show_alert=True
                    )
                logger.warning(f"Unauthorized access attempt by user {user_id} - not in whitelist")
                return
        
        return await func(self, update, context, *args, **kwargs)
    return wrapper


class EnhancedCalendarBot:
    """Main bot class that orchestrates all functionality.
    
    This class manages:
    - User authentication and configuration
    - Handler routing and caching
    - Service initialization (reminders, sync, etc.)
    - Command registration and processing
    """
    
    def __init__(self):
        """Initialize the bot with all required services and handlers."""
        self.settings = Settings()
        self.user_config_manager = UserConfigManager()
        self.application = None
        self.reminder_service = None
        self.business_sync_manager = None
        self.partner_sync_service = None  # Partner sync service
        self._handlers = {}  # Cache for user handlers
        self.debug_handler = DebugHandler(self.user_config_manager)  # Debug utilities
        
    def get_appointment_handler(self, user_id: int) -> EnhancedAppointmentHandler:
        """Get appointment handler for specific user (with caching)."""
        if user_id in self._handlers:
            return self._handlers[user_id]
        
        user_config = self.user_config_manager.get_user_config(user_id)
        if not user_config:
            return None
        
        handler = EnhancedAppointmentHandler(user_config, self.user_config_manager)
        self._handlers[user_id] = handler
        return handler
    
    @require_authorized_user
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command - show main menu."""
        user_id = update.effective_user.id
        handler = self.get_appointment_handler(user_id)
        
        if not handler:
            await update.message.reply_html(
                f'Hallo {update.effective_user.mention_html()}! 👋\n\n'
                '❌ Du bist noch nicht konfiguriert.\n\n'
                'Bitte kontaktiere den Administrator, um deine Notion-Verbindung einzurichten.\n\n'
                '<b>Benötigte Informationen:</b>\n'
                f'• Deine Telegram User ID: <code>{user_id}</code>\n'
                '• Notion API Key für private Datenbank\n'
                '• Private Notion Database ID\n'
                '• Notion API Key für gemeinsame Datenbank\n'
                '• Gemeinsame Notion Database ID'
            )
            return
        
        await handler.show_main_menu(update, context)
    
    @require_authorized_user
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle callback queries from inline keyboards."""
        user_id = update.effective_user.id
        handler = self.get_appointment_handler(user_id)
        
        if not handler:
            await update.callback_query.answer("❌ Nicht konfiguriert")
            return
        
        await handler.handle_callback(update, context)
    
    @require_authorized_user
    async def handle_appointment_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                       command: str) -> None:
        """Handle appointment commands with user-specific configuration."""
        user_id = update.effective_user.id
        handler = self.get_appointment_handler(user_id)
        
        if not handler:
            await update.message.reply_text(
                "❌ Du bist noch nicht konfiguriert. "
                "Bitte kontaktiere den Administrator."
            )
            return
        
        # Call the appropriate handler method
        if command == "add":
            await handler.add_appointment(update, context)
        elif command == "list":
            await handler.list_appointments(update, context)
        elif command == "today":
            await handler.today_appointments(update, context)
        elif command == "tomorrow":
            await handler.tomorrow_appointments(update, context)
    
    @require_authorized_user
    async def handle_memo_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                command: str) -> None:
        """Handle memo commands with user-specific configuration."""
        user_id = update.effective_user.id
        handler = self.get_appointment_handler(user_id)
        
        if not handler:
            await update.message.reply_text(
                "❌ Du bist noch nicht konfiguriert. "
                "Bitte kontaktiere den Administrator."
            )
            return
        
        if not handler.memo_handler:
            await update.message.reply_text(
                "❌ Memo-Funktionalität nicht verfügbar. "
                "Bitte wende dich an den Administrator."
            )
            return
        
        # Call the appropriate memo handler method
        if command == "show_all":
            await handler.memo_handler.handle_show_all_command(update, context)
        elif command == "check_memo":
            await handler.memo_handler.handle_check_memo_command(update, context)
    
    @require_authorized_user
    async def reminder_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle reminder settings command."""
        user_id = update.effective_user.id
        user_config = self.user_config_manager.get_user_config(user_id)
        
        if not user_config:
            await update.message.reply_text(
                "❌ Du bist noch nicht konfiguriert. "
                "Bitte kontaktiere den Administrator."
            )
            return
        
        # Check if command has arguments
        if not context.args:
            # Show current settings
            status = "✅ Aktiv" if user_config.reminder_enabled else "❌ Deaktiviert"
            shared_status = "🌐 Ja" if user_config.shared_notion_database_id else "❌ Nein"
            
            await update.message.reply_text(
                f"*⚙️ Deine Erinnerungseinstellungen:*\n\n"
                f"📋 Status: {status}\n"
                f"⏰ Zeit: {user_config.reminder_time}\n"
                f"🌐 Gemeinsame DB: {shared_status}\n\n"
                "*Befehle:*\n"
                "• `/reminder on` - Erinnerungen aktivieren\n"
                "• `/reminder off` - Erinnerungen deaktivieren\n"
                "• `/reminder time HH:MM` - Zeit ändern (z.B. 08:00)\n"
                "• `/reminder test` - Test-Erinnerung senden\n"
                "• `/reminder preview` - Vorschau der nächsten Erinnerung",
                parse_mode='Markdown'
            )
            return
        
        command = context.args[0].lower()
        
        if command == "on":
            user_config.reminder_enabled = True
            self.user_config_manager.save_to_file()
            await update.message.reply_text("✅ Tägliche Erinnerungen aktiviert!")
            
        elif command == "off":
            user_config.reminder_enabled = False
            self.user_config_manager.save_to_file()
            await update.message.reply_text("❌ Tägliche Erinnerungen deaktiviert!")
            
        elif command == "time" and len(context.args) > 1:
            time_str = context.args[1]
            # Validate time format
            try:
                hours, minutes = map(int, time_str.split(':'))
                if 0 <= hours <= 23 and 0 <= minutes <= 59:
                    user_config.reminder_time = f"{hours:02d}:{minutes:02d}"
                    self.user_config_manager.save_to_file()
                    await update.message.reply_text(
                        f"✅ Erinnerungszeit geändert auf {user_config.reminder_time} Uhr!"
                    )
                else:
                    raise ValueError
            except:
                await update.message.reply_text(
                    "❌ Ungültiges Zeitformat. Verwende HH:MM (z.B. 08:00)"
                )
                
        elif command == "test":
            if self.reminder_service:
                await update.message.reply_text("📨 Sende Test-Erinnerung...")
                success = await self.reminder_service.send_test_reminder(user_id)
                if not success:
                    await update.message.reply_text("❌ Fehler beim Senden der Test-Erinnerung")
            else:
                await update.message.reply_text("❌ Reminder-Service ist nicht aktiv")
                
        elif command == "preview":
            if self.reminder_service:
                preview = await self.reminder_service.get_reminder_preview(user_id)
                if preview:
                    await update.message.reply_text(preview, parse_mode='Markdown')
                else:
                    await update.message.reply_text("❌ Fehler beim Erstellen der Vorschau")
            else:
                await update.message.reply_text("❌ Reminder-Service ist nicht aktiv")
                
        else:
            await update.message.reply_text("❌ Unbekannter Befehl. Nutze /reminder für Hilfe.")
    
    @require_authorized_user
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send a message when the command /help is issued."""
        help_text = """
🗓 *Enhanced Kalender-Bot mit Notion-Integration*

*🚀 Neue Features:*
• 👥 Multi-User-Support mit privaten & gemeinsamen Datenbanken
• 🎛 Visuelles Menü mit Buttons
• 🌍 Erweiterte Zeitformate (Deutsch & English)
• 📨 Intelligente tägliche Erinnerungen

*📱 Verfügbare Befehle:*
• `/start` - Hauptmenü anzeigen
• `/today` - Heutige Termine (beide DBs)
• `/tomorrow` - Morgige Termine (beide DBs)
• `/list` - Kommende Termine (beide DBs)
• `/add` - Neuen Termin hinzufügen
• `/reminder` - Erinnerungen verwalten
• `/help` - Diese Hilfe anzeigen

*🔧 Debug-Befehle:*
• `/test_time <Zeit>` - Zeitformat testen
• `/formats` - Alle Zeitformate anzeigen
• `/validate <Datum> <Zeit> <Titel>` - Termin-Eingabe prüfen
• `/test_notion` - Notion-Verbindung testen

*🗂 Datenbanken:*
• 👤 *Private Datenbank* - Nur deine persönlichen Termine
• 🌐 *Gemeinsame Datenbank* - Termine aller Nutzer

*⏰ Zeitformate (Beispiele):*
• Standard: `14:00`, `14.30`, `1430`
• Deutsch: `16 Uhr`, `halb 3`, `viertel vor 5`
• English: `4 PM`, `quarter past 2`, `half past 3`

*📅 Datum-Formate:*
• Relativ: `heute`, `morgen`, `today`, `tomorrow`
• Absolut: `25.12.2024`, `2024-12-25`

*🎯 Tipps:*
• Nutze das Hauptmenü für eine intuitive Navigation
• Termine werden automatisch aus beiden Datenbanken kombiniert
• Erinnerungen zeigen die Quelle jedes Termins (👤/🌐)
        """
        await update.message.reply_text(
            help_text, 
            parse_mode='Markdown',
            reply_markup=get_back_to_menu_keyboard()
        )

    @require_authorized_user
    async def echo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle text messages - check for appointment input from menu."""
        logger.info(f"Received message: '{update.message.text}' from user {update.effective_user.id}")
        
        # Check if message looks like a start command
        if update.message.text.lower() in ['start', 'menu', 'menü']:
            await self.start(update, context)
            return
        
        # Check if user is awaiting memo input
        if context.user_data.get('awaiting_memo'):
            user_id = update.effective_user.id
            handler = self.get_appointment_handler(user_id)
            if handler and handler.memo_handler:
                await handler.memo_handler.process_ai_memo_message(update, context)
                return
        
        # Check if this is a reply to ForceReply (appointment input from menu)
        if update.message.reply_to_message and "Gib deinen Termin ein" in update.message.reply_to_message.text:
            # Use AI-powered appointment extraction
            user_id = update.effective_user.id
            handler = self.get_appointment_handler(user_id)
            
            if not handler:
                await update.message.reply_text(
                    "❌ Du bist noch nicht konfiguriert. "
                    "Bitte kontaktiere den Administrator."
                )
                return
            
            # Process with AI assistant
            await handler.process_ai_appointment_message(update, context)
            return
        
        # Check if message looks like appointment input (contains time patterns)
        message_text = update.message.text.lower()
        time_patterns = [
            r'\d{1,2}:\d{2}',  # 14:00
            r'\d{1,2}\.\d{2}',  # 14.30
            r'\d{1,2} uhr',     # 14 uhr
            r'\d{1,2} pm',      # 3 pm
            r'\d{1,2} am',      # 9 am
            r'halb \d{1,2}',    # halb 3
            r'halb',            # halb
            r'viertel',         # viertel patterns
            r'quarter',         # english quarter patterns
        ]
        
        date_patterns = [
            r'heute', r'morgen', r'übermorgen',
            r'today', r'tomorrow',
            r'montag', r'dienstag', r'mittwoch', r'donnerstag', r'freitag', r'samstag', r'sonntag',
            r'monday', r'tuesday', r'wednesday', r'thursday', r'friday', r'saturday', r'sunday',
            r'\d{1,2}\.\d{1,2}\.\d{2,4}', r'\d{4}-\d{1,2}-\d{1,2}',  # date formats
            r'nächste', r'nächsten',  # next week patterns
        ]
        
        # Check if message contains appointment-like patterns
        import re
        has_time = any(re.search(pattern, message_text) for pattern in time_patterns)
        has_date = any(re.search(pattern, message_text) for pattern in date_patterns)
        
        if has_time or has_date:
            user_id = update.effective_user.id
            handler = self.get_appointment_handler(user_id)
            
            if handler:
                await handler.process_ai_appointment_message(update, context)
                return
        
        await update.message.reply_text(
            "Ich habe deine Nachricht erhalten! 📨\n\n"
            "💡 Nutze /start für das Hauptmenü oder /help für alle Befehle!\n"
            "🤖 Oder sende mir einfach deinen Termin (z.B. 'morgen 14:00 Zahnarzttermin')"
        )
    
    async def post_init(self, application: Application) -> None:
        """Initialize services after bot startup."""
        # Set up bot commands for easy access
        commands = [
            BotCommand("start", "🎛️ Hauptmenü öffnen"),
            BotCommand("menu", "🎛️ Menü anzeigen"),
            BotCommand("today", "📅 Heutige Termine"),
            BotCommand("tomorrow", "📅 Morgige Termine"),
            BotCommand("add", "➕ Termin hinzufügen"),
            BotCommand("list", "📋 Alle Termine"),
            BotCommand("reminder", "⚙️ Erinnerungen"),
            BotCommand("show_all", "📋 Alle Memos anzeigen"),
            BotCommand("check_memo", "☑️ Memo abhaken"),
            BotCommand("help", "❓ Hilfe")
        ]
        
        try:
            await application.bot.set_my_commands(commands)
            await application.bot.set_chat_menu_button(
                menu_button=MenuButtonCommands()
            )
            logger.info("Bot commands and menu button set successfully")
        except Exception as e:
            logger.warning(f"Failed to set bot commands/menu: {e}")
        
        # Start enhanced reminder service
        self.reminder_service = EnhancedReminderService(application.bot, self.user_config_manager)
        await self.reminder_service.start()
        logger.info("Enhanced reminder service started")
        
        # Start partner sync service
        try:
            import os
            partner_sync_enabled = os.getenv('PARTNER_SYNC_ENABLED', 'true').lower() == 'true'
            
            if partner_sync_enabled:
                from src.services.partner_sync_service import PartnerSyncService
                
                self.partner_sync_service = PartnerSyncService(self.user_config_manager)
                
                # Get sync interval from environment or default to 2 hours
                sync_interval = int(os.getenv('PARTNER_SYNC_INTERVAL_HOURS', '2'))
                
                # Start background sync
                asyncio.create_task(
                    self.partner_sync_service.start_background_sync(interval_hours=sync_interval)
                )
                logger.info(f"Partner sync service started (interval: {sync_interval}h)")
            else:
                logger.info("Partner sync service disabled by configuration")
            
        except Exception as e:
            logger.error(f"Failed to start partner sync service: {e}")
            # Don't fail the whole bot if partner sync fails
        
        # Start business calendar sync
        try:
            self.business_sync_manager = create_sync_manager_from_env()
            
            # Add only valid users to business sync
            valid_users = self.user_config_manager.get_valid_users()
            
            if not valid_users:
                logger.error("No valid users configured! At least one user with valid Notion credentials is required.")
                logger.error("Please check your users_config.json file and ensure at least one user has:")
                logger.error("- Valid notion_api_key (starts with 'secret_' or 'ntn_')")
                logger.error("- Valid notion_database_id (32 character UUID)")
                logger.error("- No placeholder values like 'your_notion_' or 'secret_xxx_'")
                sys.exit(1)
            
            for user_config in valid_users.values():
                self.business_sync_manager.add_user(user_config)
            
            # Start business sync in background
            if self.business_sync_manager.user_syncs:
                asyncio.create_task(self.business_sync_manager.start_all_syncs())
                logger.info(f"Business calendar sync started for {len(valid_users)} valid users")
            else:
                logger.info("No users configured for business calendar sync")
                
        except Exception as e:
            logger.error(f"Failed to start business calendar sync: {e}")
            # Don't fail the whole bot if business sync fails
    
    async def post_shutdown(self, application: Application) -> None:
        """Cleanup services on shutdown."""
        if self.reminder_service:
            await self.reminder_service.stop()
            logger.info("Enhanced reminder service stopped")
        
        if self.partner_sync_service:
            self.partner_sync_service.stop_background_sync()
            logger.info("Partner sync service stopped")
        
        if self.business_sync_manager:
            self.business_sync_manager.stop_all_syncs()
            logger.info("Business calendar sync stopped")
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle errors securely without exposing internal details."""
        # Log detailed error for debugging (server-side only)
        error_msg = str(context.error)
        error_type = type(context.error).__name__
        
        # Log with user ID for tracking but without exposing sensitive data
        user_id = "unknown"
        if isinstance(update, Update) and update.effective_user:
            user_id = update.effective_user.id
        
        logger.error(
            f"Bot error for user {user_id}: {error_type} - {error_msg[:200]}...",
            exc_info=context.error
        )
        
        # Send safe, generic error message to user
        if isinstance(update, Update) and update.effective_message:
            try:
                # Different messages based on error type to be more helpful
                if "network" in error_msg.lower() or "timeout" in error_msg.lower():
                    user_message = (
                        "🌐 Verbindungsproblem aufgetreten. "
                        "Bitte versuche es in einem Moment erneut."
                    )
                elif "notion" in error_msg.lower():
                    user_message = (
                        "📝 Problem mit der Notion-Verbindung. "
                        "Bitte überprüfe deine Konfiguration."
                    )
                else:
                    user_message = (
                        "❌ Ein unerwarteter Fehler ist aufgetreten. "
                        "Bitte versuche es erneut oder kontaktiere den Administrator."
                    )
                
                await update.effective_message.reply_text(
                    user_message,
                    reply_markup=get_back_to_menu_keyboard()
                )
                
            except Exception as e:
                logger.error(f"Failed to send error message to user {user_id}: {e}")

    def run(self):
        """Start the bot."""
        # Create the Application
        self.application = Application.builder().token(self.settings.telegram_token).build()

        # Register handlers
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("menu", self.start))  # Alias for start
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("reminder", self.reminder_command))
        
        # Debug handlers for troubleshooting
        self.application.add_handler(CommandHandler("test_time", self.debug_handler.test_time_format))
        self.application.add_handler(CommandHandler("formats", self.debug_handler.show_time_formats))
        self.application.add_handler(CommandHandler("validate", self.debug_handler.validate_appointment_input))
        self.application.add_handler(CommandHandler("test_notion", self.debug_handler.test_notion_connection))
        
        # Appointment handlers
        self.application.add_handler(CommandHandler(
            "today", 
            lambda u, c: self.handle_appointment_command(u, c, "today")
        ))
        self.application.add_handler(CommandHandler(
            "tomorrow", 
            lambda u, c: self.handle_appointment_command(u, c, "tomorrow")
        ))
        self.application.add_handler(CommandHandler(
            "add", 
            lambda u, c: self.handle_appointment_command(u, c, "add")
        ))
        self.application.add_handler(CommandHandler(
            "list", 
            lambda u, c: self.handle_appointment_command(u, c, "list")
        ))
        
        # Memo handlers
        self.application.add_handler(CommandHandler(
            "show_all", 
            lambda u, c: self.handle_memo_command(u, c, "show_all")
        ))
        self.application.add_handler(CommandHandler(
            "check_memo", 
            lambda u, c: self.handle_memo_command(u, c, "check_memo")
        ))
        
        # Callback query handler for inline keyboards
        self.application.add_handler(CallbackQueryHandler(self.handle_callback_query))
        
        # Echo all other messages
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.echo))
        
        # Error handler
        self.application.add_error_handler(self.error_handler)
        
        # Add startup and shutdown hooks
        self.application.post_init = self.post_init
        self.application.post_shutdown = self.post_shutdown

        # Run the bot until the user presses Ctrl-C
        logger.info("Starting Enhanced Multi-User Telegram Bot with combined database support...")
        logger.info("Features: Visual Menu, Private + Shared Databases, Enhanced Time Parsing, Smart Reminders")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    bot = EnhancedCalendarBot()
    bot.run()