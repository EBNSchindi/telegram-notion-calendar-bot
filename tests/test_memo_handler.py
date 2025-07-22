"""Unit tests for MemoHandler."""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from telegram import Update, CallbackQuery, Message, User, Chat, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.handlers.memo_handler import MemoHandler
from src.models.memo import Memo
from config.user_config import UserConfig


@pytest.fixture
def user_config():
    """Create a test user configuration."""
    return UserConfig(
        user_id=123456,
        private_api_key="test_private_key",
        private_database_id="12345678901234567890123456789012",
        memo_database_id="98765432109876543210987654321098",
        shared_api_key="test_shared_key",
        shared_database_id="11111111222222223333333344444444",
        timezone="Europe/Berlin"
    )


@pytest.fixture
def memo_handler(user_config):
    """Create a MemoHandler instance with mocked services."""
    with patch('src.handlers.memo_handler.MemoService') as mock_memo_service:
        with patch('src.handlers.memo_handler.AIAssistantService') as mock_ai_service:
            handler = MemoHandler(user_config)
            # Mock services
            handler.memo_service = mock_memo_service.from_user_config.return_value
            handler.ai_service = mock_ai_service.return_value
            handler.ai_service.is_available.return_value = True
            return handler


@pytest.fixture
def update_with_message():
    """Create a mock Update with message."""
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock(spec=User)
    update.effective_user.id = 123456
    update.effective_user.mention_html.return_value = "@testuser"
    
    update.message = MagicMock(spec=Message)
    update.message.text = "Test message"
    update.message.reply_text = AsyncMock()
    update.effective_message = update.message
    
    update.callback_query = None
    
    return update


@pytest.fixture
def update_with_callback():
    """Create a mock Update with callback query."""
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock(spec=User)
    update.effective_user.id = 123456
    
    update.callback_query = MagicMock(spec=CallbackQuery)
    update.callback_query.data = "test_callback"
    update.callback_query.edit_message_text = AsyncMock()
    update.callback_query.answer = AsyncMock()
    
    update.effective_message = MagicMock()
    update.effective_message.reply_text = AsyncMock()
    
    update.message = None
    
    return update


@pytest.fixture
def context():
    """Create a mock context."""
    ctx = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    ctx.user_data = {}
    return ctx


@pytest.fixture
def sample_memos():
    """Create sample memos for testing."""
    return [
        Memo(
            aufgabe="Einkaufen gehen",
            status="Nicht begonnen",
            faelligkeitsdatum=datetime(2024, 1, 25, tzinfo=timezone.utc),
            bereich="Privat",
            projekt="Haushalt",
            notion_page_id="page-1"
        ),
        Memo(
            aufgabe="Präsentation vorbereiten",
            status="In Arbeit",
            faelligkeitsdatum=datetime(2024, 1, 26, tzinfo=timezone.utc),
            bereich="Arbeit",
            projekt="Q1 Planning",
            notion_page_id="page-2"
        ),
        Memo(
            aufgabe="Buch lesen",
            status="Erledigt",
            notizen="Sehr interessant!",
            notion_page_id="page-3"
        )
    ]


