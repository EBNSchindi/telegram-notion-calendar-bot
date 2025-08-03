"""Unit tests for AIAssistantService."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import json
from src.services.ai_assistant_service import AIAssistantService


@pytest.fixture
def ai_service_with_client():
    """Create AIAssistantService with mocked OpenAI client."""
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
        with patch('src.services.ai_assistant_service.AsyncOpenAI') as mock_openai:
            service = AIAssistantService()
            # Mock the client
            mock_client = MagicMock()
            service.client = mock_client
            return service, mock_client


@pytest.fixture
def ai_service_without_client():
    """Create AIAssistantService without OpenAI client (no API key)."""
    with patch.dict('os.environ', {}, clear=True):
        service = AIAssistantService()
        return service


@pytest.fixture
def mock_ai_response():
    """Create a mock AI response."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "title": "Zahnarzttermin",
        "date": "2024-01-25",
        "time": "15:30",
        "duration_minutes": 60,
        "description": "Kontrolluntersuchung",
        "location": "Zahnarztpraxis Dr. Schmidt",
        "confidence": 0.9
    })
    return mock_response


@pytest.fixture
def mock_ai_response_with_duration():
    """Create a mock AI response with custom duration."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "title": "Team Meeting",
        "date": "2024-01-25",
        "time": "14:00",
        "duration_minutes": 120,
        "description": "Quarterly review",
        "confidence": 0.95
    })
    return mock_response


@pytest.fixture
def mock_memo_response():
    """Create a mock AI memo response."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "aufgabe": "Präsentation vorbereiten",
        "notizen": "Für das Teammeeting am Freitag",
        "faelligkeitsdatum": "2024-01-26",
        "bereich": "Arbeit",
        "projekt": "Q1 Planning",
        "confidence": 0.85
    })
    return mock_response


