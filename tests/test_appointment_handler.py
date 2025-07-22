import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
import pytz
from src.handlers.enhanced_appointment_handler import EnhancedAppointmentHandler as AppointmentHandler
from src.models.appointment import Appointment


class TestAppointmentHandler:
    """Test cases for AppointmentHandler."""
    
    @pytest.fixture
    def appointment_handler(self, settings):
        """Create AppointmentHandler instance with mocked NotionService."""
        handler = AppointmentHandler(settings)
        handler.notion_service = AsyncMock()
        return handler
    
    @pytest.mark.asyncio
    async def test_add_appointment_success(self, appointment_handler, mock_telegram_update, mock_telegram_context):
        """Test successful appointment addition."""
        # Setup
        mock_telegram_context.args = ["morgen", "14:00", "Meeting", "Team", "besprechung"]
        appointment_handler.notion_service.create_appointment.return_value = "test-page-id"
        
        # Execute
        await appointment_handler.add_appointment(mock_telegram_update, mock_telegram_context)
        
        # Assert
        mock_telegram_update.message.reply_text.assert_called_once()
        call_args = mock_telegram_update.message.reply_text.call_args
        assert "✅ Termin erfolgreich erstellt!" in call_args[0][0]
        
        appointment_handler.notion_service.create_appointment.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_add_appointment_no_args(self, appointment_handler, mock_telegram_update, mock_telegram_context):
        """Test appointment addition with no arguments."""
        # Setup
        mock_telegram_context.args = []
        
        # Execute
        await appointment_handler.add_appointment(mock_telegram_update, mock_telegram_context)
        
        # Assert
        mock_telegram_update.message.reply_text.assert_called_once()
        call_args = mock_telegram_update.message.reply_text.call_args
        assert "❌ Bitte gib einen Termin an" in call_args[0][0]
        
        appointment_handler.notion_service.create_appointment.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_add_appointment_insufficient_args(self, appointment_handler, mock_telegram_update, mock_telegram_context):
        """Test appointment addition with insufficient arguments."""
        # Setup
        mock_telegram_context.args = ["morgen", "14:00"]  # Missing title
        
        # Execute
        await appointment_handler.add_appointment(mock_telegram_update, mock_telegram_context)
        
        # Assert
        mock_telegram_update.message.reply_text.assert_called_once()
        call_args = mock_telegram_update.message.reply_text.call_args
        assert "❌ Fehler:" in call_args[0][0]
        
        appointment_handler.notion_service.create_appointment.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_add_appointment_invalid_date(self, appointment_handler, mock_telegram_update, mock_telegram_context):
        """Test appointment addition with invalid date."""
        # Setup
        mock_telegram_context.args = ["invalid-date", "14:00", "Meeting"]
        
        # Execute
        await appointment_handler.add_appointment(mock_telegram_update, mock_telegram_context)
        
        # Assert
        mock_telegram_update.message.reply_text.assert_called_once()
        call_args = mock_telegram_update.message.reply_text.call_args
        assert "❌ Fehler:" in call_args[0][0]
        
        appointment_handler.notion_service.create_appointment.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_add_appointment_invalid_time(self, appointment_handler, mock_telegram_update, mock_telegram_context):
        """Test appointment addition with invalid time."""
        # Setup
        mock_telegram_context.args = ["morgen", "25:70", "Meeting"]
        
        # Execute
        await appointment_handler.add_appointment(mock_telegram_update, mock_telegram_context)
        
        # Assert
        mock_telegram_update.message.reply_text.assert_called_once()
        call_args = mock_telegram_update.message.reply_text.call_args
        assert "❌ Fehler:" in call_args[0][0]
        
        appointment_handler.notion_service.create_appointment.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_list_appointments_success(self, appointment_handler, mock_telegram_update, mock_telegram_context):
        """Test successful appointments listing."""
        # Setup
        future_date = datetime.now(pytz.timezone("Europe/Berlin")) + timedelta(hours=1)
        appointments = [
            Appointment(title="Meeting 1", date=future_date),
            Appointment(title="Meeting 2", date=future_date + timedelta(hours=1))
        ]
        appointment_handler.notion_service.get_appointments.return_value = appointments
        
        # Execute
        await appointment_handler.list_appointments(mock_telegram_update, mock_telegram_context)
        
        # Assert
        mock_telegram_update.message.reply_text.assert_called_once()
        call_args = mock_telegram_update.message.reply_text.call_args
        assert "📋 *Kommende Termine:*" in call_args[0][0]
        assert "Meeting 1" in call_args[0][0]
        assert "Meeting 2" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_list_appointments_empty(self, appointment_handler, mock_telegram_update, mock_telegram_context):
        """Test appointments listing with no appointments."""
        # Setup
        appointment_handler.notion_service.get_appointments.return_value = []
        
        # Execute
        await appointment_handler.list_appointments(mock_telegram_update, mock_telegram_context)
        
        # Assert
        mock_telegram_update.message.reply_text.assert_called_once()
        call_args = mock_telegram_update.message.reply_text.call_args
        assert "📅 Keine kommenden Termine vorhanden." in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_list_appointments_only_past(self, appointment_handler, mock_telegram_update, mock_telegram_context):
        """Test appointments listing with only past appointments."""
        # Setup
        past_date = datetime.now(pytz.timezone("Europe/Berlin")) - timedelta(hours=1)
        appointments = [
            Appointment(title="Past Meeting", date=past_date)
        ]
        appointment_handler.notion_service.get_appointments.return_value = appointments
        
        # Execute
        await appointment_handler.list_appointments(mock_telegram_update, mock_telegram_context)
        
        # Assert
        mock_telegram_update.message.reply_text.assert_called_once()
        call_args = mock_telegram_update.message.reply_text.call_args
        assert "📅 Keine kommenden Termine vorhanden." in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_today_appointments_success(self, appointment_handler, mock_telegram_update, mock_telegram_context):
        """Test successful today's appointments listing."""
        # Setup
        today = datetime.now(pytz.timezone("Europe/Berlin"))
        appointments = [
            Appointment(title="Today Meeting", date=today + timedelta(hours=1))
        ]
        appointment_handler.notion_service.get_appointments.return_value = appointments
        
        # Execute
        await appointment_handler.today_appointments(mock_telegram_update, mock_telegram_context)
        
        # Assert
        mock_telegram_update.message.reply_text.assert_called_once()
        call_args = mock_telegram_update.message.reply_text.call_args
        assert f"*Termine für heute ({today.strftime('%d.%m.%Y')}):*" in call_args[0][0]
        assert "Today Meeting" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_today_appointments_none(self, appointment_handler, mock_telegram_update, mock_telegram_context):
        """Test today's appointments with no appointments."""
        # Setup
        appointment_handler.notion_service.get_appointments.return_value = []
        
        # Execute
        await appointment_handler.today_appointments(mock_telegram_update, mock_telegram_context)
        
        # Assert
        mock_telegram_update.message.reply_text.assert_called_once()
        call_args = mock_telegram_update.message.reply_text.call_args
        assert "📅 Keine Termine für heute" in call_args[0][0]
    
    def test_parse_date_time_today(self, appointment_handler):
        """Test parsing 'today' date."""
        result = appointment_handler._parse_date_time("heute", "14:00")
        
        expected_date = datetime.now(appointment_handler.timezone).date()
        assert result.date() == expected_date
        assert result.hour == 14
        assert result.minute == 0
    
    def test_parse_date_time_tomorrow(self, appointment_handler):
        """Test parsing 'tomorrow' date."""
        result = appointment_handler._parse_date_time("morgen", "15:30")
        
        expected_date = (datetime.now(appointment_handler.timezone) + timedelta(days=1)).date()
        assert result.date() == expected_date
        assert result.hour == 15
        assert result.minute == 30
    
    def test_parse_date_time_absolute_date(self, appointment_handler):
        """Test parsing absolute date."""
        result = appointment_handler._parse_date_time("25.12.2024", "18:00")
        
        assert result.year == 2024
        assert result.month == 12
        assert result.day == 25
        assert result.hour == 18
        assert result.minute == 0
    
    def test_parse_date_time_past_date_fails(self, appointment_handler):
        """Test that past dates raise error."""
        yesterday = datetime.now() - timedelta(days=1)
        date_str = yesterday.strftime("%d.%m.%Y")
        
        with pytest.raises(ValueError) as exc_info:
            appointment_handler._parse_date_time(date_str, "14:00")
        
        assert "muss in der Zukunft liegen" in str(exc_info.value)
    
    def test_parse_date_time_invalid_time_format(self, appointment_handler):
        """Test that invalid time format raises error."""
        with pytest.raises(ValueError) as exc_info:
            appointment_handler._parse_date_time("morgen", "25:70")
        
        assert "Ungültiges Zeitformat" in str(exc_info.value)
    
    def test_parse_add_command_basic(self, appointment_handler):
        """Test parsing basic add command."""
        args = ["morgen", "14:00", "Meeting"]
        
        date_time, title, description = appointment_handler._parse_add_command(args)
        
        assert title == "Meeting"
        assert description is None
        assert date_time.hour == 14
    
    def test_parse_add_command_with_description(self, appointment_handler):
        """Test parsing add command with description."""
        args = ["morgen", "14:00", "Meeting", "Important", "team", "discussion"]
        
        date_time, title, description = appointment_handler._parse_add_command(args)
        
        assert title == "Meeting"
        assert description == "Important team discussion"
    
    def test_parse_add_command_insufficient_args(self, appointment_handler):
        """Test parsing add command with insufficient arguments."""
        args = ["morgen", "14:00"]  # Missing title
        
        with pytest.raises(ValueError) as exc_info:
            appointment_handler._parse_add_command(args)
        
        assert "Mindestens Datum, Zeit und Titel sind erforderlich" in str(exc_info.value)