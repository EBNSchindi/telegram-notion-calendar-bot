"""Unit tests for PartnerSyncService."""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from src.services.partner_sync_service import PartnerSyncService
from src.models.appointment import Appointment
from src.models.shared_appointment import SharedAppointment
from config.user_config import UserConfig, UserConfigManager


@pytest.fixture
def user_config():
    """Create a test user configuration."""
    return UserConfig(
        user_id=123456,
        private_api_key="test_private_key",
        private_database_id="12345678901234567890123456789012",
        shared_api_key="test_shared_key",
        shared_database_id="11111111222222223333333344444444",
        timezone="Europe/Berlin"
    )


@pytest.fixture
def partner_sync_service():
    """Create a PartnerSyncService instance with mocked services."""
    with patch('src.services.partner_sync_service.NotionService') as mock_notion:
        with patch('src.services.partner_sync_service.UserConfigManager') as mock_config_manager:
            service = PartnerSyncService()
            service.user_config_manager = mock_config_manager.return_value
            return service


@pytest.fixture
def sample_appointments():
    """Create sample appointments for testing."""
    return [
        Appointment(
            title="Partner Meeting",
            date=datetime.now(timezone.utc) + timedelta(days=1),
            description="Important meeting",
            location="Office",
            partner_relevant=True,
            notion_page_id="page-1",
            synced_to_shared_id=None
        ),
        Appointment(
            title="Personal Task",
            date=datetime.now(timezone.utc) + timedelta(days=2),
            partner_relevant=False,
            notion_page_id="page-2"
        ),
        Appointment(
            title="Already Synced",
            date=datetime.now(timezone.utc) + timedelta(days=3),
            partner_relevant=True,
            notion_page_id="page-3",
            synced_to_shared_id="shared-page-1"
        )
    ]


@pytest.fixture
def shared_appointment_data():
    """Create sample shared appointment data."""
    return {
        'id': 'shared-page-123',
        'created_time': '2024-01-20T10:00:00.000Z',
        'properties': {
            'Name': {'title': [{'text': {'content': 'Partner Meeting'}}]},
            'Datum': {'date': {'start': '2024-01-25T14:00:00+00:00'}},
            'Beschreibung': {'rich_text': [{'text': {'content': 'Important meeting'}}]},
            'Ort': {'rich_text': [{'text': {'content': 'Office'}}]},
            'SourcePrivateId': {'rich_text': [{'text': {'content': 'page-1'}}]},
            'SourceUserId': {'number': 123456}
        }
    }


