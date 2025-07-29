#!/usr/bin/env python3
"""Test script for AI functionality and database connections."""

import asyncio
import os
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.services.ai_assistant_service import AIAssistantService
from src.services.notion_service import NotionService
from config.user_config import UserConfigManager

async def test_ai_functionality():
    """Test AI assistant service."""
    print("\n🤖 Testing AI Functionality...")
    print("=" * 50)
    
    # Check for OpenAI API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment variables!")
        print("   AI functionality will NOT work.")
        return False
    else:
        print("✅ OPENAI_API_KEY found in environment")
    
    # Initialize AI service
    ai_service = AIAssistantService()
    if not ai_service.client:
        print("❌ AI client initialization failed!")
        return False
    else:
        print("✅ AI client initialized successfully")
    
    # Test AI extraction
    try:
        test_text = "Morgen um 15:30 Uhr Meeting mit Max im Büro"
        print(f"\n📝 Testing appointment extraction with: '{test_text}'")
        
        result = await ai_service.extract_appointment_info(test_text)
        
        if result:
            print("✅ AI extraction successful!")
            print(f"   Title: {result.get('title')}")
            print(f"   Date: {result.get('date')}")
            print(f"   Time: {result.get('time')}")
            print(f"   Location: {result.get('location')}")
            print(f"   Confidence: {result.get('confidence', 0):.2f}")
        else:
            print("❌ AI extraction failed!")
    except Exception as e:
        print(f"❌ Error during AI test: {e}")
        return False
    
    return True

async def test_notion_connections():
    """Test Notion database connections for all users."""
    print("\n📊 Testing Notion Database Connections...")
    print("=" * 50)
    
    # Load user configurations
    config_manager = UserConfigManager()
    users = config_manager.get_all_users()
    
    print(f"Found {len(users)} configured users\n")
    
    for user_id, user_config in users.items():
        print(f"\n👤 User {user_id} ({user_config.telegram_username}):")
        print("-" * 40)
        
        # Check API key validity
        if not config_manager.is_valid_notion_key(user_config.notion_api_key):
            print("❌ Invalid Notion API key (placeholder or malformed)")
            continue
        else:
            print("✅ Valid Notion API key format")
        
        # Test private database
        if user_config.notion_database_id:
            print(f"\n📁 Private Database: {user_config.notion_database_id}")
            from config.settings import Settings
            settings = Settings()
            settings.notion_api_key = user_config.notion_api_key
            settings.notion_database_id = user_config.notion_database_id
            notion_service = NotionService(settings)
            try:
                appointments = await notion_service.get_appointments()
                print(f"   ✅ Connected successfully! Found {len(appointments) if appointments else 0} appointments")
            except Exception as e:
                print(f"   ❌ Connection failed: {str(e)}")
        
        # Test shared database
        if user_config.shared_notion_database_id:
            print(f"\n📁 Shared Database: {user_config.shared_notion_database_id}")
            
            # Determine which API key to use
            if user_config.is_owner or not user_config.teamspace_owner_api_key:
                api_key = user_config.notion_api_key
                print("   Using: User's own API key (owner or no teamspace key)")
            else:
                api_key = user_config.teamspace_owner_api_key
                print("   Using: Teamspace owner's API key")
            
            from config.settings import Settings
            settings = Settings()
            settings.notion_api_key = api_key
            settings.notion_database_id = user_config.shared_notion_database_id
            notion_service = NotionService(settings)
            try:
                appointments = await notion_service.get_appointments()
                print(f"   ✅ Connected successfully! Found {len(appointments) if appointments else 0} appointments")
            except Exception as e:
                print(f"   ❌ Connection failed: {str(e)}")
        
        # Test business database
        if user_config.business_notion_database_id:
            print(f"\n📁 Business Database: {user_config.business_notion_database_id}")
            from config.settings import Settings
            settings = Settings()
            settings.notion_api_key = user_config.notion_api_key
            settings.notion_database_id = user_config.business_notion_database_id
            notion_service = NotionService(settings)
            try:
                appointments = await notion_service.get_appointments()
                print(f"   ✅ Connected successfully! Found {len(appointments) if appointments else 0} appointments")
            except Exception as e:
                print(f"   ❌ Connection failed: {str(e)}")
        
        # Test memo database
        if user_config.memo_database_id:
            print(f"\n📁 Memo Database: {user_config.memo_database_id}")
            from config.settings import Settings
            settings = Settings()
            settings.notion_api_key = user_config.notion_api_key
            settings.notion_database_id = user_config.memo_database_id
            notion_service = NotionService(settings)
            try:
                # Memos use different structure, just test connection
                appointments = await notion_service.get_appointments()
                print(f"   ✅ Connected successfully!")
            except Exception as e:
                print(f"   ❌ Connection failed: {str(e)}")

async def main():
    """Run all tests."""
    print("🧪 Starting Telegram-Notion Calendar Bot Tests")
    print("=" * 50)
    
    # Test AI functionality
    ai_works = await test_ai_functionality()
    
    # Test Notion connections
    await test_notion_connections()
    
    print("\n" + "=" * 50)
    print("✅ Testing completed!")
    
    if not ai_works:
        print("\n⚠️  AI functionality is not available. Add OPENAI_API_KEY to .env file to enable it.")

if __name__ == "__main__":
    asyncio.run(main())