import pytest
from datetime import datetime, timedelta, timezone
import pytz
from pydantic import ValidationError
from src.models.appointment import Appointment


class TestAppointment:
    """Test cases for Appointment model."""
    
    def test_create_valid_appointment_with_start_end_date(self):
        """Test creating a valid appointment with start_date and end_date."""
        start_date = datetime.now(timezone.utc) + timedelta(hours=1)
        end_date = start_date + timedelta(hours=2)
        appointment = Appointment(
            title="Test Meeting",
            start_date=start_date,
            end_date=end_date,
            description="Important meeting"
        )
        
        assert appointment.title == "Test Meeting"
        assert appointment.start_date == start_date
        assert appointment.end_date == end_date
        assert appointment.date == start_date  # Should be set for backward compatibility
        assert appointment.description == "Important meeting"
        assert appointment.notion_page_id is None
        assert isinstance(appointment.created_at, datetime)
    
    def test_backward_compatibility_date_only(self):
        """Test backward compatibility when only 'date' field is provided."""
        future_date = datetime.now(timezone.utc) + timedelta(hours=1)
        appointment = Appointment(
            title="Test Meeting",
            date=future_date,
            description="Important meeting"
        )
        
        assert appointment.title == "Test Meeting"
        assert appointment.date == future_date
        assert appointment.start_date == future_date
        assert appointment.end_date == future_date + timedelta(minutes=60)  # Default 60 minutes
        assert appointment.description == "Important meeting"
    
    def test_backward_compatibility_with_duration(self):
        """Test backward compatibility with duration_minutes."""
        future_date = datetime.now(timezone.utc) + timedelta(hours=1)
        appointment = Appointment(
            title="Long Meeting",
            date=future_date,
            duration_minutes=120
        )
        
        assert appointment.start_date == future_date
        assert appointment.end_date == future_date + timedelta(minutes=120)
        assert appointment.duration_minutes == 120
    
    def test_migration_logic_start_date_without_end_date(self):
        """Test migration logic when start_date is provided without end_date."""
        start_date = datetime.now(timezone.utc) + timedelta(hours=1)
        appointment = Appointment(
            title="Test Meeting",
            start_date=start_date,
            duration_minutes=90
        )
        
        assert appointment.start_date == start_date
        assert appointment.end_date == start_date + timedelta(minutes=90)
        # Note: date is not automatically set when only start_date is provided
        # This is the actual behavior in the __init__ method
    
    def test_date_validation_end_before_start_fails(self):
        """Test that end_date must be after start_date."""
        start_date = datetime.now(timezone.utc) + timedelta(hours=2)
        end_date = start_date - timedelta(hours=1)  # End before start
        
        with pytest.raises(ValidationError) as exc_info:
            Appointment(
                title="Invalid Meeting",
                start_date=start_date,
                end_date=end_date
            )
        
        assert "End date must be after start date" in str(exc_info.value)
    
    def test_date_validation_end_equals_start_fails(self):
        """Test that end_date cannot equal start_date."""
        start_date = datetime.now(timezone.utc) + timedelta(hours=1)
        
        with pytest.raises(ValidationError) as exc_info:
            Appointment(
                title="Zero Duration Meeting",
                start_date=start_date,
                end_date=start_date  # Same as start
            )
        
        assert "End date must be after start date" in str(exc_info.value)
    
    def test_appointment_without_description(self):
        """Test creating appointment without description."""
        start_date = datetime.now(timezone.utc) + timedelta(hours=1)
        end_date = start_date + timedelta(hours=1)
        appointment = Appointment(
            title="Test Meeting",
            start_date=start_date,
            end_date=end_date
        )
        
        assert appointment.title == "Test Meeting"
        assert appointment.description is None
    
    def test_empty_title_fails(self):
        """Test that empty title raises validation error."""
        start_date = datetime.now(timezone.utc) + timedelta(hours=1)
        end_date = start_date + timedelta(hours=1)
        
        with pytest.raises(ValidationError) as exc_info:
            Appointment(
                title="",
                start_date=start_date,
                end_date=end_date
            )
        
        # Pydantic 2.5.3 uses "String should have at least 1 character"
        assert "String should have at least 1 character" in str(exc_info.value)
    
    def test_whitespace_title_fails(self):
        """Test that whitespace-only title raises validation error."""
        start_date = datetime.now(timezone.utc) + timedelta(hours=1)
        end_date = start_date + timedelta(hours=1)
        
        with pytest.raises(ValidationError) as exc_info:
            Appointment(
                title="   ",
                start_date=start_date,
                end_date=end_date
            )
        
        assert "cannot be empty" in str(exc_info.value)
    
    def test_title_strip_whitespace(self):
        """Test that title whitespace is stripped."""
        start_date = datetime.now(timezone.utc) + timedelta(hours=1)
        end_date = start_date + timedelta(hours=1)
        appointment = Appointment(
            title="  Test Meeting  ",
            start_date=start_date,
            end_date=end_date
        )
        
        assert appointment.title == "Test Meeting"
    
    def test_to_notion_properties(self):
        """Test conversion to Notion properties with new date fields."""
        tz = pytz.timezone("Europe/Berlin")
        start_date = tz.localize(datetime(2024, 12, 25, 14, 30))
        end_date = tz.localize(datetime(2024, 12, 25, 16, 30))
        
        appointment = Appointment(
            title="Christmas Meeting",
            start_date=start_date,
            end_date=end_date,
            description="Holiday planning"
        )
        
        properties = appointment.to_notion_properties("Europe/Berlin")
        
        assert properties["Name"]["title"][0]["text"]["content"] == "Christmas Meeting"
        assert "2024-12-25T14:30:00" in properties["Startdatum"]["date"]["start"]
        assert "2024-12-25T16:30:00" in properties["Endedatum"]["date"]["start"]
        assert properties["Beschreibung"]["rich_text"][0]["text"]["content"] == "Holiday planning"
        assert "Datum" not in properties  # Old field should not be present
    
    def test_to_notion_properties_without_description(self):
        """Test conversion to Notion properties without description."""
        tz = pytz.timezone("Europe/Berlin")
        start_date = tz.localize(datetime(2024, 12, 25, 14, 30))
        end_date = tz.localize(datetime(2024, 12, 25, 15, 30))
        
        appointment = Appointment(
            title="Christmas Meeting",
            start_date=start_date,
            end_date=end_date
        )
        
        properties = appointment.to_notion_properties("Europe/Berlin")
        
        assert "Beschreibung" not in properties
        assert "Name" in properties
        assert "Startdatum" in properties
        assert "Endedatum" in properties
    
    def test_from_notion_page(self):
        """Test creating appointment from Notion page data with new fields."""
        notion_page = {
            "id": "test-page-id",
            "created_time": "2024-12-20T10:00:00+01:00",
            "properties": {
                "Name": {
                    "title": [
                        {
                            "text": {
                                "content": "Test Meeting"
                            }
                        }
                    ]
                },
                "Startdatum": {
                    "date": {
                        "start": "2024-12-25T14:30:00+01:00"
                    }
                },
                "Endedatum": {
                    "date": {
                        "start": "2024-12-25T16:30:00+01:00"
                    }
                },
                "Beschreibung": {
                    "rich_text": [
                        {
                            "text": {
                                "content": "Important meeting"
                            }
                        }
                    ]
                }
            }
        }
        
        appointment = Appointment.from_notion_page(notion_page)
        
        assert appointment.title == "Test Meeting"
        assert appointment.description == "Important meeting"
        assert appointment.notion_page_id == "test-page-id"
        assert appointment.start_date.year == 2024
        assert appointment.start_date.month == 12
        assert appointment.start_date.day == 25
        # The hour will be as provided in the ISO string with timezone offset
        # 14:30+01:00 is actually 14:30 in UTC+1 timezone, not converted to UTC
        assert appointment.start_date.hour == 14  # Original hour preserved
        assert appointment.end_date.hour == 16  # Original hour preserved
        assert appointment.duration_minutes == 120  # Calculated from dates
    
    def test_from_notion_page_backward_compatibility(self):
        """Test creating appointment from old Notion page data format."""
        notion_page = {
            "id": "test-page-id",
            "created_time": "2024-12-20T10:00:00+01:00",
            "properties": {
                "Title": {  # Old field name
                    "title": [
                        {
                            "text": {
                                "content": "Legacy Meeting"
                            }
                        }
                    ]
                },
                "Datum": {  # Old date field
                    "date": {
                        "start": "2024-12-25T14:30:00+01:00"
                    }
                },
                "Duration": {
                    "number": 90
                }
            }
        }
        
        appointment = Appointment.from_notion_page(notion_page)
        
        assert appointment.title == "Legacy Meeting"
        assert appointment.start_date.year == 2024
        assert appointment.start_date.month == 12
        assert appointment.start_date.day == 25
        # Should calculate end_date from duration
        assert appointment.end_date == appointment.start_date + timedelta(minutes=90)
        assert appointment.duration_minutes == 90
    
    def test_format_for_telegram(self):
        """Test formatting appointment for Telegram with time range."""
        tz = pytz.timezone("Europe/Berlin")
        start_date = tz.localize(datetime(2024, 12, 25, 14, 30))
        end_date = tz.localize(datetime(2024, 12, 25, 16, 30))
        
        appointment = Appointment(
            title="Christmas Meeting",
            start_date=start_date,
            end_date=end_date,
            description="Holiday planning"
        )
        
        formatted = appointment.format_for_telegram("Europe/Berlin")
        
        assert "📅 *Christmas Meeting*" in formatted
        assert "🕐 25.12.2024 von 14:30 bis 16:30" in formatted  # Same day format
        assert "📝 Holiday planning" in formatted
    
    def test_format_for_telegram_multi_day(self):
        """Test formatting multi-day appointment for Telegram."""
        tz = pytz.timezone("Europe/Berlin")
        start_date = tz.localize(datetime(2024, 12, 25, 14, 30))
        end_date = tz.localize(datetime(2024, 12, 26, 16, 30))  # Next day
        
        appointment = Appointment(
            title="Christmas Conference",
            start_date=start_date,
            end_date=end_date,
            description="Two-day event"
        )
        
        formatted = appointment.format_for_telegram("Europe/Berlin")
        
        assert "📅 *Christmas Conference*" in formatted
        assert "🕐 Start: 25.12.2024 um 14:30" in formatted
        assert "🕑 Ende: 26.12.2024 um 16:30" in formatted
        assert "📝 Two-day event" in formatted
    
    def test_format_for_telegram_without_description(self):
        """Test formatting appointment without description for Telegram."""
        tz = pytz.timezone("Europe/Berlin")
        start_date = tz.localize(datetime(2024, 12, 25, 14, 30))
        end_date = tz.localize(datetime(2024, 12, 25, 15, 30))
        
        appointment = Appointment(
            title="Christmas Meeting",
            start_date=start_date,
            end_date=end_date
        )
        
        formatted = appointment.format_for_telegram("Europe/Berlin")
        
        assert "📅 *Christmas Meeting*" in formatted
        assert "🕐 25.12.2024 von 14:30 bis 15:30" in formatted
        assert "📝" not in formatted
    
    def test_location_and_tags_support(self):
        """Test location and tags in appointment."""
        start_date = datetime.now(timezone.utc) + timedelta(hours=1)
        end_date = start_date + timedelta(hours=2)
        
        appointment = Appointment(
            title="Team Meeting",
            start_date=start_date,
            end_date=end_date,
            location="Conference Room A",
            tags=["work", "important", "quarterly"]
        )
        
        # Test Notion properties
        properties = appointment.to_notion_properties()
        assert properties["Ort"]["rich_text"][0]["text"]["content"] == "Conference Room A"
        assert properties["Tags"]["rich_text"][0]["text"]["content"] == "work, important, quarterly"
        
        # Test Telegram formatting
        formatted = appointment.format_for_telegram()
        assert "📍 Conference Room A" in formatted
        assert "🏷️ work, important, quarterly" in formatted