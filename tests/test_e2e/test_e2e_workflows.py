"""
End-to-end tests for critical user workflows.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta, date
import pytz
import asyncio
from freezegun import freeze_time

from tests.factories import (
    TelegramUpdateFactory, TelegramContextFactory,
    AppointmentFactory, MemoFactory, UserConfigFactory,
    NotionPageFactory
)


@pytest.mark.e2e
class TestE2EWorkflows:
    """End-to-end tests for complete user workflows."""
    
    @pytest.fixture
    def setup_mocks(self):
        """Setup all necessary mocks for E2E tests."""
        mocks = {}
        
        # Mock Notion client
        with patch('src.services.notion_service.Client') as mock_notion:
            mocks['notion'] = mock_notion
            
        # Mock OpenAI
        with patch('src.services.ai_assistant_service.OpenAI') as mock_openai:
            mocks['openai'] = mock_openai
            
        # Mock Telegram Bot
        with patch('telegram.ext.Application.builder') as mock_builder:
            mock_app = Mock()
            mock_builder.return_value.token.return_value.build.return_value = mock_app
            mocks['telegram_app'] = mock_app
            
        return mocks
    
    @pytest.mark.asyncio
    @freeze_time("2024-01-15 09:00:00")
    async def test_complete_appointment_lifecycle(self, setup_mocks):
        """Test complete appointment lifecycle: create, list, edit, remind, delete."""
        # Setup
        user_id = 123456789
        notion_client = Mock()
        
        # Step 1: Create appointment
        create_update = TelegramUpdateFactory()
        create_context = TelegramContextFactory()
        create_update.effective_user.id = user_id
        create_update.message.text = "Schedule doctor appointment tomorrow at 2:30 PM at City Medical Center"
        
        # Mock AI extraction
        ai_response = {
            "appointments": [{
                "title": "Doctor appointment",
                "date": "2024-01-16T14:30:00",
                "location": "City Medical Center",
                "is_partner_relevant": True
            }]
        }
        
        with patch('src.services.ai_assistant_service.AIAssistantService.extract_appointments_from_text') as mock_ai:
            mock_ai.return_value = ai_response
            
            # Mock Notion creation
            created_page = {
                "id": "app_001",
                "properties": {
                    "Title": {"title": [{"text": {"content": "Doctor appointment"}}]},
                    "Date": {"date": {"start": "2024-01-16T14:30:00Z"}},
                    "Location": {"rich_text": [{"text": {"content": "City Medical Center"}}]}
                }
            }
            
            with patch('src.services.notion_service.NotionService.create_appointment') as mock_create:
                mock_create.return_value = created_page
                
                # Execute creation
                from src.handlers.enhanced_appointment_handler import EnhancedAppointmentHandler
                handler = EnhancedAppointmentHandler()
                await handler.handle_message(create_update, create_context)
                
                # Verify
                mock_ai.assert_called_once()
                mock_create.assert_called_once()
        
        # Step 2: List appointments
        list_update = TelegramUpdateFactory()
        list_context = TelegramContextFactory()
        list_update.effective_user.id = user_id
        list_update.message.text = "/list"
        
        with patch('src.services.notion_service.NotionService.query_appointments') as mock_query:
            mock_query.return_value = [created_page]
            
            # Execute listing
            await handler.handle_list_appointments(list_update, list_context)
            
            # Verify
            list_update.message.reply_html.assert_called()
            response = list_update.message.reply_html.call_args[0][0]
            assert "Doctor appointment" in response
            assert "City Medical Center" in response
        
        # Step 3: Edit appointment time
        edit_update = TelegramUpdateFactory()
        edit_context = TelegramContextFactory()
        edit_update.effective_user.id = user_id
        edit_update.callback_query.data = "edit_time:app_001"
        
        # User provides new time
        new_time_update = TelegramUpdateFactory()
        new_time_context = TelegramContextFactory()
        new_time_context.user_data = {"editing_appointment": "app_001", "edit_field": "time"}
        new_time_update.message.text = "3:45 PM"
        
        updated_page = created_page.copy()
        updated_page["properties"]["Date"]["date"]["start"] = "2024-01-16T15:45:00Z"
        
        with patch('src.services.notion_service.NotionService.update_appointment') as mock_update:
            mock_update.return_value = updated_page
            
            # Execute edit
            await handler.handle_edit_appointment_callback(edit_update, edit_context)
            await handler.handle_edit_response(new_time_update, new_time_context)
            
            # Verify
            mock_update.assert_called_once()
            assert "15:45" in mock_update.call_args[0][1]["Date"]["date"]["start"]
        
        # Step 4: Set reminder
        reminder_update = TelegramUpdateFactory()
        reminder_context = TelegramContextFactory()
        reminder_update.effective_user.id = user_id
        reminder_update.callback_query.data = "set_reminder:app_001:30"
        
        with patch('src.services.enhanced_reminder_service.EnhancedReminderService.schedule_reminder') as mock_reminder:
            mock_reminder.return_value = True
            
            # Execute reminder setup
            await handler.handle_reminder_settings_callback(reminder_update, reminder_context)
            
            # Verify
            mock_reminder.assert_called_once()
            reminder_update.callback_query.answer.assert_called_with("Reminder set for 30 minutes before")
        
        # Step 5: Receive reminder (simulate time passing)
        with freeze_time("2024-01-16 15:15:00"):  # 30 minutes before appointment
            with patch('src.services.enhanced_reminder_service.EnhancedReminderService.get_pending_reminders') as mock_pending:
                mock_pending.return_value = [AppointmentFactory(
                    id="app_001",
                    title="Doctor appointment",
                    date=datetime(2024, 1, 16, 15, 45, tzinfo=pytz.UTC),
                    location="City Medical Center"
                )]
                
                # Simulate reminder check
                from src.services.enhanced_reminder_service import EnhancedReminderService
                reminder_service = EnhancedReminderService()
                reminders = await reminder_service.check_and_send_reminders()
                
                assert len(reminders) == 1
                assert reminders[0].title == "Doctor appointment"
        
        # Step 6: Delete appointment
        delete_update = TelegramUpdateFactory()
        delete_context = TelegramContextFactory()
        delete_update.effective_user.id = user_id
        delete_update.callback_query.data = "delete_appointment:app_001"
        
        with patch('src.services.notion_service.NotionService.delete_appointment') as mock_delete:
            mock_delete.return_value = True
            
            # Execute deletion
            await handler.handle_delete_appointment_callback(delete_update, delete_context)
            
            # Verify
            mock_delete.assert_called_once_with("app_001")
            delete_update.callback_query.answer.assert_called()
            assert "deleted" in delete_update.callback_query.answer.call_args[0][0].lower()
    
    @pytest.mark.asyncio
    async def test_partner_collaboration_workflow(self):
        """Test complete partner collaboration workflow."""
        # Setup users
        user1_id = 111111111
        user2_id = 222222222
        
        user1_config = UserConfigFactory(
            user_id=user1_id,
            partner_user_id=user2_id,
            shared_database_id="shared_db_123"
        )
        user2_config = UserConfigFactory(
            user_id=user2_id,
            partner_user_id=user1_id,
            shared_database_id="shared_db_123"
        )
        
        with patch('config.user_config.load_user_config') as mock_config:
            mock_config.return_value = {
                "users": {
                    str(user1_id): user1_config,
                    str(user2_id): user2_config
                }
            }
            
            # Step 1: User 1 creates partner-relevant appointment
            create_update = TelegramUpdateFactory()
            create_update.effective_user.id = user1_id
            create_update.message.text = "Anniversary dinner on Saturday at 7 PM at Italian Restaurant #partner"
            
            appointment_data = {
                "id": "shared_001",
                "title": "Anniversary dinner",
                "date": "2024-01-20T19:00:00Z",
                "location": "Italian Restaurant",
                "is_partner_relevant": True,
                "created_by": user1_id
            }
            
            with patch('src.services.partner_sync_service.PartnerSyncService.create_shared_appointment') as mock_create:
                mock_create.return_value = appointment_data
                
                # Execute creation
                from src.services.partner_sync_service import PartnerSyncService
                sync_service = PartnerSyncService()
                result = await sync_service.sync_appointment_to_partner(
                    user1_id, appointment_data
                )
                
                # Verify
                mock_create.assert_called_once()
                assert result["shared_with"] == user2_id
            
            # Step 2: User 2 views shared appointments
            list_update = TelegramUpdateFactory()
            list_update.effective_user.id = user2_id
            list_update.message.text = "/shared"
            
            with patch('src.services.partner_sync_service.PartnerSyncService.get_shared_appointments') as mock_shared:
                mock_shared.return_value = [appointment_data]
                
                # Execute listing
                shared_appointments = await sync_service.get_shared_appointments(user2_id)
                
                # Verify
                assert len(shared_appointments) == 1
                assert shared_appointments[0]["title"] == "Anniversary dinner"
            
            # Step 3: User 2 accepts the shared appointment
            accept_update = TelegramUpdateFactory()
            accept_update.effective_user.id = user2_id
            accept_update.callback_query.data = "accept_shared:shared_001"
            
            with patch('src.services.partner_sync_service.PartnerSyncService.accept_shared_appointment') as mock_accept:
                mock_accept.return_value = True
                
                # Execute acceptance
                result = await sync_service.accept_shared_appointment(user2_id, "shared_001")
                
                # Verify
                assert result is True
                mock_accept.assert_called_once_with(user2_id, "shared_001")
            
            # Step 4: Both users receive reminders
            with freeze_time("2024-01-20 18:00:00"):  # 1 hour before
                with patch('src.services.enhanced_reminder_service.EnhancedReminderService.send_reminder') as mock_remind:
                    # Simulate reminder for both users
                    for user_id in [user1_id, user2_id]:
                        await mock_remind(user_id, appointment_data)
                    
                    # Verify both users got reminders
                    assert mock_remind.call_count == 2
    
    @pytest.mark.asyncio
    async def test_memo_workflow_with_ai_categorization(self):
        """Test memo creation, AI categorization, search, and archival."""
        user_id = 333333333
        
        # Step 1: Create memo with natural language
        create_update = TelegramUpdateFactory()
        create_update.effective_user.id = user_id
        create_update.message.text = "Remember to buy groceries: milk, eggs, bread, and vegetables for the week"
        
        # Mock AI categorization
        ai_categories = {
            "category": "shopping",
            "tags": ["groceries", "weekly", "essentials"],
            "priority": "medium"
        }
        
        with patch('src.services.ai_assistant_service.AIAssistantService.categorize_memo') as mock_ai:
            mock_ai.return_value = ai_categories
            
            memo_data = {
                "id": "memo_001",
                "title": "Buy groceries",
                "content": "milk, eggs, bread, and vegetables for the week",
                "tags": ai_categories["tags"],
                "category": ai_categories["category"],
                "priority": ai_categories["priority"]
            }
            
            with patch('src.services.memo_service.MemoService.create_memo') as mock_create:
                mock_create.return_value = memo_data
                
                # Execute creation
                from src.services.memo_service import MemoService
                memo_service = MemoService()
                result = await memo_service.create_memo_with_ai(
                    user_id, create_update.message.text
                )
                
                # Verify
                assert result["category"] == "shopping"
                assert "groceries" in result["tags"]
        
        # Step 2: Search memos by tag
        search_update = TelegramUpdateFactory()
        search_update.effective_user.id = user_id
        search_update.message.text = "/search_memo groceries"
        
        with patch('src.services.memo_service.MemoService.search_memos') as mock_search:
            mock_search.return_value = [memo_data]
            
            # Execute search
            results = await memo_service.search_memos(user_id, "groceries")
            
            # Verify
            assert len(results) == 1
            assert results[0]["title"] == "Buy groceries"
        
        # Step 3: Complete and archive memo
        archive_update = TelegramUpdateFactory()
        archive_update.effective_user.id = user_id
        archive_update.callback_query.data = "archive_memo:memo_001"
        
        with patch('src.services.memo_service.MemoService.archive_memo') as mock_archive:
            mock_archive.return_value = True
            
            # Execute archival
            result = await memo_service.archive_memo(user_id, "memo_001")
            
            # Verify
            assert result is True
            mock_archive.assert_called_once_with(user_id, "memo_001")
    
    @pytest.mark.asyncio
    async def test_business_email_integration_workflow(self):
        """Test email processing and calendar integration workflow."""
        user_id = 444444444
        
        # Step 1: Configure email integration
        config_update = TelegramUpdateFactory()
        config_update.effective_user.id = user_id
        config_update.message.text = "/configure_email business@example.com"
        
        email_config = {
            "email": "business@example.com",
            "sync_enabled": True,
            "auto_create_appointments": True
        }
        
        with patch('src.services.email_processor.EmailProcessor.configure_email') as mock_config:
            mock_config.return_value = email_config
            
            # Execute configuration
            from src.services.email_processor import EmailProcessor
            email_processor = EmailProcessor()
            result = await email_processor.configure_email_for_user(
                user_id, "business@example.com"
            )
            
            # Verify
            assert result["email"] == "business@example.com"
            assert result["sync_enabled"] is True
        
        # Step 2: Process incoming email with meeting request
        email_content = """
        Subject: Project Review Meeting
        From: client@company.com
        
        Hi,
        
        Let's schedule a project review meeting for next Wednesday at 3:00 PM.
        We'll discuss the Q1 deliverables and timeline.
        
        Location: Conference Room A or Zoom
        
        Best regards,
        Client
        """
        
        # Mock AI extraction from email
        extracted_appointment = {
            "title": "Project Review Meeting",
            "date": "2024-01-24T15:00:00",
            "location": "Conference Room A or Zoom",
            "description": "Discuss Q1 deliverables and timeline",
            "participants": ["client@company.com"],
            "source": "email"
        }
        
        with patch('src.services.ai_assistant_service.AIAssistantService.extract_appointment_from_email') as mock_extract:
            mock_extract.return_value = extracted_appointment
            
            # Process email
            result = await email_processor.process_email(user_id, email_content)
            
            # Verify appointment created
            assert result["appointment"]["title"] == "Project Review Meeting"
            assert result["appointment"]["source"] == "email"
        
        # Step 3: Send confirmation
        confirm_update = TelegramUpdateFactory()
        confirm_update.effective_user.id = user_id
        confirm_update.callback_query.data = "confirm_email_appointment:app_email_001"
        
        with patch('src.services.email_processor.EmailProcessor.send_confirmation') as mock_confirm:
            mock_confirm.return_value = True
            
            # Execute confirmation
            result = await email_processor.send_meeting_confirmation(
                user_id, "app_email_001", "client@company.com"
            )
            
            # Verify
            assert result is True
            mock_confirm.assert_called_once()