# 🔧 Notion Database Setup für Partner Sync Service

## ⚠️ WICHTIG: Erforderliche Database-Anpassungen

Der Partner Sync Service benötigt **neue Properties** in Ihren Notion-Datenbanken. **Ohne diese Properties wird der Service nicht funktionieren!**

## 📋 Properties die hinzugefügt werden müssen

### 1. **Private Database(s)** - Für jeden User

#### Bestehende Properties (sollten bereits vorhanden sein):
- ✅ `Name` (Title) - Terminname
- ✅ `Datum` (Date) - Termindatum  
- ✅ `Beschreibung` (Rich Text) - Beschreibung
- ⚠️ `Ort` (Rich Text) - Location (möglicherweise neu)
- ⚠️ `Tags` (Rich Text) - Tags (möglicherweise neu)
- ⚠️ `OutlookID` (Rich Text) - Business Calendar ID (möglicherweise neu)
- ⚠️ `Organizer` (Rich Text) - Event Organizer (möglicherweise neu)

#### **🆕 NEUE Properties für Partner Sync (MÜSSEN hinzugefügt werden):**

1. **PartnerRelevant**
   - Type: `Checkbox`
   - Name: `PartnerRelevant` (genau so schreiben!)
   - Beschreibung: "Ist dieser Termin für Partner relevant?"

2. **SyncedToSharedId** 
   - Type: `Rich Text`
   - Name: `SyncedToSharedId` (genau so schreiben!)
   - Beschreibung: "ID des synchronisierten Termins in der gemeinsamen Datenbank"

### 2. **Shared Database** - Gemeinsame Datenbank

#### Alle Properties aus Private Database PLUS:

3. **SourcePrivateId**
   - Type: `Rich Text` 
   - Name: `SourcePrivateId` (genau so schreiben!)
   - Beschreibung: "ID des ursprünglichen Termins aus der privaten Datenbank"

4. **SourceUserId**
   - Type: `Number`
   - Name: `SourceUserId` (genau so schreiben!)
   - Beschreibung: "Telegram User ID des Erstellers"

## 🛠️ Schritt-für-Schritt Anleitung

### Schritt 1: Private Database(s) erweitern

Für **jeden User** in `users_config.json`:

1. **Öffnen Sie die private Notion-Datenbank**
   - Database ID finden Sie in `users_config.json` unter `notion_database_id`

2. **Klicken Sie oben rechts auf "•••" → "Edit database"**

3. **Fügen Sie folgende Properties hinzu:**

   **Property 1: PartnerRelevant**
   ```
   + Add Property
   Property name: PartnerRelevant
   Property type: Checkbox
   → Create
   ```

   **Property 2: SyncedToSharedId**
   ```
   + Add Property  
   Property name: SyncedToSharedId
   Property type: Text
   → Create
   ```

4. **Optional: Fehlende Standard-Properties hinzufügen (falls nicht vorhanden):**
   
   **Ort (Location):**
   ```
   + Add Property
   Property name: Ort
   Property type: Text
   → Create
   ```

   **Tags:**
   ```
   + Add Property
   Property name: Tags
   Property type: Text  
   → Create
   ```

### Schritt 2: Shared Database erweitern

1. **Öffnen Sie die gemeinsame Notion-Datenbank**
   - Database ID finden Sie in `users_config.json` unter `shared_notion_database_id`

2. **Stellen Sie sicher, dass ALLE Properties aus Private Database vorhanden sind:**
   - ✅ `Name` (Title)
   - ✅ `Datum` (Date)
   - ✅ `Beschreibung` (Text)
   - ✅ `Ort` (Text)
   - ✅ `Tags` (Text) 
   - ✅ `OutlookID` (Text)
   - ✅ `Organizer` (Text)
   - ✅ `PartnerRelevant` (Checkbox)
   - ✅ `SyncedToSharedId` (Text)

3. **Fügen Sie die zusätzlichen Tracking-Properties hinzu:**

   **Property 3: SourcePrivateId**
   ```
   + Add Property
   Property name: SourcePrivateId  
   Property type: Text
   → Create
   ```

   **Property 4: SourceUserId**
   ```
   + Add Property
   Property name: SourceUserId
   Property type: Number
   → Create  
   ```

## ✅ Verification Checklist

### Private Database Properties:
- [ ] `Name` (Title) ✅
- [ ] `Datum` (Date) ✅  
- [ ] `Beschreibung` (Text) ✅
- [ ] `Ort` (Text) ⚠️ 
- [ ] `Tags` (Text) ⚠️
- [ ] `OutlookID` (Text) ⚠️
- [ ] `Organizer` (Text) ⚠️
- [ ] `PartnerRelevant` (Checkbox) 🆕 **MUSS hinzugefügt werden**
- [ ] `SyncedToSharedId` (Text) 🆕 **MUSS hinzugefügt werden**

