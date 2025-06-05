import pytest
from datetime import datetime, timedelta
import pytz
from pydantic import ValidationError
from src.models.appointment import Appointment


class TestAppointment:
    """Test cases for Appointment model."""
    
    def test_create_valid_appointment(self):
        """Test creating a valid appointment."""
        future_date = datetime.utcnow() + timedelta(hours=1)
        appointment = Appointment(
            title="Test Meeting",
            date=future_date,
            description="Important meeting"
        )
        
        assert appointment.title == "Test Meeting"
        assert appointment.date == future_date
        assert appointment.description == "Important meeting"
        assert appointment.notion_page_id is None
        assert isinstance(appointment.created_at, datetime)
    
    def test_appointment_without_description(self):
        """Test creating appointment without description."""
        future_date = datetime.utcnow() + timedelta(hours=1)
        appointment = Appointment(
            title="Test Meeting",
            date=future_date
        )
        
        assert appointment.title == "Test Meeting"
        assert appointment.description is None
    
    def test_appointment_past_date_fails(self):
        """Test that past date raises validation error."""
        past_date = datetime.utcnow() - timedelta(hours=1)
        
        with pytest.raises(ValidationError) as exc_info:
            Appointment(
                title="Test Meeting",
                date=past_date
            )
        
        assert "must be in the future" in str(exc_info.value)
    
    def test_empty_title_fails(self):
        """Test that empty title raises validation error."""
        future_date = datetime.utcnow() + timedelta(hours=1)
        
        with pytest.raises(ValidationError) as exc_info:
            Appointment(
                title="",
                date=future_date
            )
        
        assert "cannot be empty" in str(exc_info.value)
    
    def test_whitespace_title_fails(self):
        """Test that whitespace-only title raises validation error."""
        future_date = datetime.utcnow() + timedelta(hours=1)
        
        with pytest.raises(ValidationError) as exc_info:
            Appointment(
                title="   ",
                date=future_date
            )
        
        assert "cannot be empty" in str(exc_info.value)
    
    def test_title_strip_whitespace(self):
        """Test that title whitespace is stripped."""
        future_date = datetime.utcnow() + timedelta(hours=1)
        appointment = Appointment(
            title="  Test Meeting  ",
            date=future_date
        )
        
        assert appointment.title == "Test Meeting"
    
    def test_to_notion_properties(self):
        """Test conversion to Notion properties."""
        tz = pytz.timezone("Europe/Berlin")
        future_date = tz.localize(datetime(2024, 12, 25, 14, 30))
        
        appointment = Appointment(
            title="Christmas Meeting",
            date=future_date,
            description="Holiday planning"
        )
        
        properties = appointment.to_notion_properties("Europe/Berlin")
        
        assert properties["Title"]["title"][0]["text"]["content"] == "Christmas Meeting"
        assert "2024-12-25T14:30:00" in properties["Date"]["date"]["start"]
        assert properties["Description"]["rich_text"][0]["text"]["content"] == "Holiday planning"
        assert "Created" in properties
    
    def test_to_notion_properties_without_description(self):
        """Test conversion to Notion properties without description."""
        tz = pytz.timezone("Europe/Berlin")
        future_date = tz.localize(datetime(2024, 12, 25, 14, 30))
        
        appointment = Appointment(
            title="Christmas Meeting",
            date=future_date
        )
        
        properties = appointment.to_notion_properties("Europe/Berlin")
        
        assert "Description" not in properties
        assert "Title" in properties
        assert "Date" in properties
        assert "Created" in properties
    
    def test_from_notion_page(self):
        """Test creating appointment from Notion page data."""
        notion_page = {
            "id": "test-page-id",
            "properties": {
                "Title": {
                    "title": [
                        {
                            "text": {
                                "content": "Test Meeting"
                            }
                        }
                    ]
                },
                "Date": {
                    "date": {
                        "start": "2024-12-25T14:30:00+01:00"
                    }
                },
                "Description": {
                    "rich_text": [
                        {
                            "text": {
                                "content": "Important meeting"
                            }
                        }
                    ]
                },
                "Created": {
                    "date": {
                        "start": "2024-12-20T10:00:00+01:00"
                    }
                }
            }
        }
        
        appointment = Appointment.from_notion_page(notion_page)
        
        assert appointment.title == "Test Meeting"
        assert appointment.description == "Important meeting"
        assert appointment.notion_page_id == "test-page-id"
        assert appointment.date.year == 2024
        assert appointment.date.month == 12
        assert appointment.date.day == 25
    
    def test_format_for_telegram(self):
        """Test formatting appointment for Telegram."""
        tz = pytz.timezone("Europe/Berlin")
        future_date = tz.localize(datetime(2024, 12, 25, 14, 30))
        
        appointment = Appointment(
            title="Christmas Meeting",
            date=future_date,
            description="Holiday planning"
        )
        
        formatted = appointment.format_for_telegram("Europe/Berlin")
        
        assert "📅 *Christmas Meeting*" in formatted
        assert "🕐 25.12.2024 um 14:30" in formatted
        assert "📝 Holiday planning" in formatted
    
    def test_format_for_telegram_without_description(self):
        """Test formatting appointment without description for Telegram."""
        tz = pytz.timezone("Europe/Berlin")
        future_date = tz.localize(datetime(2024, 12, 25, 14, 30))
        
        appointment = Appointment(
            title="Christmas Meeting",
            date=future_date
        )
        
        formatted = appointment.format_for_telegram("Europe/Berlin")
        
        assert "📅 *Christmas Meeting*" in formatted
        assert "🕐 25.12.2024 um 14:30" in formatted
        assert "📝" not in formatted