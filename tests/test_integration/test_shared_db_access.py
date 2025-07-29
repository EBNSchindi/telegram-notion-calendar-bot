#!/usr/bin/env python3
"""Test shared database access for both users."""

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.user_config import UserConfigManager
from src.services.combined_appointment_service import CombinedAppointmentService

async def test_shared_database_access():
    """Test shared database access for all users."""
    print("🧪 Testing Shared Database Access")
    print("=" * 50)
    
    # Load user configurations
    config_manager = UserConfigManager()
    users = config_manager.get_all_users()
    
    for user_id, user_config in users.items():
        print(f"\n👤 User {user_id} ({user_config.telegram_username}):")
        print("-" * 40)
        
        # Show configuration details
        print(f"Is Owner: {user_config.is_owner}")
        print(f"Has teamspace_owner_api_key: {bool(user_config.teamspace_owner_api_key)}")
        print(f"Shared DB ID: {user_config.shared_notion_database_id}")
        
        # Determine which API key will be used
        shared_api_key = config_manager.get_shared_database_api_key(user_config)
        if user_config.is_owner or not user_config.teamspace_owner_api_key:
            print("Using: Own API key")
        else:
            print("Using: Teamspace owner's API key")
        
        # Create combined service
        combined_service = CombinedAppointmentService(user_config, config_manager)
        
        # Check if shared service was created
        print(f"Shared service created: {combined_service.shared_service is not None}")
        print(f"has_shared_database(): {combined_service.has_shared_database()}")
        
        # Test connections
        try:
            private_ok, shared_ok = await combined_service.test_connections()
            print(f"\nConnection test results:")
            print(f"Private DB: {'✅' if private_ok else '❌'}")
            
            if shared_ok is None:
                print(f"Shared DB: ⚠️ Not configured")
            else:
                print(f"Shared DB: {'✅' if shared_ok else '❌'}")
            
            # If shared DB exists but test failed, try to get more info
            if combined_service.shared_service and not shared_ok:
                print("\nTrying direct shared service test...")
                try:
                    appointments = await combined_service.shared_service.get_appointments(limit=1)
                    print(f"Direct test: ✅ Success (found {len(appointments)} appointments)")
                except Exception as e:
                    print(f"Direct test: ❌ Failed - {str(e)}")
                    
        except Exception as e:
            print(f"Error testing connections: {e}")

if __name__ == "__main__":
    asyncio.run(test_shared_database_access())