"""Integration tests for memo functionality."""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from src.handlers.memo_handler import MemoHandler
from src.services.memo_service import MemoService
from src.services.ai_assistant_service import AIAssistantService
from src.models.memo import Memo
from config.user_config import UserConfig
from telegram import Update, Message, User


@pytest.fixture
def user_config():
    """Create a test user configuration."""
    return UserConfig(
        user_id=123456,
        private_api_key="test_private_key",
        private_database_id="12345678901234567890123456789012",
        memo_database_id="98765432109876543210987654321098",
        shared_api_key="test_shared_key",
        shared_database_id="11111111222222223333333344444444",
        timezone="Europe/Berlin"
    )


@pytest.fixture
def mock_notion_responses():
    """Create mock Notion API responses."""
    return {
        'create_page': {
            'id': 'new-page-123',
            'created_time': '2024-01-20T10:00:00.000Z'
        },
        'query_results': [
            {
                'id': 'page-1',
                'created_time': '2024-01-15T10:00:00.000Z',
                'properties': {
                    'Aufgabe': {'title': [{'text': {'content': 'Einkaufen gehen'}}]},
                    'Status': {'select': {'name': 'Nicht begonnen'}},
                    'Fälligkeitsdatum': {'date': {'start': '2024-01-25'}},
                    'Bereich': {'select': {'name': 'Privat'}},
                    'Notizen': {'rich_text': [{'text': {'content': 'Milch und Brot'}}]}
                }
            },
            {
                'id': 'page-2',
                'created_time': '2024-01-16T10:00:00.000Z',
                'properties': {
                    'Aufgabe': {'title': [{'text': {'content': 'Meeting vorbereiten'}}]},
                    'Status': {'select': {'name': 'In Arbeit'}},
                    'Projekt': {'rich_text': [{'text': {'content': 'Q1 Planning'}}]}
                }
            }
        ]
    }


