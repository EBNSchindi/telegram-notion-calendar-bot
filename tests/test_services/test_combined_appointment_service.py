"""
Comprehensive unit tests for CombinedAppointmentService with edge cases.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta, date
import pytz
from freezegun import freeze_time
import json

from src.services.combined_appointment_service import CombinedAppointmentService
from src.models.appointment import Appointment
from tests.factories import AppointmentFactory, NotionPageFactory, UserConfigFactory


@pytest.mark.unit
class TestCombinedAppointmentService:
    """Test suite for CombinedAppointmentService."""
    
    @pytest.fixture
    def service(self, mock_notion_client, mock_openai_client):
        """Create service instance with mocked dependencies."""
        with patch('src.services.combined_appointment_service.NotionService') as mock_notion:
            with patch('src.services.combined_appointment_service.AIAssistantService') as mock_ai:
                service = CombinedAppointmentService()
                service.notion_service = Mock()
                service.notion_service.client = mock_notion_client
                service.ai_assistant = Mock()
                service.ai_assistant.client = mock_openai_client
                service.time_parser = Mock()
                return service
    
    @pytest.mark.asyncio
    async def test_create_appointment_from_text_simple(self, service):
        """Test creating appointment from simple text."""
        # Arrange
        user_id = 123456
        text = "Meeting with team at 3pm"
        
        parsed_data = {
            "title": "Meeting with team",
            "date": datetime.now(pytz.UTC).replace(hour=15, minute=0),
            "location": None,
            "description": None
        }
        
        service.time_parser.parse_appointment_text = Mock(return_value=parsed_data)
        service.notion_service.create_appointment = AsyncMock(
            return_value={"id": "app_123", **parsed_data}
        )
        
        # Act
        result = await service.create_appointment_from_text(user_id, text)
        
        # Assert
        assert isinstance(result, Appointment)
        assert result.title == "Meeting with team"
        assert result.date.hour == 15
        service.notion_service.create_appointment.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_appointment_with_all_fields(self, service):
        """Test creating appointment with all fields populated."""
        # Arrange
        user_id = 123456
        text = "Doctor appointment tomorrow at 10:30am at City Hospital, bring medical records"
        
        tomorrow = datetime.now(pytz.UTC) + timedelta(days=1)
        parsed_data = {
            "title": "Doctor appointment",
            "date": tomorrow.replace(hour=10, minute=30),
            "location": "City Hospital",
            "description": "bring medical records",
            "participants": []
        }
        
        service.time_parser.parse_appointment_text = Mock(return_value=parsed_data)
        service.notion_service.create_appointment = AsyncMock(
            return_value={"id": "app_124", **parsed_data}
        )
        
        # Act
        result = await service.create_appointment_from_text(user_id, text)
        
        # Assert
        assert result.title == "Doctor appointment"
        assert result.location == "City Hospital"
        assert result.description == "bring medical records"
        assert result.date.hour == 10
        assert result.date.minute == 30
    
    @pytest.mark.asyncio
    async def test_create_appointment_with_timezone_conversion(self, service):
        """Test appointment creation with timezone conversion."""
        # Arrange
        user_id = 123456
        text = "Call with New York office at 2pm EST"
        user_timezone = "Europe/Berlin"
        
        # 2pm EST = 8pm Berlin time
        est_time = datetime.now(pytz.timezone('US/Eastern')).replace(hour=14, minute=0)
        utc_time = est_time.astimezone(pytz.UTC)
        
        parsed_data = {
            "title": "Call with New York office",
            "date": utc_time,
            "timezone_info": "EST"
        }
        
        service.time_parser.parse_appointment_text = Mock(return_value=parsed_data)
        service.notion_service.create_appointment = AsyncMock(
            return_value={"id": "app_125", **parsed_data}
        )
        
        # Act
        result = await service.create_appointment_from_text(
            user_id, text, user_timezone=user_timezone
        )
        
        # Assert
        assert result.date.tzinfo == pytz.UTC
        service.time_parser.parse_appointment_text.assert_called_once_with(
            text, default_timezone=user_timezone
        )
    
    @pytest.mark.asyncio
    async def test_get_user_appointments_with_filtering(self, service):
        """Test getting user appointments with date filtering."""
        # Arrange
        user_id = 123456
        start_date = datetime.now(pytz.UTC)
        end_date = start_date + timedelta(days=7)
        
        notion_pages = [
            NotionPageFactory(),
            NotionPageFactory(),
            NotionPageFactory()
        ]
        
        service.notion_service.query_appointments = AsyncMock(
            return_value=notion_pages
        )
        
        # Act
        result = await service.get_user_appointments(
            user_id, start_date=start_date, end_date=end_date
        )
        
        # Assert
        assert len(result) == 3
        service.notion_service.query_appointments.assert_called_once()
        call_args = service.notion_service.query_appointments.call_args[1]
        assert call_args["start_date"] == start_date
        assert call_args["end_date"] == end_date
    
    @pytest.mark.asyncio
    async def test_get_appointments_for_date(self, service):
        """Test getting appointments for a specific date."""
        # Arrange
        user_id = 123456
        target_date = date(2024, 1, 15)
        
        # Create appointments for different times on the target date
        notion_pages = [
            {
                "id": "app_1",
                "properties": {
                    "Title": {"title": [{"text": {"content": "Morning meeting"}}]},
                    "Date": {"date": {"start": "2024-01-15T09:00:00Z"}}
                }
            },
            {
                "id": "app_2",
                "properties": {
                    "Title": {"title": [{"text": {"content": "Lunch appointment"}}]},
                    "Date": {"date": {"start": "2024-01-15T12:30:00Z"}}
                }
            }
        ]
        
        service.notion_service.query_appointments = AsyncMock(
            return_value=notion_pages
        )
        
        # Act
        result = await service.get_appointments_for_date(user_id, target_date)
        
        # Assert
        assert len(result) == 2
        assert result[0].title == "Morning meeting"
        assert result[1].title == "Lunch appointment"
        
        # Verify the service was called with correct date range
        call_args = service.notion_service.query_appointments.call_args[1]
        assert call_args["start_date"].date() == target_date
        assert call_args["end_date"].date() == target_date
    
    @pytest.mark.asyncio
    async def test_update_appointment_partial_update(self, service):
        """Test partial update of appointment fields."""
        # Arrange
        appointment_id = "app_123"
        updates = {
            "title": "Updated Title",
            "location": "New Location"
        }
        
        updated_notion_page = NotionPageFactory()
        service.notion_service.update_appointment = AsyncMock(
            return_value=updated_notion_page
        )
        
        # Act
        result = await service.update_appointment(appointment_id, updates)
        
        # Assert
        assert isinstance(result, Appointment)
        service.notion_service.update_appointment.assert_called_once_with(
            appointment_id, updates
        )
    
    @pytest.mark.asyncio
    async def test_delete_appointment_success(self, service):
        """Test successful appointment deletion."""
        # Arrange
        appointment_id = "app_123"
        user_id = 123456
        
        service.notion_service.delete_appointment = AsyncMock(return_value=True)
        
        # Act
        result = await service.delete_appointment(appointment_id, user_id)
        
        # Assert
        assert result is True
        service.notion_service.delete_appointment.assert_called_once_with(
            appointment_id
        )
    
    @pytest.mark.asyncio
    async def test_create_recurring_appointment(self, service):
        """Test creating recurring appointments."""
        # Arrange
        user_id = 123456
        base_appointment = AppointmentFactory(
            title="Weekly Team Meeting",
            date=datetime.now(pytz.UTC).replace(hour=10, minute=0)
        )
        recurrence_pattern = {
            "frequency": "weekly",
            "interval": 1,
            "count": 4,
            "days_of_week": ["monday"]
        }
        
        created_appointments = []
        for i in range(4):
            app_data = {
                "id": f"app_{i}",
                "title": base_appointment.title,
                "date": base_appointment.date + timedelta(weeks=i)
            }
            created_appointments.append(app_data)
        
        service.notion_service.create_appointment = AsyncMock(
            side_effect=created_appointments
        )
        
        # Act
        result = await service.create_recurring_appointment(
            user_id, base_appointment, recurrence_pattern
        )
        
        # Assert
        assert len(result) == 4
        assert service.notion_service.create_appointment.call_count == 4
        
        # Verify appointments are created with correct dates
        for i, appointment in enumerate(result):
            expected_date = base_appointment.date + timedelta(weeks=i)
            assert appointment.date.date() == expected_date.date()
    
    @pytest.mark.asyncio
    async def test_search_appointments_by_keyword(self, service):
        """Test searching appointments by keyword."""
        # Arrange
        user_id = 123456
        keyword = "doctor"
        
        matching_pages = [
            {
                "id": "app_1",
                "properties": {
                    "Title": {"title": [{"text": {"content": "Doctor appointment"}}]},
                    "Date": {"date": {"start": "2024-01-20T10:00:00Z"}}
                }
            },
            {
                "id": "app_2",
                "properties": {
                    "Title": {"title": [{"text": {"content": "Follow-up with doctor"}}]},
                    "Date": {"date": {"start": "2024-01-25T14:00:00Z"}}
                }
            }
        ]
        
        service.notion_service.search_appointments = AsyncMock(
            return_value=matching_pages
        )
        
        # Act
        result = await service.search_appointments(user_id, keyword)
        
        # Assert
        assert len(result) == 2
        assert all(keyword.lower() in app.title.lower() for app in result)
        service.notion_service.search_appointments.assert_called_once_with(
            user_id, keyword
        )
    
    @pytest.mark.asyncio
    async def test_get_appointment_conflicts(self, service):
        """Test detecting appointment conflicts."""
        # Arrange
        user_id = 123456
        new_appointment_time = datetime.now(pytz.UTC).replace(hour=14, minute=0)
        duration_minutes = 60
        
        existing_appointments = [
            AppointmentFactory(
                title="Existing meeting",
                date=new_appointment_time.replace(minute=30)  # Overlaps
            ),
            AppointmentFactory(
                title="Later meeting",
                date=new_appointment_time + timedelta(hours=2)  # No overlap
            )
        ]
        
        service.get_user_appointments = AsyncMock(
            return_value=existing_appointments
        )
        
        # Act
        conflicts = await service.check_conflicts(
            user_id, new_appointment_time, duration_minutes
        )
        
        # Assert
        assert len(conflicts) == 1
        assert conflicts[0].title == "Existing meeting"
    
    @pytest.mark.asyncio
    async def test_create_appointment_from_ai_data(self, service):
        """Test creating appointment from AI-extracted data."""
        # Arrange
        user_id = 123456
        ai_data = {
            "title": "Project deadline",
            "date": "2024-02-01T17:00:00",
            "location": "Office",
            "description": "Final submission for Q1 project",
            "participants": ["John", "Sarah"],
            "is_partner_relevant": True
        }
        
        service.notion_service.create_appointment = AsyncMock(
            return_value={"id": "app_ai_1", **ai_data}
        )
        
        # Act
        result = await service.create_appointment_from_ai_data(user_id, ai_data)
        
        # Assert
        assert result.title == "Project deadline"
        assert result.is_partner_relevant is True
        assert len(result.participants) == 2
        service.notion_service.create_appointment.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_reminder_settings(self, service):
        """Test updating appointment reminder settings."""
        # Arrange
        appointment_id = "app_123"
        reminder_minutes = 30
        
        service.notion_service.update_appointment = AsyncMock(
            return_value=NotionPageFactory()
        )
        
        # Act
        result = await service.update_reminder_settings(
            appointment_id, reminder_minutes
        )
        
        # Assert
        assert result is True
        service.notion_service.update_appointment.assert_called_once()
        call_args = service.notion_service.update_appointment.call_args[0]
        assert call_args[1]["reminder_minutes"] == reminder_minutes
    
    @pytest.mark.asyncio
    async def test_handle_appointment_with_attachment(self, service):
        """Test creating appointment with file attachment."""
        # Arrange
        user_id = 123456
        appointment_data = {
            "title": "Contract Review",
            "date": datetime.now(pytz.UTC) + timedelta(days=2)
        }
        file_data = {
            "file_id": "file_123",
            "file_name": "contract.pdf",
            "file_size": 1024000
        }
        
        service.notion_service.create_appointment_with_attachment = AsyncMock(
            return_value={"id": "app_attach_1", **appointment_data}
        )
        
        # Act
        result = await service.create_appointment_with_attachment(
            user_id, appointment_data, file_data
        )
        
        # Assert
        assert result.title == "Contract Review"
        service.notion_service.create_appointment_with_attachment.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_bulk_operations(self, service):
        """Test bulk appointment operations."""
        # Arrange
        user_id = 123456
        appointment_ids = ["app_1", "app_2", "app_3"]
        operation = "archive"
        
        service.notion_service.bulk_update_appointments = AsyncMock(
            return_value=True
        )
        
        # Act
        result = await service.bulk_operation(user_id, appointment_ids, operation)
        
        # Assert
        assert result is True
        service.notion_service.bulk_update_appointments.assert_called_once_with(
            appointment_ids, {"archived": True}
        )
    
    @pytest.mark.asyncio
    async def test_error_handling_notion_api_error(self, service):
        """Test handling of Notion API errors."""
        # Arrange
        user_id = 123456
        text = "Meeting tomorrow"
        
        service.time_parser.parse_appointment_text = Mock()
        service.notion_service.create_appointment = AsyncMock(
            side_effect=Exception("Notion API Error: Rate limited")
        )
        
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await service.create_appointment_from_text(user_id, text)
        
        assert "Notion API Error" in str(exc_info.value)
    
    @pytest.mark.asyncio
    @freeze_time("2024-01-15 10:00:00")
    async def test_get_upcoming_appointments(self, service):
        """Test getting upcoming appointments within next 24 hours."""
        # Arrange
        user_id = 123456
        
        # Create appointments at different times
        appointments = [
            AppointmentFactory(date=datetime.now(pytz.UTC) + timedelta(hours=2)),  # In 2 hours
            AppointmentFactory(date=datetime.now(pytz.UTC) + timedelta(hours=12)), # In 12 hours
            AppointmentFactory(date=datetime.now(pytz.UTC) + timedelta(days=2)),   # In 2 days
        ]
        
        service.get_user_appointments = AsyncMock(return_value=appointments[:2])
        
        # Act
        result = await service.get_upcoming_appointments(user_id, hours=24)
        
        # Assert
        assert len(result) == 2
        assert all((app.date - datetime.now(pytz.UTC)).total_seconds() <= 86400 for app in result)