class TestAIAssistantService:
    """Test cases for AIAssistantService."""
    
    def test_initialization_with_api_key(self):
        """Test initialization with API key."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            with patch('src.services.ai_assistant_service.AsyncOpenAI') as mock_openai:
                service = AIAssistantService()
                assert service.client is not None
                mock_openai.assert_called_once()
    
    def test_initialization_without_api_key(self):
        """Test initialization without API key."""
        with patch.dict('os.environ', {}, clear=True):
            service = AIAssistantService()
            assert service.client is None
    
    def test_is_available_with_client(self, ai_service_with_client):
        """Test is_available returns True when client exists."""
        service, _ = ai_service_with_client
        assert service.is_available() is True
    
    def test_is_available_without_client(self, ai_service_without_client):
        """Test is_available returns False when no client."""
        assert ai_service_without_client.is_available() is False
    
    @pytest.mark.asyncio
    async def test_extract_appointment_success(self, ai_service_with_client, mock_ai_response):
        """Test successful appointment extraction."""
        service, mock_client = ai_service_with_client
        
        # Setup mock
        mock_create = AsyncMock(return_value=mock_ai_response)
        mock_client.chat.completions.create = mock_create
        
        result = await service.extract_appointment_from_text(
            "Morgen um 15:30 Zahnarzttermin bei Dr. Schmidt"
        )
        
        assert result is not None
        assert result['title'] == 'Zahnarzttermin'
        assert result['date'] == '2024-01-25'
        assert result['time'] == '15:30'
        assert result['location'] == 'Zahnarztpraxis Dr. Schmidt'
        assert result['confidence'] == 0.9
        
        # Verify API was called
        mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_extract_appointment_low_confidence(self, ai_service_with_client):
        """Test appointment extraction with low confidence is rejected."""
        service, mock_client = ai_service_with_client
        
        # Mock response with low confidence
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "title": "Maybe something",
            "date": "2024-01-25",
            "confidence": 0.3  # Low confidence
        })
        
        mock_create = AsyncMock(return_value=mock_response)
        mock_client.chat.completions.create = mock_create
        
        result = await service.extract_appointment_from_text("maybe tomorrow something")
        
        assert result is None  # Rejected due to low confidence
    
    @pytest.mark.asyncio
    async def test_extract_appointment_no_client(self, ai_service_without_client):
        """Test appointment extraction without client returns None."""
        result = await ai_service_without_client.extract_appointment_from_text(
            "Morgen Zahnarzttermin"
        )
        assert result is None
    
    @pytest.mark.asyncio
    async def test_extract_memo_success(self, ai_service_with_client, mock_memo_response):
        """Test successful memo extraction."""
        service, mock_client = ai_service_with_client
        
        # Setup mock
        mock_create = AsyncMock(return_value=mock_memo_response)
        mock_client.chat.completions.create = mock_create
        
        result = await service.extract_memo_from_text(
            "Präsentation für Teammeeting am Freitag vorbereiten"
        )
        
        assert result is not None
        assert result['aufgabe'] == 'Präsentation vorbereiten'
        assert result['faelligkeitsdatum'] == '2024-01-26'
        assert result['bereich'] == 'Arbeit'
        assert result['projekt'] == 'Q1 Planning'
        assert result['confidence'] == 0.85
    
    @pytest.mark.asyncio
    async def test_extract_memo_fallback(self, ai_service_without_client):
        """Test memo extraction fallback when no AI available."""
        result = await ai_service_without_client.extract_memo_from_text(
            "Einkaufen gehen bis morgen"
        )
        
        assert result is not None  # Should use fallback
        assert result['aufgabe'] == 'Einkaufen gehen bis morgen'
        assert result['confidence'] == 0.6  # Default fallback confidence
        # Should detect "morgen" and set due date
        tomorrow = (datetime.now().date() + timedelta(days=1)).strftime('%Y-%m-%d')
        assert result['faelligkeitsdatum'] == tomorrow
    
    def test_basic_memo_extraction(self, ai_service_without_client):
        """Test basic memo extraction logic."""
        # Test with date pattern
        result = ai_service_without_client._basic_memo_extraction(
            "Präsentation fertigstellen bis 25.01.2024"
        )
        
        assert result is not None
        assert result['aufgabe'] == 'Präsentation fertigstellen bis 25.01.2024'
        # The service auto-corrects past dates to future
        assert result['faelligkeitsdatum'] == '2025-01-25'
        
        # Test with relative date
        result = ai_service_without_client._basic_memo_extraction(
            "Meeting vorbereiten bis morgen"
        )
        
        assert result is not None
        tomorrow = (datetime.now().date() + timedelta(days=1)).strftime('%Y-%m-%d')
        assert result['faelligkeitsdatum'] == tomorrow
        
        # Test with project keyword
        result = ai_service_without_client._basic_memo_extraction(
            "Projekt Review durchführen"
        )
        
        assert result is not None
        assert result['bereich'] == 'Projekt'
    
    @pytest.mark.asyncio
    async def test_validate_appointment_data(self, ai_service_with_client):
        """Test appointment data validation."""
        service, _ = ai_service_with_client
        
        # Valid data with duration
        data = {
            'title': 'Test Appointment',
            'date': '2024-01-25',
            'time': '14:30',
            'duration_minutes': 90,
            'description': 'Test description',
            'location': 'Test location'
        }
        
        validated = await service.validate_appointment_data(data)
        
        assert validated['title'] == 'Test Appointment'
        assert validated['date'] == '2024-01-25'
        assert validated['time'] == '14:30'
        assert validated['duration_minutes'] == 90
        
        # Invalid time format
        data['time'] = '25:99'
        validated = await service.validate_appointment_data(data)
        assert validated['time'] is None  # Invalid time should be removed
        
        # Missing title
        data = {'date': '2024-01-25'}
        validated = await service.validate_appointment_data(data)
        assert validated['title'] == 'Neuer Termin'  # Default title
        assert validated['duration_minutes'] == 60  # Default duration
    
    @pytest.mark.asyncio
    async def test_validate_duration_boundaries(self, ai_service_with_client):
        """Test duration validation boundaries."""
        service, _ = ai_service_with_client
        
        # Test too small duration
        data = {
            'title': 'Quick Task',
            'date': '2024-01-25',
            'duration_minutes': 3  # Less than 5 minutes
        }
        validated = await service.validate_appointment_data(data)
        assert validated['duration_minutes'] == 60  # Should default to 60
        
        # Test too large duration
        data['duration_minutes'] = 1500  # More than 24 hours
        validated = await service.validate_appointment_data(data)
        assert validated['duration_minutes'] == 1440  # Should cap at 24 hours
        
        # Test valid durations
        for duration in [5, 30, 60, 120, 1440]:
            data['duration_minutes'] = duration
            validated = await service.validate_appointment_data(data)
            assert validated['duration_minutes'] == duration
    
    @pytest.mark.asyncio
    async def test_validate_duration_type_conversion(self, ai_service_with_client):
        """Test duration type conversion."""
        service, _ = ai_service_with_client
        
        # Test string to int conversion
        data = {
            'title': 'Meeting',
            'date': '2024-01-25',
            'duration_minutes': '90'  # String instead of int
        }
        validated = await service.validate_appointment_data(data)
        assert validated['duration_minutes'] == 90
        assert isinstance(validated['duration_minutes'], int)
        
        # Test invalid duration (non-numeric)
        data['duration_minutes'] = 'invalid'
        validated = await service.validate_appointment_data(data)
        assert validated['duration_minutes'] == 60  # Default
    
    @pytest.mark.asyncio
    async def test_validate_memo_data(self, ai_service_with_client):
        """Test memo data validation."""
        service, _ = ai_service_with_client
        
        # Valid data
        data = {
            'aufgabe': 'Test Task',
            'faelligkeitsdatum': '2024-01-25',
            'notizen': 'Some notes',
            'bereich': 'Work',
            'projekt': 'Test Project'
        }
        
        validated = await service.validate_memo_data(data)
        
        assert validated['aufgabe'] == 'Test Task'
        assert validated['faelligkeitsdatum'] == '2024-01-25'
        
        # Missing required field
        from src.utils.error_handler import BotError
        with pytest.raises(BotError) as exc_info:
            await service.validate_memo_data({})
        assert "Missing required 'aufgabe' field" in str(exc_info.value)
        
        # Long text truncation
        data['aufgabe'] = 'x' * 300
        validated = await service.validate_memo_data(data)
        assert len(validated['aufgabe']) == 200  # Should be truncated
    
    @pytest.mark.asyncio
    async def test_retry_logic(self, ai_service_with_client):
        """Test retry logic on API failures."""
        service, mock_client = ai_service_with_client
        service.max_retries = 3
        
        # Mock to fail twice then succeed
        call_count = 0
        
        async def mock_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("API Error")
            return MagicMock(choices=[MagicMock(message=MagicMock(content='{"title": "Test", "date": "2024-01-25", "confidence": 0.8}'))])
        
        mock_client.chat.completions.create = mock_create
        
        result = await service.extract_appointment_from_text("Test")
        
        assert result is not None
        assert result['title'] == 'Test'
        assert call_count == 3  # Should have retried
    
    @pytest.mark.asyncio
    async def test_json_extraction_from_text(self, ai_service_with_client):
        """Test JSON extraction from mixed text response."""
        service, mock_client = ai_service_with_client
        
        # Mock response with JSON embedded in text
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """
        Here is the extracted data:
        {"title": "Meeting", "date": "2024-01-25", "duration_minutes": 60, "confidence": 0.9}
        That's all!
        """
        
        mock_create = AsyncMock(return_value=mock_response)
        mock_client.chat.completions.create = mock_create
        
        result = await service.extract_appointment_from_text("Meeting tomorrow")
        
        assert result is not None
        assert result['title'] == 'Meeting'
        assert result['duration_minutes'] == 60
    
    @pytest.mark.asyncio
    async def test_json_extraction_with_code_block(self, ai_service_with_client):
        """Test JSON extraction from markdown code block."""
        service, mock_client = ai_service_with_client
        
        # Mock response with JSON in code block
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """
        Here's the extracted appointment:
        ```json
        {
            "title": "Arzttermin",
            "date": "2024-01-26",
            "time": "10:00",
            "duration_minutes": 30,
            "confidence": 0.85
        }
        ```
        Done!
        """
        
        mock_create = AsyncMock(return_value=mock_response)
        mock_client.chat.completions.create = mock_create
        
        result = await service.extract_appointment_from_text("Arzttermin morgen um 10")
        
        assert result is not None
        assert result['title'] == 'Arzttermin'
        assert result['duration_minutes'] == 30
        assert result['time'] == '10:00'
    
    @pytest.mark.asyncio
    async def test_json_extraction_multiple_objects(self, ai_service_with_client):
        """Test JSON extraction with multiple JSON objects (should extract first)."""
        service, mock_client = ai_service_with_client
        
        # Mock response with multiple JSON objects
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """
        First appointment:
        {"title": "Meeting 1", "date": "2024-01-25", "duration_minutes": 60, "confidence": 0.9}
        Second appointment:
        {"title": "Meeting 2", "date": "2024-01-26", "duration_minutes": 90, "confidence": 0.8}
        """
        
        mock_create = AsyncMock(return_value=mock_response)
        mock_client.chat.completions.create = mock_create
        
        result = await service.extract_appointment_from_text("Two meetings")
        
        assert result is not None
        assert result['title'] == 'Meeting 1'  # Should extract first valid JSON
        assert result['duration_minutes'] == 60
    
    @pytest.mark.asyncio
    async def test_duration_extraction_german_patterns(self, ai_service_with_client, mock_ai_response_with_duration):
        """Test duration extraction from German patterns."""
        service, mock_client = ai_service_with_client
        
        # Test various German duration patterns
        test_cases = [
            ("30 min", 30),
            ("1 Stunde", 60),
            ("2 Stunden", 120),
            ("halbe Stunde", 30),
            ("anderthalb Stunden", 90),
            ("1.5h", 90),
            ("2,5 Stunden", 150)
        ]
        
        for pattern, expected_duration in test_cases:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = json.dumps({
                "title": "Test Termin",
                "date": "2024-01-25",
                "time": "14:00",
                "duration_minutes": expected_duration,
                "confidence": 0.9
            })
            
            mock_create = AsyncMock(return_value=mock_response)
            mock_client.chat.completions.create = mock_create
            
            result = await service.extract_appointment_from_text(f"Termin morgen für {pattern}")
            
            assert result is not None
            assert result['duration_minutes'] == expected_duration
    
    @pytest.mark.asyncio
    async def test_duration_default_when_not_specified(self, ai_service_with_client):
        """Test default duration when not specified."""
        service, mock_client = ai_service_with_client
        
        # Mock response without duration_minutes
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "title": "Quick Meeting",
            "date": "2024-01-25",
            "time": "15:00",
            "confidence": 0.85
        })
        
        mock_create = AsyncMock(return_value=mock_response)
        mock_client.chat.completions.create = mock_create
        
        result = await service.extract_appointment_from_text("Quick meeting tomorrow at 3pm")
        
        assert result is not None
        assert result['duration_minutes'] == 60  # Default duration
    
    @pytest.mark.asyncio
    async def test_malformed_json_error_handling(self, ai_service_with_client):
        """Test error handling for malformed JSON responses."""
        service, mock_client = ai_service_with_client
        
        # Mock response with malformed JSON
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """
        {
            "title": "Meeting",
            "date": "2024-01-25",
            "confidence": 0.9
        } extra text here causing error
        """
        
        mock_create = AsyncMock(return_value=mock_response)
        mock_client.chat.completions.create = mock_create
        
        result = await service.extract_appointment_from_text("Meeting tomorrow")
        
        # Should still extract valid JSON despite trailing text
        assert result is not None
        assert result['title'] == 'Meeting'


class TestAIAssistantServiceIntegration:
    """Integration-style tests for AIAssistantService."""
    
    @pytest.mark.asyncio
    async def test_full_appointment_flow(self, ai_service_with_client, mock_ai_response):
        """Test full appointment extraction and validation flow."""
        service, mock_client = ai_service_with_client
        
        # Setup mock
        mock_create = AsyncMock(return_value=mock_ai_response)
        mock_client.chat.completions.create = mock_create
        
        # Extract
        result = await service.extract_appointment_from_text(
            "Morgen um 15:30 Zahnarzttermin bei Dr. Schmidt"
        )
        
        # Validate
        validated = await service.validate_appointment_data(result)
        
        assert validated['title'] == 'Zahnarzttermin'
        assert validated['date'] == '2024-01-25'
        assert validated['time'] == '15:30'
        assert validated['location'] == 'Zahnarztpraxis Dr. Schmidt'
    
    @pytest.mark.asyncio
    async def test_improve_appointment_title(self, ai_service_with_client):
        """Test appointment title improvement."""
        service, mock_client = ai_service_with_client
        
        # Mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Zahnarzttermin - Kontrolluntersuchung"
        
        mock_create = AsyncMock(return_value=mock_response)
        mock_client.chat.completions.create = mock_create
        
        improved = await service.improve_appointment_title("Zahnarzt")
        
        assert improved == "Zahnarzttermin - Kontrolluntersuchung"
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, ai_service_with_client):
        """Test timeout handling."""
        service, mock_client = ai_service_with_client
        service.timeout = 0.1  # Very short timeout
        
        # Mock to simulate slow response
        import asyncio
        
        async def slow_response(*args, **kwargs):
            await asyncio.sleep(1)  # Longer than timeout
            return MagicMock()
        
        mock_client.chat.completions.create = slow_response
        
        result = await service.extract_appointment_from_text("Test")
        
        assert result is None  # Should timeout and return None