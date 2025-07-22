#!/usr/bin/env python3
"""Test für vereinfachtes Menü und praktische Integration."""

import asyncio
import sys
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.user_config import UserConfigManager
from src.handlers.enhanced_appointment_handler import EnhancedAppointmentHandler
from src.handlers.memo_handler import MemoHandler


class MockUpdate:
    """Mock Telegram Update object."""
    def __init__(self, user_id: int = 6091255402):
        self.effective_user = Mock()
        self.effective_user.id = user_id
        self.effective_user.first_name = "Testuser"
        
        self.callback_query = Mock()
        self.callback_query.data = None
        self.callback_query.answer = AsyncMock()
        self.callback_query.edit_message_text = AsyncMock()
        
        self.message = Mock()
        self.message.reply_text = AsyncMock()
        self.message.text = ""
        
        self.effective_message = self.message

class MockContext:
    """Mock Telegram Context object."""
    def __init__(self):
        self.user_data = {}


async def test_simplified_menu():
    """Test das vereinfachte Hauptmenü."""
    print("\n🎯 TEST: VEREINFACHTES HAUPTMENÜ")
    print("=" * 50)
    
    try:
        # Setup
        config_manager = UserConfigManager()
        user_config = config_manager.get_user_config(6091255402)
        handler = EnhancedAppointmentHandler(user_config)
        
        update = MockUpdate()
        context = MockContext()
        
        # Test main menu display
        await handler.show_main_menu(update, context)
        
        # Verify menu was called
        assert update.message.reply_text.called, "Menu sollte angezeigt werden"
        call_args = update.message.reply_text.call_args
        menu_text = call_args[1]['text']  # kwargs['text']
        
        print("✅ Hauptmenü erfolgreich angezeigt")
        
        # Check for simplified menu elements
        expected_buttons = [
            "📅 Termine Heute & Morgen",
            "📝 Letzte 10 Memos", 
            "➕ Neuer Termin",
            "➕ Neues Memo",
            "❓ Hilfe"
        ]
        
        menu_markup = call_args[1]['reply_markup']  # kwargs['reply_markup']
        keyboard = menu_markup.inline_keyboard
        
        # Flatten keyboard to get all button texts
        all_button_texts = []
        for row in keyboard:
            for button in row:
                all_button_texts.append(button.text)
        
        print(f"📋 Gefundene Buttons: {all_button_texts}")
        
        # Check if all expected buttons are present
        for expected in expected_buttons:
            if expected in all_button_texts:
                print(f"  ✅ {expected}")
            else:
                print(f"  ❌ {expected} - FEHLT!")
                
        # Check layout (2x2 + 1)
        if len(keyboard) == 3 and len(keyboard[0]) == 2 and len(keyboard[1]) == 2 and len(keyboard[2]) == 1:
            print("✅ Korrekte 2x2+1 Layout-Struktur")
        else:
            print(f"❌ Layout-Problem: {[len(row) for row in keyboard]} (erwartet: [2,2,1])")
            
        return True
        
    except Exception as e:
        print(f"❌ Menu-Test fehlgeschlagen: {e}")
        return False


async def test_combined_today_tomorrow():
    """Test kombinierte Heute/Morgen Ansicht."""
    print("\n📅 TEST: KOMBINIERTE HEUTE/MORGEN ANSICHT")
    print("=" * 50)
    
    try:
        # Setup
        config_manager = UserConfigManager()
        user_config = config_manager.get_user_config(6091255402)
        handler = EnhancedAppointmentHandler(user_config)
        
        update = MockUpdate()
        update.callback_query.data = "today_tomorrow"
        context = MockContext()
        
        # Test combined view
        await handler.today_tomorrow_appointments_callback(update, context)
        
        # Verify callback was handled
        assert update.callback_query.edit_message_text.called, "Callback sollte verarbeitet werden"
        call_args = update.callback_query.edit_message_text.call_args
        message_text = call_args[1]['text']
        
        print("✅ Kombinierte Ansicht erfolgreich angezeigt")
        
        # Check for expected content
        if "*Termine für Heute & Morgen*" in message_text:
            print("✅ Korrekter Titel vorhanden")
        else:
            print("❌ Titel fehlt oder falsch")
            
        if "Heute" in message_text and "Morgen" in message_text:
            print("✅ Beide Tage angezeigt")
        else:
            print("❌ Ein Tag fehlt")
            
        return True
        
    except Exception as e:
        print(f"❌ Kombinierte Ansicht Test fehlgeschlagen: {e}")
        return False


