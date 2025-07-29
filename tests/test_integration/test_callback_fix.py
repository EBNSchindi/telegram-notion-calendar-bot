#!/usr/bin/env python3
"""Test the fixed callback functionality."""

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
from src.handlers.enhanced_appointment_handler import EnhancedAppointmentHandler

async def test_callback_fix():
    """Test the fixed today_tomorrow_appointments_callback."""
    print("🧪 Testing Fixed Callback Function")
    print("=" * 50)
    
    # Load user configurations
    config_manager = UserConfigManager()
    user_config = config_manager.get_user_config(906939299)  # Test with Meli
    
    if not user_config:
        print("❌ User configuration not found")
        return
    
    print(f"Testing with user: {user_config.telegram_username}")
    
    try:
        # Create handler
        handler = EnhancedAppointmentHandler(user_config, config_manager)
        
        # Get timezone
        timezone = pytz.timezone(user_config.timezone or 'Europe/Berlin')
        today = datetime.now(timezone).date()
        tomorrow = (datetime.now(timezone) + timedelta(days=1)).date()
        
        print(f"\nTimezone: {timezone}")
        print(f"Today: {today.strftime('%d.%m.%Y')}")
        print(f"Tomorrow: {tomorrow.strftime('%d.%m.%Y')}")
        
        # Simulate the callback function logic
        print("\n📅 Simulating today_tomorrow_appointments_callback:")
        
        # Get appointments
        today_appointments = await handler.combined_service.get_today_appointments()
        tomorrow_appointments = await handler.combined_service.get_tomorrow_appointments()
        
        print(f"\nToday appointments found: {len(today_appointments)}")
        print(f"Tomorrow appointments found: {len(tomorrow_appointments)}")
        
        # Build message like the callback does
        message = "📅 *Termine für Heute & Morgen*\n\n"
        
        # Today's appointments
        if today_appointments:
            message += f"*Heute ({today.strftime('%d.%m.%Y')}):*\n"
            for i, apt_src in enumerate(today_appointments, 1):
                apt = apt_src.appointment
                source_icon = "🌐" if apt_src.is_shared else "👤"
                local_date = apt.date.astimezone(timezone) if apt.date.tzinfo else timezone.localize(apt.date)
                message += f"{i}. {source_icon} *{local_date.strftime('%H:%M')}* - {apt.title}"
                if apt.location:
                    message += f" (📍 {apt.location})"
                message += "\n"
            message += "\n"
        else:
            message += f"*Heute ({today.strftime('%d.%m.%Y')}):*\nKeine Termine! 🎉\n\n"
        
        # Tomorrow's appointments
        if tomorrow_appointments:
            message += f"*Morgen ({tomorrow.strftime('%d.%m.%Y')}):*\n"
            for i, apt_src in enumerate(tomorrow_appointments, 1):
                apt = apt_src.appointment
                source_icon = "🌐" if apt_src.is_shared else "👤"
                local_date = apt.date.astimezone(timezone) if apt.date.tzinfo else timezone.localize(apt.date)
                message += f"{i}. {source_icon} *{local_date.strftime('%H:%M')}* - {apt.title}"
                if apt.location:
                    message += f" (📍 {apt.location})"
                message += "\n"
        else:
            message += f"*Morgen ({tomorrow.strftime('%d.%m.%Y')}):*\nKeine Termine! 🎉"
        
        print("\n✅ Generated message successfully:")
        print("-" * 40)
        print(message)
        print("-" * 40)
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_callback_fix())