"""Memo handler for task and memo management."""
import logging
from datetime import datetime, timezone
from typing import List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from telegram.ext import ContextTypes
import pytz

from src.models.memo import Memo
from src.services.memo_service import MemoService
from src.services.ai_assistant_service import AIAssistantService
from config.user_config import UserConfig
from src.utils.rate_limiter import rate_limit
from pydantic import ValidationError
from src.constants import (
    AI_RATE_LIMIT_REQUESTS,
    AI_RATE_LIMIT_WINDOW,
    DEFAULT_APPOINTMENTS_LIMIT,
    MEMO_STATUS_NOT_STARTED,
    MEMO_STATUS_IN_PROGRESS,
    MEMO_STATUS_COMPLETED,
    MEMO_STATUS_POSTPONED,
    MenuButtons
)
from src.utils.error_handler import BotError, ErrorType, ErrorSeverity, SafeOperationContext

logger = logging.getLogger(__name__)


class MemoHandler:
    """Handler for memo-related Telegram commands."""
    
    def __init__(self, user_config: UserConfig):
        self.user_config = user_config
        self.ai_service = AIAssistantService()
        
        # Initialize memo service if memo database is configured
        if user_config.memo_database_id:
            try:
                self.memo_service = MemoService.from_user_config(user_config)
            except ValueError as e:
                logger.error(f"Failed to initialize memo service: {e}")
                self.memo_service = None
        else:
            logger.warning("No memo database configured for user")
            self.memo_service = None
        
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
    
    @rate_limit(max_requests=AI_RATE_LIMIT_REQUESTS, time_window=AI_RATE_LIMIT_WINDOW)
    async def show_recent_memos(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show the most recent memos (only unchecked ones by default)."""
        if not self.memo_service:
            await update.effective_message.reply_text(
                "❌ Memo-Datenbank nicht konfiguriert. Bitte wende dich an den Administrator.",
                parse_mode='Markdown',
                reply_markup=self.get_back_to_menu_keyboard()
            )
            return
        
        try:
            memos = await self.memo_service.get_recent_memos(limit=DEFAULT_APPOINTMENTS_LIMIT)
            
            if not memos:
                message = "📝 *Deine letzten Memos*\n\nNoch keine Memos vorhanden! 🎯\nErstelle dein erstes Memo mit dem ➕ Button."
            else:
                message = f"📝 *Deine letzten {len(memos)} Memos*\n\n"
                for i, memo in enumerate(memos, 1):
                    # Status emoji based on checkbox
                    emoji = "✅" if memo.status_check else "☐"
                    
                    # Format memo entry
                    entry = f"{i}. {emoji} *{memo.aufgabe}*"
                    
                    # Add due date if available
                    if memo.faelligkeitsdatum:
                        local_date = memo.faelligkeitsdatum.astimezone(self.timezone) if memo.faelligkeitsdatum.tzinfo else self.timezone.localize(memo.faelligkeitsdatum)
                        entry += f" (📅 {local_date.strftime('%d.%m.%Y')})"
                    
                    # Add project if available
                    if memo.projekt:
                        entry += f" • 📁 {memo.projekt}"
                    
                    message += entry + "\n"
            
            # Add buttons for actions
            keyboard = [
                [InlineKeyboardButton("➕ Neues Memo", callback_data="add_memo")],
                [InlineKeyboardButton("🏠 Hauptmenü", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Send or edit message depending on context
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    text=message,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            else:
                await update.effective_message.reply_text(
                    text=message,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"Error showing recent memos: {e}", exc_info=True)
            error_message = "❌ Fehler beim Laden der Memos. Bitte versuche es später erneut."
            
            if update.callback_query:
                await update.callback_query.edit_message_text(text=error_message)
            else:
                await update.effective_message.reply_text(text=error_message, reply_markup=self.get_back_to_menu_keyboard())
    
    async def prompt_for_new_memo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Prompt user to enter a new memo."""
        if not self.memo_service:
            await update.effective_message.reply_text(
                "❌ Memo-Datenbank nicht konfiguriert. Bitte wende dich an den Administrator."
            )
            return
        
        message = (
            "📝 *Neues Memo erstellen*\n\n"
            "Schreibe deine Aufgabe oder Notiz:\n\n"
            "*Beispiele:*\n"
            "• Präsentation vorbereiten bis Freitag\n"
            "• Einkaufsliste: Milch, Brot, Butter\n"
            "• Website Projekt: Feedback einholen\n"
            "• Zahnarzttermin buchen\n\n"
            "💡 *Tipp:* Der Bot versteht natürliche Sprache dank KI!"
        )
        
        # Set context for next message
        context.user_data['awaiting_memo'] = True
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=message,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🚫 Abbrechen", callback_data="cancel_memo")
                ]])
            )
        else:
            await update.effective_message.reply_text(
                text=message,
                parse_mode='Markdown',
                reply_markup=ForceReply(selective=True)
            )
    
    async def process_ai_memo_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Process a memo message using AI extraction."""
        if not self.memo_service:
            await update.effective_message.reply_text(
                "❌ Memo-Datenbank nicht konfiguriert.",
                reply_markup=self.get_back_to_menu_keyboard()
            )
            return
        
        user_message = update.message.text
        logger.info(f"Processing memo message: {user_message}")
        
        # Show processing message
        ai_available = self.ai_service.is_available()
        processing_text = "🤖 Verarbeite dein Memo..." if ai_available else "📝 Erstelle dein Memo..."
        processing_msg = await update.message.reply_text(processing_text)
        
        try:
            # Extract memo data using AI
            memo_data = await self.ai_service.extract_memo_from_text(
                user_message, 
                self.user_config.timezone
            )
            
            if not memo_data:
                await processing_msg.edit_text(
                    "❌ Konnte kein Memo aus deiner Nachricht extrahieren.\n"
                    "Versuche es mit einer klareren Beschreibung:\n\n"
                    "*Beispiel:* \"Einkaufen gehen bis morgen\" oder \"Präsentation vorbereiten\"",
                    parse_mode='Markdown'
                )
                return
            
            # Validate memo data
            try:
                validated_data = await self.ai_service.validate_memo_data(memo_data)
            except BotError as e:
                await processing_msg.edit_text(e.user_message)
                return
            except Exception as e:
                logger.error(f"Unexpected error during memo validation: {e}")
                await processing_msg.edit_text("❌ Fehler bei der Memo-Validierung. Bitte versuche es erneut.")
                return
            
            # Parse due date if present
            faelligkeitsdatum = None
            if validated_data.get('faelligkeitsdatum'):
                try:
                    faelligkeitsdatum = datetime.strptime(validated_data['faelligkeitsdatum'], '%Y-%m-%d').replace(tzinfo=timezone.utc)
                except ValueError:
                    logger.warning(f"Failed to parse due date: {validated_data['faelligkeitsdatum']}")
            
            # Create memo object
            try:
                memo = Memo(
                    aufgabe=validated_data['aufgabe'],
                    status_check=False,  # Neue Memos sind standardmäßig nicht abgehakt
                    faelligkeitsdatum=faelligkeitsdatum,
                    bereich=validated_data.get('bereich'),
                    projekt=validated_data.get('projekt'),
                    notizen=validated_data.get('notizen')
                )
            except ValidationError as e:
                await processing_msg.edit_text(f"❌ Fehler beim Erstellen des Memos: {e}")
                return
            
            # Save to Notion
            try:
                page_id = await self.memo_service.create_memo(memo)
                memo.notion_page_id = page_id
                
                # Success message
                ai_note = "" if ai_available else "\n\n_💡 Hinweis: Memo ohne KI erstellt_"
                success_message = f"✅ *Memo erstellt!*\n\n{memo.format_for_telegram(self.user_config.timezone)}{ai_note}"
                
                keyboard = [
                    [InlineKeyboardButton("📝 Letzte Memos", callback_data="recent_memos")],
                    [InlineKeyboardButton("🏠 Hauptmenü", callback_data="main_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await processing_msg.edit_text(
                    text=success_message,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
                
                logger.info(f"Successfully created memo: {memo.aufgabe} (AI: {ai_available})")
                
            except Exception as e:
                logger.error(f"Error creating memo in Notion: {e}")
                await processing_msg.edit_text(
                    "❌ Fehler beim Speichern des Memos in Notion. "
                    "Bitte überprüfe deine Datenbankverbindung."
                )
        
        except BotError as e:
            logger.error(f"Bot error processing memo message: {e}")
            await processing_msg.edit_text(e.user_message)
        except Exception as e:
            logger.error(f"Unexpected error processing memo message: {e}", exc_info=True)
            await processing_msg.edit_text(
                "❌ Unerwarteter Fehler beim Verarbeiten deines Memos. "
                "Bitte versuche es erneut."
            )
        
        finally:
            # Clear context
            context.user_data['awaiting_memo'] = False
    
    async def handle_show_all_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show all memos including checked ones with checkbox indicators."""
        if not self.memo_service:
            await update.effective_message.reply_text(
                "❌ Memo-Datenbank nicht konfiguriert. Bitte wende dich an den Administrator.",
                parse_mode='Markdown',
                reply_markup=self.get_back_to_menu_keyboard()
            )
            return
        
        try:
            memos = await self.memo_service.get_all_memos_including_checked(limit=DEFAULT_APPOINTMENTS_LIMIT)
            
            if not memos:
                message = "📝 *Alle deine Memos*\n\nNoch keine Memos vorhanden! 🎯\nErstelle dein erstes Memo mit dem ➕ Button."
            else:
                message = f"📝 *Alle deine Memos ({len(memos)})*\n\n"
                for i, memo in enumerate(memos, 1):
                    # Use checkbox format for display
                    formatted_memo = memo.format_for_telegram_with_checkbox(self.user_config.timezone or 'Europe/Berlin')
                    # Extract first line for compact display
                    first_line = formatted_memo.split('\n')[0]
                    message += f"{i}. {first_line}\n"
            
            # Add buttons for actions
            keyboard = [
                [InlineKeyboardButton("➕ Neues Memo", callback_data="add_memo")],
                [InlineKeyboardButton("☑️ Memo abhaken", callback_data="check_memo")],
                [InlineKeyboardButton("📝 Nur offene Memos", callback_data="recent_memos")],
                [InlineKeyboardButton("🏠 Hauptmenü", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Send or edit message depending on context
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    text=message,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            else:
                await update.effective_message.reply_text(
                    text=message,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"Error showing all memos: {e}")
            error_message = "❌ Fehler beim Laden aller Memos. Bitte versuche es später erneut."
            
            if update.callback_query:
                await update.callback_query.edit_message_text(text=error_message)
            else:
                await update.effective_message.reply_text(text=error_message, reply_markup=self.get_back_to_menu_keyboard())
    
    async def handle_check_memo_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show a list of unchecked memos with check buttons."""
        if not self.memo_service:
            await update.effective_message.reply_text(
                "❌ Memo-Datenbank nicht konfiguriert. Bitte wende dich an den Administrator.",
                parse_mode='Markdown',
                reply_markup=self.get_back_to_menu_keyboard()
            )
            return
        
        try:
            # Get only unchecked memos
            memos = await self.memo_service.get_recent_memos(limit=10, only_open=True)
            
            if not memos:
                message = "📝 *Memos abhaken*\n\nKeine offenen Memos zum Abhaken vorhanden! 🎯\nErstelle ein neues Memo mit dem ➕ Button."
                keyboard = [
                    [InlineKeyboardButton("➕ Neues Memo", callback_data="add_memo")],
                    [InlineKeyboardButton("🏠 Hauptmenü", callback_data="main_menu")]
                ]
            else:
                message = f"📝 *Memos abhaken ({len(memos)} offen)*\n\nWähle ein Memo zum Abhaken:"
                
                # Create keyboard with check buttons for each memo
                keyboard = []
                for memo in memos:
                    # Limit title length for button display
                    title = memo.aufgabe[:30] + "..." if len(memo.aufgabe) > 30 else memo.aufgabe
                    button_text = f"☑️ {title}"
                    keyboard.append([InlineKeyboardButton(button_text, callback_data=f"check_memo_{memo.notion_page_id}")])
                
                # Add navigation buttons
                keyboard.extend([
                    [InlineKeyboardButton("📝 Alle Memos anzeigen", callback_data="show_all_memos")],
                    [InlineKeyboardButton("🏠 Hauptmenü", callback_data="main_menu")]
                ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Send or edit message depending on context
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    text=message,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            else:
                await update.effective_message.reply_text(
                    text=message,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"Error showing check memo list: {e}")
            error_message = "❌ Fehler beim Laden der Memos zum Abhaken. Bitte versuche es später erneut."
            
            if update.callback_query:
                await update.callback_query.edit_message_text(text=error_message)
            else:
                await update.effective_message.reply_text(text=error_message, reply_markup=self.get_back_to_menu_keyboard())
    
    async def handle_memo_check_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, page_id: str) -> None:
        """Handle checking/unchecking a specific memo."""
        if not self.memo_service:
            await update.callback_query.answer("❌ Memo-Service nicht verfügbar")
            return
        
        query = update.callback_query
        
        try:
            # Update the memo status check to True (checked)
            success = await self.memo_service.update_memo_status_check(page_id, True)
            
            if success:
                await query.answer("✅ Memo als erledigt markiert!")
                
                # Show success message and return to memo list
                message = "✅ *Memo erfolgreich abgehakt!*\n\nDas Memo wurde als erledigt markiert."
                keyboard = [
                    [InlineKeyboardButton("☑️ Weitere Memos abhaken", callback_data="check_memo")],
                    [InlineKeyboardButton("📝 Alle Memos anzeigen", callback_data="show_all_memos")],
                    [InlineKeyboardButton("🏠 Hauptmenü", callback_data="main_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    text=message,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            else:
                await query.answer("❌ Fehler beim Abhaken des Memos")
                
        except Exception as e:
            logger.error(f"Error checking memo {page_id}: {e}")
            await query.answer("❌ Fehler beim Abhaken des Memos")
    
    async def handle_memo_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle memo-related callback queries."""
        query = update.callback_query
        await query.answer()
        
        if query.data == "recent_memos":
            await self.show_recent_memos(update, context)
        elif query.data == "add_memo":
            await self.prompt_for_new_memo(update, context)
        elif query.data == "show_all_memos":
            await self.handle_show_all_command(update, context)
        elif query.data == "check_memo":
            await self.handle_check_memo_command(update, context)
        elif query.data.startswith("check_memo_"):
            # Extract page_id from callback data
            page_id = query.data.replace("check_memo_", "")
            await self.handle_memo_check_callback(update, context, page_id)
        elif query.data == "cancel_memo":
            context.user_data['awaiting_memo'] = False
            # Return to main menu without circular import
            await self._return_to_main_menu(update, context)
    
    async def _return_to_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Return to main menu without circular import."""
        keyboard = [
            [InlineKeyboardButton("📅 Termine verwalten", callback_data="list_appointments")],
            [InlineKeyboardButton("➕ Neuen Termin erstellen", callback_data="create_appointment")],
            [InlineKeyboardButton("🔄 Terminerinnerungen", callback_data="check_reminders")],
            [InlineKeyboardButton("📝 Memos", callback_data="memo_menu")],
            [InlineKeyboardButton("📨 Business-Kalender", callback_data="sync_business_calendar")],
            [InlineKeyboardButton("🔍 Debug-Menü", callback_data="debug_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.message.edit_text(
                "🤖 *Telegram Notion Bot - Hauptmenü*\n\n"
                "Wähle eine Option:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "🤖 *Telegram Notion Bot - Hauptmenü*\n\n"
                "Wähle eine Option:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    
    def is_memo_service_available(self) -> bool:
        """Check if memo service is available."""
        return self.memo_service is not None