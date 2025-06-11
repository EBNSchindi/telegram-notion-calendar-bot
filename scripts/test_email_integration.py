#!/usr/bin/env python3
"""Test script for business email integration."""
import sys
import os
import asyncio
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.json_parser import BusinessEventParser, create_test_event
from src.services.email_processor import create_email_processor_from_config
from src.services.business_calendar_sync import BusinessCalendarSync, create_sync_manager_from_env
from config.user_config import UserConfig
from dotenv import load_dotenv

load_dotenv()

def test_json_parser():
    """Test the JSON parser with sample data."""
    print("=" * 50)
    print("Testing JSON Parser")
    print("=" * 50)
    
    parser = BusinessEventParser()
    
    # Test email content
    test_email_body = f"""
Betreff: Terminweiterleitung

{create_test_event()}

[Firmen-Footer kann ignoriert werden]
Mit freundlichen Grüßen
DM Corporate
Automatisch generierte Nachricht
"""
    
    print("Sample email body:")
    print(test_email_body)
    print("\n" + "-" * 40 + "\n")
    
    # Extract and parse event
    json_string = parser.extract_json_from_email(test_email_body)
    if json_string:
        print(f"Extracted JSON: {json_string}")
        
        business_event = parser.parse_business_event(json_string)
        if business_event:
            print(f"✅ Successfully parsed business event:")
            print(f"   Action: {business_event.action}")
            print(f"   Title: {business_event.event_title}")
            print(f"   Start: {business_event.event_start}")
            print(f"   End: {business_event.event_end}")
            print(f"   Organizer: {business_event.organizer}")
            print(f"   Is Team Event: {business_event.is_team_event()}")
            return True
        else:
            print("❌ Failed to parse business event")
            return False
    else:
        print("❌ Failed to extract JSON from email")
        return False

def test_email_configuration():
    """Test email configuration and connection."""
    print("=" * 50)
    print("Testing Email Configuration")
    print("=" * 50)
    
    email_address = os.getenv('EMAIL_ADDRESS')
    email_password = os.getenv('EMAIL_PASSWORD')
    email_enabled = os.getenv('EMAIL_SYNC_ENABLED', 'false').lower() == 'true'
    
    print(f"Email Sync Enabled: {email_enabled}")
    print(f"Email Address: {email_address or 'Not configured'}")
    print(f"Email Password: {'*' * len(email_password) if email_password else 'Not configured'}")
    
    if not email_enabled:
        print("⚠️  Email sync is disabled in configuration")
        return False
    
    if not email_address or not email_password:
        print("⚠️  Email credentials not configured")
        return False
    
    try:
        processor = create_email_processor_from_config(
            email_address=email_address,
            email_password=email_password,
            delete_after_processing=False
        )
        
        print("✅ Email processor created successfully")
        
        # Test connection (don't actually fetch emails in test)
        print("⚠️  Skipping actual email fetch in test mode")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create email processor: {e}")
        return False

def test_business_sync_configuration():
    """Test business calendar sync configuration."""
    print("=" * 50)
    print("Testing Business Calendar Sync Configuration")
    print("=" * 50)
    
    try:
        sync_manager = create_sync_manager_from_env()
        print("✅ Sync manager created successfully")
        
        print(f"Configuration:")
        for key, value in sync_manager.global_config.items():
            if 'password' in key.lower():
                display_value = '*' * len(str(value)) if value else 'Not set'
            else:
                display_value = value or 'Not set'
            print(f"   {key}: {display_value}")
        
        # Test user configuration
        test_user_config = UserConfig(
            telegram_user_id=123456789,
            telegram_username="test_user",
            notion_api_key="test_api_key",
            notion_database_id="test_db_id",
            shared_notion_api_key="shared_api_key",
            shared_notion_database_id="shared_db_id"
        )
        
        sync_manager.add_user(test_user_config)
        print(f"✅ Test user added to sync manager")
        print(f"   Users configured: {len(sync_manager.user_syncs)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to configure business sync: {e}")
        return False

def test_notion_integration():
    """Test Notion database field mapping."""
    print("=" * 50)
    print("Testing Notion Integration")
    print("=" * 50)
    
    from src.models.appointment import Appointment
    
    # Create test business appointment
    test_appointment = Appointment(
        title="Test Business Meeting",
        date=datetime(2025, 6, 15, 14, 30),
        description="Test business event from email",
        organizer="test@company.com",
        outlook_id="test_outlook_id_123",
        is_business_event=True,
        duration_minutes=60
    )
    
    print("Test appointment created:")
    print(f"   Title: {test_appointment.title}")
    print(f"   Date: {test_appointment.date}")
    print(f"   Organizer: {test_appointment.organizer}")
    print(f"   Outlook ID: {test_appointment.outlook_id}")
    print(f"   Is Business Event: {test_appointment.is_business_event}")
    
    # Test Notion properties mapping
    properties = test_appointment.to_notion_properties()
    print("\nNotion properties mapping:")
    for key, value in properties.items():
        print(f"   {key}: {value}")
    
    print("✅ Notion integration fields mapped successfully")
    return True

async def run_all_tests():
    """Run all tests."""
    print("🚀 Starting Business Email Integration Tests\n")
    
    tests = [
        ("JSON Parser", test_json_parser),
        ("Email Configuration", test_email_configuration),
        ("Business Sync Configuration", test_business_sync_configuration),
        ("Notion Integration", test_notion_integration),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test '{test_name}' failed with exception: {e}")
            results.append((test_name, False))
        print("\n")
    
    # Summary
    print("=" * 50)
    print("Test Summary")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Business email integration is ready.")
    else:
        print("⚠️  Some tests failed. Please check configuration.")
    
    return passed == total

def main():
    """Main function."""
    asyncio.run(run_all_tests())

if __name__ == "__main__":
    main()