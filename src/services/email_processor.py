"""Email processor service for retrieving and processing business calendar emails."""
import imaplib
import email
import logging
import asyncio
import time
import socket
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Dict, Tuple
from email.mime.text import MIMEText
from dataclasses import dataclass
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@dataclass
class EmailConfig:
    """Email configuration for a user."""
    email_address: str
    password: str
    imap_server: str = "imap.gmail.com"
    imap_port: int = 993
    enabled: bool = True


@dataclass
class EmailMessage:
    """Represents an email message with metadata."""
    uid: str
    subject: str
    sender: str
    body: str
    date: str
    is_unread: bool = True


class EmailProcessor:
    """Service for processing emails via IMAP."""
    
    def __init__(self, email_config: EmailConfig, delete_after_processing: bool = False):
        """
        Initialize email processor.
        
        Args:
            email_config: Email configuration
            delete_after_processing: Whether to delete emails after successful processing
        """
        self.email_config = email_config
        self.delete_after_processing = delete_after_processing
        self.connection = None
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 3
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="imap")
        self._imap_timeout = 30  # seconds
        
    @contextmanager
    def imap_connection(self):
        """Context manager for IMAP connection with automatic cleanup."""
        connection = None
        try:
            connection = self._connect()
            yield connection
        except Exception as e:
            logger.error(f"IMAP connection error: {e}")
            raise
        finally:
            if connection:
                try:
                    connection.close()
                    connection.logout()
                except Exception as e:
                    logger.debug(f"Error during IMAP cleanup: {e}")  # Log but don't fail
    
    def _connect(self) -> imaplib.IMAP4_SSL:
        """
        Establish IMAP connection.
        
        Returns:
            IMAP connection object
            
        Raises:
            Exception: If connection fails
        """
        try:
            logger.info(f"Connecting to {self.email_config.imap_server}:{self.email_config.imap_port}")
            
            # Set socket timeout
            socket.setdefaulttimeout(self._imap_timeout)
            
            connection = imaplib.IMAP4_SSL(
                self.email_config.imap_server, 
                self.email_config.imap_port
            )
            
            connection.login(
                self.email_config.email_address, 
                self.email_config.password
            )
            
            connection.select('INBOX')
            self._reconnect_attempts = 0
            
            logger.info(f"Successfully connected to {self.email_config.email_address}")
            return connection
            
        except imaplib.IMAP4.error as e:
            logger.error(f"IMAP authentication failed for {self.email_config.email_address}: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to email server: {e}")
            raise
        finally:
            # Reset socket timeout
            socket.setdefaulttimeout(None)
    
    def _reconnect_if_needed(self) -> imaplib.IMAP4_SSL:
        """
        Reconnect to IMAP server if connection is lost.
        
        Returns:
            IMAP connection object
            
        Raises:
            Exception: If reconnection fails after max attempts
        """
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            raise Exception(f"Max reconnection attempts ({self._max_reconnect_attempts}) exceeded")
        
        self._reconnect_attempts += 1
        logger.warning(f"Reconnecting to email server (attempt {self._reconnect_attempts})")
        
        # Wait before reconnecting
        time.sleep(2 ** self._reconnect_attempts)
        
        return self._connect()
    
    def fetch_emails(self, limit: int = 50, is_initial: bool = False) -> List[EmailMessage]:
        """
        Fetch emails from inbox with limit for performance.
        For initial run, fetch all recent emails. Otherwise, fetch recent emails only.
        
        Args:
            limit: Maximum number of emails to fetch (default: 50)
            is_initial: Whether this is the initial processing run (default: False)
        
        Returns:
            List of email messages (read and unread from whitelist senders)
        """
        try:
            with self.imap_connection() as connection:
                # For initial run, fetch all recent emails. Otherwise, recent emails only
                from datetime import datetime, timedelta
                today = datetime.now()
                
                if is_initial:
                    # Search for ALL emails from last 7 days for initial processing
                    last_week = today - timedelta(days=7)
                    search_criteria = f'SINCE "{last_week.strftime("%d-%b-%Y")}"'
                    logger.info("Initial processing: fetching all emails from last 7 days")
                else:
                    # Search for all emails from today and yesterday
                    yesterday = today - timedelta(days=1)
                    search_criteria = f'SINCE "{yesterday.strftime("%d-%b-%Y")}"'
                    logger.info("Regular processing: fetching emails from last 2 days")
                
                status, messages = connection.search(None, search_criteria)
                
                if status != 'OK':
                    logger.warning(f"Email search failed, falling back to all emails")
                    status, messages = connection.search(None, 'ALL')
                
                if status != 'OK':
                    logger.error(f"Failed to search emails: {status}")
                    return []
                
                email_ids = messages[0].split()
                total_emails = len(email_ids)
                
                # Limit emails for performance
                if total_emails > limit:
                    logger.info(f"Found {total_emails} emails, processing latest {limit}")
                    email_ids = email_ids[-limit:]  # Get the most recent emails
                else:
                    logger.info(f"Found {total_emails} emails")
                
                emails = []
                for email_id in email_ids:
                    try:
                        email_msg = self._fetch_email_by_id(connection, email_id.decode())
                        if email_msg:
                            emails.append(email_msg)
                    except Exception as e:
                        logger.error(f"Error fetching email {email_id}: {e}")
                        continue
                
                return emails
                
        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            return []
    
    def _fetch_email_by_id(self, connection: imaplib.IMAP4_SSL, email_id: str) -> Optional[EmailMessage]:
        """
        Fetch a specific email by ID.
        
        Args:
            connection: IMAP connection
            email_id: Email ID to fetch
            
        Returns:
            EmailMessage object if successful, None otherwise
        """
        try:
            # First fetch email body
            status, data = connection.fetch(email_id, '(RFC822)')
            
            if status != 'OK':
                logger.error(f"Failed to fetch email {email_id}: {status}")
                return None
            
            email_body = data[0][1]
            email_message = email.message_from_bytes(email_body)
            
            # Then fetch flags separately
            try:
                flag_status, flag_data = connection.fetch(email_id, '(FLAGS)')
                if flag_status == 'OK':
                    flags_str = flag_data[0].decode() if isinstance(flag_data[0], bytes) else str(flag_data[0])
                    is_unread = '\\Seen' not in flags_str
                else:
                    is_unread = True  # Default to unread if flags can't be fetched
            except Exception as e:
                logger.warning(f"Could not fetch flags for email {email_id}: {e}")
                is_unread = True  # Default to unread
            
            # Extract email metadata
            subject = self._decode_header(email_message.get('Subject', ''))
            sender = self._decode_header(email_message.get('From', ''))
            date = email_message.get('Date', '')
            
            # Extract email body
            body = self._extract_email_body(email_message)
            
            return EmailMessage(
                uid=email_id,
                subject=subject,
                sender=sender,
                body=body,
                date=date,
                is_unread=is_unread
            )
            
        except Exception as e:
            logger.error(f"Error parsing email {email_id}: {e}")
            return None
    
    def _decode_header(self, header_value: str) -> str:
        """Decode email header value."""
        try:
            decoded_parts = email.header.decode_header(header_value)
            decoded_header = ''
            
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    if encoding:
                        decoded_header += part.decode(encoding)
                    else:
                        decoded_header += part.decode('utf-8', errors='ignore')
                else:
                    decoded_header += part
            
            return decoded_header
        except Exception as e:
            logger.error(f"Error decoding header: {e}")
            return header_value
    
    def _extract_email_body(self, email_message) -> str:
        """
        Extract email body text.
        
        Args:
            email_message: Email message object
            
        Returns:
            Email body as string
        """
        try:
            if email_message.is_multipart():
                # Handle multipart emails
                for part in email_message.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get('Content-Disposition'))
                    
                    # Skip attachments
                    if 'attachment' in content_disposition:
                        continue
                    
                    if content_type == 'text/plain':
                        body = part.get_payload(decode=True)
                        if isinstance(body, bytes):
                            return body.decode('utf-8', errors='ignore')
                        return str(body)
                
                # If no text/plain part found, try text/html
                for part in email_message.walk():
                    content_type = part.get_content_type()
                    if content_type == 'text/html':
                        body = part.get_payload(decode=True)
                        if isinstance(body, bytes):
                            return body.decode('utf-8', errors='ignore')
                        return str(body)
            else:
                # Handle single part emails
                body = email_message.get_payload(decode=True)
                if isinstance(body, bytes):
                    return body.decode('utf-8', errors='ignore')
                return str(body)
            
            return ""
            
        except Exception as e:
            logger.error(f"Error extracting email body: {e}")
            return ""
    
    def mark_email_as_read(self, email_uid: str) -> bool:
        """
        Mark email as read.
        
        Args:
            email_uid: Email UID to mark as read
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.imap_connection() as connection:
                status, _ = connection.store(email_uid, '+FLAGS', '\\Seen')
                return status == 'OK'
                
        except Exception as e:
            logger.error(f"Error marking email {email_uid} as read: {e}")
            return False
    
    def delete_email(self, email_uid: str) -> bool:
        """
        Delete email from server immediately.
        
        Args:
            email_uid: Email UID to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.imap_connection() as connection:
                # Mark for deletion
                status, _ = connection.store(email_uid, '+FLAGS', '\\Deleted')
                
                if status == 'OK':
                    # Expunge immediately to permanently delete
                    logger.info(f"Expunging email {email_uid}...")
                    status, response = connection.expunge()
                    
                    if status == 'OK':
                        logger.info(f"Successfully deleted email {email_uid}")
                        return True
                    else:
                        logger.error(f"Failed to expunge email {email_uid}: {response}")
                        return False
                else:
                    logger.error(f"Failed to mark email {email_uid} for deletion")
                    return False
                    
        except socket.timeout:
            logger.error(f"Timeout while deleting email {email_uid}")
            return False
        except Exception as e:
            logger.error(f"Error deleting email {email_uid}: {e}")
            return False
    
    def flag_email_as_processed(self, email_uid: str, flag: str = "PROCESSED") -> bool:
        """
        Add custom flag to email to mark it as processed.
        
        Args:
            email_uid: Email UID to flag
            flag: Custom flag name
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.imap_connection() as connection:
                status, _ = connection.store(email_uid, '+FLAGS', f'\\{flag}')
                return status == 'OK'
                
        except Exception as e:
            logger.error(f"Error flagging email {email_uid}: {e}")
            return False
    
    def process_email_after_success(self, email_uid: str) -> bool:
        """
        Process email after successful calendar sync.
        
        Args:
            email_uid: Email UID to process
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.delete_after_processing:
                return self.delete_email(email_uid)
            else:
                # Just mark as read and add processed flag
                read_success = self.mark_email_as_read(email_uid)
                flag_success = self.flag_email_as_processed(email_uid)
                return read_success and flag_success
                
        except Exception as e:
            logger.error(f"Error processing email {email_uid} after success: {e}")
            return False


