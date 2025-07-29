#!/usr/bin/env python3
"""Comprehensive test for appointment retrieval functionality."""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.user_config import UserConfigManager
from src.services.combined_appointment_service import CombinedAppointmentService
from src.services.notion_service import NotionService
from src.handlers.enhanced_appointment_handler import EnhancedAppointmentHandler

async def test_appointment_retrieval():
    """Test appointment retrieval for all users."""
    print("🧪 Comprehensive Appointment Retrieval Test")
    print("=" * 50)
    
    # Load user configurations
    config_manager = UserConfigManager()
    users = config_manager.get_all_users()
    
    for user_id, user_config in users.items():
        print(f"\n\n👤 Testing User {user_id} ({user_config.telegram_username}):")
        print("=" * 50)
        
        # 1. Test Direct NotionService Access
        print("\n📌 1. Testing Direct NotionService Access:")
        print("-" * 40)
        
        # Private database
        try:
            print(f"\n🔍 Private Database ({user_config.notion_database_id}):")
            private_service = NotionService(
                notion_api_key=user_config.notion_api_key,
                database_id=user_config.notion_database_id
            )
            
            # Test connection
            connection_ok = await private_service.test_connection()
            print(f"   Connection test: {'✅' if connection_ok else '❌'}")
            
            # Get appointments
            appointments = await private_service.get_appointments(limit=5)
            print(f"   Appointments found: {len(appointments) if appointments else 0}")
            
            if appointments:
                for i, apt in enumerate(appointments[:3], 1):
                    print(f"   {i}. {apt.title} - {apt.date.strftime('%d.%m.%Y %H:%M')}")
                    
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
        
        # Shared database
        if user_config.shared_notion_database_id:
            try:
                print(f"\n🔍 Shared Database ({user_config.shared_notion_database_id}):")
                
                # Determine API key
                shared_api_key = config_manager.get_shared_database_api_key(user_config)
                print(f"   Using API key: {'Own' if shared_api_key == user_config.notion_api_key else 'Owner'}")
                
                shared_service = NotionService(
                    notion_api_key=shared_api_key,
                    database_id=user_config.shared_notion_database_id
                )
                
                # Test connection
                connection_ok = await shared_service.test_connection()
                print(f"   Connection test: {'✅' if connection_ok else '❌'}")
                
                # Get appointments
                appointments = await shared_service.get_appointments(limit=5)
                print(f"   Appointments found: {len(appointments) if appointments else 0}")
                
                if appointments:
                    for i, apt in enumerate(appointments[:3], 1):
                        print(f"   {i}. {apt.title} - {apt.date.strftime('%d.%m.%Y %H:%M')}")
                        
            except Exception as e:
                print(f"   ❌ Error: {str(e)}")
        
        # 2. Test CombinedAppointmentService
        print("\n\n📌 2. Testing CombinedAppointmentService:")
        print("-" * 40)
        
        try:
            combined_service = CombinedAppointmentService(user_config, config_manager)
            
            # Test all appointments
            print("\n🔍 All Appointments:")
            all_appointments = await combined_service.get_all_appointments()
            print(f"   Total found: {len(all_appointments)}")
            
            private_count = sum(1 for apt in all_appointments if not apt.is_shared)
            shared_count = sum(1 for apt in all_appointments if apt.is_shared)
            print(f"   Private: {private_count}, Shared: {shared_count}")
            
            # Test today's appointments
            print("\n🔍 Today's Appointments:")
            today_appointments = await combined_service.get_today_appointments()
            print(f"   Found: {len(today_appointments)}")
            
            # Test tomorrow's appointments
            print("\n🔍 Tomorrow's Appointments:")
            tomorrow_appointments = await combined_service.get_tomorrow_appointments()
            print(f"   Found: {len(tomorrow_appointments)}")
            
            # Test upcoming appointments
            print("\n🔍 Upcoming Appointments:")
            upcoming_appointments = await combined_service.get_upcoming_appointments()
            print(f"   Found: {len(upcoming_appointments)}")
            
        except Exception as e:
            print(f"   ❌ Error in CombinedAppointmentService: {str(e)}")
            import traceback
            traceback.print_exc()
        
        # 3. Test EnhancedAppointmentHandler
        print("\n\n📌 3. Testing EnhancedAppointmentHandler:")
        print("-" * 40)
        
        try:
            handler = EnhancedAppointmentHandler(user_config, config_manager)
            
            # Test format for telegram
            print("\n🔍 Formatting for Telegram:")
            if all_appointments:
                message = combined_service.format_appointments_for_telegram(
                    all_appointments[:5], 
                    "Test Appointments"
                )
                print("   ✅ Formatting successful")
                print("\n   Preview:")
                print("   " + "\n   ".join(message.split("\n")[:10]))
            else:
                print("   ⚠️ No appointments to format")
                
        except Exception as e:
            print(f"   ❌ Error in EnhancedAppointmentHandler: {str(e)}")
            import traceback
            traceback.print_exc()

async def test_database_structure():
    """Test database structure and fields."""
    print("\n\n🗄️ Testing Database Structure")
    print("=" * 50)
    
    config_manager = UserConfigManager()
    users = config_manager.get_all_users()
    
    for user_id, user_config in users.items():
        print(f"\n👤 User {user_id} ({user_config.telegram_username}):")
        
        try:
            from notion_client import Client
            
            # Test private database
            print(f"\n📁 Private Database Structure:")
            client = Client(auth=user_config.notion_api_key)
            
            db_info = client.databases.retrieve(database_id=user_config.notion_database_id)
            properties = db_info.get('properties', {})
            
            print("   Properties found:")
            for prop_name, prop_info in properties.items():
                prop_type = prop_info.get('type', 'unknown')
                print(f"   - {prop_name}: {prop_type}")
            
            # Check required fields
            required_fields = ['Name', 'Datum']
            missing_fields = [f for f in required_fields if f not in properties]
            if missing_fields:
                print(f"   ⚠️ Missing required fields: {missing_fields}")
            else:
                print("   ✅ All required fields present")
                
        except Exception as e:
            print(f"   ❌ Error checking database structure: {str(e)}")

async def main():
    """Run all tests."""
    await test_appointment_retrieval()
    await test_database_structure()
    
    print("\n\n✅ Testing completed!")
    print("\n💡 Next steps:")
    print("1. Check for any ❌ errors above")
    print("2. Verify database field names match expected values")
    print("3. Ensure 'Datum' property exists and is of type 'date'")
    print("4. Check if appointments have valid date values")

if __name__ == "__main__":
    asyncio.run(main())