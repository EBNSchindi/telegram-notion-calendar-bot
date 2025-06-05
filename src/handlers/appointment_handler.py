import logging
from datetime import datetime, timedelta
from typing import List
from telegram import Update
from telegram.ext import ContextTypes
from dateutil import parser
import pytz

from src.models.appointment import Appointment
from src.services.notion_service import NotionService
from config.settings import Settings

logger = logging.getLogger(__name__)


class AppointmentHandler:
    """Handler for appointment-related Telegram commands."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.notion_service = NotionService(settings)
        self.timezone = pytz.timezone(settings.timezone)
    
    async def add_appointment(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /add command to create new appointment.
        
        Usage: /add <date> <time> <title> [description]
        Examples:
        - /add tomorrow 14:00 Meeting with team
        - /add 25.12.2024 18:00 Christmas party Optional description
        - /add heute 15:30 Arzttermin
        """
        logger.info(f"Received /add command from user {update.effective_user.id} with args: {context.args}")
        
        if not context.args:
            await update.message.reply_text(
                "❌ Bitte gib einen Termin an.\n\n"
                "*Format:* `/add <Datum> <Zeit> <Titel> [Beschreibung]`\n\n"
                "*Beispiele:*\n"
                "• `/add morgen 14:00 Meeting`\n"
                "• `/add 25.12.2024 18:00 Weihnachtsfeier`\n"
                "• `/add heute 15:30 Arzttermin Wichtiger Termin`",
                parse_mode='Markdown'
            )
            return
        
        try:
            # Parse command arguments
            date_time, title, description = self._parse_add_command(context.args)
            
            # Create appointment
            appointment = Appointment(
                title=title,
                date=date_time,
                description=description
            )
            
            # Save to Notion
            page_id = await self.notion_service.create_appointment(appointment)
            appointment.notion_page_id = page_id
            
            # Send confirmation
            formatted_appointment = appointment.format_for_telegram(self.settings.timezone)
            await update.message.reply_text(
                f"✅ Termin erfolgreich erstellt!\n\n{formatted_appointment}",
                parse_mode='Markdown'
            )
            
            logger.info(f"Created appointment: {title} at {date_time}")
            
        except ValueError as e:
            await update.message.reply_text(f"❌ Fehler: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to create appointment: {e}")
            await update.message.reply_text(
                "❌ Fehler beim Erstellen des Termins. Bitte versuche es erneut."
            )
    
    async def list_appointments(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /list command to show upcoming appointments."""
        try:
            appointments = await self.notion_service.get_appointments(limit=10)
            
            if not appointments:
                await update.message.reply_text(
                    "📅 Keine kommenden Termine vorhanden."
                )
                return
            
            # Filter future appointments
            now = datetime.now(self.timezone)
            future_appointments = [
                apt for apt in appointments 
                if apt.date.replace(tzinfo=self.timezone) > now
            ]
            
            if not future_appointments:
                await update.message.reply_text(
                    "📅 Keine kommenden Termine vorhanden."
                )
                return
            
            message = "📋 *Kommende Termine:*\n\n"
            for i, appointment in enumerate(future_appointments[:5], 1):
                formatted = appointment.format_for_telegram(self.settings.timezone)
                message += f"{i}. {formatted}\n"
            
            if len(future_appointments) > 5:
                message += f"\n... und {len(future_appointments) - 5} weitere Termine"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Failed to list appointments: {e}")
            await update.message.reply_text(
                "❌ Fehler beim Abrufen der Termine. Bitte versuche es erneut."
            )
    
    async def today_appointments(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /today command to show today's appointments."""
        try:
            appointments = await self.notion_service.get_appointments(limit=20)
            
            # Filter today's appointments
            today = datetime.now(self.timezone).date()
            today_appointments = [
                apt for apt in appointments 
                if apt.date.astimezone(self.timezone).date() == today
            ]
            
            if not today_appointments:
                today_str = today.strftime("%d.%m.%Y")
                await update.message.reply_text(
                    f"📅 Keine Termine für heute ({today_str}) vorhanden."
                )
                return
            
            message = f"📅 *Termine für heute ({today.strftime('%d.%m.%Y')}):*\n\n"
            for i, appointment in enumerate(today_appointments, 1):
                formatted = appointment.format_for_telegram(self.settings.timezone)
                message += f"{i}. {formatted}\n"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Failed to get today's appointments: {e}")
            await update.message.reply_text(
                "❌ Fehler beim Abrufen der heutigen Termine. Bitte versuche es erneut."
            )
    
    def _parse_add_command(self, args: List[str]) -> tuple[datetime, str, str]:
        """
        Parse arguments for add command.
        
        Returns:
            tuple: (datetime, title, description)
        """
        if len(args) < 3:
            raise ValueError("Mindestens Datum, Zeit und Titel sind erforderlich")
        
        date_str = args[0]
        time_str = args[1]
        title_and_desc = args[2:]
        
        # Parse date
        date_time = self._parse_date_time(date_str, time_str)
        
        # Split title and description
        # Title is required, description is optional
        if len(title_and_desc) == 1:
            title = title_and_desc[0]
            description = None
        else:
            # First word is title, rest is description
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
        else:
            # Parse absolute date
            try:
                # Try different date formats
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
        
        # Parse time
        try:
            time_obj = datetime.strptime(time_str, '%H:%M').time()
        except ValueError:
            try:
                time_obj = datetime.strptime(time_str, '%H.%M').time()
            except ValueError:
                raise ValueError(f"Ungültiges Zeitformat: {time_str}. Verwende HH:MM oder HH.MM")
        
        # Combine date and time
        date_time = datetime.combine(target_date, time_obj)
        
        # Localize to timezone
        date_time = self.timezone.localize(date_time)
        
        # Validate that appointment is in the future
        if date_time <= now:
            raise ValueError("Termin muss in der Zukunft liegen")
        
        return date_time