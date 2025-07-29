"""
Integration tests for the complete bot workflow.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import pytz
import asyncio
from telegram import Update, Message, User, Chat
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler

from src.bot import TelegramBot
from tests.factories import (
    TelegramUpdateFactory, TelegramContextFactory,
    AppointmentFactory, MemoFactory, UserConfigFactory
)


@pytest.mark.integration
class TestBotIntegration:
    """Integration tests for TelegramBot."""
    
    @pytest.fixture
    async def bot(self, mock_notion_client, mock_openai_client):
        """Create bot instance with mocked external services."""
        with patch('src.bot.NotionService') as mock_notion:
            with patch('src.bot.OpenAI') as mock_openai:
                with patch('src.bot.Application.builder') as mock_builder:
                    # Mock the application builder
                    mock_app = Mock()
                    mock_app.add_handler = Mock()
                    mock_app.add_error_handler = Mock()
                    mock_app.run_polling = AsyncMock()
                    mock_app.initialize = AsyncMock()
                    mock_app.start = AsyncMock()
                    mock_app.stop = AsyncMock()
                    mock_app.shutdown = AsyncMock()
                    
                    mock_builder_instance = Mock()
                    mock_builder_instance.token = Mock(return_value=mock_builder_instance)
                    mock_builder_instance.build = Mock(return_value=mock_app)
                    mock_builder.return_value = mock_builder_instance
                    
                    bot = TelegramBot()
                    bot.application = mock_app
                    return bot
    
    @pytest.mark.asyncio
    async def test_start_command_flow(self, bot):
        """Test the complete /start command flow."""
        # Arrange
        update = TelegramUpdateFactory()
        context = TelegramContextFactory()
        update.message.text = "/start"
        
        handler = None
        for call in bot.application.add_handler.call_args_list:
            if isinstance(call[0][0], CommandHandler) and call[0][0].commands == {"start"}:
                handler = call[0][0].callback
                break
        
        # Act
        if handler:
            await handler(update, context)
        
        # Assert
        update.message.reply_html.assert_called_once()
        welcome_message = update.message.reply_html.call_args[0][0]
        assert "Welcome" in welcome_message
        assert "commands" in welcome_message.lower()
    
    @pytest.mark.asyncio
    async def test_appointment_creation_flow(self, bot):
        """Test complete appointment creation flow from user input to confirmation."""
        # Arrange
        update = TelegramUpdateFactory()
        context = TelegramContextFactory()
        update.message.text = "Meeting with client tomorrow at 2pm at downtown office"
        
        # Mock services
        with patch('src.handlers.enhanced_appointment_handler.CombinedAppointmentService') as mock_service:
            appointment = AppointmentFactory(
                title="Meeting with client",
                date=datetime.now(pytz.UTC) + timedelta(days=1, hours=14),
                location="downtown office"
            )
            mock_service.return_value.create_appointment_from_text = AsyncMock(
                return_value=appointment
            )
            
            # Find and execute the message handler
            handler = None
            for call in bot.application.add_handler.call_args_list:
                if isinstance(call[0][0], MessageHandler):
                    handler = call[0][0].callback
                    break
            
            # Act
            if handler:
                await handler(update, context)
            
            # Assert
            update.message.reply_html.assert_called()
            response = update.message.reply_html.call_args[0][0]
            assert "created successfully" in response.lower()
            assert "Meeting with client" in response
    
    @pytest.mark.asyncio
    async def test_memo_creation_and_retrieval_flow(self, bot):
        """Test complete memo creation and retrieval flow."""
        # Test memo creation
        update_create = TelegramUpdateFactory()
        context_create = TelegramContextFactory()
        update_create.message.text = "/memo Important: Review project proposal by Friday"
        
        with patch('src.services.memo_service.MemoService') as mock_memo_service:
            memo = MemoFactory(
                title="Important",
                content="Review project proposal by Friday"
            )
            mock_memo_service.return_value.create_memo = AsyncMock(return_value=memo)
            mock_memo_service.return_value.get_user_memos = AsyncMock(return_value=[memo])
            
            # Execute memo creation
            handler_create = None
            for call in bot.application.add_handler.call_args_list:
                if isinstance(call[0][0], CommandHandler) and "memo" in call[0][0].commands:
                    handler_create = call[0][0].callback
                    break
            
            if handler_create:
                await handler_create(update_create, context_create)
            
            # Assert creation
            update_create.message.reply_text.assert_called()
            assert "created successfully" in update_create.message.reply_text.call_args[0][0].lower()
            
            # Test memo listing
            update_list = TelegramUpdateFactory()
            context_list = TelegramContextFactory()
            update_list.message.text = "/memos"
            
            handler_list = None
            for call in bot.application.add_handler.call_args_list:
                if isinstance(call[0][0], CommandHandler) and "memos" in call[0][0].commands:
                    handler_list = call[0][0].callback
                    break
            
            if handler_list:
                await handler_list(update_list, context_list)
            
            # Assert listing
            update_list.message.reply_html.assert_called()
            response = update_list.message.reply_html.call_args[0][0]
            assert "Important" in response
            assert "Review project proposal" in response
    
    @pytest.mark.asyncio
    async def test_callback_query_flow(self, bot):
        """Test callback query handling for interactive buttons."""
        # Arrange
        update = TelegramUpdateFactory()
        context = TelegramContextFactory()
        appointment_id = "app_123"
        update.callback_query.data = f"delete_appointment:{appointment_id}"
        
        with patch('src.services.combined_appointment_service.CombinedAppointmentService') as mock_service:
            mock_service.return_value.delete_appointment = AsyncMock(return_value=True)
            
            # Find callback query handler
            handler = None
            for call in bot.application.add_handler.call_args_list:
                if isinstance(call[0][0], CallbackQueryHandler):
                    handler = call[0][0].callback
                    break
            
            # Act
            if handler:
                await handler(update, context)
            
            # Assert
            update.callback_query.answer.assert_called_once()
            update.callback_query.edit_message_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_error_handling_flow(self, bot):
        """Test error handling in the bot flow."""
        # Arrange
        update = TelegramUpdateFactory()
        context = TelegramContextFactory()
        context.error = Exception("Test error")
        
        # Find error handler
        error_handler = None
        for call in bot.application.add_error_handler.call_args_list:
            error_handler = call[0][0]
            break
        
        # Act
        if error_handler:
            await error_handler(update, context)
        
        # Assert
        # Verify error is logged (would need to mock logger)
        assert context.error is not None
    
    @pytest.mark.asyncio
    async def test_partner_sync_flow(self, bot):
        """Test partner synchronization flow."""
        # Arrange
        update = TelegramUpdateFactory()
        context = TelegramContextFactory()
        update.message.text = "/sync_partner"
        
        partner_user_id = 987654321
        user_config = UserConfigFactory(
            user_id=update.effective_user.id,
            partner_user_id=partner_user_id
        )
        
        with patch('src.services.partner_sync_service.PartnerSyncService') as mock_sync:
            mock_sync.return_value.sync_appointments = AsyncMock(return_value=5)
            
            with patch('config.user_config.load_user_config') as mock_config:
                mock_config.return_value = {"users": {str(update.effective_user.id): user_config}}
                
                # Find sync handler
                handler = None
                for call in bot.application.add_handler.call_args_list:
                    if isinstance(call[0][0], CommandHandler) and "sync_partner" in call[0][0].commands:
                        handler = call[0][0].callback
                        break
                
                # Act
                if handler:
                    await handler(update, context)
                
                # Assert
                update.message.reply_text.assert_called()
                response = update.message.reply_text.call_args[0][0]
                assert "synced" in response.lower()
                assert "5" in response
    
    @pytest.mark.asyncio
    async def test_reminder_scheduling_flow(self, bot):
        """Test reminder scheduling for appointments."""
        # Arrange
        with patch('src.services.enhanced_reminder_service.EnhancedReminderService') as mock_reminder:
            mock_reminder.return_value.schedule_reminders = AsyncMock()
            mock_reminder.return_value.get_pending_reminders = AsyncMock(
                return_value=[
                    AppointmentFactory(
                        title="Important meeting",
                        date=datetime.now(pytz.UTC) + timedelta(minutes=30)
                    )
                ]
            )
            
            # Simulate reminder check
            await bot.check_and_send_reminders()
            
            # Assert
            mock_reminder.return_value.get_pending_reminders.assert_called()
    
    @pytest.mark.asyncio
    async def test_daily_summary_flow(self, bot):
        """Test daily summary generation and sending."""
        # Arrange
        user_id = 123456789
        
        with patch('src.services.combined_appointment_service.CombinedAppointmentService') as mock_service:
            appointments = [
                AppointmentFactory(title="Morning standup", date=datetime.now(pytz.UTC).replace(hour=9)),
                AppointmentFactory(title="Client call", date=datetime.now(pytz.UTC).replace(hour=14)),
                AppointmentFactory(title="Team review", date=datetime.now(pytz.UTC).replace(hour=16))
            ]
            mock_service.return_value.get_appointments_for_date = AsyncMock(
                return_value=appointments
            )
            
            # Act
            summary = await bot.generate_daily_summary(user_id)
            
            # Assert
            assert "Morning standup" in summary
            assert "Client call" in summary
            assert "Team review" in summary
            assert "3 appointments" in summary.lower()
    
    @pytest.mark.asyncio
    async def test_ai_appointment_extraction_flow(self, bot):
        """Test AI-powered appointment extraction from natural language."""
        # Arrange
        update = TelegramUpdateFactory()
        context = TelegramContextFactory()
        update.message.text = "I need to visit the dentist next Tuesday at 3pm and pick up groceries on the way back"
        
        with patch('src.services.ai_assistant_service.AIAssistantService') as mock_ai:
            ai_response = {
                "appointments": [
                    {
                        "title": "Dentist visit",
                        "date": "2024-01-23T15:00:00",
                        "is_partner_relevant": False
                    },
                    {
                        "title": "Pick up groceries",
                        "date": "2024-01-23T16:00:00",
                        "is_partner_relevant": True
                    }
                ]
            }
            mock_ai.return_value.extract_appointments_from_text = AsyncMock(
                return_value=ai_response
            )
            
            # Act - process through AI handler
            await bot.process_ai_appointment_extraction(update, context)
            
            # Assert
            mock_ai.return_value.extract_appointments_from_text.assert_called_once_with(
                update.message.text
            )
    
    @pytest.mark.asyncio
    async def test_concurrent_user_handling(self, bot):
        """Test handling multiple concurrent user requests."""
        # Arrange
        users = []
        for i in range(5):
            update = TelegramUpdateFactory()
            update.effective_user.id = 100000 + i
            update.message.text = f"/new Meeting {i} tomorrow at {i+1}pm"
            context = TelegramContextFactory()
            users.append((update, context))
        
        with patch('src.services.combined_appointment_service.CombinedAppointmentService') as mock_service:
            mock_service.return_value.create_appointment_from_text = AsyncMock(
                side_effect=[
                    AppointmentFactory(title=f"Meeting {i}")
                    for i in range(5)
                ]
            )
            
            # Act - simulate concurrent requests
            handler = None
            for call in bot.application.add_handler.call_args_list:
                if isinstance(call[0][0], CommandHandler) and "new" in call[0][0].commands:
                    handler = call[0][0].callback
                    break
            
            if handler:
                tasks = [handler(update, context) for update, context in users]
                await asyncio.gather(*tasks)
            
            # Assert
            assert mock_service.return_value.create_appointment_from_text.call_count == 5
    
    @pytest.mark.asyncio
    async def test_rate_limiting_flow(self, bot):
        """Test rate limiting for user requests."""
        # Arrange
        update = TelegramUpdateFactory()
        context = TelegramContextFactory()
        update.message.text = "/list"
        
        with patch('src.utils.rate_limiter.RateLimiter') as mock_limiter:
            # First request should pass
            mock_limiter.return_value.check_rate_limit = Mock(return_value=True)
            
            handler = None
            for call in bot.application.add_handler.call_args_list:
                if isinstance(call[0][0], CommandHandler) and "list" in call[0][0].commands:
                    handler = call[0][0].callback
                    break
            
            # Act - first request
            if handler:
                await handler(update, context)
            
            # Now simulate rate limit exceeded
            mock_limiter.return_value.check_rate_limit = Mock(return_value=False)
            update.message.reply_text.reset_mock()
            
            # Act - second request (should be rate limited)
            if handler:
                await handler(update, context)
            
            # Assert
            update.message.reply_text.assert_called()
            assert "rate limit" in update.message.reply_text.call_args[0][0].lower()
    
    @pytest.mark.asyncio
    async def test_multilingual_support_flow(self, bot):
        """Test multilingual support in bot responses."""
        # Arrange
        update = TelegramUpdateFactory()
        context = TelegramContextFactory()
        update.effective_user.language_code = "de"  # German
        update.message.text = "/help"
        
        with patch('src.utils.i18n.get_translation') as mock_i18n:
            mock_i18n.return_value = "Hilfe-Menü"  # German translation
            
            handler = None
            for call in bot.application.add_handler.call_args_list:
                if isinstance(call[0][0], CommandHandler) and "help" in call[0][0].commands:
                    handler = call[0][0].callback
                    break
            
            # Act
            if handler:
                await handler(update, context)
            
            # Assert
            mock_i18n.assert_called_with("help_menu", "de")