### Shared Database Properties:
- [ ] Alle Properties aus Private Database ✅
- [ ] `SourcePrivateId` (Text) 🆕 **MUSS hinzugefügt werden**
- [ ] `SourceUserId` (Number) 🆕 **MUSS hinzugefügt werden**

## 🧪 Test der Database-Konfiguration

Erstellen Sie dieses Test-Script und führen Sie es aus:

```python
# test_notion_properties.py
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.services.notion_service import NotionService
from src.models.appointment import Appointment  
from config.user_config import UserConfigManager
from datetime import datetime, timedelta

async def test_notion_properties():
    print("🧪 Testing Notion Database Properties...")
    
    # Load user config
    user_config_manager = UserConfigManager()
    users = user_config_manager.get_valid_users()
    
    if not users:
        print("❌ No valid users found in users_config.json")
        return False
    
    user_id, user_config = next(iter(users.items()))
    print(f"Testing with user: {user_id}")
    
    # Test private database
    private_service = NotionService(
        notion_api_key=user_config.notion_api_key,
        database_id=user_config.notion_database_id
    )
    
    # Create test appointment with all new fields
    test_appointment = Appointment(
        title="Partner Sync Test",
        date=datetime.now() + timedelta(days=1),
        description="Test für Partner Sync Properties",
        location="Test Location",
        partner_relevant=True,
        synced_to_shared_id="test_shared_id_123"
    )
    
    try:
        # Test creating appointment  
        page_id = await private_service.create_appointment(test_appointment)
        print(f"✅ Created test appointment: {page_id}")
        
        # Test reading it back
        appointments = await private_service.get_appointments(limit=1)
        if appointments:
            apt = appointments[0]
            print(f"✅ Read appointment back: {apt.title}")
            print(f"✅ PartnerRelevant: {apt.partner_relevant}")
            print(f"✅ SyncedToSharedId: {apt.synced_to_shared_id}")
        
        # Test shared database if configured
        if user_config.shared_notion_database_id:
            shared_service = NotionService(
                notion_api_key=user_config.notion_api_key,
                database_id=user_config.shared_notion_database_id
            )
            
            # Test appointment for shared DB
            shared_test = Appointment(
                title="Shared DB Test",
                date=datetime.now() + timedelta(days=1),
                description="Test für Shared DB Properties",
                partner_relevant=True,
                source_private_id="private_123",
                source_user_id=user_id
            )
            
            shared_page_id = await shared_service.create_appointment(shared_test)
            print(f"✅ Created shared test appointment: {shared_page_id}")
        
        print("🎉 All database properties working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing properties: {e}")
        print("\n🔧 Mögliche Ursachen:")
        print("- Properties fehlen in Notion Database")
        print("- Property-Namen stimmen nicht überein (Case-sensitive!)")
        print("- Notion Integration hat keinen Zugriff")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_notion_properties())
    sys.exit(0 if success else 1)
```

## 🚨 Häufige Fehler

### "Property 'PartnerRelevant' does not exist"
```
Ursache: Property wurde nicht hinzugefügt oder falsch benannt
Lösung: Property mit genau diesem Namen hinzufügen: PartnerRelevant
```

### "Property 'SyncedToSharedId' does not exist"  
```
Ursache: Property wurde nicht hinzugefügt
Lösung: Rich Text Property hinzufügen: SyncedToSharedId
```

### "Property 'SourceUserId' does not exist"
```
Ursache: Property in Shared Database fehlt
Lösung: Number Property hinzufügen: SourceUserId  
```

### "Invalid property type"
```
Ursache: Falscher Property-Type verwendet
Lösung: 
- PartnerRelevant → Checkbox
- SyncedToSharedId → Text/Rich Text
- SourcePrivateId → Text/Rich Text  
- SourceUserId → Number
```

## 📝 Property-Namen Referenz

**⚠️ GENAU diese Namen verwenden (Case-sensitive!):**

| Property | Type | Database | Zweck |
|----------|------|----------|-------|
| `PartnerRelevant` | Checkbox | Private + Shared | Sync-Flag |
| `SyncedToSharedId` | Text | Private | Link zu Shared DB |
| `SourcePrivateId` | Text | Shared | Link zu Private DB |
| `SourceUserId` | Number | Shared | Ersteller-ID |

## ✅ Nach der Konfiguration

1. **Testen Sie mit dem Test-Script oben**
2. **Starten Sie den Bot neu**
3. **Erstellen Sie einen Testtermin mit Partner-Relevanz**
4. **Prüfen Sie, ob er in der Shared Database erscheint**

---

**Wichtig:** Erst nach der korrekten Property-Konfiguration wird der Partner Sync Service funktionieren!