#!/usr/bin/env python3
"""Test today and tomorrow appointments functionality."""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv
import pytz

# Load environment variables
load_dotenv()

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.user_config import UserConfigManager
from src.services.combined_appointment_service import CombinedAppointmentService
from src.handlers.enhanced_appointment_handler import EnhancedAppointmentHandler

async def test_today_tomorrow_functionality():
    """Test the today/tomorrow appointments retrieval."""
    print("🧪 Testing Today & Tomorrow Appointments")
    print("=" * 50)
    
    # Load user configurations
    config_manager = UserConfigManager()
    users = config_manager.get_all_users()
    
    for user_id, user_config in users.items():
        print(f"\n\n👤 Testing User {user_id} ({user_config.telegram_username}):")
        print("-" * 40)
        
        try:
            # Create services
            combined_service = CombinedAppointmentService(user_config, config_manager)
            handler = EnhancedAppointmentHandler(user_config, config_manager)
            
            # Get timezone
            timezone = pytz.timezone(user_config.timezone or 'Europe/Berlin')
            today = datetime.now(timezone).date()
            tomorrow = (datetime.now(timezone) + timedelta(days=1)).date()
            
            print(f"\nTimezone: {timezone}")
            print(f"Today: {today.strftime('%d.%m.%Y')}")
            print(f"Tomorrow: {tomorrow.strftime('%d.%m.%Y')}")
            
            # Test get_today_appointments
            print("\n📅 Testing get_today_appointments():")
            try:
                today_appointments = await combined_service.get_today_appointments()
                print(f"   Found {len(today_appointments)} appointments for today")
                
                for i, apt_src in enumerate(today_appointments[:3], 1):
                    apt = apt_src.appointment
                    source = "🌐 Shared" if apt_src.is_shared else "👤 Private"
                    time_str = apt.date.astimezone(timezone).strftime('%H:%M')
                    print(f"   {i}. {source} {time_str} - {apt.title}")
                    
            except Exception as e:
                print(f"   ❌ Error: {str(e)}")
                import traceback
                traceback.print_exc()
            
            # Test get_tomorrow_appointments
            print("\n📅 Testing get_tomorrow_appointments():")
            try:
                tomorrow_appointments = await combined_service.get_tomorrow_appointments()
                print(f"   Found {len(tomorrow_appointments)} appointments for tomorrow")
                
                for i, apt_src in enumerate(tomorrow_appointments[:3], 1):
                    apt = apt_src.appointment
                    source = "🌐 Shared" if apt_src.is_shared else "👤 Private"
                    time_str = apt.date.astimezone(timezone).strftime('%H:%M')
                    print(f"   {i}. {source} {time_str} - {apt.title}")
                    
            except Exception as e:
                print(f"   ❌ Error: {str(e)}")
                import traceback
                traceback.print_exc()
            
            # Test the callback function logic (simulate)
            print("\n🔧 Testing callback function logic:")
            try:
                # Get all appointments first to debug
                all_appointments = await combined_service.get_all_appointments()
                print(f"   Total appointments in database: {len(all_appointments)}")
                
                # Check date filtering
                today_count = 0
                tomorrow_count = 0
                future_count = 0
                past_count = 0
                
                for apt_src in all_appointments:
                    apt_date = apt_src.appointment.date.astimezone(timezone).date()
                    if apt_date == today:
                        today_count += 1
                    elif apt_date == tomorrow:
                        tomorrow_count += 1
                    elif apt_date > tomorrow:
                        future_count += 1
                    else:
                        past_count += 1
                
                print(f"   Date distribution:")
                print(f"   - Past: {past_count}")
                print(f"   - Today: {today_count}")
                print(f"   - Tomorrow: {tomorrow_count}")
                print(f"   - Future: {future_count}")
                
                # Show first few appointments with dates
                print(f"\n   First 5 appointments:")
                for i, apt_src in enumerate(all_appointments[:5], 1):
                    apt = apt_src.appointment
                    apt_date = apt.date.astimezone(timezone)
                    source = "🌐" if apt_src.is_shared else "👤"
                    print(f"   {i}. {source} {apt_date.strftime('%d.%m.%Y %H:%M')} - {apt.title}")
                    
            except Exception as e:
                print(f"   ❌ Error in callback logic: {str(e)}")
                import traceback
                traceback.print_exc()
                
        except Exception as e:
            print(f"\n❌ General error for user {user_id}: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_today_tomorrow_functionality())