class TestMemoIntegrationFlow:
    """Test complete memo creation and retrieval flow."""
    
    @pytest.mark.asyncio
    async def test_complete_memo_flow_with_ai(self, user_config, mock_notion_responses):
        """Test complete flow: AI extraction -> validation -> creation -> retrieval."""
        with patch('src.services.notion_service.NotionService') as mock_notion_class:
            # Setup Notion mock
            mock_notion = mock_notion_class.return_value
            mock_notion.create_page = AsyncMock(return_value=mock_notion_responses['create_page']['id'])
            mock_notion.query_database = AsyncMock(return_value={'results': mock_notion_responses['query_results']})
            
            # Create services
            memo_service = MemoService(user_config.private_api_key, user_config.memo_database_id)
            memo_service.notion_service = mock_notion
            
            ai_service = AIAssistantService()
            
            # Create handler
            handler = MemoHandler(user_config)
            handler.memo_service = memo_service
            handler.ai_service = ai_service
            
            # Mock AI service
            with patch.object(ai_service, 'client') as mock_client:
                mock_client.chat.completions.create = AsyncMock()
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = '''
                {
                    "aufgabe": "Präsentation für Teammeeting vorbereiten",
                    "faelligkeitsdatum": "2024-01-26",
                    "bereich": "Arbeit",
                    "projekt": "Q1 Planning",
                    "notizen": "Slides und Handouts erstellen",
                    "confidence": 0.9
                }
                '''
                mock_client.chat.completions.create.return_value = mock_response
                
                # Step 1: Extract memo from text
                memo_data = await ai_service.extract_memo_from_text(
                    "Präsentation für Teammeeting am Freitag vorbereiten - Slides und Handouts",
                    user_config.timezone
                )
                
                assert memo_data is not None
                assert memo_data['aufgabe'] == 'Präsentation für Teammeeting vorbereiten'
                assert memo_data['confidence'] == 0.9
                
                # Step 2: Validate data
                validated_data = await ai_service.validate_memo_data(memo_data)
                assert validated_data['aufgabe'] == 'Präsentation für Teammeeting vorbereiten'
                
                # Step 3: Create memo object
                memo = Memo(
                    aufgabe=validated_data['aufgabe'],
                    status="Nicht begonnen",
                    faelligkeitsdatum=datetime.strptime(validated_data['faelligkeitsdatum'], '%Y-%m-%d').replace(tzinfo=timezone.utc) if validated_data.get('faelligkeitsdatum') else None,
                    bereich=validated_data.get('bereich'),
                    projekt=validated_data.get('projekt'),
                    notizen=validated_data.get('notizen')
                )
                
                # Step 4: Save to Notion
                page_id = await memo_service.create_memo(memo)
                assert page_id == 'new-page-123'
                
                # Step 5: Retrieve memos
                memos = await memo_service.get_recent_memos(limit=10)
                assert len(memos) == 2
                assert memos[0].aufgabe == 'Einkaufen gehen'
                assert memos[1].aufgabe == 'Meeting vorbereiten'
    
    @pytest.mark.asyncio
    async def test_memo_flow_without_ai_fallback(self, user_config):
        """Test memo creation when AI is not available (using fallback)."""
        # Create AI service without API key
        with patch.dict('os.environ', {}, clear=True):
            ai_service = AIAssistantService()
            assert ai_service.client is None
            
            # Test fallback extraction
            memo_data = await ai_service.extract_memo_from_text(
                "Arzttermin buchen bis morgen",
                user_config.timezone
            )
            
            assert memo_data is not None
            assert memo_data['aufgabe'] == 'Arzttermin buchen bis morgen'
            assert memo_data['confidence'] == 0.6  # Fallback confidence
            
            # Should detect "bis morgen" and set due date
            tomorrow = (datetime.now().date() + timedelta(days=1)).strftime('%Y-%m-%d')
            assert memo_data['faelligkeitsdatum'] == tomorrow
    
    @pytest.mark.asyncio
    async def test_memo_telegram_interaction(self, user_config):
        """Test complete Telegram interaction for memo creation."""
        with patch('src.services.notion_service.NotionService') as mock_notion_class:
            with patch('src.services.ai_assistant_service.AsyncOpenAI'):
                # Setup mocks
                mock_notion = mock_notion_class.return_value
                mock_notion.create_page = AsyncMock(return_value='page-789')
                
                # Create handler
                handler = MemoHandler(user_config)
                
                # Mock update and context
                update = MagicMock(spec=Update)
                update.effective_user = MagicMock(spec=User)
                update.effective_user.id = 123456
                
                update.message = MagicMock(spec=Message)
                update.message.text = "Zahnarzttermin am 30.01. um 14:00 Uhr buchen"
                
                processing_msg = MagicMock()
                processing_msg.edit_text = AsyncMock()
                update.message.reply_text = AsyncMock(return_value=processing_msg)
                
                context = MagicMock()
                context.user_data = {'awaiting_memo': True}
                
                # Mock AI response
                handler.ai_service.extract_memo_from_text = AsyncMock(return_value={
                    'aufgabe': 'Zahnarzttermin buchen',
                    'faelligkeitsdatum': '2024-01-30',
                    'notizen': 'um 14:00 Uhr',
                    'confidence': 0.85
                })
                handler.ai_service.validate_memo_data = AsyncMock(return_value={
                    'aufgabe': 'Zahnarzttermin buchen',
                    'faelligkeitsdatum': '2024-01-30',
                    'notizen': 'um 14:00 Uhr'
                })
                
                # Process message
                await handler.process_ai_memo_message(update, context)
                
                # Verify flow
                update.message.reply_text.assert_called_once()
                handler.ai_service.extract_memo_from_text.assert_called_once()
                
                # Check success message
                processing_msg.edit_text.assert_called()
                last_call = processing_msg.edit_text.call_args_list[-1]
                assert "Memo erstellt!" in last_call[1]['text']
                assert context.user_data['awaiting_memo'] is False
    
    @pytest.mark.asyncio
    async def test_memo_status_update_flow(self, user_config):
        """Test updating memo status."""
        with patch('src.services.notion_service.NotionService') as mock_notion_class:
            mock_notion = mock_notion_class.return_value
            mock_notion.update_page = AsyncMock(return_value=True)
            
            memo_service = MemoService(user_config.private_api_key, user_config.memo_database_id)
            memo_service.notion_service = mock_notion
            
            # Update status
            success = await memo_service.update_memo_status('page-123', 'Erledigt')
            
            assert success is True
            mock_notion.update_page.assert_called_once_with(
                'page-123',
                {'Status': {'select': {'name': 'Erledigt'}}}
            )
    
    @pytest.mark.asyncio
    async def test_memo_search_flow(self, user_config, mock_notion_responses):
        """Test searching for memos."""
        with patch('src.services.notion_service.NotionService') as mock_notion_class:
            mock_notion = mock_notion_class.return_value
            
            # Mock search results
            search_results = [mock_notion_responses['query_results'][0]]  # Only "Einkaufen" memo
            mock_notion.query_database = AsyncMock(return_value={'results': search_results})
            
            memo_service = MemoService(user_config.private_api_key, user_config.memo_database_id)
            memo_service.notion_service = mock_notion
            
            # Search for "Einkaufen"
            memos = await memo_service.search_memos("Einkaufen")
            
            assert len(memos) == 1
            assert memos[0].aufgabe == 'Einkaufen gehen'
            assert memos[0].notizen == 'Milch und Brot'
            
            # Verify search filter was applied
            call_args = mock_notion.query_database.call_args
            assert 'filter' in call_args[1]


