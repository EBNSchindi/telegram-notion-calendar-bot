#!/usr/bin/env python3
"""Enhanced multi-user calendar bot with visual menu and combined database support."""
import logging
import asyncio
import sys
import os

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

# Enable secure logging with data sanitization
from utils.log_sanitizer import setup_secure_logging
setup_secure_logging('bot.log', 'INFO')
logger = logging.getLogger(__name__)


class EnhancedCalendarBot:
    def __init__(self):
        self.settings = Settings()
        self.user_config_manager = UserConfigManager()
        self.application = None
        self.reminder_service = None
        self.business_sync_manager = None
        self._handlers = {}  # Cache for user handlers
        self.debug_handler = DebugHandler(self.user_config_manager)  # Debug utilities
        
    def get_appointment_handler(self, user_id: int) -> EnhancedAppointmentHandler:
        """Get appointment handler for specific user (with caching)."""
        if user_id in self._handlers:
            return self._handlers[user_id]
        
        user_config = self.user_config_manager.get_user_config(user_id)
        if not user_config:
            return None
        
        handler = EnhancedAppointmentHandler(user_config)
        self._handlers[user_id] = handler
        return handler
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command - show main menu."""
        user_id = update.effective_user.id
        handler = self.get_appointment_handler(user_id)
        
        if not handler:
            await update.message.reply_html(
                f'Hallo {update.effective_user.mention_html()}! 👋\n\n'
                '❌ Du bist noch nicht konfiguriert.\n\n'
                'Bitte kontaktiere den Administrator, um deine Notion-Verbindung einzurichten.\n\n'
                '*Benötigte Informationen:*\n'
                f'• Deine Telegram User ID: `{user_id}`\n'
                '• Notion API Key für private Datenbank\n'
                '• Private Notion Database ID\n'
                '• Notion API Key für gemeinsame Datenbank\n'
                '• Gemeinsame Notion Database ID',
                parse_mode='Markdown'
            )
            return
        
        await handler.show_main_menu(update, context)
    
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle callback queries from inline keyboards."""
        user_id = update.effective_user.id
        handler = self.get_appointment_handler(user_id)
        
        if not handler:
            await update.callback_query.answer("❌ Nicht konfiguriert")
            return
        
        await handler.handle_callback(update, context)
    
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
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def echo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle text messages - check for appointment input from menu."""
        logger.info(f"Received message: '{update.message.text}' from user {update.effective_user.id}")
        
        # Check if message looks like a start command
        if update.message.text.lower() in ['start', 'menu', 'menü']:
            await self.start(update, context)
            return
        
        # Check if this is a reply to ForceReply (appointment input from menu)
        if update.message.reply_to_message and "Gib deinen Termin ein" in update.message.reply_to_message.text:
            # Treat this as /add command
            user_id = update.effective_user.id
            handler = self.get_appointment_handler(user_id)
            
            if not handler:
                await update.message.reply_text(
                    "❌ Du bist noch nicht konfiguriert. "
                    "Bitte kontaktiere den Administrator."
                )
                return
            
            # Parse the message as /add command arguments
            args = update.message.text.strip().split()
            context.args = args  # Set args for the handler
            
            await handler.add_appointment(update, context)
            return
        
        await update.message.reply_text(
            "Ich habe deine Nachricht erhalten! 📨\n\n"
            "💡 Nutze /start für das Hauptmenü oder /help für alle Befehle!"
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
        
        # Start business calendar sync
        try:
            self.business_sync_manager = create_sync_manager_from_env()
            
            # Add all configured users to business sync
            for user_config in self.user_config_manager._users.values():
                if user_config.telegram_user_id != 0:  # Skip default user
                    self.business_sync_manager.add_user(user_config)
            
            # Start business sync in background
            if self.business_sync_manager.user_syncs:
                asyncio.create_task(self.business_sync_manager.start_all_syncs())
                logger.info("Business calendar sync started")
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
                
                await update.effective_message.reply_text(user_message)
                
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