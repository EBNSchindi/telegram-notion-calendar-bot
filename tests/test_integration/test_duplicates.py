#!/usr/bin/env python3
"""Test for duplicate appointments issue."""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.user_config import UserConfigManager
from src.services.combined_appointment_service import CombinedAppointmentService
from src.services.notion_service import NotionService

async def test_duplicate_appointments():
    """Test and analyze duplicate appointments."""
    print("🔍 Testing Duplicate Appointments Issue")
    print("=" * 50)
    
    # Load user configurations
    config_manager = UserConfigManager()
    
    # Test for both users
    for user_id in [906939299, 6091255402]:  # Meli and default
        user_config = config_manager.get_user_config(user_id)
        if not user_config:
            continue
            
        print(f"\n\n👤 User: {user_config.telegram_username} ({user_id})")
        print("-" * 40)
        
        # Create services
        combined_service = CombinedAppointmentService(user_config, config_manager)
        
        # Get today's appointments
        today_appointments = await combined_service.get_today_appointments()
        
        print(f"\nToday's appointments: {len(today_appointments)}")
        
        # Analyze appointments
        appointment_details = []
        for apt_src in today_appointments:
            apt = apt_src.appointment
            details = {
                'title': apt.title,
                'date': apt.date.strftime('%d.%m.%Y %H:%M'),
                'source': 'Shared' if apt_src.is_shared else 'Private',
                'page_id': apt.notion_page_id,
                'partner_relevant': apt.partner_relevant,
                'synced_to_shared_id': apt.synced_to_shared_id
            }
            appointment_details.append(details)
            
        # Print details
        for i, details in enumerate(appointment_details, 1):
            print(f"\n{i}. {details['title']} - {details['date']}")
            print(f"   Source: {details['source']}")
            print(f"   Page ID: {details['page_id']}")
            print(f"   Partner Relevant: {details['partner_relevant']}")
            print(f"   Synced ID: {details['synced_to_shared_id']}")
        
        # Check for duplicates
        print("\n🔍 Duplicate Analysis:")
        
        # Group by title and time
        title_time_groups = {}
        for apt_src in today_appointments:
            apt = apt_src.appointment
            key = f"{apt.title}_{apt.date.strftime('%H:%M')}"
            if key not in title_time_groups:
                title_time_groups[key] = []
            title_time_groups[key].append(apt_src)
        
        # Find duplicates
        duplicates_found = False
        for key, appointments in title_time_groups.items():
            if len(appointments) > 1:
                duplicates_found = True
                print(f"\n⚠️ Duplicate found: {key}")
                for apt_src in appointments:
                    apt = apt_src.appointment
                    print(f"   - {'Shared' if apt_src.is_shared else 'Private'} DB: {apt.notion_page_id}")
        
        if not duplicates_found:
            print("   ✅ No duplicates found")
        
        # Check if private appointments are synced to shared
        print("\n🔄 Partner Sync Analysis:")
        private_appointments = [apt_src for apt_src in today_appointments if not apt_src.is_shared]
        for apt_src in private_appointments:
            apt = apt_src.appointment
            if apt.partner_relevant:
                print(f"\n   {apt.title}:")
                print(f"   - Partner relevant: ✓")
                print(f"   - Synced to shared ID: {apt.synced_to_shared_id or 'None'}")
                
                # Check if there's a corresponding shared appointment
                shared_matches = [
                    s for s in today_appointments 
                    if s.is_shared and s.appointment.title == apt.title 
                    and s.appointment.date == apt.date
                ]
                print(f"   - Found in shared DB: {'✓' if shared_matches else '✗'} ({len(shared_matches)} copies)")

async def check_shared_database_directly():
    """Check shared database directly for duplicates."""
    print("\n\n📊 Direct Shared Database Check")
    print("=" * 50)
    
    config_manager = UserConfigManager()
    user_config = config_manager.get_user_config(6091255402)  # Use owner
    
    if not user_config or not user_config.shared_notion_database_id:
        print("❌ Cannot check shared database")
        return
    
    # Direct access to shared database
    shared_service = NotionService(
        notion_api_key=user_config.notion_api_key,
        database_id=user_config.shared_notion_database_id
    )
    
    # Get all appointments
    all_appointments = await shared_service.get_appointments(limit=100)
    
    print(f"Total appointments in shared DB: {len(all_appointments)}")
    
    # Group by title and date
    duplicates = {}
    for apt in all_appointments:
        key = f"{apt.title}_{apt.date.strftime('%d.%m.%Y %H:%M')}"
        if key not in duplicates:
            duplicates[key] = []
        duplicates[key].append(apt)
    
    # Show duplicates
    print("\nDuplicates in shared database:")
    for key, apts in duplicates.items():
        if len(apts) > 1:
            print(f"\n⚠️ {key}: {len(apts)} copies")
            for apt in apts:
                print(f"   - Page ID: {apt.notion_page_id}")

if __name__ == "__main__":
    asyncio.run(test_duplicate_appointments())
    asyncio.run(check_shared_database_directly())