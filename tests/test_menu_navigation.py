"""Tests for menu navigation and UI flow."""
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from telegram import Update, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, User
from telegram.ext import ContextTypes
from src.handlers.enhanced_appointment_handler import EnhancedAppointmentHandler
from src.handlers.memo_handler import MemoHandler
from config.user_config import UserConfig


@pytest.fixture
def user_config():
    """Create a test user configuration."""
    return UserConfig(
        user_id=123456,
        private_api_key="test_private_key",
        private_database_id="12345678901234567890123456789012",
        shared_api_key="test_shared_key",
        shared_database_id="11111111222222223333333344444444",
        timezone="Europe/Berlin",
        memo_database_id="98765432109876543210987654321098"
    )


@pytest.fixture
def appointment_handler(user_config):
    """Create an EnhancedAppointmentHandler instance."""
    with patch('src.handlers.enhanced_appointment_handler.CombinedAppointmentService'):
        with patch('src.handlers.enhanced_appointment_handler.BusinessCalendarSyncManager'):
            with patch('src.handlers.enhanced_appointment_handler.AIAssistantService'):
                with patch('src.handlers.enhanced_appointment_handler.MemoHandler'):
                    handler = EnhancedAppointmentHandler(user_config, None)
                    # Mock services
                    handler.appointment_service = MagicMock()
                    handler.ai_service = MagicMock()
                    handler.ai_service.is_available.return_value = True
                    handler.memo_handler = MagicMock()
                    handler.memo_handler.is_memo_service_available.return_value = True
                    return handler


@pytest.fixture
def update_with_callback():
    """Create a mock Update with callback query."""
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock(spec=User)
    update.effective_user.id = 123456
    update.effective_user.first_name = "Test"
    
    update.callback_query = MagicMock(spec=CallbackQuery)
    update.callback_query.data = "main_menu"
    update.callback_query.edit_message_text = AsyncMock()
    update.callback_query.answer = AsyncMock()
    update.callback_query.message = MagicMock()
    
    update.effective_message = MagicMock()
    update.message = None
    
    return update


@pytest.fixture
def update_with_message():
    """Create a mock Update with message."""
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock(spec=User)
    update.effective_user.id = 123456
    update.effective_user.first_name = "Test"
    
    update.message = MagicMock()
    update.message.reply_text = AsyncMock()
    update.message.reply_html = AsyncMock()
    update.effective_message = update.message
    
    update.callback_query = None
    
    return update


@pytest.fixture
def context():
    """Create a mock context."""
    ctx = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    ctx.user_data = {}
    return ctx


class TestMainMenuNavigation:
    """Test main menu navigation."""
    
    @pytest.mark.asyncio
    async def test_show_main_menu_initial(self, appointment_handler, update_with_message, context):
        """Test showing main menu for the first time."""
        await appointment_handler.show_main_menu(update_with_message, context)
        
        # Verify message was sent
        update_with_message.message.reply_text.assert_called_once()
        
        # Check message content
        call_args = update_with_message.message.reply_text.call_args
        message_text = call_args[1]['text']
        
        assert "Willkommen" in message_text or "Hauptmenü" in message_text
        
        # Check keyboard
        reply_markup = call_args[1]['reply_markup']
        assert isinstance(reply_markup, InlineKeyboardMarkup)
        
        # Verify main menu buttons exist
        buttons = reply_markup.inline_keyboard
        button_texts = [btn[0].text for btn in buttons if btn]
        
        expected_buttons = ["Termine anzeigen", "Neuer Termin", "Letzte Memos"]
        for expected in expected_buttons:
            assert any(expected in text for text in button_texts)
    
    @pytest.mark.asyncio
    async def test_show_main_menu_from_callback(self, appointment_handler, update_with_callback, context):
        """Test showing main menu from callback query."""
        await appointment_handler.show_main_menu(update_with_callback, context)
        
        # Should edit message instead of sending new one
        update_with_callback.callback_query.edit_message_text.assert_called_once()
        
        # Check keyboard structure
        call_args = update_with_callback.callback_query.edit_message_text.call_args
        reply_markup = call_args[1]['reply_markup']
        assert isinstance(reply_markup, InlineKeyboardMarkup)
    
    @pytest.mark.asyncio
    async def test_navigate_to_appointments_menu(self, appointment_handler, update_with_callback, context):
        """Test navigating to appointments menu."""
        update_with_callback.callback_query.data = "show_appointments"
        
        # Mock appointment service response
        appointment_handler.appointment_service.get_upcoming_appointments = AsyncMock(return_value=[])
        
        await appointment_handler.handle_callback(update_with_callback, context)
        
        # Should answer callback
        update_with_callback.callback_query.answer.assert_called_once()
        
        # Should show appointments
        appointment_handler.appointment_service.get_upcoming_appointments.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_navigate_to_memo_menu(self, appointment_handler, update_with_callback, context):
        """Test navigating to memo menu."""
        update_with_callback.callback_query.data = "recent_memos"
        
        # Mock memo handler
        appointment_handler.memo_handler.handle_memo_callback = AsyncMock()
        
        await appointment_handler.handle_callback(update_with_callback, context)
        
        # Should delegate to memo handler
        appointment_handler.memo_handler.handle_memo_callback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_back_to_main_menu(self, appointment_handler, update_with_callback, context):
        """Test going back to main menu."""
        update_with_callback.callback_query.data = "main_menu"
        
        await appointment_handler.handle_callback(update_with_callback, context)
        
        # Should show main menu
        update_with_callback.callback_query.edit_message_text.assert_called()
        
        call_args = update_with_callback.callback_query.edit_message_text.call_args
        message_text = call_args[1]['text']
        assert "Hauptmenü" in message_text or "Willkommen" in message_text