class TestPartnerSyncService:
    """Test cases for PartnerSyncService."""
    
    @pytest.mark.asyncio
    async def test_sync_partner_relevant_appointments(self, partner_sync_service, user_config, sample_appointments):
        """Test syncing partner-relevant appointments."""
        # Mock services
        mock_private_service = AsyncMock()
        mock_shared_service = AsyncMock()
        
        # Mock get_all_appointments to return sample appointments
        mock_private_service.get_all_appointments = AsyncMock(return_value=sample_appointments)
        
        # Mock create_page for shared database
        mock_shared_service.create_page = AsyncMock(return_value='shared-page-123')
        
        # Mock update_page for private database
        mock_private_service.update_page = AsyncMock(return_value=True)
        
        with patch.object(partner_sync_service, '_get_notion_services', return_value=(mock_private_service, mock_shared_service)):
            result = await partner_sync_service.sync_partner_relevant_appointments(user_config)
            
            # Verify results
            assert result['synced_count'] == 1  # Only one new partner-relevant appointment
            assert result['already_synced'] == 1  # One already synced
            assert result['errors'] == 0
            assert len(result['synced_appointments']) == 1
            
            # Verify create_page was called for new partner-relevant appointment
            mock_shared_service.create_page.assert_called_once()
            
            # Verify update_page was called to update sync tracking
            mock_private_service.update_page.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_sync_single_appointment_success(self, partner_sync_service, user_config):
        """Test syncing a single appointment successfully."""
        appointment = Appointment(
            title="Test Meeting",
            date=datetime.now(timezone.utc) + timedelta(days=1),
            partner_relevant=True,
            notion_page_id="page-test"
        )
        
        mock_private_service = AsyncMock()
        mock_shared_service = AsyncMock()
        
        mock_shared_service.create_page = AsyncMock(return_value='shared-page-new')
        mock_private_service.update_page = AsyncMock(return_value=True)
        
        with patch.object(partner_sync_service, '_get_notion_services', return_value=(mock_private_service, mock_shared_service)):
            result = await partner_sync_service.sync_single_appointment(appointment, user_config)
            
            assert result is True
            
            # Verify shared appointment was created
            mock_shared_service.create_page.assert_called_once()
            
            # Check the properties passed to create_page
            call_args = mock_shared_service.create_page.call_args[0][0]
            assert 'PartnerRelevant' not in call_args  # Should be excluded in shared DB
            assert call_args['SourcePrivateId']['rich_text'][0]['text']['content'] == 'page-test'
            assert call_args['SourceUserId']['number'] == 123456
    
    @pytest.mark.asyncio
    async def test_sync_single_appointment_already_synced(self, partner_sync_service, user_config):
        """Test syncing an appointment that's already synced."""
        appointment = Appointment(
            title="Already Synced",
            date=datetime.now(timezone.utc),
            partner_relevant=True,
            notion_page_id="page-synced",
            synced_to_shared_id="shared-existing"
        )
        
        mock_private_service = AsyncMock()
        mock_shared_service = AsyncMock()
        
        with patch.object(partner_sync_service, '_get_notion_services', return_value=(mock_private_service, mock_shared_service)):
            result = await partner_sync_service.sync_single_appointment(appointment, user_config)
            
            assert result is False
            
            # Verify no operations were performed
            mock_shared_service.create_page.assert_not_called()
            mock_private_service.update_page.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_sync_single_appointment_not_partner_relevant(self, partner_sync_service, user_config):
        """Test syncing a non-partner-relevant appointment."""
        appointment = Appointment(
            title="Personal Task",
            date=datetime.now(timezone.utc),
            partner_relevant=False,
            notion_page_id="page-personal"
        )
        
        mock_private_service = AsyncMock()
        mock_shared_service = AsyncMock()
        
        with patch.object(partner_sync_service, '_get_notion_services', return_value=(mock_private_service, mock_shared_service)):
            result = await partner_sync_service.sync_single_appointment(appointment, user_config)
            
            assert result is False
            
            # Verify no operations were performed
            mock_shared_service.create_page.assert_not_called()
            mock_private_service.update_page.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_check_for_updates_in_shared_db(self, partner_sync_service, user_config, shared_appointment_data):
        """Test checking for updates in shared database."""
        mock_private_service = AsyncMock()
        mock_shared_service = AsyncMock()
        
        # Mock query_database to return shared appointment
        mock_shared_service.query_database = AsyncMock(
            return_value={'results': [shared_appointment_data]}
        )
        
        # Mock get_appointment_by_id to return None (not in private DB)
        mock_private_service.get_appointment_by_id = AsyncMock(return_value=None)
        
        # Mock create_page for copying to private DB
        mock_private_service.create_page = AsyncMock(return_value='private-page-new')
        
        with patch.object(partner_sync_service, '_get_notion_services', return_value=(mock_private_service, mock_shared_service)):
            result = await partner_sync_service.check_for_updates_in_shared_db(user_config)
            
            assert result['new_appointments'] == 1
            assert result['updated_appointments'] == 0
            assert result['errors'] == 0
            
            # Verify appointment was copied to private DB
            mock_private_service.create_page.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_background_sync(self, partner_sync_service):
        """Test starting background sync."""
        # Mock user configs
        mock_configs = [
            UserConfig(user_id=1, private_api_key="key1", private_database_id="db1", 
                      shared_api_key="shared1", shared_database_id="shared_db"),
            UserConfig(user_id=2, private_api_key="key2", private_database_id="db2",
                      shared_api_key="shared2", shared_database_id="shared_db")
        ]
        
        partner_sync_service.user_config_manager.get_all_user_configs.return_value = mock_configs
        
        # Mock sync methods
        partner_sync_service.sync_partner_relevant_appointments = AsyncMock(
            return_value={'synced_count': 1, 'errors': 0}
        )
        partner_sync_service.check_for_updates_in_shared_db = AsyncMock(
            return_value={'new_appointments': 0, 'errors': 0}
        )
        
        # Start background sync with very short interval for testing
        task = await partner_sync_service.start_background_sync(interval_hours=0.0001)
        
        # Give it a moment to run
        import asyncio
        await asyncio.sleep(0.1)
        
        # Cancel the task
        task.cancel()
        
        # Verify sync was called for both users
        assert partner_sync_service.sync_partner_relevant_appointments.call_count >= 2
        assert partner_sync_service.check_for_updates_in_shared_db.call_count >= 2
    
    @pytest.mark.asyncio
    async def test_error_handling_in_sync(self, partner_sync_service, user_config):
        """Test error handling during sync operations."""
        mock_private_service = AsyncMock()
        mock_shared_service = AsyncMock()
        
        # Mock create_page to raise an error
        mock_shared_service.create_page = AsyncMock(side_effect=Exception("API Error"))
        
        appointment = Appointment(
            title="Error Test",
            date=datetime.now(timezone.utc),
            partner_relevant=True,
            notion_page_id="page-error"
        )
        
        mock_private_service.get_all_appointments = AsyncMock(return_value=[appointment])
        
        with patch.object(partner_sync_service, '_get_notion_services', return_value=(mock_private_service, mock_shared_service)):
            result = await partner_sync_service.sync_partner_relevant_appointments(user_config)
            
            assert result['errors'] == 1
            assert result['synced_count'] == 0
            assert len(result['error_details']) == 1
            assert "API Error" in result['error_details'][0]
    
    @pytest.mark.asyncio
    async def test_get_notion_services(self, partner_sync_service, user_config):
        """Test getting Notion services for a user."""
        with patch('src.services.partner_sync_service.NotionService') as mock_notion_class:
            mock_private = MagicMock()
            mock_shared = MagicMock()
            
            mock_notion_class.side_effect = [mock_private, mock_shared]
            
            private_service, shared_service = partner_sync_service._get_notion_services(user_config)
            
            assert private_service == mock_private
            assert shared_service == mock_shared
            
            # Verify NotionService was called with correct parameters
            calls = mock_notion_class.call_args_list
            assert calls[0][0] == (user_config.private_api_key, user_config.private_database_id)
            assert calls[1][0] == (user_config.shared_api_key, user_config.shared_database_id)
    
    @pytest.mark.asyncio
    async def test_shared_appointment_model_conversion(self):
        """Test SharedAppointment model property conversion."""
        appointment = Appointment(
            title="Test",
            date=datetime.now(timezone.utc),
            partner_relevant=True,
            synced_to_shared_id="shared-123",
            source_private_id="private-123",
            source_user_id=123456
        )
        
        # Convert to SharedAppointment
        shared_appointment = SharedAppointment(**appointment.model_dump())
        
        # Convert to Notion properties
        properties = shared_appointment.to_notion_properties()
        
        # Verify excluded properties
        assert 'PartnerRelevant' not in properties
        assert 'SyncedToSharedId' not in properties
        
        # Verify included properties
        assert 'SourcePrivateId' in properties
        assert 'SourceUserId' in properties
        assert properties['SourcePrivateId']['rich_text'][0]['text']['content'] == 'private-123'
        assert properties['SourceUserId']['number'] == 123456


