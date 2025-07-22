"""Unit tests for EmailProcessor service."""
import pytest
from unittest.mock import Mock, MagicMock, patch, call
import imaplib
import email
from datetime import datetime
from src.services.email_processor import EmailProcessor, EmailConfig, EmailMessage


@pytest.fixture
def email_config():
    """Create a test email configuration."""
    return EmailConfig(
        email_address="test@example.com",
        password="test_password",
        imap_server="imap.test.com",
        imap_port=993,
        enabled=True
    )


@pytest.fixture
def email_processor(email_config):
    """Create an EmailProcessor instance."""
    return EmailProcessor(email_config, delete_after_processing=True)


@pytest.fixture
def email_processor_no_delete(email_config):
    """Create an EmailProcessor instance without deletion."""
    return EmailProcessor(email_config, delete_after_processing=False)


@pytest.fixture
def mock_imap_connection():
    """Create a mock IMAP connection."""
    mock_conn = MagicMock(spec=imaplib.IMAP4_SSL)
    mock_conn.login.return_value = ('OK', ['Logged in'])
    mock_conn.select.return_value = ('OK', ['INBOX selected'])
    mock_conn.close.return_value = ('OK', ['Closed'])
    mock_conn.logout.return_value = ('OK', ['Logged out'])
    return mock_conn


@pytest.fixture
def sample_email_message():
    """Create a sample email message."""
    return EmailMessage(
        uid='123',
        subject='Test Subject',
        sender='sender@example.com',
        body='Test email body',
        date='2024-01-20',
        is_unread=True
    )


class TestEmailProcessor:
    """Test cases for EmailProcessor."""
    
    def test_initialization(self, email_config):
        """Test EmailProcessor initialization."""
        processor = EmailProcessor(email_config, delete_after_processing=True)
        
        assert processor.email_config == email_config
        assert processor.delete_after_processing is True
        assert processor.connection is None
    
    @patch('imaplib.IMAP4_SSL')
    def test_connect_success(self, mock_imap_class, email_processor, mock_imap_connection):
        """Test successful IMAP connection."""
        mock_imap_class.return_value = mock_imap_connection
        
        result = email_processor.connect()
        
        assert result is True
        mock_imap_class.assert_called_with(
            email_processor.email_config.imap_server,
            email_processor.email_config.imap_port
        )
        mock_imap_connection.login.assert_called_with(
            email_processor.email_config.email_address,
            email_processor.email_config.password
        )
    
    @patch('imaplib.IMAP4_SSL')
    def test_connect_failure(self, mock_imap_class, email_processor):
        """Test failed IMAP connection."""
        mock_imap_class.side_effect = Exception("Connection failed")
        
        result = email_processor.connect()
        
        assert result is False
    
    def test_delete_email_success(self, email_processor, mock_imap_connection):
        """Test successful email deletion."""
        email_processor.connection = mock_imap_connection
        mock_imap_connection.store.return_value = ('OK', ['Marked for deletion'])
        mock_imap_connection.expunge.return_value = ('OK', ['Expunged'])
        
        result = email_processor.delete_email('123')
        
        assert result is True
        mock_imap_connection.store.assert_called_with('123', '+FLAGS', '\\Deleted')
        mock_imap_connection.expunge.assert_called_once()
    
    def test_delete_email_failure_mark(self, email_processor, mock_imap_connection):
        """Test email deletion failure during marking."""
        email_processor.connection = mock_imap_connection
        mock_imap_connection.store.return_value = ('NO', ['Failed to mark'])
        
        result = email_processor.delete_email('123')
        
        assert result is False
        mock_imap_connection.expunge.assert_not_called()
    
    def test_delete_email_failure_expunge(self, email_processor, mock_imap_connection):
        """Test email deletion failure during expunge."""
        email_processor.connection = mock_imap_connection
        mock_imap_connection.store.return_value = ('OK', ['Marked for deletion'])
        mock_imap_connection.expunge.return_value = ('NO', ['Failed to expunge'])
        
        result = email_processor.delete_email('123')
        
        assert result is False
    
    def test_delete_email_no_connection(self, email_processor):
        """Test email deletion with no connection."""
        email_processor.connection = None
        
        result = email_processor.delete_email('123')
        
        assert result is False
    
    def test_mark_email_as_read(self, email_processor, mock_imap_connection):
        """Test marking email as read."""
        email_processor.connection = mock_imap_connection
        mock_imap_connection.store.return_value = ('OK', ['Marked as read'])
        
        result = email_processor.mark_email_as_read('123')
        
        assert result is True
        mock_imap_connection.store.assert_called_with('123', '+FLAGS', '\\Seen')
    
    def test_flag_email_as_processed(self, email_processor, mock_imap_connection):
        """Test flagging email as processed."""
        email_processor.connection = mock_imap_connection
        mock_imap_connection.store.return_value = ('OK', ['Flagged'])
        
        result = email_processor.flag_email_as_processed('123')
        
        assert result is True
        mock_imap_connection.store.assert_called_with('123', '+FLAGS', 'ProcessedByBot')
    
    def test_handle_email_processing_with_deletion(self, email_processor, mock_imap_connection):
        """Test email processing with deletion enabled."""
        email_processor.connection = mock_imap_connection
        email_processor.delete_after_processing = True
        
        # Mock delete_email method
        with patch.object(email_processor, 'delete_email', return_value=True) as mock_delete:
            result = email_processor.handle_email_processing('123', success=True)
            
            assert result is True
            mock_delete.assert_called_once_with('123')
    
    def test_handle_email_processing_without_deletion(self, email_processor_no_delete, mock_imap_connection):
        """Test email processing with deletion disabled."""
        email_processor_no_delete.connection = mock_imap_connection
        mock_imap_connection.store.return_value = ('OK', ['Success'])
        
        result = email_processor_no_delete.handle_email_processing('123', success=True)
        
        assert result is True
        # Should be called twice: once for \\Seen, once for ProcessedByBot
        assert mock_imap_connection.store.call_count == 2
    
    def test_handle_email_processing_failed(self, email_processor, mock_imap_connection):
        """Test handling failed email processing."""
        email_processor.connection = mock_imap_connection
        email_processor.delete_after_processing = True
        
        result = email_processor.handle_email_processing('123', success=False)
        
        assert result is False
        # Should not delete or mark as processed if processing failed
        mock_imap_connection.store.assert_not_called()
    
    @patch('imaplib.IMAP4_SSL')
    def test_get_with_connection_context(self, mock_imap_class, email_processor, mock_imap_connection):
        """Test get_connection context manager."""
        mock_imap_class.return_value = mock_imap_connection
        
        with email_processor.get_connection() as conn:
            assert conn == mock_imap_connection
        
        # Should select INBOX
        mock_imap_connection.select.assert_called_with('INBOX')
    
    def test_create_gmail_processor(self):
        """Test creating Gmail processor."""
        from src.services.email_processor import create_gmail_processor
        
        processor = create_gmail_processor(
            email_address="test@gmail.com",
            email_password="app_password",
            delete_after_processing=True
        )
        
        assert processor.email_config.email_address == "test@gmail.com"
        assert processor.email_config.imap_server == "imap.gmail.com"
        assert processor.delete_after_processing is True