# Factory function to create EmailProcessor from user config
def create_email_processor_from_config(
    email_address: str,
    email_password: str,
    imap_server: str = "imap.gmail.com",
    imap_port: int = 993,
    delete_after_processing: bool = False
) -> EmailProcessor:
    """
    Create EmailProcessor from configuration parameters.
    
    Args:
        email_address: Gmail address
        email_password: Gmail app password
        imap_server: IMAP server address
        imap_port: IMAP server port
        delete_after_processing: Whether to delete emails after processing
        
    Returns:
        Configured EmailProcessor instance
    """
    email_config = EmailConfig(
        email_address=email_address,
        password=email_password,
        imap_server=imap_server,
        imap_port=imap_port
    )
    
    return EmailProcessor(email_config, delete_after_processing)


if __name__ == "__main__":
    # Test the email processor
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Test configuration
    test_email = os.getenv('EMAIL_ADDRESS', 'test@gmail.com')
    test_password = os.getenv('EMAIL_PASSWORD', 'test_password')
    
    processor = create_email_processor_from_config(
        email_address=test_email,
        password=test_password,
        delete_after_processing=False
    )
    
    try:
        emails = processor.fetch_emails()
        print(f"Found {len(emails)} emails")
        
        for email_msg in emails[:3]:  # Show first 3 emails
            print(f"Subject: {email_msg.subject}")
            print(f"From: {email_msg.sender}")
            print(f"Body preview: {email_msg.body[:100]}...")
            print("-" * 50)
            
    except Exception as e:
        print(f"Error testing email processor: {e}")