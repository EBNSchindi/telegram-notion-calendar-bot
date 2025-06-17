#!/usr/bin/env python3
"""Ad-hoc test script for immediate email processing."""
import sys
import os
import asyncio
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.business_calendar_sync import create_sync_manager_from_env
from src.services.notion_service import NotionService
from config.user_config import UserConfigManager
from dotenv import load_dotenv

load_dotenv()

async def test_email_processing_now():
    """Test email processing immediately without waiting for timer."""
    print("🔍 Starting immediate email processing test...")
    print(f"⏰ Started at: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 50)
    
    try:
        # Create sync manager
        sync_manager = create_sync_manager_from_env()
        print(f"✅ Sync manager created")
        
        # Load user configurations
        user_config_manager = UserConfigManager()
        user_count = 0
        
        for user_config in user_config_manager._users.values():
            if user_config.telegram_user_id != 0:  # Skip default user
                sync_manager.add_user(user_config)
                user_count += 1
        
        print(f"✅ Added {user_count} users to sync manager")
        
        if user_count == 0:
            print("❌ No users configured for email sync")
            return
        
        # Process emails for each user immediately
        print("\n📧 Starting immediate email processing...")
        
        for user_id, business_sync in sync_manager.user_syncs.items():
            print(f"\n👤 Processing emails for user {user_id}:")
            print("-" * 30)
            
            try:
                # Run single sync cycle immediately
                await business_sync.sync_business_calendars()
                
                # Show statistics
                stats = business_sync.get_sync_stats()
                print(f"📊 Results for user {user_id}:")
                print(f"   📧 Emails processed: {stats['emails_processed']}")
                print(f"   ➕ Events created: {stats['events_created']}")
                print(f"   📝 Events updated: {stats['events_updated']}")
                print(f"   🗑️ Events deleted: {stats['events_deleted']}")
                print(f"   ❌ Errors: {stats['errors']}")
                
                if stats['emails_processed'] > 0:
                    print(f"   ✅ Successfully processed emails!")
                elif stats['errors'] > 0:
                    print(f"   ⚠️ Encountered {stats['errors']} errors")
                else:
                    print(f"   📭 No new emails found")
                    
            except Exception as e:
                print(f"   ❌ Error processing emails for user {user_id}: {e}")
        
        print("\n" + "=" * 50)
        print(f"⏰ Completed at: {datetime.now().strftime('%H:%M:%S')}")
        print("🎯 Ad-hoc email processing test finished!")
        
        # Check Notion databases for verification
        print("\n🔍 Verifying results in Notion databases...")
        await verify_notion_databases(sync_manager)
        
    except Exception as e:
        print(f"❌ Fatal error in email processing test: {e}")
        import traceback
        traceback.print_exc()

async def verify_notion_databases(sync_manager):
    """Verify results in Notion databases for all users."""
    try:
        user_config_manager = UserConfigManager()
        
        for user_config in user_config_manager._users.values():
            if user_config.telegram_user_id == 0:  # Skip default user
                continue
                
            print(f"\n👤 Checking Notion databases for user {user_config.telegram_username}:")
            await verify_single_user_notion(user_config)
            
    except Exception as e:
        print(f"❌ Error verifying Notion databases: {e}")

async def verify_single_user_notion(user_config):
    """Verify Notion database for a single user."""
    try:
        # Check business database
        business_db_id = os.getenv('BUSINESS_NOTION_DATABASE_ID')
        if business_db_id:
            print(f"📊 Business Database ({business_db_id[:8]}...):")
            await check_notion_database(
                user_config.shared_notion_api_key or user_config.notion_api_key, 
                business_db_id,
                "business"
            )
        
        # Check private database
        print(f"📊 Private Database ({user_config.notion_database_id[:8]}...):")
        await check_notion_database(
            user_config.notion_api_key, 
            user_config.notion_database_id,
            "private"
        )
        
        # Check shared database if configured
        if user_config.shared_notion_database_id:
            print(f"📊 Shared Database ({user_config.shared_notion_database_id[:8]}...):")
            await check_notion_database(
                user_config.shared_notion_api_key, 
                user_config.shared_notion_database_id,
                "shared"
            )
    
    except Exception as e:
        print(f"❌ Error verifying user's Notion databases: {e}")

async def check_notion_database(api_key, database_id, db_type):
    """Check a specific Notion database for recent entries."""
    try:
        notion_service = NotionService(notion_api_key=api_key, database_id=database_id)
        
        # Get recent appointments (last 24 hours)
        from datetime import datetime, timedelta, timezone
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        
        appointments = await notion_service.get_appointments()
        
        # Filter recent appointments
        recent_appointments = []
        business_appointments = []
        
        for appointment in appointments:
            # Check if appointment is recent (created in last 24 hours)
            if appointment.created_at:
                # Ensure both datetimes are timezone-aware for comparison
                created_at = appointment.created_at
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)
                
                if created_at >= yesterday:
                    recent_appointments.append(appointment)
            
            # Check if it's a business appointment (has OutlookID)
            if appointment.outlook_id:
                business_appointments.append(appointment)
        
        print(f"   📅 Total appointments: {len(appointments)}")
        print(f"   🕐 Recent (24h): {len(recent_appointments)}")
        print(f"   📧 Business events: {len(business_appointments)}")
        
        # Show recent business appointments
        if recent_appointments:
            print(f"   📋 Recent appointments:")
            for appointment in recent_appointments[-3:]:  # Show last 3
                outlook_info = f" [Outlook: {appointment.outlook_id[:8]}...]" if appointment.outlook_id else ""
                organizer_info = f" (by {appointment.organizer})" if appointment.organizer else ""
                print(f"      • {appointment.title}{organizer_info}{outlook_info}")
        
        if business_appointments:
            print(f"   📧 Latest business events:")
            for appointment in business_appointments[-2:]:  # Show last 2 business events
                print(f"      • {appointment.title} (Outlook: {appointment.outlook_id[:8]}...)")
                print(f"        📅 {appointment.date.strftime('%Y-%m-%d %H:%M')}")
                if appointment.organizer:
                    print(f"        👤 {appointment.organizer}")
        
        print(f"   ✅ {db_type.title()} database accessible")
        
    except Exception as e:
        if "should be a valid uuid" in str(e):
            print(f"   ❌ Invalid database ID format for {db_type} database")
        elif "object does not exist" in str(e):
            print(f"   ❌ {db_type.title()} database not found or no access")
        else:
            print(f"   ❌ Error accessing {db_type} database: {str(e)[:100]}...")

