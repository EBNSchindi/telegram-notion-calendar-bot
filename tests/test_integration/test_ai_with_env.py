#!/usr/bin/env python3
"""Test AI functionality with proper environment loading."""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.services.ai_assistant_service import AIAssistantService

async def test_ai_functionality():
    """Test AI assistant service with loaded environment."""
    print("\n🤖 Testing AI Functionality with Environment...")
    print("=" * 50)
    
    # Check for OpenAI API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment variables!")
        return False
    else:
        print(f"✅ OPENAI_API_KEY found: sk-...{api_key[-4:]}")
    
    # Initialize AI service
    ai_service = AIAssistantService()
    if not ai_service.client:
        print("❌ AI client initialization failed!")
        return False
    else:
        print("✅ AI client initialized successfully")
    
    # Test AI extraction
    try:
        test_cases = [
            "Morgen um 15:30 Uhr Meeting mit Max im Büro",
            "Arzttermin nächsten Dienstag 10 Uhr",
            "Kauf Milch und Brot bis Freitag",
            "Projekt ABC bis Ende des Monats fertigstellen"
        ]
        
        for test_text in test_cases:
            print(f"\n📝 Testing: '{test_text}'")
            
            # Test appointment extraction
            apt_result = await ai_service.extract_appointment_info(test_text)
            if apt_result and apt_result.get('confidence', 0) > 0.5:
                print(f"   📅 Appointment detected (confidence: {apt_result.get('confidence', 0):.2f})")
                print(f"      Title: {apt_result.get('title')}")
                print(f"      Date: {apt_result.get('date')}")
                print(f"      Time: {apt_result.get('time')}")
                if apt_result.get('location'):
                    print(f"      Location: {apt_result.get('location')}")
            
            # Test memo extraction
            memo_result = await ai_service.extract_memo_info(test_text)
            if memo_result and memo_result.get('confidence', 0) > 0.5:
                print(f"   📝 Memo detected (confidence: {memo_result.get('confidence', 0):.2f})")
                print(f"      Task: {memo_result.get('task')}")
                if memo_result.get('due_date'):
                    print(f"      Due: {memo_result.get('due_date')}")
                if memo_result.get('area'):
                    print(f"      Area: {memo_result.get('area')}")
            
            await asyncio.sleep(1)  # Rate limiting
        
        print("\n✅ AI functionality test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error during AI test: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_ai_functionality())