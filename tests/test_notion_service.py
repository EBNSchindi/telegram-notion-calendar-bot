import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta, timezone
from notion_client.errors import APIResponseError
from src.services.notion_service import NotionService
from src.models.appointment import Appointment


class TestNotionService:
    """Test cases for NotionService."""
    
    @pytest.fixture
    def notion_service(self, settings, mock_notion_client):
        """Create NotionService instance with mocked client."""
        service = NotionService(settings)
        service.client = mock_notion_client
        return service
    
    @pytest.mark.asyncio
    async def test_create_appointment_success(self, notion_service, mock_notion_client):
        """Test successful appointment creation."""
        # Setup
        future_date = datetime.now(timezone.utc) + timedelta(hours=1)
        appointment = Appointment(
            title="Test Meeting",
            date=future_date,
            description="Important meeting"
        )
        
        mock_notion_client.pages.create.return_value = {
            "id": "test-page-id"
        }
        
        # Execute
        page_id = await notion_service.create_appointment(appointment)
        
        # Assert
        assert page_id == "test-page-id"
        mock_notion_client.pages.create.assert_called_once()
        
        call_args = mock_notion_client.pages.create.call_args
        assert call_args[1]["parent"]["database_id"] == "test_database_id"
        assert "Title" in call_args[1]["properties"]
        assert "Date" in call_args[1]["properties"]
    
    @pytest.mark.asyncio
    async def test_create_appointment_api_error(self, notion_service, mock_notion_client):
        """Test appointment creation with API error."""
        # Setup
        future_date = datetime.now(timezone.utc) + timedelta(hours=1)
        appointment = Appointment(
            title="Test Meeting",
            date=future_date
        )
        
        mock_notion_client.pages.create.side_effect = APIResponseError("API Error", response=Mock(), body={})
        
        # Execute & Assert
        with pytest.raises(APIResponseError):
            await notion_service.create_appointment(appointment)
    
    @pytest.mark.asyncio
    async def test_get_appointments_success(self, notion_service, mock_notion_client):
        """Test successful appointments retrieval."""
        # Setup
        mock_notion_client.databases.query.return_value = {
            "results": [
                {
                    "id": "page-1",
                    "created_time": "2024-12-20T10:00:00+01:00",
                    "properties": {
                        "Title": {
                            "title": [
                                {
                                    "text": {
                                        "content": "Meeting 1"
                                    }
                                }
                            ]
                        },
                        "Date": {
                            "date": {
                                "start": "2024-12-25T14:30:00+01:00"
                            }
                        },
                        "Created": {
                            "date": {
                                "start": "2024-12-20T10:00:00+01:00"
                            }
                        }
                    }
                },
                {
                    "id": "page-2",
                    "created_time": "2024-12-20T10:00:00+01:00",
                    "properties": {
                        "Title": {
                            "title": [
                                {
                                    "text": {
                                        "content": "Meeting 2"
                                    }
                                }
                            ]
                        },
                        "Date": {
                            "date": {
                                "start": "2024-12-26T10:00:00+01:00"
                            }
                        },
                        "Created": {
                            "date": {
                                "start": "2024-12-20T10:00:00+01:00"
                            }
                        }
                    }
                }
            ]
        }
        
        # Execute
        appointments = await notion_service.get_appointments(limit=10)
        
        # Assert
        assert len(appointments) == 2
        assert appointments[0].title == "Meeting 1"
        assert appointments[1].title == "Meeting 2"
        
        mock_notion_client.databases.query.assert_called_once_with(
            database_id="test_database_id",
            sorts=[{"property": "Datum", "direction": "ascending"}],
            page_size=10
        )
    
    @pytest.mark.asyncio
    async def test_get_appointments_empty_result(self, notion_service, mock_notion_client):
        """Test appointments retrieval with empty result."""
        # Setup
        mock_notion_client.databases.query.return_value = {
            "results": []
        }
        
        # Execute
        appointments = await notion_service.get_appointments()
        
        # Assert
        assert len(appointments) == 0
    
    @pytest.mark.asyncio
    async def test_get_appointments_api_error(self, notion_service, mock_notion_client):
        """Test appointments retrieval with API error."""
        # Setup
        mock_notion_client.databases.query.side_effect = APIResponseError("API Error", response=Mock(), body={})
        
        # Execute & Assert
        with pytest.raises(APIResponseError):
            await notion_service.get_appointments()
    
    @pytest.mark.asyncio
    async def test_update_appointment_success(self, notion_service, mock_notion_client):
        """Test successful appointment update."""
        # Setup
        future_date = datetime.now(timezone.utc) + timedelta(hours=1)
        appointment = Appointment(
            title="Updated Meeting",
            date=future_date
        )
        
        # Execute
        result = await notion_service.update_appointment("test-page-id", appointment)
        
        # Assert
        assert result is True
        mock_notion_client.pages.update.assert_called_once()
        
        call_args = mock_notion_client.pages.update.call_args
        assert call_args[1]["page_id"] == "test-page-id"
        assert "Title" in call_args[1]["properties"]
    
    @pytest.mark.asyncio
    async def test_delete_appointment_success(self, notion_service, mock_notion_client):
        """Test successful appointment deletion."""
        # Execute
        result = await notion_service.delete_appointment("test-page-id")
        
        # Assert
        assert result is True
        mock_notion_client.pages.update.assert_called_once_with(
            page_id="test-page-id",
            archived=True
        )
    
    @pytest.mark.asyncio
    async def test_test_connection_success(self, notion_service, mock_notion_client):
        """Test successful connection test."""
        # Setup
        mock_notion_client.databases.retrieve.return_value = {
            "id": "test_database_id"
        }
        
        # Execute
        result = await notion_service.test_connection()
        
        # Assert
        assert result is True
        mock_notion_client.databases.retrieve.assert_called_once_with(
            database_id="test_database_id"
        )
    
    @pytest.mark.asyncio
    async def test_test_connection_failure(self, notion_service, mock_notion_client):
        """Test connection test failure."""
        # Setup
        mock_notion_client.databases.retrieve.side_effect = APIResponseError("Connection failed", response=Mock(), body={})
        
        # Execute
        result = await notion_service.test_connection()
        
        # Assert
        assert result is False