class TestAppointmentMenuNavigation:
    """Test appointment-related menu navigation."""
    
    @pytest.mark.asyncio
    async def test_appointment_detail_view(self, appointment_handler, update_with_callback, context):
        """Test viewing appointment details."""
        update_with_callback.callback_query.data = "view_appt_123"
        
        # Mock appointment data
        from src.models.appointment import Appointment
        from datetime import datetime, timezone
        
        mock_appointment = Appointment(
            title="Test Appointment",
            date=datetime.now(timezone.utc),
            description="Test description",
            notion_page_id="123"
        )
        
        appointment_handler.appointment_service.get_appointment_by_id = AsyncMock(
            return_value=mock_appointment
        )
        
        await appointment_handler.handle_callback(update_with_callback, context)
        
        # Should fetch appointment
        appointment_handler.appointment_service.get_appointment_by_id.assert_called_with("123")
        
        # Should show appointment details
        update_with_callback.callback_query.edit_message_text.assert_called()
        call_args = update_with_callback.callback_query.edit_message_text.call_args
        message_text = call_args[1]['text']
        
        assert "Test Appointment" in message_text
    
    @pytest.mark.asyncio
    async def test_add_appointment_flow(self, appointment_handler, update_with_callback, context):
        """Test appointment creation flow navigation."""
        # Start appointment creation
        update_with_callback.callback_query.data = "add_appointment"
        
        await appointment_handler.handle_callback(update_with_callback, context)
        
        # Should set context for appointment input
        assert context.user_data.get('awaiting_appointment') is True
        
        # Should show input prompt
        update_with_callback.callback_query.edit_message_text.assert_called()
        call_args = update_with_callback.callback_query.edit_message_text.call_args
        message_text = call_args[1]['text']
        
        assert "Termin" in message_text or "eingeben" in message_text
    
    @pytest.mark.asyncio
    async def test_cancel_appointment_creation(self, appointment_handler, update_with_callback, context):
        """Test canceling appointment creation."""
        # Set context as if in appointment creation
        context.user_data['awaiting_appointment'] = True
        
        update_with_callback.callback_query.data = "cancel_appointment"
        
        await appointment_handler.handle_callback(update_with_callback, context)
        
        # Should clear context
        assert context.user_data.get('awaiting_appointment') is False
        
        # Should return to main menu
        update_with_callback.callback_query.edit_message_text.assert_called()


