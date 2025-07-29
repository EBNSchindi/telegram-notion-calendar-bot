#!/usr/bin/env python3
"""Test specific problematic page."""

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from notion_client import Client
from config.user_config import UserConfigManager

async def test_problematic_page():
    """Test the specific page that's causing parsing errors."""
    print("🔍 Testing Problematic Page")
    print("=" * 50)
    
    page_id = "233fe177-8b4d-80bc-ab69-d4be0da3c528"
    
    # Load user configurations
    config_manager = UserConfigManager()
    user_config = config_manager.get_user_config(906939299)  # Meli
    
    if not user_config:
        print("❌ User configuration not found")
        return
    
    print(f"Testing page ID: {page_id}")
    print(f"User: {user_config.telegram_username}")
    
    try:
        # Create Notion client
        client = Client(auth=user_config.notion_api_key)
        
        # Retrieve the page
        print("\nRetrieving page from Notion...")
        page = client.pages.retrieve(page_id=page_id)
        
        print("✅ Page retrieved successfully")
        
        # Check page structure
        print("\nPage Structure:")
        print(f"- ID: {page.get('id')}")
        print(f"- Archived: {page.get('archived', False)}")
        print(f"- Created: {page.get('created_time')}")
        print(f"- Last edited: {page.get('last_edited_time')}")
        
        # Check properties
        properties = page.get('properties', {})
        print("\nPage Properties:")
        
        for prop_name, prop_data in properties.items():
            prop_type = prop_data.get('type')
            print(f"\n- {prop_name} ({prop_type}):")
            
            # Extract value based on type
            if prop_type == 'title':
                title_content = prop_data.get('title', [])
                if title_content:
                    text = title_content[0].get('plain_text', '') if title_content else ''
                    print(f"  Value: '{text}'")
                else:
                    print(f"  Value: None (empty)")
            
            elif prop_type == 'date':
                date_value = prop_data.get('date')
                print(f"  Value: {date_value}")
                if date_value is None:
                    print("  ⚠️ Date is None - this might cause parsing errors!")
            
            elif prop_type == 'rich_text':
                text_content = prop_data.get('rich_text', [])
                if text_content:
                    text = text_content[0].get('plain_text', '') if text_content else ''
                    print(f"  Value: '{text}'")
                else:
                    print(f"  Value: None (empty)")
            
            elif prop_type == 'checkbox':
                checkbox_value = prop_data.get('checkbox', False)
                print(f"  Value: {checkbox_value}")
            
            elif prop_type == 'multi_select':
                options = prop_data.get('multi_select', [])
                values = [opt.get('name') for opt in options]
                print(f"  Values: {values}")
        
        # Try to parse as appointment
        print("\n\nTrying to parse as Appointment:")
        try:
            from src.models.appointment import Appointment
            appointment = Appointment.from_notion_page(page)
            print("✅ Successfully parsed!")
            print(f"   Title: {appointment.title}")
            print(f"   Date: {appointment.date}")
        except Exception as e:
            print(f"❌ Parsing failed: {str(e)}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"❌ Error retrieving page: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_problematic_page())