class TestEmailDeletionIntegration:
    """Integration tests for email deletion functionality."""
    
    @patch('imaplib.IMAP4_SSL')
    def test_full_email_processing_flow_with_deletion(self, mock_imap_class, email_config):
        """Test complete email processing flow with deletion."""
        mock_conn = MagicMock()
        mock_imap_class.return_value = mock_conn
        
        # Setup mock responses
        mock_conn.login.return_value = ('OK', ['Logged in'])
        mock_conn.select.return_value = ('OK', ['INBOX selected'])
        mock_conn.search.return_value = ('OK', [b'1 2 3'])
        mock_conn.fetch.return_value = ('OK', [(b'1 (UID 123)', b'email data')])
        mock_conn.store.return_value = ('OK', ['Success'])
        mock_conn.expunge.return_value = ('OK', ['Expunged'])
        
        processor = EmailProcessor(email_config, delete_after_processing=True)
        
        # Connect and process
        assert processor.connect() is True
        
        # Process email successfully
        result = processor.handle_email_processing('123', success=True)
        assert result is True
        
        # Verify deletion sequence
        expected_calls = [
            call('123', '+FLAGS', '\\Deleted'),  # Mark for deletion
        ]
        assert any(c in mock_conn.store.call_args_list for c in expected_calls)
        mock_conn.expunge.assert_called_once()
    
    @patch('imaplib.IMAP4_SSL')
    def test_multiple_email_deletion(self, mock_imap_class, email_config):
        """Test deleting multiple emails."""
        mock_conn = MagicMock()
        mock_imap_class.return_value = mock_conn
        
        mock_conn.login.return_value = ('OK', ['Logged in'])
        mock_conn.select.return_value = ('OK', ['INBOX selected'])
        mock_conn.store.return_value = ('OK', ['Success'])
        mock_conn.expunge.return_value = ('OK', ['Expunged'])
        
        processor = EmailProcessor(email_config, delete_after_processing=True)
        processor.connect()
        
        # Delete multiple emails
        emails_to_delete = ['123', '456', '789']
        results = []
        
        for uid in emails_to_delete:
            result = processor.delete_email(uid)
            results.append(result)
        
        assert all(results)  # All deletions should succeed
        assert mock_conn.store.call_count == len(emails_to_delete)
        assert mock_conn.expunge.call_count == len(emails_to_delete)
    
    def test_deletion_configuration(self):
        """Test that deletion configuration is properly respected."""
        # With deletion enabled
        config = EmailConfig("test@example.com", "password")
        processor_with_delete = EmailProcessor(config, delete_after_processing=True)
        assert processor_with_delete.delete_after_processing is True
        
        # With deletion disabled
        processor_no_delete = EmailProcessor(config, delete_after_processing=False)
        assert processor_no_delete.delete_after_processing is False
        
        # Default should be False for safety
        processor_default = EmailProcessor(config)
        assert processor_default.delete_after_processing is False


class TestEmailProcessorErrorHandling:
    """Test error handling in email processor."""
    
    def test_delete_email_with_exception(self, email_processor, mock_imap_connection):
        """Test email deletion with unexpected exception."""
        email_processor.connection = mock_imap_connection
        mock_imap_connection.store.side_effect = Exception("IMAP error")
        
        result = email_processor.delete_email('123')
        
        assert result is False
    
    @patch('imaplib.IMAP4_SSL')
    def test_reconnect_on_connection_error(self, mock_imap_class, email_processor):
        """Test reconnection logic on connection errors."""
        mock_conn = MagicMock()
        mock_imap_class.return_value = mock_conn
        
        # First connection succeeds
        mock_conn.login.return_value = ('OK', ['Logged in'])
        assert email_processor.connect() is True
        
        # Simulate connection lost
        mock_conn.store.side_effect = imaplib.IMAP4.abort("Connection lost")
        
        # Try to delete, should fail
        result = email_processor.delete_email('123')
        assert result is False
        
        # Next operation should attempt reconnect
        mock_conn.store.side_effect = None
        mock_conn.store.return_value = ('OK', ['Success'])
        
        # This would trigger reconnect in real implementation
        email_processor.connection = None
        assert email_processor.connect() is True