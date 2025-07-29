"""
Comprehensive unit tests for EnhancedAppointmentHandler with edge cases.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import pytz
from freezegun import freeze_time

from src.handlers.enhanced_appointment_handler import EnhancedAppointmentHandler
from src.models.appointment import Appointment
from tests.factories import (
    TelegramUpdateFactory, TelegramContextFactory,
    AppointmentFactory, UserConfigFactory
)


@pytest.mark.unit
class TestEnhancedAppointmentHandler:
    """Test suite for EnhancedAppointmentHandler."""
    
    @pytest.fixture
    def handler(self, mock_notion_client, mock_openai_client):
        """Create handler instance with mocked dependencies."""
        with patch('src.handlers.enhanced_appointment_handler.NotionService') as mock_notion_service:
            with patch('src.handlers.enhanced_appointment_handler.CombinedAppointmentService') as mock_appointment_service:
                with patch('src.handlers.enhanced_appointment_handler.PartnerSyncService') as mock_partner_service:
                    handler = EnhancedAppointmentHandler()
                    handler.notion_service = Mock()
                    handler.appointment_service = Mock()
                    handler.partner_sync_service = Mock()
                    handler.ai_assistant = Mock()
                    handler.ai_assistant.client = mock_openai_client
                    return handler
    
    @pytest.mark.asyncio
    async def test_create_appointment_success(self, handler, mock_telegram_update, mock_telegram_context):
        """Test successful appointment creation."""
        # Arrange
        update = mock_telegram_update
        context = mock_telegram_context
        update.message.text = "/new Meeting with John tomorrow at 2pm"
        
        appointment = AppointmentFactory(
            title="Meeting with John",
            date=datetime.now(pytz.UTC) + timedelta(days=1, hours=14)
        )
        
        handler.appointment_service.create_appointment_from_text = AsyncMock(
            return_value=appointment
        )
        
        # Act
        await handler.handle_new_appointment(update, context)
        
        # Assert
        handler.appointment_service.create_appointment_from_text.assert_called_once()
        update.message.reply_html.assert_called_once()
        assert "created successfully" in update.message.reply_html.call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_create_appointment_with_invalid_date(self, handler, mock_telegram_update, mock_telegram_context):
        """Test appointment creation with invalid date format."""
        # Arrange
        update = mock_telegram_update
        context = mock_telegram_context
        update.message.text = "/new Meeting on invalid-date"
        
        handler.appointment_service.create_appointment_from_text = AsyncMock(
            side_effect=ValueError("Invalid date format")
        )
        
        # Act
        await handler.handle_new_appointment(update, context)
        
        # Assert
        update.message.reply_text.assert_called_once()
        assert "Invalid date" in update.message.reply_text.call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_list_appointments_empty(self, handler, mock_telegram_update, mock_telegram_context):
        """Test listing appointments when none exist."""
        # Arrange
        update = mock_telegram_update
        context = mock_telegram_context
        
        handler.appointment_service.get_user_appointments = AsyncMock(
            return_value=[]
        )
        
        # Act
        await handler.handle_list_appointments(update, context)
        
        # Assert
        update.message.reply_text.assert_called_once()
        assert "No appointments found" in update.message.reply_text.call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_list_appointments_with_data(self, handler, mock_telegram_update, mock_telegram_context):
        """Test listing appointments with multiple entries."""
        # Arrange
        update = mock_telegram_update
        context = mock_telegram_context
        
        appointments = [
            AppointmentFactory(title="Meeting 1", date=datetime.now(pytz.UTC) + timedelta(hours=2)),
            AppointmentFactory(title="Meeting 2", date=datetime.now(pytz.UTC) + timedelta(days=1)),
            AppointmentFactory(title="Meeting 3", date=datetime.now(pytz.UTC) + timedelta(days=7))
        ]
        
        handler.appointment_service.get_user_appointments = AsyncMock(
            return_value=appointments
        )
        
        # Act
        await handler.handle_list_appointments(update, context)
        
        # Assert
        update.message.reply_html.assert_called_once()
        response = update.message.reply_html.call_args[0][0]
        assert "Meeting 1" in response
        assert "Meeting 2" in response
        assert "Meeting 3" in response
    
    @pytest.mark.asyncio
    async def test_delete_appointment_success(self, handler, mock_telegram_update, mock_telegram_context):
        """Test successful appointment deletion."""
        # Arrange
        update = mock_telegram_update
        context = mock_telegram_context
        appointment_id = "test_appointment_123"
        
        update.callback_query.data = f"delete_appointment:{appointment_id}"
        
        handler.appointment_service.delete_appointment = AsyncMock(
            return_value=True
        )
        
        # Act
        await handler.handle_delete_appointment_callback(update, context)
        
        # Assert
        handler.appointment_service.delete_appointment.assert_called_once_with(
            appointment_id, update.effective_user.id
        )
        update.callback_query.answer.assert_called_once()
        update.callback_query.edit_message_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_appointment_not_found(self, handler, mock_telegram_update, mock_telegram_context):
        """Test deletion of non-existent appointment."""
        # Arrange
        update = mock_telegram_update
        context = mock_telegram_context
        appointment_id = "non_existent_id"
        
        update.callback_query.data = f"delete_appointment:{appointment_id}"
        
        handler.appointment_service.delete_appointment = AsyncMock(
            return_value=False
        )
        
        # Act
        await handler.handle_delete_appointment_callback(update, context)
        
        # Assert
        update.callback_query.answer.assert_called_once()
        assert "not found" in update.callback_query.answer.call_args[0][0].lower()
    
    @pytest.mark.asyncio
    @freeze_time("2024-01-15 10:00:00")
    async def test_handle_today_appointments(self, handler, mock_telegram_update, mock_telegram_context):
        """Test handling 'today' appointments query."""
        # Arrange
        update = mock_telegram_update
        context = mock_telegram_context
        update.message.text = "/today"
        
        today_appointments = [
            AppointmentFactory(
                title="Morning Meeting",
                date=datetime.now(pytz.UTC).replace(hour=9, minute=0)
            ),
            AppointmentFactory(
                title="Lunch with Client",
                date=datetime.now(pytz.UTC).replace(hour=12, minute=30)
            )
        ]
        
        handler.appointment_service.get_appointments_for_date = AsyncMock(
            return_value=today_appointments
        )
        
        # Act
        await handler.handle_today_appointments(update, context)
        
        # Assert
        handler.appointment_service.get_appointments_for_date.assert_called_once()
        update.message.reply_html.assert_called_once()
        response = update.message.reply_html.call_args[0][0]
        assert "Morning Meeting" in response
        assert "Lunch with Client" in response
    
    @pytest.mark.asyncio
    async def test_handle_tomorrow_appointments(self, handler, mock_telegram_update, mock_telegram_context):
        """Test handling 'tomorrow' appointments query."""
        # Arrange
        update = mock_telegram_update
        context = mock_telegram_context
        update.message.text = "/tomorrow"
        
        tomorrow_appointments = [
            AppointmentFactory(
                title="Team Standup",
                date=datetime.now(pytz.UTC) + timedelta(days=1, hours=10)
            )
        ]
        
        handler.appointment_service.get_appointments_for_date = AsyncMock(
            return_value=tomorrow_appointments
        )
        
        # Act
        await handler.handle_tomorrow_appointments(update, context)
        
        # Assert
        handler.appointment_service.get_appointments_for_date.assert_called_once()
        # Verify it's called with tomorrow's date
        call_args = handler.appointment_service.get_appointments_for_date.call_args[0]
        assert (call_args[1] - datetime.now(pytz.UTC).date()).days == 1
    
    @pytest.mark.asyncio
    async def test_edit_appointment_title(self, handler, mock_telegram_update, mock_telegram_context):
        """Test editing appointment title."""
        # Arrange
        update = mock_telegram_update
        context = mock_telegram_context
        appointment_id = "app_123"
        new_title = "Updated Meeting Title"
        
        update.callback_query.data = f"edit_title:{appointment_id}"
        context.user_data = {"editing_appointment": appointment_id}
        update.message.text = new_title
        
        handler.appointment_service.update_appointment = AsyncMock(
            return_value=AppointmentFactory(title=new_title)
        )
        
        # Act
        await handler.handle_edit_title_response(update, context)
        
        # Assert
        handler.appointment_service.update_appointment.assert_called_once()
        assert handler.appointment_service.update_appointment.call_args[0][1]["title"] == new_title
    
    @pytest.mark.asyncio
    async def test_partner_sync_appointments(self, handler, mock_telegram_update, mock_telegram_context):
        """Test partner appointment synchronization."""
        # Arrange
        update = mock_telegram_update
        context = mock_telegram_context
        partner_id = 987654321
        
        # Setup user config with partner
        user_config = UserConfigFactory(partner_user_id=partner_id)
        handler.user_config = {"users": {str(update.effective_user.id): user_config}}
        
        appointments = [
            AppointmentFactory(is_partner_relevant=True),
            AppointmentFactory(is_partner_relevant=False)
        ]
        
        handler.partner_sync_service.sync_appointments = AsyncMock()
        handler.appointment_service.get_user_appointments = AsyncMock(
            return_value=appointments
        )
        
        # Act
        await handler.handle_sync_partner_appointments(update, context)
        
        # Assert
        handler.partner_sync_service.sync_appointments.assert_called_once()
        # Verify only partner-relevant appointments are synced
        synced_appointments = handler.partner_sync_service.sync_appointments.call_args[0][1]
        assert len(synced_appointments) == 1
        assert synced_appointments[0].is_partner_relevant
    
    @pytest.mark.asyncio
    async def test_handle_appointment_with_ai_extraction(self, handler, mock_telegram_update, mock_telegram_context):
        """Test appointment creation with AI-powered extraction."""
        # Arrange
        update = mock_telegram_update
        context = mock_telegram_context
        update.message.text = "I have a doctor's appointment next Tuesday at 3:30 PM at the medical center"
        
        # Mock AI response
        ai_response = {
            "appointments": [{
                "title": "Doctor's appointment",
                "date": "2024-01-23T15:30:00",
                "location": "Medical center"
            }]
        }
        
        handler.ai_assistant.extract_appointments_from_text = AsyncMock(
            return_value=ai_response
        )
        
        appointment = AppointmentFactory(
            title="Doctor's appointment",
            location="Medical center"
        )
        
        handler.appointment_service.create_appointment_from_ai_data = AsyncMock(
            return_value=appointment
        )
        
        # Act
        await handler.handle_ai_appointment_creation(update, context)
        
        # Assert
        handler.ai_assistant.extract_appointments_from_text.assert_called_once_with(update.message.text)
        handler.appointment_service.create_appointment_from_ai_data.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_recurring_appointment(self, handler, mock_telegram_update, mock_telegram_context):
        """Test creation of recurring appointments."""
        # Arrange
        update = mock_telegram_update
        context = mock_telegram_context
        update.message.text = "/recurring Weekly team meeting every Monday at 10am"
        
        recurring_appointments = [
            AppointmentFactory(title="Weekly team meeting", date=datetime.now(pytz.UTC) + timedelta(days=i*7))
            for i in range(4)
        ]
        
        handler.appointment_service.create_recurring_appointment = AsyncMock(
            return_value=recurring_appointments
        )
        
        # Act
        await handler.handle_recurring_appointment(update, context)
        
        # Assert
        handler.appointment_service.create_recurring_appointment.assert_called_once()
        update.message.reply_html.assert_called_once()
        assert "4 recurring appointments created" in update.message.reply_html.call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_handle_appointment_with_timezone(self, handler, mock_telegram_update, mock_telegram_context):
        """Test appointment creation with timezone consideration."""
        # Arrange
        update = mock_telegram_update
        context = mock_telegram_context
        update.message.text = "/new Conference call at 2pm EST"
        
        # User has Europe/Berlin timezone
        user_config = UserConfigFactory(timezone="Europe/Berlin")
        handler.user_config = {"users": {str(update.effective_user.id): user_config}}
        
        handler.appointment_service.create_appointment_from_text = AsyncMock()
        
        # Act
        await handler.handle_new_appointment(update, context)
        
        # Assert
        handler.appointment_service.create_appointment_from_text.assert_called_once()
        # Verify timezone is passed to service
        call_kwargs = handler.appointment_service.create_appointment_from_text.call_args[1]
        assert call_kwargs.get("user_timezone") == "Europe/Berlin"
    
    @pytest.mark.asyncio
    async def test_handle_appointment_reminder_settings(self, handler, mock_telegram_update, mock_telegram_context):
        """Test appointment creation with custom reminder settings."""
        # Arrange
        update = mock_telegram_update
        context = mock_telegram_context
        appointment_id = "app_456"
        
        update.callback_query.data = f"set_reminder:{appointment_id}:30"
        
        handler.appointment_service.update_reminder_settings = AsyncMock(
            return_value=True
        )
        
        # Act
        await handler.handle_reminder_settings_callback(update, context)
        
        # Assert
        handler.appointment_service.update_reminder_settings.assert_called_once_with(
            appointment_id, 30
        )
        update.callback_query.answer.assert_called_once()
        assert "Reminder set" in update.callback_query.answer.call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_error_handling_network_failure(self, handler, mock_telegram_update, mock_telegram_context):
        """Test error handling for network failures."""
        # Arrange
        update = mock_telegram_update
        context = mock_telegram_context
        update.message.text = "/list"
        
        handler.appointment_service.get_user_appointments = AsyncMock(
            side_effect=ConnectionError("Network error")
        )
        
        # Act
        await handler.handle_list_appointments(update, context)
        
        # Assert
        update.message.reply_text.assert_called_once()
        assert "temporary issue" in update.message.reply_text.call_args[0][0].lower()
    
    @pytest.mark.asyncio
    async def test_handle_appointment_with_attachments(self, handler, mock_telegram_update, mock_telegram_context):
        """Test appointment creation with document attachments."""
        # Arrange
        update = mock_telegram_update
        context = mock_telegram_context
        update.message.text = "/new Project review"
        update.message.document = Mock()
        update.message.document.file_id = "doc_123"
        update.message.document.file_name = "project_specs.pdf"
        
        appointment = AppointmentFactory(title="Project review")
        
        handler.appointment_service.create_appointment_with_attachment = AsyncMock(
            return_value=appointment
        )
        
        # Act
        await handler.handle_new_appointment_with_document(update, context)
        
        # Assert
        handler.appointment_service.create_appointment_with_attachment.assert_called_once()
        assert handler.appointment_service.create_appointment_with_attachment.call_args[1]["file_id"] == "doc_123"