class TestPartnerSyncServiceIntegration:
    """Integration tests for PartnerSyncService."""
    
    @pytest.mark.asyncio
    async def test_bidirectional_sync_flow(self, partner_sync_service, user_config):
        """Test complete bidirectional sync flow."""
        # Setup appointments in both databases
        private_appointments = [
            Appointment(
                title="Private to Shared",
                date=datetime.now(timezone.utc) + timedelta(days=1),
                partner_relevant=True,
                notion_page_id="private-1"
            )
        ]
        
        shared_appointment_data = {
            'id': 'shared-1',
            'created_time': '2024-01-20T10:00:00.000Z',
            'properties': {
                'Name': {'title': [{'text': {'content': 'Shared to Private'}}]},
                'Datum': {'date': {'start': '2024-01-25T14:00:00+00:00'}},
                'SourcePrivateId': {'rich_text': []},  # Not from private DB
                'SourceUserId': {'number': 789}  # Different user
            }
        }
        
        mock_private_service = AsyncMock()
        mock_shared_service = AsyncMock()
        
        # Setup mocks
        mock_private_service.get_all_appointments = AsyncMock(return_value=private_appointments)
        mock_shared_service.query_database = AsyncMock(return_value={'results': [shared_appointment_data]})
        mock_private_service.get_appointment_by_id = AsyncMock(return_value=None)
        
        mock_shared_service.create_page = AsyncMock(return_value='new-shared-1')
        mock_private_service.create_page = AsyncMock(return_value='new-private-1')
        mock_private_service.update_page = AsyncMock(return_value=True)
        
        with patch.object(partner_sync_service, '_get_notion_services', return_value=(mock_private_service, mock_shared_service)):
            # Sync from private to shared
            sync_result = await partner_sync_service.sync_partner_relevant_appointments(user_config)
            assert sync_result['synced_count'] == 1
            
            # Check for updates from shared to private
            update_result = await partner_sync_service.check_for_updates_in_shared_db(user_config)
            assert update_result['new_appointments'] == 1