#!/usr/bin/env python3
"""Umfangreiche Tests für die neue Memo-Funktionalität."""

import asyncio
import sys
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import test modules
from config.user_config import UserConfigManager, UserConfig
from src.models.memo import Memo
from src.services.memo_service import MemoService
from src.services.ai_assistant_service import AIAssistantService
from src.handlers.memo_handler import MemoHandler
from src.handlers.enhanced_appointment_handler import EnhancedAppointmentHandler

# Test status tracking
class TestResults:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failures = []

    def record_test(self, test_name: str, success: bool, error: str = None):
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {test_name}")
        else:
            self.tests_failed += 1
            self.failures.append(f"{test_name}: {error}")
            print(f"❌ {test_name}: {error}")

    def print_summary(self):
        print(f"\n{'='*60}")
        print(f"📊 TEST ZUSAMMENFASSUNG")
        print(f"{'='*60}")
        print(f"Gesamt: {self.tests_run}")
        print(f"✅ Erfolgreich: {self.tests_passed}")
        print(f"❌ Fehlgeschlagen: {self.tests_failed}")
        print(f"📈 Erfolgsrate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if self.failures:
            print(f"\n🔍 FEHLGESCHLAGENE TESTS:")
            for failure in self.failures:
                print(f"  • {failure}")


async def test_memo_database_connection():
    """Test 1: Memo-Datenbank-Verbindung"""
    print(f"\n🔍 TEST 1: MEMO-DATENBANK-VERBINDUNG")
    print(f"{'='*50}")
    
    results = TestResults()
    
    # Load user config
    try:
        config_manager = UserConfigManager()
        user_config = config_manager.get_user_config(6091255402)  # User mit Memo-DB
        
        if not user_config:
            results.record_test("UserConfig laden", False, "User nicht gefunden")
            return results
        
        results.record_test("UserConfig laden", True)
        print(f"📋 User: {user_config.telegram_username}")
        print(f"🔑 API Key: {user_config.notion_api_key[:10]}...")
        print(f"📝 Memo DB ID: {user_config.memo_database_id}")
        
    except Exception as e:
        results.record_test("UserConfig laden", False, str(e))
        return results

    # Test MemoService initialization
    try:
        memo_service = MemoService.from_user_config(user_config)
        results.record_test("MemoService initialisieren", True)
    except Exception as e:
        results.record_test("MemoService initialisieren", False, str(e))
        return results

    # Test database connection
    try:
        connection_ok = await memo_service.test_connection()
        results.record_test("Datenbank-Verbindung", connection_ok, 
                          "Verbindung fehlgeschlagen" if not connection_ok else None)
    except Exception as e:
        results.record_test("Datenbank-Verbindung", False, str(e))

    # Test getting existing memos
    try:
        memos = await memo_service.get_recent_memos(limit=5)
        results.record_test("Bestehende Memos abrufen", True)
        print(f"📊 Gefundene Memos: {len(memos)}")
        
        for i, memo in enumerate(memos[:3], 1):
            print(f"  {i}. {memo.aufgabe} (Status: {memo.status})")
            
    except Exception as e:
        results.record_test("Bestehende Memos abrufen", False, str(e))

    return results


async def test_ai_memo_extraction():
    """Test 2: AI-Memo-Extraktion"""
    print(f"\n🤖 TEST 2: AI-MEMO-EXTRAKTION") 
    print(f"{'='*50}")
    
    results = TestResults()
    
    # Initialize AI service
    try:
        ai_service = AIAssistantService()
        if not ai_service.is_available():
            results.record_test("AI-Service verfügbar", False, "OpenAI API Key fehlt")
            return results
        
        results.record_test("AI-Service initialisieren", True)
    except Exception as e:
        results.record_test("AI-Service initialisieren", False, str(e))
        return results

    # Test cases for memo extraction
    test_cases = [
        {
            "text": "Präsentation vorbereiten bis Freitag",
            "expected_fields": ["aufgabe", "faelligkeitsdatum"]
        },
        {
            "text": "Einkaufsliste erstellen: Milch, Brot, Butter",
            "expected_fields": ["aufgabe", "notizen"]
        },
        {
            "text": "Website Projekt: Client Feedback einholen",
            "expected_fields": ["aufgabe", "projekt"]
        },
        {
            "text": "Arbeitsbereich: Meeting notes zusammenfassen",
            "expected_fields": ["aufgabe", "bereich"]
        },
        {
            "text": "Zahnarzttermin buchen für nächste Woche",
            "expected_fields": ["aufgabe"]
        }
    ]

    for i, test_case in enumerate(test_cases, 1):
        try:
            print(f"\n📝 Test Fall {i}: '{test_case['text']}'")
            
            # Extract memo data
            memo_data = await ai_service.extract_memo_from_text(test_case['text'])
            
            if not memo_data:
                results.record_test(f"AI-Extraktion Fall {i}", False, "Keine Extraktion")
                continue
            
            # Validate memo data
            validated_data = await ai_service.validate_memo_data(memo_data)
            
            # Check required field
            if not validated_data.get('aufgabe'):
                results.record_test(f"AI-Extraktion Fall {i}", False, "Aufgabe fehlt")
                continue
            
            results.record_test(f"AI-Extraktion Fall {i}", True)
            print(f"  ✓ Aufgabe: {validated_data['aufgabe']}")
            
            # Check expected fields
            for field in test_case['expected_fields']:
                if field in validated_data and validated_data[field]:
                    print(f"  ✓ {field}: {validated_data[field]}")
                    
        except Exception as e:
            results.record_test(f"AI-Extraktion Fall {i}", False, str(e))

    return results


async def test_memo_model_and_service():
    """Test 3: Memo-Model und Service-Operationen"""
    print(f"\n📋 TEST 3: MEMO-MODEL UND SERVICE")
    print(f"{'='*50}")
    
    results = TestResults()
    
    # Load user config
    try:
        config_manager = UserConfigManager()
        user_config = config_manager.get_user_config(6091255402)
        memo_service = MemoService.from_user_config(user_config)
    except Exception as e:
        results.record_test("Setup", False, str(e))
        return results

    # Test Memo model creation
    try:
        test_memo = Memo(
            aufgabe="TEST: Memo-Funktionalität testen",
            status="Nicht begonnen",
            faelligkeitsdatum=datetime.now(timezone.utc) + timedelta(days=1),
            bereich="Test",
            projekt="Telegram Bot",
            notizen="Automatischer Test der Memo-Funktionalität"
        )
        results.record_test("Memo-Model erstellen", True)
        print(f"📝 Memo erstellt: {test_memo.aufgabe}")
    except Exception as e:
        results.record_test("Memo-Model erstellen", False, str(e))
        return results

    # Test Notion properties generation
    try:
        properties = test_memo.to_notion_properties()
        required_fields = ["Aufgabe", "Status"]
        
        for field in required_fields:
            if field not in properties:
                raise ValueError(f"Pflichtfeld {field} fehlt")
        
        results.record_test("Notion-Properties generieren", True)
        print(f"✓ Properties generiert: {list(properties.keys())}")
    except Exception as e:
        results.record_test("Notion-Properties generieren", False, str(e))

    # Test memo creation in Notion
    try:
        page_id = await memo_service.create_memo(test_memo)
        test_memo.notion_page_id = page_id
        results.record_test("Memo in Notion erstellen", True)
        print(f"✓ Notion Page ID: {page_id}")
    except Exception as e:
        results.record_test("Memo in Notion erstellen", False, str(e))
        return results

    # Test memo retrieval
    try:
        recent_memos = await memo_service.get_recent_memos(limit=5)
        test_memo_found = any(memo.notion_page_id == page_id for memo in recent_memos)
        results.record_test("Memo abrufen", test_memo_found, "Erstelltes Memo nicht gefunden" if not test_memo_found else None)
    except Exception as e:
        results.record_test("Memo abrufen", False, str(e))

    # Test status update
    try:
        await memo_service.update_memo_status(page_id, "In Arbeit")
        results.record_test("Status aktualisieren", True)
    except Exception as e:
        results.record_test("Status aktualisieren", False, str(e))

    # Cleanup: Delete test memo
    try:
        await memo_service.delete_memo(page_id)
        results.record_test("Test-Memo löschen", True)
        print("🧹 Test-Memo gelöscht")
    except Exception as e:
        results.record_test("Test-Memo löschen", False, str(e))

    return results


async def test_user_config_migration():
    """Test 4: UserConfig-Migration und Services"""
    print(f"\n⚙️ TEST 4: USERCONFIG-MIGRATION UND SERVICES")
    print(f"{'='*50}")
    
    results = TestResults()
    
    # Load user configs
    try:
        config_manager = UserConfigManager()
        all_users = config_manager.get_all_users()
        results.record_test("UserConfig Manager laden", True)
        print(f"👥 Gefundene User: {len(all_users)}")
    except Exception as e:
        results.record_test("UserConfig Manager laden", False, str(e))
        return results

    # Test each user configuration
    for user_id, user_config in all_users.items():
        print(f"\n👤 User: {user_config.telegram_username} ({user_id})")
        
        # Check new unified structure
        try:
            # Should have single notion_api_key
            if not user_config.notion_api_key:
                results.record_test(f"User {user_id}: API Key", False, "notion_api_key fehlt")
                continue
                
            # Should NOT have old separate keys
            if hasattr(user_config, 'shared_notion_api_key') and user_config.shared_notion_api_key:
                results.record_test(f"User {user_id}: Migration", False, "Alte shared_notion_api_key noch vorhanden")
                continue
                
            if hasattr(user_config, 'business_notion_api_key') and user_config.business_notion_api_key:
                results.record_test(f"User {user_id}: Migration", False, "Alte business_notion_api_key noch vorhanden")
                continue
                
            results.record_test(f"User {user_id}: Struktur-Migration", True)
            
            # Test memo database if configured
            if user_config.memo_database_id:
                try:
                    memo_service = MemoService.from_user_config(user_config)
                    connection_ok = await memo_service.test_connection()
                    results.record_test(f"User {user_id}: Memo-DB Verbindung", connection_ok,
                                      "Verbindung fehlgeschlagen" if not connection_ok else None)
                except Exception as e:
                    results.record_test(f"User {user_id}: Memo-DB Verbindung", False, str(e))
            else:
                print(f"  ⚠️ Keine Memo-Datenbank konfiguriert")
                
        except Exception as e:
            results.record_test(f"User {user_id}: Konfiguration", False, str(e))

    return results


async def test_appointment_handler_integration():
    """Test 5: Integration mit EnhancedAppointmentHandler"""
    print(f"\n🔗 TEST 5: APPOINTMENT-HANDLER INTEGRATION")
    print(f"{'='*50}")
    
    results = TestResults()
    
    try:
        config_manager = UserConfigManager()
        user_config = config_manager.get_user_config(6091255402)
        
        # Test EnhancedAppointmentHandler with memo support
        handler = EnhancedAppointmentHandler(user_config)
        results.record_test("EnhancedAppointmentHandler initialisieren", True)
        
        # Check if memo_handler is initialized
        if hasattr(handler, 'memo_handler') and handler.memo_handler:
            results.record_test("MemoHandler Integration", True)
            print(f"✓ MemoHandler verfügbar: {type(handler.memo_handler).__name__}")
            
            # Test memo service availability
            if handler.memo_handler.is_memo_service_available():
                results.record_test("MemoService Verfügbarkeit", True)
            else:
                results.record_test("MemoService Verfügbarkeit", False, "MemoService nicht verfügbar")
        else:
            results.record_test("MemoHandler Integration", False, "MemoHandler nicht initialisiert")
            
    except Exception as e:
        results.record_test("EnhancedAppointmentHandler initialisieren", False, str(e))

    return results


async def main():
    """Haupttest-Funktion"""
    print(f"🚀 UMFANGREICHE TESTS: TELEGRAM NOTION MEMO BOT")
    print(f"{'='*60}")
    print(f"📅 Testdatum: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    all_results = []
    
    # Test 1: Memo-Datenbank-Verbindung
    results1 = await test_memo_database_connection()
    all_results.append(results1)
    
    # Test 2: AI-Memo-Extraktion
    results2 = await test_ai_memo_extraction()
    all_results.append(results2)
    
    # Test 3: Memo-Model und Service
    results3 = await test_memo_model_and_service()
    all_results.append(results3)
    
    # Test 4: UserConfig-Migration
    results4 = await test_user_config_migration()
    all_results.append(results4)
    
    # Test 5: Handler Integration
    results5 = await test_appointment_handler_integration()
    all_results.append(results5)
    
    # Gesamtergebnis
    total_tests = sum(r.tests_run for r in all_results)
    total_passed = sum(r.tests_passed for r in all_results)
    total_failed = sum(r.tests_failed for r in all_results)
    
    print(f"\n🎯 GESAMTERGEBNIS")
    print(f"{'='*60}")
    print(f"📊 Tests insgesamt: {total_tests}")
    print(f"✅ Erfolgreich: {total_passed}")
    print(f"❌ Fehlgeschlagen: {total_failed}")
    print(f"📈 Gesamt-Erfolgsrate: {(total_passed/total_tests*100):.1f}%")
    
    if total_failed > 0:
        print(f"\n⚠️ WICHTIGE FEHLER:")
        for i, results in enumerate(all_results, 1):
            if results.failures:
                print(f"\nTest {i} Fehler:")
                for failure in results.failures:
                    print(f"  • {failure}")
    
    # Empfehlungen
    print(f"\n💡 EMPFEHLUNGEN:")
    if total_failed == 0:
        print("✅ Alle Tests bestanden! Das System ist bereit für den Produktionseinsatz.")
    elif total_failed < 3:
        print("⚠️ Wenige Fehler gefunden. Überprüfen Sie die spezifischen Probleme.")
    else:
        print("❌ Mehrere kritische Fehler. System benötigt Fehlerbehebung vor Deployment.")
    
    return total_failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)