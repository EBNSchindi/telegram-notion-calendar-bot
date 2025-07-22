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
    
    @rate_limit(max_requests=AI_RATE_LIMIT_REQUESTS, time_window=AI_RATE_LIMIT_WINDOW)
    async def show_recent_memos(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show the most recent memos."""
        if not self.memo_service:
            await update.effective_message.reply_text(
                "❌ Memo-Datenbank nicht konfiguriert. Bitte wende dich an den Administrator.",
                parse_mode='Markdown'
            )
            return
        
        try:
            memos = await self.memo_service.get_recent_memos(limit=DEFAULT_APPOINTMENTS_LIMIT)
            
            if not memos:
                message = "📝 *Deine letzten Memos*\n\nNoch keine Memos vorhanden! 🎯\nErstelle dein erstes Memo mit dem ➕ Button."
            else:
                message = f"📝 *Deine letzten {len(memos)} Memos*\n\n"
                for i, memo in enumerate(memos, 1):
                    # Status emoji
                    status_emoji = {
                        MEMO_STATUS_NOT_STARTED: "⭕",
                        MEMO_STATUS_IN_PROGRESS: "🔄", 
                        MEMO_STATUS_COMPLETED: "✅"
                    }
                    emoji = status_emoji.get(memo.status, "⭕")
                    
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
            logger.error(f"Error showing recent memos: {e}")
            error_message = "❌ Fehler beim Laden der Memos. Bitte versuche es später erneut."
            
            if update.callback_query:
                await update.callback_query.edit_message_text(text=error_message)
            else:
                await update.effective_message.reply_text(text=error_message)
    
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
                "❌ Memo-Datenbank nicht konfiguriert."
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
                    status=MEMO_STATUS_NOT_STARTED,
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
    
    async def handle_memo_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle memo-related callback queries."""
        query = update.callback_query
        await query.answer()
        
        if query.data == "recent_memos":
            await self.show_recent_memos(update, context)
        elif query.data == "add_memo":
            await self.prompt_for_new_memo(update, context)
        elif query.data == "cancel_memo":
            context.user_data['awaiting_memo'] = False
            from src.handlers.enhanced_appointment_handler import EnhancedAppointmentHandler
            handler = EnhancedAppointmentHandler(self.user_config)
            await handler.show_main_menu(update, context)
    
    def is_memo_service_available(self) -> bool:
        """Check if memo service is available."""
        return self.memo_service is not None