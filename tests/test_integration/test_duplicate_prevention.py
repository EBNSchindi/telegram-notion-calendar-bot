#!/usr/bin/env python3
"""Test script for duplicate prevention logic."""

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
from src.services.partner_sync_service import PartnerSyncService
from src.models.appointment import Appointment
from src.utils.duplicate_checker import DuplicateChecker


async def test_duplicate_checker():
    """Test the DuplicateChecker utility."""
    print("🧪 Testing DuplicateChecker Utility")
    print("=" * 50)
    
    # Create test appointments
    tz = pytz.timezone('Europe/Berlin')
    now = datetime.now(tz)
    
    apt1 = Appointment(
        title="Team Meeting",
        date=now + timedelta(hours=2),
        location="Conference Room A",
        description="Weekly team sync"
    )
    
    # Same appointment with slight variations
    apt2 = Appointment(
        title="team meeting",  # Different case
        date=now + timedelta(hours=2, seconds=30),  # Different seconds
        location="Conference Room A",
        description="Different description"  # Different description
    )
    
    apt3 = Appointment(
        title="Team Meeting",
        date=now + timedelta(hours=3),  # Different time
        location="Conference Room A",
        description="Weekly team sync"
    )
    
    # Test create_appointment_key
    key1 = DuplicateChecker.create_appointment_key(apt1)
    key2 = DuplicateChecker.create_appointment_key(apt2)
    key3 = DuplicateChecker.create_appointment_key(apt3)
    
    print("\n🔑 Appointment Keys:")
    print(f"Apt1: {key1}")
    print(f"Apt2: {key2}")
    print(f"Apt3: {key3}")
    
    assert key1 == key2, "Keys should match for same appointment (ignoring case and seconds)"
    assert key1 != key3, "Keys should differ for different times"
    print("✅ Key generation working correctly")
    
    # Test is_same_appointment
    same = DuplicateChecker.is_same_appointment(apt1, apt2)
    different = DuplicateChecker.is_same_appointment(apt1, apt3)
    
    print(f"\n🔍 Comparison Results:")
    print(f"Apt1 vs Apt2 (should be same): {same}")
    print(f"Apt1 vs Apt3 (should be different): {different}")
    
    assert same == True, "Should detect as same appointment"
    assert different == False, "Should detect as different appointment"
    print("✅ Appointment comparison working correctly")
    
    # Test check_for_duplicates
    appointments = [apt1, apt2, apt3]
    duplicates = DuplicateChecker.check_for_duplicates(appointments)
    
    print(f"\n📊 Duplicate Detection:")
    print(f"Found {len(duplicates)} duplicate groups")
    for key, dups in duplicates.items():
        print(f"   - {key}: {len(dups)} duplicates")
    
    assert len(duplicates) == 1, "Should find one duplicate group"
    print("✅ Duplicate detection working correctly")


async def test_combined_service_deduplication():
    """Test that CombinedAppointmentService properly deduplicates."""
    print("\n\n🧪 Testing CombinedAppointmentService Deduplication")
    print("=" * 50)
    
    config_manager = UserConfigManager()
    user_config = config_manager.get_user_config(6091255402)
    
    if not user_config:
        print("❌ Cannot load user config")
        return
    
    # Create service
    combined_service = CombinedAppointmentService(user_config, config_manager)
    
    # Get appointments
    print("\n📅 Fetching appointments from both databases...")
    appointments = await combined_service.get_all_appointments(limit=100)
    
    print(f"Total appointments retrieved: {len(appointments)}")
    
    # Check for duplicates
    all_apts = [apt_src.appointment for apt_src in appointments]
    duplicates = DuplicateChecker.check_for_duplicates(all_apts)
    
    if duplicates:
        print(f"\n⚠️ Found {len(duplicates)} duplicate groups after deduplication:")
        for key, dups in duplicates.items():
            print(f"   - {key}: {len(dups)} copies")
        print("❌ Deduplication may not be working properly")
    else:
        print("\n✅ No duplicates found - deduplication working correctly!")
    
    # Show source distribution
    private_count = sum(1 for apt_src in appointments if not apt_src.is_shared)
    shared_count = sum(1 for apt_src in appointments if apt_src.is_shared)
    
    print(f"\n📊 Source Distribution:")
    print(f"   - Private database: {private_count}")
    print(f"   - Shared database: {shared_count}")


async def test_partner_sync_duplicate_prevention():
    """Test that partner sync doesn't create duplicates."""
    print("\n\n🧪 Testing Partner Sync Duplicate Prevention")
    print("=" * 50)
    
    config_manager = UserConfigManager()
    sync_service = PartnerSyncService(config_manager)
    
    # Get Meli's config
    user_config = config_manager.get_user_config(906939299)
    
    if not user_config or not user_config.shared_notion_database_id:
        print("❌ Cannot test - user not configured for shared database")
        return
    
    print(f"\n👤 Testing for user: {user_config.telegram_username}")
    
    # Run sync twice to ensure no duplicates are created
    print("\n🔄 First sync run...")
    result1 = await sync_service.sync_partner_relevant_appointments(user_config)
    
    if result1["success"]:
        stats1 = result1["stats"]
        print(f"✅ First sync completed:")
        print(f"   - Created: {stats1['created']}")
        print(f"   - Updated: {stats1['updated']}")
        print(f"   - Errors: {stats1['errors']}")
    
    # Small delay
    await asyncio.sleep(2)
    
    print("\n🔄 Second sync run (should not create duplicates)...")
    result2 = await sync_service.sync_partner_relevant_appointments(user_config)
    
    if result2["success"]:
        stats2 = result2["stats"]
        print(f"✅ Second sync completed:")
        print(f"   - Created: {stats2['created']} (should be 0)")
        print(f"   - Updated: {stats2['updated']}")
        print(f"   - Errors: {stats2['errors']}")
        
        if stats2['created'] > 0:
            print("⚠️ WARNING: Second sync created new appointments - possible duplicate issue!")
        else:
            print("✅ No duplicates created on second sync!")


async def main():
    """Run all tests."""
    print("🚀 Running Duplicate Prevention Tests")
    print("=" * 70)
    
    # Test 1: DuplicateChecker utility
    await test_duplicate_checker()
    
    # Test 2: Combined service deduplication
    await test_combined_service_deduplication()
    
    # Test 3: Partner sync duplicate prevention
    await test_partner_sync_duplicate_prevention()
    
    print("\n\n✅ All tests completed!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())