# Partner Sync Service Documentation

## 🎯 Übersicht

Der Partner Sync Service umgeht die Notion Plus-Plan-Beschränkungen durch intelligente bidirektionale Synchronisation von Partner-relevanten Terminen zwischen privaten und gemeinsamen Datenbanken.

## ✨ Features

### 🔄 Automatische Synchronisation
- **Sofortiger Sync**: Partner-relevante Termine werden bei Erstellung sofort kopiert
- **Bidirektionale Updates**: Änderungen werden in beide Richtungen synchronisiert  
- **Hintergrund-Sync**: Regelmäßige Synchronisation alle 2 Stunden (konfigurierbar)
- **Cleanup**: Automatisches Entfernen nicht mehr relevanter Termine

### 🛡️ Robuste Implementierung
- **Duplikat-Vermeidung**: Intelligentes Tracking verhindert doppelte Einträge
- **Fehlertoleranz**: Service funktioniert auch bei temporären API-Ausfällen
- **Atomare Updates**: Konsistenz durch transaktionale Operationen
- **Performance-Optimiert**: Effiziente API-Nutzung und Bulk-Operationen

### 📊 Tracking & Monitoring
- **Sync-Status**: Detaillierte Status-Abfrage für jeden User
- **Statistiken**: Anzahl synchronisierter, erstellter und aktualisierter Termine
- **Logging**: Umfassendes Logging aller Sync-Operationen

## 🏗️ Architektur

### Datenfluss

```
┌─────────────────┐    PartnerRelevant=True    ┌──────────────────┐
│ Private Database│ ────────────────────────► │ Shared Database  │
│ (Individual)    │                           │ (Gemeinsam)      │
│                 │ ◄──────────────────────── │                  │
└─────────────────┘    Bidirektional          └──────────────────┘
```

### Tracking-Eigenschaften

#### Private Database Properties
```
Name (Title): Terminname
Datum (Date): Termindatum
Beschreibung (RichText): Beschreibung
Ort (RichText): Ort
PartnerRelevant (Checkbox): Sync-Flag
SyncedToSharedId (RichText): ID in Shared DB
```

#### Shared Database Properties  
```
Name (Title): Terminname (kopiert)
Datum (Date): Termindatum (kopiert)  
Beschreibung (RichText): Beschreibung (kopiert)
Ort (RichText): Ort (kopiert)
PartnerRelevant (Checkbox): Immer True
SourcePrivateId (RichText): Ursprungs-ID
SourceUserId (Number): Telegram User ID
```

## 🚀 Setup & Konfiguration

### Umgebungsvariablen (.env)

```bash
# Partner Sync Konfiguration
PARTNER_SYNC_ENABLED=true
PARTNER_SYNC_INTERVAL_HOURS=2
```

### Notion Database Setup

1. **Private Database** (pro User):
   - Bestehende Properties beibehalten
   - **Neue Properties hinzufügen:**
     - `PartnerRelevant` (Checkbox)
     - `SyncedToSharedId` (Rich Text)

2. **Shared Database** (gemeinsam):
   - Gleiche Properties wie Private Database
   - **Zusätzliche Tracking-Properties:**
     - `SourcePrivateId` (Rich Text)  
     - `SourceUserId` (Number)

### Bot Integration

```python
# Automatische Integration über bot.py
self.partner_sync_service = PartnerSyncService(self.user_config_manager)
await self.partner_sync_service.start_background_sync(interval_hours=2)
```

## 💻 API Referenz

### PartnerSyncService

#### Hauptmethoden

```python
async def sync_partner_relevant_appointments(self, user_config: UserConfig) -> Dict[str, Any]:
    """
    Synchronisiert alle Partner-relevanten Termine für einen User.
    
    Returns:
        {
            "success": bool,
            "stats": {
                "total_processed": int,
                "created": int, 
                "updated": int,
                "errors": int,
                "removed": int
            }
        }
    """
```

```python
async def sync_single_appointment(self, appointment: Appointment, 
                                user_config: UserConfig,
                                force_sync: bool = False) -> bool:
    """
    Synchronisiert einen einzelnen Termin.
    
    Args:
        appointment: Zu synchronisierender Termin
        user_config: User-Konfiguration  
        force_sync: Erzwinge Sync auch wenn bereits synchronisiert
        
    Returns:
        True wenn erfolgreich synchronisiert
    """
```

```python
async def get_sync_status(self, user_config: UserConfig) -> Dict[str, Any]:
    """
    Liefert Sync-Status und Statistiken.
    
    Returns:
        {
            "enabled": bool,
            "running": bool,
            "interval_hours": int,
            "private_partner_relevant": int,
            "shared_synced": int,
            "last_sync": str
        }
    """
```

#### Lifecycle Management

```python
async def start_background_sync(self, interval_hours: int = 2):
    """Startet Hintergrund-Sync mit konfigurierbarem Intervall."""

def stop_background_sync():
    """Stoppt Hintergrund-Sync graceful."""
```

### CombinedAppointmentService Integration

```python
async def create_appointment(self, appointment: Appointment, use_shared: bool = False) -> str:
    """
    Erweitert um automatischen Partner-Sync:
    - Bei PartnerRelevant=True → Sofortiger Sync zur Shared DB
    - Transparent für bestehenden Code
    """
```

## 🔄 Sync-Szenarien

### 1. Neuer Partner-relevanter Termin

```
User erstellt Termin mit PartnerRelevant=True
    ↓
Private DB: Termin gespeichert  
    ↓
Sofortiger Sync ausgelöst
    ↓
Shared DB: Kopie erstellt mit SourcePrivateId/SourceUserId
    ↓
Private DB: SyncedToSharedId gesetzt
```

