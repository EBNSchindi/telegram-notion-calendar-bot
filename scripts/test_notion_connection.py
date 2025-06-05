#!/usr/bin/env python3
"""
Script to test Notion connection and create sample appointments.
Run this to verify your Notion setup is working correctly.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
import pytz

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config.settings import Settings
from src.models.appointment import Appointment
from src.services.notion_service import NotionService


async def test_notion_connection():
    """Test Notion connection and create sample data."""
    print("🔧 Testing Notion Connection...")
    print("=" * 50)
    
    try:
        # Initialize settings and service
        settings = Settings()
        notion_service = NotionService(settings)
        
        print(f"📊 Database ID: {settings.notion_database_id}")
        print(f"🌍 Timezone: {settings.timezone}")
        print()
        
        # Test 1: Connection test
        print("1️⃣ Testing basic connection...")
        connection_ok = await notion_service.test_connection()
        
        if connection_ok:
            print("✅ Connection successful!")
        else:
            print("❌ Connection failed!")
            return False
        
        print()
        
        # Test 2: Retrieve database properties
        print("2️⃣ Checking database properties...")
        try:
            db_info = notion_service.client.databases.retrieve(database_id=settings.notion_database_id)
            properties = db_info.get('properties', {})
            
            print("Available properties:")
            for prop_name, prop_info in properties.items():
                prop_type = prop_info.get('type', 'unknown')
                print(f"  - {prop_name}: {prop_type}")
            
            # Check for required properties
            required_props = ['Name', 'Datum']  # Updated for your database
            missing_props = [prop for prop in required_props if prop not in properties]
            
            if missing_props:
                print(f"⚠️ Missing required properties: {missing_props}")
                print("Your database should have: Name (Title), Datum (Date), Beschreibung (Text), Tags (Multi-select), Ort (Text)")
            else:
                print("✅ Required properties found!")
            
        except Exception as e:
            print(f"❌ Error checking database properties: {e}")
        
        print()
        
        # Test 3: Create sample appointments
        print("3️⃣ Creating sample appointments...")
        
        # Sample appointments with your database structure
        sample_appointments = [
            {
                "title": "Team Meeting",
                "date": datetime.now(pytz.timezone(settings.timezone)) + timedelta(hours=2),
                "description": "Wöchentliches Standup Meeting",
                "location": "Büro Raum 42",
                "tags": ["work", "meeting"]
            },
            {
                "title": "Zahnarzttermin", 
                "date": datetime.now(pytz.timezone(settings.timezone)) + timedelta(days=1, hours=3),
                "description": "Routinekontrolle",
                "location": "Dr. Schmidt Praxis",
                "tags": ["health", "appointment"]
            },
            {
                "title": "Projektpräsentation",
                "date": datetime.now(pytz.timezone(settings.timezone)) + timedelta(days=2),
                "description": "Abschlusspräsentation des Q4 Projekts",
                "location": "Konferenzraum A",
                "tags": ["work", "presentation", "important"]
            }
        ]
        
        created_appointments = []
        
        for i, apt_data in enumerate(sample_appointments, 1):
            try:
                print(f"  Creating appointment {i}: {apt_data['title']}")
                
                appointment = Appointment(
                    title=apt_data['title'],
                    date=apt_data['date'],
                    description=apt_data['description'],
                    location=apt_data['location'],
                    tags=apt_data['tags']
                )
                
                page_id = await notion_service.create_appointment(appointment)
                created_appointments.append((appointment, page_id))
                
                print(f"    ✅ Created with ID: {page_id}")
                
            except Exception as e:
                print(f"    ❌ Failed to create appointment {i}: {e}")
        
        print()
        
        # Test 4: Retrieve created appointments
        print("4️⃣ Retrieving appointments from Notion...")
        
        try:
            appointments = await notion_service.get_appointments(limit=5)
            print(f"Found {len(appointments)} appointments:")
            
            for i, apt in enumerate(appointments, 1):
                print(f"  {i}. {apt.title}")
                print(f"     📅 {apt.date.strftime('%d.%m.%Y %H:%M')}")
                if apt.description:
                    print(f"     📝 {apt.description}")
                if hasattr(apt, 'location') and apt.location:
                    print(f"     📍 {apt.location}")
                if hasattr(apt, 'tags') and apt.tags:
                    print(f"     🏷️ {', '.join(apt.tags)}")
                print()
                
        except Exception as e:
            print(f"❌ Error retrieving appointments: {e}")
        
        print()
        
        # Test 5: Format test for Telegram
        print("5️⃣ Testing Telegram formatting...")
        
        if created_appointments:
            appointment, _ = created_appointments[0]
            formatted = appointment.format_for_telegram(settings.timezone)
            print("Sample Telegram message:")
            print("-" * 30)
            print(formatted)
            print("-" * 30)
        
        print()
        print("🎉 All tests completed successfully!")
        print()
        print("Next steps:")
        print("- Start the bot with: make run-local")
        print("- Test with Telegram: /add morgen 14:00 Test-Meeting")
        print("- Check your Notion database for new entries")
        
        return True
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False


async def cleanup_test_data():
    """Optional: Clean up test data (archives test appointments)."""
    print("\n🧹 Cleaning up test data...")
    
    try:
        settings = Settings()
        notion_service = NotionService(settings)
        
        # Get recent appointments
        appointments = await notion_service.get_appointments(limit=10)
        
        # Find test appointments (those created in last hour)
        now = datetime.now(pytz.timezone(settings.timezone))
        recent_cutoff = now - timedelta(hours=1)
        
        test_appointments = [
            apt for apt in appointments 
            if apt.created_at.replace(tzinfo=pytz.timezone(settings.timezone)) > recent_cutoff
            and apt.title in ["Team Meeting", "Zahnarzttermin", "Projektpräsentation"]
        ]
        
        if not test_appointments:
            print("No test appointments found to clean up.")
            return
        
        print(f"Found {len(test_appointments)} test appointments to clean up:")
        for apt in test_appointments:
            print(f"  - {apt.title}")
        
        response = input("\nDo you want to archive these test appointments? (y/N): ")
        
        if response.lower() == 'y':
            for apt in test_appointments:
                if apt.notion_page_id:
                    await notion_service.delete_appointment(apt.notion_page_id)
                    print(f"  ✅ Archived: {apt.title}")
            print("Cleanup completed!")
        else:
            print("Cleanup skipped.")
            
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")


if __name__ == "__main__":
    print("Notion Connection Test")
    print("=" * 50)
    
    # Check if .env exists
    env_file = os.path.join(os.path.dirname(__file__), '..', '.env')
    if not os.path.exists(env_file):
        print("❌ .env file not found!")
        print("Please copy .env.example to .env and fill in your API keys.")
        sys.exit(1)
    
    # Run connection test
    success = asyncio.run(test_notion_connection())
    
    if success:
        # Ask if user wants to clean up
        print("\n" + "=" * 50)
        cleanup_response = input("Do you want to clean up the test data? (y/N): ")
        if cleanup_response.lower() == 'y':
            asyncio.run(cleanup_test_data())
    
    sys.exit(0 if success else 1)