"""Comprehensive error handling tests for the bot."""
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime, timezone
import json
import asyncio
from telegram.error import TelegramError, NetworkError, TimedOut
from src.services.ai_assistant_service import AIAssistantService
from src.services.memo_service import MemoService
from src.services.notion_service import NotionService
from src.services.partner_sync_service import PartnerSyncService
from src.handlers.enhanced_appointment_handler import EnhancedAppointmentHandler
from src.handlers.memo_handler import MemoHandler
from config.user_config import UserConfig


@pytest.fixture
def user_config():
    """Create a test user configuration."""
    return UserConfig(
        user_id=123456,
        private_api_key="test_key",
        private_database_id="12345678901234567890123456789012",
        memo_database_id="98765432109876543210987654321098"
    )


class TestNotionServiceErrorHandling:
    """Test error handling in Notion service."""
    
    @pytest.mark.asyncio
    async def test_notion_api_connection_error(self, user_config):
        """Test handling Notion API connection errors."""
        with patch('notion_client.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            
            # Simulate connection error
            mock_client.databases.query = AsyncMock(
                side_effect=Exception("Connection refused")
            )
            
            service = NotionService(user_config.private_api_key, user_config.private_database_id)
            service.client = mock_client
            
            # Should handle error gracefully
            result = await service.query_database()
            assert result == {'results': []}  # Empty result on error
    
    @pytest.mark.asyncio
    async def test_notion_api_rate_limit(self, user_config):
        """Test handling Notion API rate limits."""
        with patch('notion_client.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            
            # Simulate rate limit error
            mock_client.pages.create = AsyncMock(
                side_effect=Exception("Rate limited")
            )
            
            service = NotionService(user_config.private_api_key, user_config.private_database_id)
            service.client = mock_client
            
            # Should handle error gracefully
            with pytest.raises(Exception) as exc_info:
                await service.create_page({})
            
            assert "Rate limited" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_notion_invalid_database_id(self):
        """Test handling invalid database ID."""
        with patch('notion_client.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            
            # Invalid database ID
            service = NotionService("test_key", "invalid_id")
            service.client = mock_client
            
            mock_client.databases.query = AsyncMock(
                side_effect=Exception("Database not found")
            )
            
            result = await service.query_database()
            assert result == {'results': []}


class TestAIServiceErrorHandling:
    """Test error handling in AI service."""
    
    @pytest.mark.asyncio
    async def test_ai_service_no_api_key(self):
        """Test AI service behavior without API key."""
        with patch.dict('os.environ', {}, clear=True):
            service = AIAssistantService()
            
            assert service.client is None
            assert not service.is_available()
            
            # Should use fallback
            result = await service.extract_memo_from_text("Test memo")
            assert result is not None  # Fallback should work
            assert result['confidence'] == 0.6  # Fallback confidence
    
    @pytest.mark.asyncio
    async def test_ai_service_timeout(self):
        """Test AI service timeout handling."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test_key'}):
            service = AIAssistantService()
            service.timeout = 0.1  # Very short timeout
            
            # Mock slow response
            async def slow_response(*args, **kwargs):
                await asyncio.sleep(1)
                return MagicMock()
            
            with patch.object(service, 'client') as mock_client:
                mock_client.chat.completions.create = slow_response
                
                result = await service.extract_appointment_from_text("Test")
                assert result is None  # Should timeout
    
    @pytest.mark.asyncio
    async def test_ai_service_json_parse_error(self):
        """Test AI service handling invalid JSON responses."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test_key'}):
            service = AIAssistantService()
            
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Not valid JSON"
            
            with patch.object(service, 'client') as mock_client:
                mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
                
                result = await service.extract_appointment_from_text("Test")
                assert result is None  # Should handle JSON error
    
    @pytest.mark.asyncio
    async def test_ai_service_retry_mechanism(self):
        """Test AI service retry mechanism."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test_key'}):
            service = AIAssistantService()
            service.max_retries = 3
            
            call_count = 0
            
            async def failing_then_success(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    raise Exception("Temporary error")
                
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = json.dumps({
                    "aufgabe": "Test",
                    "confidence": 0.8
                })
                return mock_response
            
            with patch.object(service, 'client') as mock_client:
                mock_client.chat.completions.create = failing_then_success
                
                result = await service.extract_memo_from_text("Test")
                assert result is not None
                assert call_count == 3  # Should retry twice before success


class TestTelegramErrorHandling:
    """Test handling Telegram-specific errors."""
    
    @pytest.mark.asyncio
    async def test_telegram_network_error(self, user_config):
        """Test handling Telegram network errors."""
        handler = EnhancedAppointmentHandler(user_config, None)
        
        update = MagicMock()
        update.message = MagicMock()
        update.message.reply_text = AsyncMock(side_effect=NetworkError("Network error"))
        update.effective_user = MagicMock()
        update.effective_user.first_name = "Test"
        
        context = MagicMock()
        
        # Should handle network error gracefully
        with patch('logging.Logger.error') as mock_log:
            await handler.show_main_menu(update, context)
            mock_log.assert_called()
    
    @pytest.mark.asyncio
    async def test_telegram_timeout_error(self, user_config):
        """Test handling Telegram timeout errors."""
        memo_handler = MemoHandler(user_config)
        memo_handler.memo_service = MagicMock()
        
        update = MagicMock()
        update.effective_message = MagicMock()
        update.effective_message.reply_text = AsyncMock(side_effect=TimedOut())
        
        context = MagicMock()
        
        # Should handle timeout gracefully
        await memo_handler.show_recent_memos(update, context)
        
        # Should have attempted to send message
        update.effective_message.reply_text.assert_called()
    
    @pytest.mark.asyncio
    async def test_callback_query_already_answered(self, user_config):
        """Test handling already answered callback queries."""
        handler = EnhancedAppointmentHandler(user_config, None)
        
        update = MagicMock()
        update.callback_query = MagicMock()
        update.callback_query.answer = AsyncMock(
            side_effect=TelegramError("Query already answered")
        )
        update.callback_query.data = "test"
        
        context = MagicMock()
        
        # Should handle gracefully
        await handler.handle_callback(update, context)


class TestPartnerSyncErrorHandling:
    """Test error handling in partner sync service."""
    
    @pytest.mark.asyncio
    async def test_sync_with_database_error(self, user_config):
        """Test sync handling database errors."""
        service = PartnerSyncService()
        
        with patch.object(service, '_get_notion_services') as mock_get_services:
            mock_private = MagicMock()
            mock_shared = MagicMock()
            
            # Simulate database error
            mock_private.get_all_appointments = AsyncMock(
                side_effect=Exception("Database error")
            )
            
            mock_get_services.return_value = (mock_private, mock_shared)
            
            result = await service.sync_partner_relevant_appointments(user_config)
            
            assert result['errors'] > 0
            assert 'error_details' in result
    
    @pytest.mark.asyncio
    async def test_sync_partial_failure(self, user_config):
        """Test sync with partial failures."""
        service = PartnerSyncService()
        
        from src.models.appointment import Appointment
        
        appointments = [
            Appointment(
                title="Success",
                date=datetime.now(timezone.utc),
                partner_relevant=True,
                notion_page_id="1"
            ),
            Appointment(
                title="Fail",
                date=datetime.now(timezone.utc),
                partner_relevant=True,
                notion_page_id="2"
            )
        ]
        
        with patch.object(service, '_get_notion_services') as mock_get_services:
            mock_private = MagicMock()
            mock_shared = MagicMock()
            
            mock_private.get_all_appointments = AsyncMock(return_value=appointments)
            
            # First succeeds, second fails
            call_count = 0
            
            async def create_with_failure(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return "shared-1"
                else:
                    raise Exception("Create failed")
            
            mock_shared.create_page = create_with_failure
            mock_private.update_page = AsyncMock(return_value=True)
            
            mock_get_services.return_value = (mock_private, mock_shared)
            
            result = await service.sync_partner_relevant_appointments(user_config)
            
            assert result['synced_count'] == 1
            assert result['errors'] == 1


class TestValidationErrorHandling:
    """Test input validation error handling."""
    
    @pytest.mark.asyncio
    async def test_invalid_memo_data_validation(self):
        """Test validation of invalid memo data."""
        from src.models.memo import Memo
        from pydantic import ValidationError
        
        # Missing required field
        with pytest.raises(ValidationError):
            Memo(status="Invalid")  # Missing 'aufgabe'
    
    @pytest.mark.asyncio
    async def test_invalid_appointment_date(self):
        """Test handling invalid appointment dates."""
        service = AIAssistantService()
        
        # Invalid date format
        data = {
            'title': 'Test',
            'date': 'invalid-date',
            'confidence': 0.8
        }
        
        with pytest.raises(ValueError) as exc_info:
            await service.validate_appointment_data(data)
        
        assert "Invalid date format" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_memo_text_length_validation(self):
        """Test memo text length validation."""
        service = AIAssistantService()
        
        # Very long text
        long_text = "x" * 1000
        data = {
            'aufgabe': long_text,
            'notizen': long_text * 3,
            'confidence': 0.8
        }
        
        validated = await service.validate_memo_data(data)
        
        # Should truncate
        assert len(validated['aufgabe']) <= 200
        assert len(validated['notizen']) <= 2000


class TestConcurrencyErrorHandling:
    """Test handling concurrent operations."""
    
    @pytest.mark.asyncio
    async def test_concurrent_sync_operations(self, user_config):
        """Test handling concurrent sync operations."""
        service = PartnerSyncService()
        
        with patch.object(service, 'sync_partner_relevant_appointments') as mock_sync:
            mock_sync.return_value = {'synced_count': 1, 'errors': 0}
            
            # Simulate concurrent sync requests
            tasks = []
            for _ in range(5):
                task = service.sync_partner_relevant_appointments(user_config)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All should complete without exceptions
            assert all(isinstance(r, dict) for r in results)
    
    @pytest.mark.asyncio
    async def test_database_lock_handling(self, user_config):
        """Test handling database lock scenarios."""
        memo_service = MemoService(
            user_config.private_api_key,
            user_config.memo_database_id
        )
        
        with patch.object(memo_service, 'notion_service') as mock_notion:
            # Simulate database lock error
            mock_notion.create_page = AsyncMock(
                side_effect=Exception("Database is locked")
            )
            
            from src.models.memo import Memo
            memo = Memo(aufgabe="Test", status="Nicht begonnen")
            
            with pytest.raises(Exception) as exc_info:
                await memo_service.create_memo(memo)
            
            assert "Database is locked" in str(exc_info.value)


class TestRecoveryMechanisms:
    """Test error recovery mechanisms."""
    
    @pytest.mark.asyncio
    async def test_notion_reconnection(self):
        """Test Notion service reconnection after error."""
        service = NotionService("test_key", "test_db")
        
        with patch('notion_client.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            
            # First call fails
            mock_client.databases.query = AsyncMock(
                side_effect=[Exception("Connection lost"), {'results': []}]
            )
            
            # First attempt fails
            result1 = await service.query_database()
            assert result1 == {'results': []}
            
            # Second attempt should work
            result2 = await service.query_database()
            assert result2 == {'results': []}
    
    @pytest.mark.asyncio
    async def test_graceful_degradation(self, user_config):
        """Test graceful degradation when services fail."""
        handler = EnhancedAppointmentHandler(user_config, None)
        
        # Mock all services to fail
        handler.appointment_service = MagicMock()
        handler.appointment_service.get_upcoming_appointments = AsyncMock(
            side_effect=Exception("Service unavailable")
        )
        
        update = MagicMock()
        update.effective_message = MagicMock()
        update.effective_message.reply_text = AsyncMock()
        
        context = MagicMock()
        
        # Should show error message instead of crashing
        await handler.list_appointments(update, context)
        
        update.effective_message.reply_text.assert_called()
        call_args = update.effective_message.reply_text.call_args
        assert "Fehler" in call_args[0][0] or "Error" in call_args[0][0]