### 2. Partner-Relevanz ändern (False → True)

```
User ändert PartnerRelevant von False auf True
    ↓
Hintergrund-Sync erkennt Änderung
    ↓
Shared DB: Neue Kopie erstellt
    ↓
Private DB: SyncedToSharedId gesetzt
```

### 3. Partner-Relevanz ändern (True → False)

```
User ändert PartnerRelevant von True auf False
    ↓
Hintergrund-Sync erkennt Änderung
    ↓
Shared DB: Termin gelöscht (über SourcePrivateId)
    ↓
Private DB: SyncedToSharedId gelöscht
```

### 4. Termin-Update

```
User ändert Termin-Details (mit PartnerRelevant=True)
    ↓
Hintergrund-Sync erkennt Änderung
    ↓
Shared DB: Entsprechender Termin aktualisiert
    ↓
Bidirektionale Konsistenz gewährleistet
```

## 📊 Monitoring & Debugging

### Logging

```bash
# Sync-Operationen
[INFO] Partner sync service started (interval: 2h)
[INFO] Automatically synced partner-relevant appointment abc123 to shared database
[INFO] Sync completed for user 123456789: {'created': 2, 'updated': 1, 'removed': 0}

# Fehler-Handling  
[ERROR] Error during sync for user 123456789: Database not found
[WARNING] User 123456789 has no shared database configured
```

### Status-Abfrage (Entwicklung)

```python
# Sync-Status für User abrufen
status = await partner_sync_service.get_sync_status(user_config)
print(f"Sync enabled: {status['enabled']}")
print(f"Partner-relevant appointments: {status['private_partner_relevant']}")
print(f"Synced appointments: {status['shared_synced']}")
```

## 🧪 Testing

### Test-Suite ausführen

```bash
# Alle Tests ausführen
python test_partner_sync.py

# Mit virtual environment
source venv/bin/activate && python test_partner_sync.py
```

### Test-Szenarien

- ✅ Service-Initialisierung
- ✅ Appointment-Model Sync-Felder  
- ✅ Einzeltermin-Synchronisation
- ✅ Sync-Status Abfrage
- ✅ Background-Sync Lifecycle
- ✅ Error-Handling
- ✅ Duplikat-Vermeidung

## 🚨 Troubleshooting

### Häufige Probleme

#### "Database not found"
```
Ursache: Notion API-Key hat keinen Zugriff auf Datenbank
Lösung: Database mit Notion-Integration teilen
```

#### "No shared database configured"  
```
Ursache: shared_notion_database_id nicht gesetzt
Lösung: users_config.json mit Shared DB ID ergänzen
```

#### "Partner sync not working"
```
Ursache: PARTNER_SYNC_ENABLED=false oder Service nicht gestartet  
Lösung: Konfiguration prüfen und Bot neu starten
```

#### "Duplicate appointments"
```
Ursache: Sync-Tracking Properties fehlen in Notion DB
Lösung: SyncedToSharedId, SourcePrivateId, SourceUserId hinzufügen
```

### Debug-Befehle

```python
# Manual Sync auslösen (Entwicklung)
result = await partner_sync_service.sync_partner_relevant_appointments(user_config)
print(f"Sync result: {result}")

# Sync-Status prüfen
status = await partner_sync_service.get_sync_status(user_config)  
print(f"Status: {status}")
```

## 🔒 Sicherheit

### Datenschutz
- Keine zusätzlichen persönlichen Daten gespeichert
- Nur Termin-IDs und User-IDs für Tracking
- Konforme Datenverarbeitung nach DSGVO

### API-Sicherheit
- Rate-Limiting für Notion API-Calls
- Fehlertolerante API-Behandlung
- Sichere Token-Handhabung

## 🚀 Deployment

### Produktions-Checkliste

- [ ] Notion Databases mit allen Properties eingerichtet
- [ ] Environment-Variablen konfiguriert  
- [ ] users_config.json mit shared_notion_database_id erweitert
- [ ] Notion-Integration hat Zugriff auf alle Datenbanken
- [ ] Tests erfolgreich durchgelaufen
- [ ] Logging konfiguriert
- [ ] Monitoring eingerichtet

### Rollback-Plan

```bash
# Service deaktivieren
echo "PARTNER_SYNC_ENABLED=false" >> .env

# Bot neu starten 
systemctl restart telegram-bot

# Optional: Manueller Cleanup Shared DB
# (Partner-relevante Termine in Shared DB löschen)
```

## 📈 Performance

### Optimierungen

- **Batch-Operationen**: Mehrere Termine gleichzeitig verarbeiten
- **Caching**: Häufig verwendete Daten zwischenspeichern  
- **Rate-Limiting**: Notion API-Limits respektieren
- **Asynchrone Verarbeitung**: Non-blocking Sync-Operationen

### Skalierung

- **Multi-User**: Unterstützt unbegrenzte Anzahl User
- **Bulk-Sync**: Effiziente Verarbeitung großer Terminmengen
- **Background-Processing**: Minimale Auswirkung auf Bot-Performance

---

## 🎉 Fazit

Der Partner Sync Service ermöglicht eine nahtlose Zusammenarbeit ohne Notion Plus-Plan durch:

- 🔄 **Automatische Synchronisation** Partner-relevanter Termine
- 🛡️ **Robuste Implementation** mit Fehlerbehandlung  
- 📊 **Monitoring & Debugging** für transparente Operationen
- 🚀 **Performance-Optimierung** für Produktionsumgebung
- 🧪 **Umfassende Tests** für zuverlässige Funktionalität

**Ergebnis**: Alle User können Partner-relevante Termine in der gemeinsamen Datenbank sehen, ohne dass jeder User einen Notion Plus-Plan benötigt.