class TestMemoMenuNavigation:
    """Test memo-related menu navigation."""
    
    @pytest.mark.asyncio
    async def test_memo_list_navigation(self, user_config):
        """Test memo list navigation."""
        memo_handler = MemoHandler(user_config)
        memo_handler.memo_service = MagicMock()
        memo_handler.memo_service.get_recent_memos = AsyncMock(return_value=[])
        
        update = MagicMock()
        update.callback_query = MagicMock()
        update.callback_query.data = "recent_memos"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.effective_message = MagicMock()
        
        context = MagicMock()
        
        await memo_handler.handle_memo_callback(update, context)
        
        # Should fetch memos
        memo_handler.memo_service.get_recent_memos.assert_called()
        
        # Should show memo list
        update.callback_query.edit_message_text.assert_called()
    
    @pytest.mark.asyncio
    async def test_add_memo_navigation(self, user_config):
        """Test navigating to add memo."""
        memo_handler = MemoHandler(user_config)
        memo_handler.memo_service = MagicMock()
        
        update = MagicMock()
        update.callback_query = MagicMock()
        update.callback_query.data = "add_memo"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        
        context = MagicMock()
        context.user_data = {}
        
        await memo_handler.handle_memo_callback(update, context)
        
        # Should set context for memo input
        assert context.user_data.get('awaiting_memo') is True
        
        # Should show input prompt
        update.callback_query.edit_message_text.assert_called()


class TestNavigationEdgeCases:
    """Test edge cases in navigation."""
    
    @pytest.mark.asyncio
    async def test_unknown_callback_data(self, appointment_handler, update_with_callback, context):
        """Test handling unknown callback data."""
        update_with_callback.callback_query.data = "unknown_action"
        
        await appointment_handler.handle_callback(update_with_callback, context)
        
        # Should still answer callback to prevent timeout
        update_with_callback.callback_query.answer.assert_called()
    
    @pytest.mark.asyncio
    async def test_navigation_with_no_memo_service(self, user_config):
        """Test navigation when memo service is not available."""
        with patch('src.handlers.enhanced_appointment_handler.MemoHandler') as mock_memo_class:
            mock_memo = MagicMock()
            mock_memo.is_memo_service_available.return_value = False
            mock_memo_class.return_value = mock_memo
            
            handler = EnhancedAppointmentHandler(user_config, None)
            handler.appointment_service = MagicMock()
            
            update = MagicMock()
            update.message = MagicMock()
            update.message.reply_text = AsyncMock()
            update.effective_user = MagicMock()
            update.effective_user.first_name = "Test"
            update.callback_query = None
            
            context = MagicMock()
            
            await handler.show_main_menu(update, context)
            
            # Check that memo button is not included
            call_args = update.message.reply_text.call_args
            reply_markup = call_args[1]['reply_markup']
            
            button_texts = []
            for row in reply_markup.inline_keyboard:
                for btn in row:
                    button_texts.append(btn.text)
            
            # Memo button should not be present
            assert not any("Memo" in text for text in button_texts)
    
    @pytest.mark.asyncio
    async def test_concurrent_navigation(self, appointment_handler, context):
        """Test handling concurrent navigation requests."""
        # Simulate rapid navigation clicks
        updates = []
        for i in range(5):
            update = MagicMock()
            update.callback_query = MagicMock()
            update.callback_query.data = "main_menu"
            update.callback_query.answer = AsyncMock()
            update.callback_query.edit_message_text = AsyncMock()
            update.effective_user = MagicMock()
            update.effective_user.id = 123456
            update.effective_user.first_name = "Test"
            updates.append(update)
        
        # Process all navigation requests
        for update in updates:
            await appointment_handler.handle_callback(update, context)
        
        # All callbacks should be answered
        for update in updates:
            update.callback_query.answer.assert_called()


class TestDeepLinkNavigation:
    """Test deep link navigation patterns."""
    
    @pytest.mark.asyncio
    async def test_appointment_quick_actions(self, appointment_handler, update_with_callback, context):
        """Test quick action buttons in appointment view."""
        # Simulate viewing an appointment
        update_with_callback.callback_query.data = "view_appt_123"
        
        from src.models.appointment import Appointment
        from datetime import datetime, timezone
        
        mock_appointment = Appointment(
            title="Test Appointment",
            date=datetime.now(timezone.utc),
            notion_page_id="123"
        )
        
        appointment_handler.appointment_service.get_appointment_by_id = AsyncMock(
            return_value=mock_appointment
        )
        
        await appointment_handler.handle_callback(update_with_callback, context)
        
        # Check that action buttons are included
        call_args = update_with_callback.callback_query.edit_message_text.call_args
        reply_markup = call_args[1]['reply_markup']
        
        # Should have delete and back buttons
        button_callbacks = []
        for row in reply_markup.inline_keyboard:
            for btn in row:
                if btn.callback_data:
                    button_callbacks.append(btn.callback_data)
        
        assert any("delete" in cb for cb in button_callbacks)
        assert any("back" in cb or "main" in cb for cb in button_callbacks)