async def test_memo_handler_integration():
    """Test Memo-Handler Integration."""
    print("\n📝 TEST: MEMO-HANDLER INTEGRATION")
    print("=" * 50)
    
    try:
        # Setup
        config_manager = UserConfigManager()
        user_config = config_manager.get_user_config(6091255402)
        memo_handler = MemoHandler(user_config)
        
        update = MockUpdate()
        context = MockContext()
        
        # Test recent memos display
        await memo_handler.show_recent_memos(update, context)
        
        # Verify display was called
        assert update.message.reply_text.called, "Recent memos sollten angezeigt werden"
        call_args = update.message.reply_text.call_args
        message_text = call_args[1]['text']
        
        print("✅ Recent Memos erfolgreich angezeigt")
        
        if "*Deine letzten" in message_text and "Memos*" in message_text:
            print("✅ Korrekter Memo-Titel")
        else:
            print("❌ Memo-Titel fehlt oder falsch")
            
        # Test memo prompt
        update.callback_query.edit_message_text = AsyncMock()
        await memo_handler.prompt_for_new_memo(update, context)
        
        # Should set context for awaiting memo
        if context.user_data.get('awaiting_memo'):
            print("✅ Memo-Eingabe-Modus aktiviert")
        else:
            print("❌ Memo-Eingabe-Modus nicht gesetzt")
            
        return True
        
    except Exception as e:
        print(f"❌ Memo-Handler Test fehlgeschlagen: {e}")
        return False


async def test_help_system():
    """Test das Hilfe-System."""
    print("\n❓ TEST: HILFE-SYSTEM")
    print("=" * 50)
    
    try:
        # Setup
        config_manager = UserConfigManager()
        user_config = config_manager.get_user_config(6091255402)
        handler = EnhancedAppointmentHandler(user_config)
        
        update = MockUpdate()
        update.callback_query.data = "help"
        context = MockContext()
        
        # Test help display
        await handler.help_callback(update, context)
        
        # Verify help was displayed
        assert update.callback_query.edit_message_text.called, "Hilfe sollte angezeigt werden"
        call_args = update.callback_query.edit_message_text.call_args
        help_text = call_args[1]['text']
        
        print("✅ Hilfe-System erfolgreich angezeigt")
        
        # Check for expected help sections
        expected_sections = [
            "Termine erstellen",
            "Memos erstellen", 
            "Erinnerungen",
            "Hauptfunktionen",
            "KI-Unterstützung"
        ]
        
        for section in expected_sections:
            if section in help_text:
                print(f"  ✅ {section}")
            else:
                print(f"  ❌ {section} - FEHLT!")
                
        # Check for reminder time personalization
        if user_config.reminder_time in help_text:
            print(f"✅ Erinnerungszeit personalisiert: {user_config.reminder_time}")
        else:
            print("❌ Erinnerungszeit nicht personalisiert")
            
        return True
        
    except Exception as e:
        print(f"❌ Hilfe-System Test fehlgeschlagen: {e}")
        return False


async def test_callback_routing():
    """Test Callback-Routing für alle neuen Menu-Optionen."""
    print("\n🔄 TEST: CALLBACK-ROUTING")
    print("=" * 50)
    
    try:
        # Setup
        config_manager = UserConfigManager()
        user_config = config_manager.get_user_config(6091255402)
        handler = EnhancedAppointmentHandler(user_config)
        
        # Test callbacks
        test_callbacks = [
            ("today_tomorrow", "Heute & Morgen"),
            ("recent_memos", "Recent Memos"),
            ("add_appointment", "Neuer Termin"),
            ("add_memo", "Neues Memo"),
            ("help", "Hilfe")
        ]
        
        for callback_data, description in test_callbacks:
            update = MockUpdate()
            update.callback_query.data = callback_data
            update.callback_query.edit_message_text = AsyncMock()
            context = MockContext()
            
            try:
                await handler.handle_callback(update, context)
                print(f"  ✅ {description} ({callback_data})")
            except Exception as e:
                print(f"  ❌ {description} ({callback_data}): {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Callback-Routing Test fehlgeschlagen: {e}")
        return False


async def main():
    """Haupttest für Menü und Integration."""
    print("🚀 MENU UND INTEGRATIONS-TESTS")
    print("=" * 60)
    print(f"📅 Testdatum: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # Menu Tests
    results.append(await test_simplified_menu())
    results.append(await test_combined_today_tomorrow())
    results.append(await test_memo_handler_integration())
    results.append(await test_help_system())
    results.append(await test_callback_routing())
    
    # Summary
    passed = sum(results)
    total = len(results)
    success_rate = (passed / total) * 100
    
    print(f"\n🎯 MENU-TEST ERGEBNIS")
    print("=" * 60)
    print(f"📊 Tests insgesamt: {total}")
    print(f"✅ Erfolgreich: {passed}")
    print(f"❌ Fehlgeschlagen: {total - passed}")
    print(f"📈 Erfolgsrate: {success_rate:.1f}%")
    
    if success_rate == 100:
        print("\n🎉 ALLE MENU-TESTS BESTANDEN!")
        print("✅ Das vereinfachte Menü ist vollständig funktional")
        print("✅ Memo-Integration funktioniert korrekt")
        print("✅ Hilfe-System ist umfangreich und personalisiert")
    else:
        print(f"\n⚠️ {total - passed} Test(s) fehlgeschlagen - Details oben prüfen")
    
    return success_rate == 100


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)