async def test_single_user_sync():
    """Test email processing for first configured user only."""
    print("🔍 Testing single user email sync...")
    
    try:
        # Create sync manager
        sync_manager = create_sync_manager_from_env()
        
        # Load user configurations
        user_config_manager = UserConfigManager()
        
        # Get first real user
        test_user = None
        for user_config in user_config_manager._users.values():
            if user_config.telegram_user_id != 0:  # Skip default user
                test_user = user_config
                break
        
        if not test_user:
            print("❌ No test user found")
            return
        
        print(f"👤 Testing with user: {test_user.telegram_username} (ID: {test_user.telegram_user_id})")
        
        # Add user to sync manager
        sync_manager.add_user(test_user)
        
        if not sync_manager.user_syncs:
            print("❌ No sync configured for user")
            return
        
        # Get the sync instance
        business_sync = list(sync_manager.user_syncs.values())[0]
        
        print("📧 Checking for new emails...")
        
        # Run immediate sync
        await business_sync.sync_business_calendars()
        
        # Show detailed results
        stats = business_sync.get_sync_stats()
        print(f"\n📊 Detailed Results:")
        print(f"   📧 Emails processed: {stats['emails_processed']}")
        print(f"   ➕ Events created: {stats['events_created']}")
        print(f"   📝 Events updated: {stats['events_updated']}")
        print(f"   🗑️ Events deleted: {stats['events_deleted']}")
        print(f"   ❌ Errors: {stats['errors']}")
        print(f"   🕐 Last sync: {stats['last_sync']}")
        
        if stats['emails_processed'] > 0:
            print("\n🎉 SUCCESS: New emails were processed!")
        elif stats['errors'] > 0:
            print(f"\n⚠️ WARNING: {stats['errors']} errors occurred during processing")
        else:
            print("\n📭 INFO: No new emails found")
        
        # Verify results in Notion database
        print("\n🔍 Verifying results in Notion database...")
        await verify_single_user_notion(test_user)
            
    except Exception as e:
        print(f"❌ Error in single user sync test: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main function with options."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test email processing immediately')
    parser.add_argument('--single', action='store_true', 
                       help='Test only first configured user')
    parser.add_argument('--all', action='store_true', 
                       help='Test all configured users (default)')
    
    args = parser.parse_args()
    
    if args.single:
        asyncio.run(test_single_user_sync())
    else:
        asyncio.run(test_email_processing_now())

if __name__ == "__main__":
    main()