class TestMemoErrorHandling:
    """Test error handling in memo operations."""
    
    @pytest.mark.asyncio
    async def test_notion_api_error_handling(self, user_config):
        """Test handling of Notion API errors."""
        with patch('src.services.notion_service.NotionService') as mock_notion_class:
            mock_notion = mock_notion_class.return_value
            mock_notion.create_page = AsyncMock(side_effect=Exception("Notion API Error"))
            
            memo_service = MemoService(user_config.private_api_key, user_config.memo_database_id)
            memo_service.notion_service = mock_notion
            
            memo = Memo(aufgabe="Test Task", status="Nicht begonnen")
            
            with pytest.raises(Exception) as exc_info:
                await memo_service.create_memo(memo)
            
            assert "Notion API Error" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_invalid_memo_data_handling(self, user_config):
        """Test handling of invalid memo data."""
        handler = MemoHandler(user_config)
        
        # Mock services
        handler.ai_service.extract_memo_from_text = AsyncMock(return_value={
            # Missing required 'aufgabe' field
            'notizen': 'Some notes',
            'confidence': 0.7
        })
        
        update = MagicMock()
        update.message = MagicMock()
        update.message.text = "Invalid memo"
        
        processing_msg = MagicMock()
        processing_msg.edit_text = AsyncMock()
        update.message.reply_text = AsyncMock(return_value=processing_msg)
        
        context = MagicMock()
        context.user_data = {}
        
        await handler.process_ai_memo_message(update, context)
        
        # Should show extraction error
        processing_msg.edit_text.assert_called_with(
            "❌ Konnte kein Memo aus deiner Nachricht extrahieren.\n"
            "Versuche es mit einer klareren Beschreibung:\n\n"
            "*Beispiel:* \"Einkaufen gehen bis morgen\" oder \"Präsentation vorbereiten\"",
            parse_mode='Markdown'
        )
    
    @pytest.mark.asyncio
    async def test_database_connection_error(self, user_config):
        """Test handling of database connection errors."""
        with patch('src.services.notion_service.NotionService') as mock_notion_class:
            mock_notion_class.side_effect = Exception("Connection failed")
            
            with pytest.raises(Exception):
                memo_service = MemoService.from_user_config(user_config)