class TestMemoHandler:
    """Test cases for MemoHandler."""
    
    @pytest.mark.asyncio
    async def test_show_recent_memos_with_data(self, memo_handler, update_with_message, context, sample_memos):
        """Test showing recent memos when memos exist."""
        # Mock memo service to return sample memos
        memo_handler.memo_service.get_recent_memos = AsyncMock(return_value=sample_memos)
        
        await memo_handler.show_recent_memos(update_with_message, context)
        
        # Verify memo service was called
        memo_handler.memo_service.get_recent_memos.assert_called_once_with(limit=10)
        
        # Verify message was sent
        update_with_message.effective_message.reply_text.assert_called_once()
        
        # Check message content
        call_args = update_with_message.effective_message.reply_text.call_args
        message_text = call_args[1]['text']
        
        assert "Deine letzten 3 Memos" in message_text
        assert "Einkaufen gehen" in message_text
        assert "Präsentation vorbereiten" in message_text
        assert "Buch lesen" in message_text
        assert "⭕" in message_text  # Not started emoji
        assert "🔄" in message_text  # In progress emoji
        assert "✅" in message_text  # Completed emoji
        
        # Check keyboard
        reply_markup = call_args[1]['reply_markup']
        assert isinstance(reply_markup, InlineKeyboardMarkup)
    
    @pytest.mark.asyncio
    async def test_show_recent_memos_empty(self, memo_handler, update_with_message, context):
        """Test showing recent memos when database is empty."""
        memo_handler.memo_service.get_recent_memos = AsyncMock(return_value=[])
        
        await memo_handler.show_recent_memos(update_with_message, context)
        
        # Check message content
        call_args = update_with_message.effective_message.reply_text.call_args
        message_text = call_args[1]['text']
        
        assert "Noch keine Memos vorhanden" in message_text
        assert "Erstelle dein erstes Memo" in message_text
    
    @pytest.mark.asyncio
    async def test_show_recent_memos_no_service(self, user_config, update_with_message, context):
        """Test showing memos when memo service is not configured."""
        # Create handler without memo service
        with patch('src.handlers.memo_handler.MemoService') as mock_memo_service:
            mock_memo_service.from_user_config.side_effect = ValueError("No memo database")
            handler = MemoHandler(user_config)
            handler.memo_service = None
            
            await handler.show_recent_memos(update_with_message, context)
            
            # Should show error message
            update_with_message.effective_message.reply_text.assert_called_once()
            call_args = update_with_message.effective_message.reply_text.call_args
            assert "Memo-Datenbank nicht konfiguriert" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_prompt_for_new_memo(self, memo_handler, update_with_callback, context):
        """Test prompting user for new memo."""
        await memo_handler.prompt_for_new_memo(update_with_callback, context)
        
        # Check context was set
        assert context.user_data['awaiting_memo'] is True
        
        # Check message
        update_with_callback.callback_query.edit_message_text.assert_called_once()
        call_args = update_with_callback.callback_query.edit_message_text.call_args
        message_text = call_args[1]['text']
        
        assert "Neues Memo erstellen" in message_text
        assert "Beispiele:" in message_text
        assert "KI" in message_text
    
    @pytest.mark.asyncio
    async def test_process_ai_memo_message_success(self, memo_handler, update_with_message, context):
        """Test successful AI memo processing."""
        # Mock AI service response
        ai_response = {
            'aufgabe': 'Einkaufen gehen',
            'faelligkeitsdatum': '2024-01-25',
            'bereich': 'Privat',
            'notizen': 'Milch und Brot',
            'confidence': 0.8
        }
        
        memo_handler.ai_service.extract_memo_from_text = AsyncMock(return_value=ai_response)
        memo_handler.ai_service.validate_memo_data = AsyncMock(return_value=ai_response)
        memo_handler.memo_service.create_memo = AsyncMock(return_value='page-123')
        
        # Set up processing message mock
        processing_msg = MagicMock()
        processing_msg.edit_text = AsyncMock()
        update_with_message.message.reply_text.return_value = processing_msg
        
        # Process message
        update_with_message.message.text = "Einkaufen gehen bis morgen - Milch und Brot"
        await memo_handler.process_ai_memo_message(update_with_message, context)
        
        # Verify AI service was called
        memo_handler.ai_service.extract_memo_from_text.assert_called_once_with(
            "Einkaufen gehen bis morgen - Milch und Brot",
            user_config.timezone
        )
        
        # Verify memo was created
        memo_handler.memo_service.create_memo.assert_called_once()
        created_memo = memo_handler.memo_service.create_memo.call_args[0][0]
        assert created_memo.aufgabe == 'Einkaufen gehen'
        
        # Verify success message
        processing_msg.edit_text.assert_called()
        final_call = processing_msg.edit_text.call_args_list[-1]
        assert "Memo erstellt!" in final_call[1]['text']
    
    @pytest.mark.asyncio
    async def test_process_ai_memo_message_no_extraction(self, memo_handler, update_with_message, context):
        """Test when AI cannot extract memo."""
        memo_handler.ai_service.extract_memo_from_text = AsyncMock(return_value=None)
        
        processing_msg = MagicMock()
        processing_msg.edit_text = AsyncMock()
        update_with_message.message.reply_text.return_value = processing_msg
        
        update_with_message.message.text = "Random text"
        await memo_handler.process_ai_memo_message(update_with_message, context)
        
        # Should show error message
        processing_msg.edit_text.assert_called_with(
            "❌ Konnte kein Memo aus deiner Nachricht extrahieren.\n"
            "Versuche es mit einer klareren Beschreibung:\n\n"
            "*Beispiel:* \"Einkaufen gehen bis morgen\" oder \"Präsentation vorbereiten\"",
            parse_mode='Markdown'
        )
    
    @pytest.mark.asyncio
    async def test_process_ai_memo_message_without_ai(self, memo_handler, update_with_message, context):
        """Test memo processing when AI is not available (fallback)."""
        # Disable AI service
        memo_handler.ai_service.is_available.return_value = False
        
        # Mock fallback response
        fallback_response = {
            'aufgabe': 'Test task',
            'confidence': 0.6
        }
        memo_handler.ai_service.extract_memo_from_text = AsyncMock(return_value=fallback_response)
        memo_handler.ai_service.validate_memo_data = AsyncMock(return_value=fallback_response)
        memo_handler.memo_service.create_memo = AsyncMock(return_value='page-456')
        
        processing_msg = MagicMock()
        processing_msg.edit_text = AsyncMock()
        update_with_message.message.reply_text.return_value = processing_msg
        
        update_with_message.message.text = "Test task"
        await memo_handler.process_ai_memo_message(update_with_message, context)
        
        # Should show non-AI processing message
        update_with_message.message.reply_text.assert_called_with("📝 Erstelle dein Memo...")
        
        # Should still create memo
        memo_handler.memo_service.create_memo.assert_called_once()
        
        # Success message should indicate no AI
        final_call = processing_msg.edit_text.call_args_list[-1]
        assert "Memo erstellt!" in final_call[1]['text']
        assert "Hinweis: Memo ohne KI erstellt" in final_call[1]['text']
    
    @pytest.mark.asyncio
    async def test_handle_memo_callback_recent_memos(self, memo_handler, update_with_callback, context):
        """Test handling callback for recent memos."""
        update_with_callback.callback_query.data = "recent_memos"
        memo_handler.show_recent_memos = AsyncMock()
        
        await memo_handler.handle_memo_callback(update_with_callback, context)
        
        update_with_callback.callback_query.answer.assert_called_once()
        memo_handler.show_recent_memos.assert_called_once_with(update_with_callback, context)
    
    @pytest.mark.asyncio
    async def test_handle_memo_callback_add_memo(self, memo_handler, update_with_callback, context):
        """Test handling callback for adding memo."""
        update_with_callback.callback_query.data = "add_memo"
        memo_handler.prompt_for_new_memo = AsyncMock()
        
        await memo_handler.handle_memo_callback(update_with_callback, context)
        
        memo_handler.prompt_for_new_memo.assert_called_once_with(update_with_callback, context)
    
    @pytest.mark.asyncio
    async def test_handle_memo_callback_cancel(self, memo_handler, update_with_callback, context):
        """Test handling cancel callback."""
        update_with_callback.callback_query.data = "cancel_memo"
        context.user_data['awaiting_memo'] = True
        
        with patch('src.handlers.memo_handler.EnhancedAppointmentHandler') as mock_handler:
            mock_instance = mock_handler.return_value
            mock_instance.show_main_menu = AsyncMock()
            
            await memo_handler.handle_memo_callback(update_with_callback, context)
            
            assert context.user_data['awaiting_memo'] is False
            mock_instance.show_main_menu.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_error_handling_database_error(self, memo_handler, update_with_message, context):
        """Test error handling when database operation fails."""
        memo_handler.memo_service.get_recent_memos = AsyncMock(
            side_effect=Exception("Database error")
        )
        
        await memo_handler.show_recent_memos(update_with_message, context)
        
        # Should show error message
        update_with_message.effective_message.reply_text.assert_called_once()
        call_args = update_with_message.effective_message.reply_text.call_args
        assert "Fehler beim Laden der Memos" in call_args[0][0]
    
    def test_is_memo_service_available(self, memo_handler):
        """Test checking if memo service is available."""
        assert memo_handler.is_memo_service_available() is True
        
        memo_handler.memo_service = None
        assert memo_handler.is_memo_service_available() is False