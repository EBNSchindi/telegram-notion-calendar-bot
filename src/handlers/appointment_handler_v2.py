"""Refactored appointment handler with improved structure and reduced complexity."""

import logging
from datetime import datetime, timedelta, date
from typing import List, Optional
from telegram import Update, ForceReply
from telegram.ext import ContextTypes

from src.handlers.base_handler import BaseHandler
from src.models.appointment import Appointment
from src.services.combined_appointment_service import CombinedAppointmentService
from src.services.ai_assistant_service import AIAssistantService
from src.handlers.memo_handler import MemoHandler
from config.user_config import UserConfig
from src.utils.robust_time_parser import RobustTimeParser
from src.utils.rate_limiter import rate_limit
from src.utils.input_validator import InputValidator
from src.utils.telegram_helpers import TelegramFormatter, KeyboardBuilder, DateTimeHelpers
from src.constants import (
    DEFAULT_RATE_LIMIT_REQUESTS, DEFAULT_RATE_LIMIT_WINDOW,
    AI_RATE_LIMIT_REQUESTS, AI_RATE_LIMIT_WINDOW,
    StatusEmojis, CallbackData, DEFAULT_APPOINTMENTS_LIMIT
)
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class AppointmentHandler(BaseHandler):
    """Refactored appointment handler with cleaner structure."""
    
    def __init__(self, user_config: UserConfig):
        super().__init__(user_config)
        self.combined_service = CombinedAppointmentService(user_config)
        self.ai_service = AIAssistantService()
        self.memo_handler = MemoHandler(user_config)
        self.time_parser = RobustTimeParser()
    
    @rate_limit(max_requests=DEFAULT_RATE_LIMIT_REQUESTS, time_window=DEFAULT_RATE_LIMIT_WINDOW)
    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show the main menu with inline buttons."""
        user = update.effective_user
        
        # Test database connections
        private_ok, shared_ok = await self.combined_service.test_connections()
        
        # Format status message
        status_text = TelegramFormatter.format_status_message(
            private_ok, shared_ok, user.first_name or "User"
        )
        
        # Create keyboard
        reply_markup = KeyboardBuilder.create_main_menu()
        
        # Send message
        await self.send_message_safe(
            update, status_text, parse_mode='Markdown', 
            reply_markup=reply_markup, edit_message=bool(update.callback_query)
        )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle inline keyboard callbacks."""
        await self.answer_callback_query(update)
        
        callback_data = update.callback_query.data
        
        # Route to appropriate handler
        callback_handlers = {
            CallbackData.TODAY_TOMORROW: self._handle_today_tomorrow,
            CallbackData.RECENT_MEMOS: self._handle_recent_memos,
            CallbackData.ADD_APPOINTMENT: self._handle_add_appointment,
            CallbackData.ADD_MEMO: self._handle_add_memo,
            CallbackData.HELP: self._handle_help,
            "main_menu": self.show_main_menu,
        }
        
        # Handle partner relevance callbacks
        if callback_data.startswith(CallbackData.PARTNER_RELEVANT_YES):
            await self._handle_partner_relevance(update, context, True)
            return
        elif callback_data.startswith(CallbackData.PARTNER_RELEVANT_NO):
            await self._handle_partner_relevance(update, context, False)
            return
        
        # Execute handler
        handler = callback_handlers.get(callback_data)
        if handler:
            await handler(update, context)
        else:
            await self.send_message_safe(
                update, 
                self.format_error_message("Unbekannte Aktion"),
                edit_message=True
            )
    
    async def _handle_today_tomorrow(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle today and tomorrow appointments display."""
        try:
            today = datetime.now(self.timezone).date()
            tomorrow = today + timedelta(days=1)
            
            # Get appointments for both days
            today_appointments = await self.combined_service.get_appointments_for_date(today)
            tomorrow_appointments = await self.combined_service.get_appointments_for_date(tomorrow)
            
            # Combine and format
            all_appointments = today_appointments + tomorrow_appointments
            
            if not all_appointments:
                message = f"*📅 Termine Heute & Morgen*\\n\\n{StatusEmojis.INFO} Keine Termine gefunden."
            else:
                # Sort by date and time
                all_appointments.sort(key=lambda apt: apt.start_datetime or datetime.min.replace(tzinfo=self.timezone))
                
                message = TelegramFormatter.format_appointment_list(
                    all_appointments,
                    "📅 Termine Heute & Morgen",
                    show_database_source=True
                )
            
            # Add back button
            keyboard = KeyboardBuilder.create_back_to_menu_keyboard()
            
            await self.send_message_safe(
                update, message, parse_mode='Markdown',
                reply_markup=keyboard, edit_message=True
            )
            
        except Exception as e:
            logger.error(f"Error fetching today/tomorrow appointments: {e}")
            await self.send_message_safe(
                update,
                self.format_error_message(
                    "Fehler beim Laden der Termine",
                    "Bitte versuche es später erneut."
                ),
                edit_message=True
            )
    
    async def _handle_recent_memos(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle recent memos display."""
        if not self.memo_handler:
            await self.send_message_safe(
                update,
                self.format_warning_message("Memo-Funktion ist nicht verfügbar"),
                edit_message=True
            )
            return
        
        try:
            # Get recent memos
            memos = await self.memo_handler.memo_service.get_recent_memos(limit=10)
            
            # Format message
            message = TelegramFormatter.format_memo_list(memos, "📝 Letzte 10 Memos")
            
            # Add back button
            keyboard = KeyboardBuilder.create_back_to_menu_keyboard()
            
            await self.send_message_safe(
                update, message, parse_mode='Markdown',
                reply_markup=keyboard, edit_message=True
            )
            
        except Exception as e:
            logger.error(f"Error fetching recent memos: {e}")
            await self.send_message_safe(
                update,
                self.format_error_message(
                    "Fehler beim Laden der Memos",
                    "Bitte versuche es später erneut."
                ),
                edit_message=True
            )
    
    async def _handle_add_appointment(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle add appointment request."""
        help_text = (
            "📝 *Termin hinzufügen*\\n\\n"
            "Gib deinen Termin in natürlicher Sprache ein:\\n\\n"
            "*Beispiele:*\\n"
            "• `morgen 14:00 Zahnarzttermin`\\n"
            "• `übermorgen 9 Uhr Meeting mit Team`\\n"
            "• `25.12.2024 15:30 Weihnachtsfeier`\\n\\n"
            "*Unterstützte Zeitformate:*\\n"
            "• Standard: `14:00`, `14.30`, `1430`\\n"
            "• Deutsch: `16 Uhr`, `halb 3`, `viertel vor 5`\\n"
            "• English: `4 PM`, `quarter past 2`"
        )
        
        force_reply = self.create_force_reply("z.B. morgen 14:00 Zahnarzttermin")
        
        await self.send_message_safe(
            update, help_text, parse_mode='Markdown',
            reply_markup=force_reply, edit_message=True
        )
    
    async def _handle_add_memo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle add memo request."""
        if not self.memo_handler:
            await self.send_message_safe(
                update,
                self.format_warning_message("Memo-Funktion ist nicht verfügbar"),
                edit_message=True
            )
            return
        
        # Delegate to memo handler
        await self.memo_handler.add_memo_callback(update, context)
    
    async def _handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle help request."""
        help_text = self._generate_help_text()
        keyboard = KeyboardBuilder.create_back_to_menu_keyboard()
        
        await self.send_message_safe(
            update, help_text, parse_mode='Markdown',
            reply_markup=keyboard, edit_message=True
        )
    
    def _generate_help_text(self) -> str:
        """Generate comprehensive help text."""
        return (
            "*🗓 Enhanced Kalender-Bot mit Notion-Integration*\\n\\n"
            "*🚀 Neue Features:*\\n"
            "• 👥 Multi-User-Support mit privaten & gemeinsamen Datenbanken\\n"
            "• 🎛 Visuelles Menü mit Buttons\\n"
            "• 🌍 Erweiterte Zeitformate (Deutsch & English)\\n"
            "• 📝 KI-gestützte Memo-Verwaltung\\n"
            "• 📨 Intelligente tägliche Erinnerungen\\n\\n"
            "*📱 Verfügbare Befehle:*\\n"
            "• `/start` - Hauptmenü anzeigen\\n"
            "• `/today` - Heutige Termine (beide DBs)\\n"
            "• `/tomorrow` - Morgige Termine (beide DBs)\\n"
            "• `/list` - Kommende Termine (beide DBs)\\n"
            "• `/add` - Neuen Termin hinzufügen\\n"
            "• `/reminder` - Erinnerungen verwalten\\n"
            "• `/help` - Diese Hilfe anzeigen\\n\\n"
            "*🗂 Datenbanken:*\\n"
            "• 👤 *Private Datenbank* - Nur deine persönlichen Termine\\n"
            "• 🌐 *Gemeinsame Datenbank* - Termine aller Nutzer\\n\\n"
            "*⏰ Zeitformate (Beispiele):*\\n"
            "• Standard: `14:00`, `14.30`, `1430`\\n"
            "• Deutsch: `16 Uhr`, `halb 3`, `viertel vor 5`\\n"
            "• English: `4 PM`, `quarter past 2`, `half past 3`\\n\\n"
            "*📅 Datum-Formate:*\\n"
            "• Relativ: `heute`, `morgen`, `today`, `tomorrow`\\n"
            "• Absolut: `25.12.2024`, `2024-12-25`"
        )
    
    @rate_limit(max_requests=AI_RATE_LIMIT_REQUESTS, time_window=AI_RATE_LIMIT_WINDOW)
    async def process_ai_appointment_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Process appointment input using AI assistance."""
        message_text = update.message.text
        
        if not self.validate_user_input(message_text):
            await self.send_message_safe(
                update,
                self.format_error_message(
                    "Ungültige Eingabe",
                    "Bitte verwende normale Zeichen und halte die Nachricht unter 1000 Zeichen."
                )
            )
            return
        
        try:
            # Process with AI
            processing_msg = await update.message.reply_text(
                f"{StatusEmojis.PENDING} Verarbeite deinen Termin mit KI-Unterstützung..."
            )
            
            appointment_data = await self.ai_service.extract_appointment_from_text(message_text)
            
            if not appointment_data or not appointment_data.get('title'):
                await processing_msg.edit_text(
                    self.format_error_message(
                        "KI konnte keinen Termin erkennen",
                        "Bitte versuche es mit einem klareren Format: 'morgen 14:00 Zahnarzttermin'"
                    )
                )
                return
            
            # Create appointment
            appointment = await self._create_appointment_from_ai_data(appointment_data)
            
            if not appointment:
                await processing_msg.edit_text(
                    self.format_error_message(
                        "Termin konnte nicht erstellt werden",
                        "Bitte überprüfe das Datum und die Uhrzeit."
                    )
                )
                return
            
            # Ask about partner relevance if shared database is configured
            if self.user_config.shared_notion_database_id:
                keyboard = KeyboardBuilder.create_partner_relevance_keyboard(update.effective_user.id)
                context.user_data['pending_appointment'] = appointment
                
                await processing_msg.edit_text(
                    f"{StatusEmojis.SUCCESS} Termin erstellt: *{appointment.title}*\\n"
                    f"📅 {appointment.start_datetime.strftime('%d.%m.%Y %H:%M')}\\n\\n"
                    "Soll dieser Termin auch für Partner sichtbar sein?",
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
            else:
                # Save to private database only
                success = await self.combined_service.create_appointment(appointment, use_shared=False)
                
                if success:
                    await processing_msg.edit_text(
                        self.format_success_message(
                            f"Termin erfolgreich erstellt!\\n"
                            f"📅 {appointment.start_datetime.strftime('%d.%m.%Y %H:%M')}\\n"
                            f"📝 {appointment.title}"
                        )
                    )
                else:
                    await processing_msg.edit_text(
                        self.format_error_message(
                            "Fehler beim Speichern des Termins",
                            "Bitte versuche es erneut."
                        )
                    )
                    
        except Exception as e:
            logger.error(f"Error processing AI appointment: {e}")
            await self.send_message_safe(
                update,
                self.format_error_message(
                    "Unerwarteter Fehler aufgetreten",
                    "Bitte versuche es erneut."
                )
            )
    
    async def _create_appointment_from_ai_data(self, ai_data: dict) -> Optional[Appointment]:
        """Create appointment object from AI-extracted data."""
        try:
            # Parse date and time
            datetime_str = f"{ai_data.get('date', '')} {ai_data.get('time', '')}"
            parsed_datetime = self.time_parser.parse_datetime(datetime_str.strip())
            
            if not parsed_datetime:
                return None
            
            # Ensure datetime is timezone-aware
            if parsed_datetime.tzinfo is None:
                parsed_datetime = self.timezone.localize(parsed_datetime)
            
            # Create appointment
            appointment = Appointment(
                title=ai_data['title'],
                start_datetime=parsed_datetime,
                description=ai_data.get('description', ''),
                location=ai_data.get('location', '')
            )
            
            return appointment
            
        except Exception as e:
            logger.error(f"Error creating appointment from AI data: {e}")
            return None
    
    async def _handle_partner_relevance(self, update: Update, context: ContextTypes.DEFAULT_TYPE, is_relevant: bool) -> None:
        """Handle partner relevance selection."""
        await self.answer_callback_query(update)
        
        # Get pending appointment
        appointment = context.user_data.get('pending_appointment')
        if not appointment:
            await self.send_message_safe(
                update,
                self.format_error_message("Termin-Daten nicht gefunden"),
                edit_message=True
            )
            return
        
        # Save appointment to appropriate database
        use_shared = is_relevant
        success = await self.combined_service.create_appointment(appointment, use_shared=use_shared)
        
        if success:
            db_type = "gemeinsamen" if use_shared else "privaten"
            message = self.format_success_message(
                f"Termin in der {db_type} Datenbank gespeichert!\\n"
                f"📅 {appointment.start_datetime.strftime('%d.%m.%Y %H:%M')}\\n"
                f"📝 {appointment.title}"
            )
        else:
            message = self.format_error_message(
                "Fehler beim Speichern des Termins",
                "Bitte versuche es erneut."
            )
        
        # Clear pending data
        context.user_data.pop('pending_appointment', None)
        
        # Add back to menu button
        keyboard = KeyboardBuilder.create_back_to_menu_keyboard()
        
        await self.send_message_safe(
            update, message, parse_mode='Markdown',
            reply_markup=keyboard, edit_message=True
        )
    
    # Legacy method compatibility
    async def today_appointments(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Get today's appointments - legacy compatibility."""
        try:
            today = datetime.now(self.timezone).date()
            appointments = await self.combined_service.get_appointments_for_date(today)
            
            message = TelegramFormatter.format_appointment_list(
                appointments, "📅 Heutige Termine", show_database_source=True
            )
            
            await self.send_message_safe(update, message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error fetching today's appointments: {e}")
            await self.send_message_safe(
                update,
                self.format_error_message("Fehler beim Laden der heutigen Termine")
            )
    
    async def tomorrow_appointments(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Get tomorrow's appointments - legacy compatibility."""
        try:
            tomorrow = datetime.now(self.timezone).date() + timedelta(days=1)
            appointments = await self.combined_service.get_appointments_for_date(tomorrow)
            
            message = TelegramFormatter.format_appointment_list(
                appointments, "📅 Morgige Termine", show_database_source=True
            )
            
            await self.send_message_safe(update, message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error fetching tomorrow's appointments: {e}")
            await self.send_message_safe(
                update,
                self.format_error_message("Fehler beim Laden der morgigen Termine")
            )
    
    async def list_appointments(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """List upcoming appointments - legacy compatibility."""
        try:
            appointments = await self.combined_service.get_upcoming_appointments(
                limit=DEFAULT_APPOINTMENTS_LIMIT
            )
            
            message = TelegramFormatter.format_appointment_list(
                appointments, "📅 Kommende Termine", show_database_source=True
            )
            
            await self.send_message_safe(update, message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error fetching upcoming appointments: {e}")
            await self.send_message_safe(
                update,
                self.format_error_message("Fehler beim Laden der kommenden Termine")
            )
    
    async def add_appointment(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Add appointment - legacy compatibility."""
        await self._handle_add_appointment(update, context)