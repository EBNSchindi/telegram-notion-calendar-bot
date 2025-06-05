#!/usr/bin/env python3
import logging
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from config.settings import Settings
from src.handlers.appointment_handler import AppointmentHandler
from src.services.notion_service import NotionService

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG,  # Changed to DEBUG for more detailed logs
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler('bot.log')  # Also log to file
    ]
)
logger = logging.getLogger(__name__)

class CalendarBot:
    def __init__(self):
        self.settings = Settings()
        self.application = None
        self.appointment_handler = AppointmentHandler(self.settings)
        self.notion_service = NotionService(self.settings)
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send a message when the command /start is issued."""
        user = update.effective_user
        logger.info(f"Received /start command from user {user.id} ({user.username})")
        
        # Test Notion connection
        connection_status = "✅" if await self.notion_service.test_connection() else "❌"
        
        await update.message.reply_html(
            f'Hallo {user.mention_html()}! 👋\n\n'
            f'Ich bin dein Kalender-Bot mit Notion-Integration {connection_status}\n\n'
            '*Verfügbare Befehle:*\n'
            '• /start - Bot starten\n'
            '• /help - Hilfe anzeigen\n'
            '• /today - Heutige Termine anzeigen\n'
            '• /add - Neuen Termin hinzufügen\n'
            '• /list - Alle kommenden Termine anzeigen\n\n'
            '*Beispiele:*\n'
            '• `/add morgen 14:00 Meeting Team-Besprechung`\n'
            '• `/add 25.12.2024 18:00 Weihnachtsfeier`'
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send a message when the command /help is issued."""
        help_text = """
🗓 *Kalender-Bot mit Notion-Integration*

*Verfügbare Befehle:*
• `/start` - Bot starten und Status anzeigen
• `/help` - Diese Hilfe anzeigen
• `/today` - Zeigt die heutigen Termine
• `/add` - Fügt einen neuen Termin hinzu
• `/list` - Zeigt alle kommenden Termine

*Termin hinzufügen:*
`/add <Datum> <Zeit> <Titel> [Beschreibung]`

*Datum-Formate:*
• `heute` oder `today`
• `morgen` oder `tomorrow`
• `25.12.2024` (DD.MM.YYYY)
• `2024-12-25` (YYYY-MM-DD)

*Zeit-Format:*
• `14:00` oder `14.00`

*Beispiele:*
• `/add morgen 14:00 Meeting`
• `/add heute 15:30 Arzttermin Wichtiger Termin`
• `/add 25.12.2024 18:00 Weihnachtsfeier Familie`
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def echo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Echo the user message."""
        logger.info(f"Received message: '{update.message.text}' from user {update.effective_user.id}")
        await update.message.reply_text(
            "Ich habe deine Nachricht erhalten. "
            "Nutze /help um zu sehen, was ich kann!"
        )

    def run(self):
        """Start the bot."""
        # Create the Application
        self.application = Application.builder().token(self.settings.telegram_token).build()

        # Register handlers
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("today", self.appointment_handler.today_appointments))
        self.application.add_handler(CommandHandler("add", self.appointment_handler.add_appointment))
        self.application.add_handler(CommandHandler("list", self.appointment_handler.list_appointments))
        
        # Echo all other messages
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.echo))

        # Run the bot until the user presses Ctrl-C
        logger.info("Starting Telegram Bot with Notion integration...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    bot = CalendarBot()
    bot.run()