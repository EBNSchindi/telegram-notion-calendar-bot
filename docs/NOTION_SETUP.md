# 🗂️ Notion Setup Guide - Multi-User Calendar Bot

Diese Anleitung führt Sie durch die Einrichtung der Notion-Integration für den Multi-User Calendar Bot mit Business Email Integration.

## 📋 Übersicht

Der Bot unterstützt **drei verschiedene Datenbank-Typen**:
- **🏠 Private Database**: Persönliche Termine je User
- **🌐 Shared Database**: Gemeinsame Team-Termine für alle User
- **📧 Business Database**: Automatische E-Mail-Synchronisation (optional)

## 🔧 Voraussetzungen

- Notion Account mit Workspace-Zugang
- Telegram Bot Token
- Für Business Email: Gmail App-Passwort

---

## 1️⃣ Notion Integration erstellen

### Schritt 1: Integration erstellen

1. Öffnen Sie https://www.notion.so/my-integrations
2. Klicken Sie auf **\"New integration\"**
3. Geben Sie der Integration einen Namen (z.B. \"Calendar Bot - User1\")
4. Wählen Sie den Workspace aus
5. Klicken Sie auf **\"Submit\"**
6. **Kopieren Sie den \"Internal Integration Token\"** (beginnt mit `secret_` oder `ntn_`)

⚠️ **Wichtig**: Für jeden User sollten Sie eine **separate Integration** erstellen für bessere Sicherheit.

### Schritt 2: Weitere Integrationen (Multi-User)

Wiederholen Sie Schritt 1 für:
- **Shared Database Integration**: \"Calendar Bot - Shared\"
- **Business Database Integration**: \"Calendar Bot - Business\" (optional)
- **Weitere User**: \"Calendar Bot - User2\", etc.

---

## 2️⃣ Notion Datenbanken erstellen

### 🏠 Private Database (pro User)

Jeder User benötigt eine eigene private Datenbank:

1. Erstellen Sie eine neue Seite in Notion
2. Fügen Sie eine Datenbank hinzu (Table empfohlen)
3. **Benennen Sie die Datenbank**: \"📅 Kalender - [Username]\"
4. Fügen Sie folgende Properties hinzu:

| Property Name | Type | Erforderlich | Beschreibung |
|---------------|------|-------------|-------------|
| **Name** | Title | ✅ | Terminbezeichnung |
| **Startdatum** | Date | ✅ | Startzeit des Termins (mit Zeit-Support) |
| **Endedatum** | Date | ✅ | Endzeit des Termins (mit Zeit-Support) |
| **Datum** | Date | ❌ | Legacy-Feld (optional für Abwärtskompatibilität) |
| **Beschreibung** | Text | ❌ | Detaillierte Beschreibung |
| **Ort** | Text | ❌ | Terminort (für AI-Features) |
| **Tags** | Text | ❌ | Komma-separierte Tags |
| **PartnerRelevant** | Checkbox | ✅ | **AI-Feature: Partner-Relevanz** |
| **OutlookID** | Text | ❌ | Eindeutige ID für Business Events |
| **Organizer** | Text | ❌ | Organisator/Absender |

### 🌐 Shared Database (global)

Eine zentrale Datenbank für alle Team-Termine:

1. Erstellen Sie eine neue Seite in Notion
2. Fügen Sie eine Datenbank hinzu
3. **Benennen Sie die Datenbank**: \"🌐 Team-Kalender\"
4. Verwenden Sie **identische Properties** wie bei der Private Database

### 📧 Business Database (optional)

Für automatische E-Mail-Synchronisation:

1. Erstellen Sie eine neue Seite in Notion
2. Fügen Sie eine Datenbank hinzu
3. **Benennen Sie die Datenbank**: \"📧 Business-Kalender - [Username]\"
4. Verwenden Sie **identische Properties** wie bei der Private Database

⚠️ **Wichtig**: Die **OutlookID** und **Organizer** Felder sind für Business Events essentiell!

---

## 3️⃣ Datenbank-Permissions einrichten

### Private Database

1. Öffnen Sie Ihre private Kalender-Datenbank in Notion
2. Klicken Sie auf **\"...\"** (drei Punkte) oben rechts
3. Wählen Sie **\"Add connections\"**
4. Suchen Sie nach Ihrer **User-spezifischen Integration**
5. Klicken Sie auf **\"Confirm\"**

### Shared Database

1. Öffnen Sie die Team-Kalender-Datenbank
2. Klicken Sie auf **\"...\"** (drei Punkte) oben rechts
3. Wählen Sie **\"Add connections\"**
4. Verbinden Sie die **Shared Integration**
5. **Wichtig**: Diese Datenbank muss für **alle User-Integrationen** freigegeben werden!

### Business Database

1. Öffnen Sie die Business-Kalender-Datenbank
2. Verbinden Sie die **Business Integration**
3. Optional: Auch mit der **User-Integration** verbinden für manuellen Zugriff

---

## 4️⃣ Database IDs ermitteln

### Methode 1: Über URL

1. Öffnen Sie die Datenbank in Notion
2. Schauen Sie sich die URL an:
   ```
   https://www.notion.so/workspace/1c81778a50cc80f4ae07f9a0fa059292?v=...
   ```
3. Die Database ID ist der Teil zwischen dem letzten `/` und dem `?`:
   ```
   1c81778a50cc80f4ae07f9a0fa059292
   ```

### Methode 2: Über Share-Link

1. Klicken Sie auf **\"Share\"** oben rechts in der Datenbank
2. Kopieren Sie den Link
3. Die Database ID ist der 32-stellige Hex-String in der URL

---

## 5️⃣ Bot konfigurieren

### Schritt 1: .env Datei erstellen

Kopieren Sie `.env.example` zu `.env`:

```bash
cp .env.example .env
```

Füllen Sie die **grundlegenden Einstellungen** aus:

```env
# Telegram Bot Token
TELEGRAM_BOT_TOKEN=ihr_telegram_bot_token

# Application Settings
TIMEZONE=Europe/Berlin
LANGUAGE=de

# Business Email Integration (optional)
EMAIL_SYNC_ENABLED=true
EMAIL_ADDRESS=ihr_gmail@gmail.com
EMAIL_PASSWORD=ihr_gmail_app_passwort
OUTLOOK_SENDER_WHITELIST=vertrauenswürdiger_sender@firma.com
```

### Schritt 2: users_config.json erstellen

Kopieren Sie `users_config.example.json` zu `users_config.json`:

```bash
cp users_config.example.json users_config.json
```

Konfigurieren Sie **jeden User**:

```json
{
  \"users\": [
    {
      \"telegram_user_id\": 123456789,
      \"telegram_username\": \"john_doe\",
      
      // Private Database
      \"notion_api_key\": \"secret_private_integration_token\",
      \"notion_database_id\": \"private_database_id_32_chars\",
      
      // Shared Database (für alle User gleich)
      \"shared_notion_api_key\": \"secret_shared_integration_token\",
      \"shared_notion_database_id\": \"shared_database_id_32_chars\",
      
      // Business Database (optional)
      \"business_notion_api_key\": \"secret_business_integration_token\",
      \"business_notion_database_id\": \"business_database_id_32_chars\",
      
      // User Settings
      \"timezone\": \"Europe/Berlin\",
      \"language\": \"de\",
      \"reminder_time\": \"08:00\",
      \"reminder_enabled\": true
    }
  ]
}
```

---

## 6️⃣ Verbindung testen

### Schritt 1: Notion-Verbindung testen

```bash
python scripts/test_notion_connection.py
```

**Erwartete Ausgabe**:
```
✅ User 123456789 - Private Database: Connection successful!
✅ User 123456789 - Shared Database: Connection successful!
✅ User 123456789 - Business Database: Connection successful!
✅ All required properties found!
```

### Schritt 2: Bot starten

```bash
python src/bot.py
```

**Erwartete Ausgabe**:
```
INFO - Enhanced Multi-User Telegram Bot starting...
INFO - Business calendar sync started for 1 valid users
INFO - Application started
```

### Schritt 3: Bot testen

1. Senden Sie `/start` an den Bot
2. Sie sollten das Hauptmenü sehen
3. Testen Sie `/add morgen 14:30 Test-Termin`
4. Überprüfen Sie, ob der Termin in Notion erscheint

---

## 7️⃣ Erweiterte Konfiguration

### Multi-User Setup

Für **jeden neuen User**:

1. **Telegram User ID ermitteln**:
   - User sendet `/start` → Bot zeigt User ID
   
2. **Notion Setup**:
   - Neue Integration erstellen
   - Private Database erstellen
   - Shared Database freigeben
   - Optional: Business Database erstellen
   
3. **Bot konfigurieren**:
   - User zu `users_config.json` hinzufügen
   - Bot neu starten

### Business Email Integration

Für **automatische E-Mail-Synchronisation**:

1. **Gmail App-Passwort erstellen**:
   - https://myaccount.google.com/apppasswords
   - Neues App-Passwort für \"Calendar Bot\"
   
2. **Sender-Whitelist konfigurieren**:
   ```env
   OUTLOOK_SENDER_WHITELIST=trusted1@firma.com,trusted2@firma.com
   ```
   
3. **E-Mail-Format sicherstellen**:
   - Betreff muss Keywords enthalten: `termin`, `meeting`, etc.
   - Body muss JSON mit `\"Action\"` enthalten

### Shared Database für alle User

**Wichtig**: Die Shared Database muss für **alle User-Integrationen** freigegeben werden:

1. Öffnen Sie die Shared Database
2. Klicken Sie auf **\"...\"** → **\"Add connections\"**
3. Fügen Sie **jede User-Integration** hinzu
4. **Alle User** können jetzt Team-Termine lesen/schreiben

---

## 🔍 Troubleshooting

### \"Du bist noch nicht konfiguriert\"

**Ursache**: User nicht in `users_config.json` oder ungültige Konfiguration

**Lösung**:
1. Überprüfen Sie die Telegram User ID
2. Stellen Sie sicher, dass die Notion-Keys gültig sind
3. Prüfen Sie die Database IDs

### \"Notion API Error - 401 Unauthorized\"

**Ursache**: Ungültiger API-Key oder fehlende Permissions

**Lösung**:
1. Prüfen Sie den API-Key (muss mit `secret_` oder `ntn_` beginnen)
2. Stellen Sie sicher, dass die Integration mit der Datenbank geteilt wurde
3. Regenerieren Sie den API-Key falls nötig

### \"Database not found\"

**Ursache**: Falsche Database-ID oder fehlende Berechtigung

**Lösung**:
1. Überprüfen Sie die Database-ID (32 Hex-Zeichen)
2. Stellen Sie sicher, dass die Integration Zugriff hat
3. Verwenden Sie die Share-URL Methode zur ID-Ermittlung

### \"Properties not found\"

**Ursache**: Fehlende oder falsch benannte Datenbank-Felder

**Lösung**:
1. Überprüfen Sie die Feldnamen (Groß-/Kleinschreibung!)
2. **Erforderlich**: Name (Title), Startdatum (Date), Endedatum (Date), PartnerRelevant (Checkbox)
3. **Optional**: Datum (Legacy), Beschreibung, Ort, Tags, OutlookID, Organizer
4. **Hinweis**: Bei Upgrade von Version 2.x siehe [Migration Guide](MIGRATION_GUIDE.md)

### \"No valid users configured\"

**Ursache**: Alle User haben ungültige Platzhalter-Konfigurationen

**Lösung**:
1. Ersetzen Sie alle `secret_xxx_` Werte durch echte API-Keys
2. Ersetzen Sie alle `your_database_id` Werte durch echte Database-IDs
3. Stellen Sie sicher, dass mindestens ein User vollständig konfiguriert ist

### Business Email Integration funktioniert nicht

**Ursache**: E-Mail-Konfiguration oder Whitelist-Problem

**Lösung**:
1. Überprüfen Sie Gmail App-Passwort
2. Prüfen Sie `OUTLOOK_SENDER_WHITELIST`
3. Stellen Sie sicher, dass E-Mails das JSON-Format enthalten
4. Aktivieren Sie Debug-Logs: `LOG_LEVEL=DEBUG`

---

## 📊 Datenbank-Properties im Detail

### Erforderliche Properties

| Property | Type | Notion-Beispiel | Beschreibung |
|----------|------|----------------|-------------|
| **Name** | Title | \"Team Meeting\" | Termintitel - automatisch befüllt |
| **Startdatum** | Date | 2024-06-15 14:30 | Startzeit - **Zeit-Support aktivieren!** |
| **Endedatum** | Date | 2024-06-15 15:30 | Endzeit - **Zeit-Support aktivieren!** |

### Optionale Properties

| Property | Type | Notion-Beispiel | Beschreibung |
|----------|------|----------------|-------------|
| **Beschreibung** | Text | \"Wöchentliches Standup\" | Zusätzliche Notizen |
| **OutlookID** | Text | \"event_123_456\" | Eindeutige ID für Business Events |
| **Organizer** | Text | \"john.doe@firma.com\" | Organisator/Absender |

### Property-Einstellungen

#### Datum-Properties (Startdatum & Endedatum)
- ✅ **\"Include time\"** aktivieren für beide Felder
- ✅ **Timezone** auf Ihre lokale Zeit setzen
- ✅ **Format**: \"June 15, 2024 2:30 PM\"

#### Legacy Datum-Property (optional)
- ❌ Kann beibehalten werden für Abwärtskompatibilität
- ❌ Neue Termine verwenden automatisch Startdatum/Endedatum

#### Text-Properties
- ✅ **Standard-Text-Felder** verwenden
- ❌ **Nicht** Multi-Select oder andere Typen

---

## 🚀 Produktive Nutzung

### Performance-Optimierung

1. **Separate Integrationen** für bessere Sicherheit
2. **Minimal erforderliche Permissions** vergeben
3. **Regelmäßige API-Key-Rotation**

### Backup-Strategie

1. **Notion-Datenbanken** regelmäßig exportieren
2. **Konfigurationsdateien** sichern
3. **API-Keys** sicher aufbewahren

### Monitoring

1. **Bot-Logs** regelmäßig überprüfen
2. **Notion-Limits** im Auge behalten
3. **E-Mail-Sync-Status** überwachen

---

## 🔐 Sicherheitshinweise

### API-Key-Sicherheit

- ✅ **Niemals** API-Keys in Version Control committen
- ✅ **Separate Keys** für verschiedene Environments
- ✅ **Regelmäßige Rotation** der Keys
- ✅ **Minimal erforderliche Permissions**

### Access Control

- ✅ **AUTHORIZED_USERS** in .env konfigurieren
- ✅ **Shared Database** nur für vertrauenswürdige User
- ✅ **Business Email Whitelist** restriktiv konfigurieren

### Datenschutz

- ✅ **Persönliche Termine** in separaten Private Databases
- ✅ **Sensible Daten** nicht in Shared Database
- ✅ **E-Mail-Inhalte** nach Verarbeitung löschen

---

*Letzte Aktualisierung: 2025-01-21*  
*Version: 3.1.0 - Multi-User Setup mit separaten Start-/End-Datum Feldern*