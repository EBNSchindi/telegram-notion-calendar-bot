# 📚 API Reference - Telegram Notion Calendar Bot

Vollständige Referenz aller Bot-Kommandos, Features und Konfigurationsoptionen.

## 🤖 Bot-Kommandos

### Haupt-Navigation

#### `/start`
**Beschreibung**: Zeigt das interaktive Hauptmenü an  
**Berechtigung**: Alle autorisierten User  
**Antwort**: Visuelles Menü mit Inline-Buttons

```
📅 Heutige Termine    🗓️ Termine für morgen
📋 Alle anstehenden   ➕ Neuen Termin hinzufügen  
⚙️ Erinnerungen      ❓ Hilfe
```

#### `/menu`
**Beschreibung**: Alias für `/start`  
**Berechtigung**: Alle autorisierten User

#### `/help`
**Beschreibung**: Zeigt ausführliche Hilfe und alle unterstützten Zeitformate  
**Berechtigung**: Alle autorisierten User

---

### Terminverwaltung

#### `/add <datum> <zeit> <titel> [beschreibung]`
**Beschreibung**: Erstellt einen neuen Termin  
**Berechtigung**: Alle autorisierten User  
**Parameter**:
- `datum`: Datum im unterstützten Format (siehe Zeitformate)
- `zeit`: Uhrzeit im unterstützten Format
- `titel`: Termintitel (erforderlich)
- `beschreibung`: Optionale Beschreibung

**Beispiele**:
```bash
/add morgen 14:30 Meeting mit Team
/add Sonntag 17 Uhr Familienessen
/add 25.12.2024 viertel vor 8 Weihnachtsfeier
/add Monday 4 PM Team Call
```

#### `/today`
**Beschreibung**: Zeigt heutige Termine aus allen Datenbanken  
**Berechtigung**: Alle autorisierten User  
**Antwort**: Liste mit Terminen, gekennzeichnet nach Quelle (👤 🌐 📧)

#### `/tomorrow`
**Beschreibung**: Zeigt morgige Termine aus allen Datenbanken  
**Berechtigung**: Alle autorisierten User

#### `/list`
**Beschreibung**: Zeigt alle kommenden Termine  
**Berechtigung**: Alle autorisierten User  
**Parameter**: Optional Anzahl Tage (Standard: 7)

```bash
/list        # Nächste 7 Tage
/list 14     # Nächste 14 Tage
```

---

### Erinnerungen

#### `/reminder`
**Beschreibung**: Zeigt aktuelle Erinnerungseinstellungen  
**Berechtigung**: Alle autorisierten User

#### `/reminder on`
**Beschreibung**: Aktiviert tägliche Erinnerungen  
**Berechtigung**: Alle autorisierten User

#### `/reminder off`
**Beschreibung**: Deaktiviert tägliche Erinnerungen  
**Berechtigung**: Alle autorisierten User

#### `/reminder time <zeit>`
**Beschreibung**: Ändert die Erinnerungszeit  
**Berechtigung**: Alle autorisierten User  
**Parameter**: `zeit` im Format HH:MM (24h)

**Beispiele**:
```bash
/reminder time 08:00
/reminder time 09:30
```

#### `/reminder test`
**Beschreibung**: Sendet eine Test-Erinnerung  
**Berechtigung**: Alle autorisierten User

#### `/reminder preview`
**Beschreibung**: Zeigt Vorschau der morgigen Erinnerung  
**Berechtigung**: Alle autorisierten User

---

### Debug-Kommandos (nur Admins)

#### `/test_time <zeitausdruck>`
**Beschreibung**: Testet die Zeitformat-Erkennung  
**Berechtigung**: Nur Admin-User  
**Parameter**: `zeitausdruck` - Beliebiger Zeitausdruck

**Beispiele**:
```bash
/test_time morgen 16 Uhr
/test_time Sonntag halb 10
/test_time Monday 4 PM
```

#### `/formats`
**Beschreibung**: Zeigt alle unterstützten Zeitformate  
**Berechtigung**: Nur Admin-User

#### `/validate <datum> <zeit> <titel>`
**Beschreibung**: Validiert Termineingabe ohne zu speichern  
**Berechtigung**: Nur Admin-User

#### `/test_notion`
**Beschreibung**: Testet Notion-Verbindung für aktuellen User  
**Berechtigung**: Nur Admin-User

---

## 🕐 Unterstützte Zeitformate

### Datums-Formate

#### Relative Datumsangaben (Deutsch)
- `heute`
- `morgen`
- `übermorgen`

#### Wochentage (Deutsch)
- `Montag`, `Dienstag`, `Mittwoch`, `Donnerstag`, `Freitag`, `Samstag`, `Sonntag`
- **Automatisch nächster Termin**: Bei „Freitag" am Freitag → nächster Freitag

#### Wochentage (English)
- `Monday`, `Tuesday`, `Wednesday`, `Thursday`, `Friday`, `Saturday`, `Sunday`

#### Absolute Datumsangaben
- `DD.MM.YYYY`: `25.12.2024`
- `DD.MM.YY`: `25.12.24`
- `DD.MM`: `25.12` (aktuelles Jahr)
- `YYYY-MM-DD`: `2024-12-25`

### Zeit-Formate

#### Standard-Formate
- `HH:MM`: `14:30`
- `HH.MM`: `14.30`
- `HHMM`: `1430`
- `HH`: `14` (volle Stunde)

#### Deutsche Zeitausdrücke
- `16 Uhr`: 16:00
- `halb 3`: 2:30
- `viertel vor 5`: 4:45
- `viertel nach 2`: 2:15
- `dreiviertel 3`: 2:45

#### Englische Zeitausdrücke
- `4 PM`, `4 AM`: 16:00, 4:00
- `quarter past 2`: 2:15
- `half past 3`: 3:30
- `quarter to 5`: 4:45

---

## 🗂️ Datenbank-Struktur

### Notion-Datenbank-Felder

Alle Datenbanken (Private, Shared, Business) benötigen diese Felder:

| Feld | Typ | Erforderlich | Beschreibung |
|------|-----|-------------|-------------|
| **Name** | Title | ✅ | Termintitel |
| **Datum** | Date | ✅ | Datum und Uhrzeit |
| **Beschreibung** | Text | ❌ | Zusätzliche Notizen |
| **OutlookID** | Text | ❌ | Eindeutige ID für Business-Events |
| **Organizer** | Text | ❌ | Organisator (für Business-Events) |

### Datenbank-Typen

#### 1. Private Database
- **Zweck**: Persönliche Termine je User
- **Zugriff**: Nur der jeweilige User
- **Konfiguration**: `notion_api_key` + `notion_database_id` in users_config.json

#### 2. Shared Database
- **Zweck**: Gemeinsame Team-Termine
- **Zugriff**: Alle User können lesen/schreiben
- **Konfiguration**: `shared_notion_api_key` + `shared_notion_database_id` in users_config.json

#### 3. Business Database (optional)
- **Zweck**: Automatische E-Mail-Synchronisation
- **Zugriff**: Automatisch befüllt aus E-Mails
- **Konfiguration**: `business_notion_api_key` + `business_notion_database_id` in users_config.json

---

## 📧 Business Email Integration

### Konfiguration

#### E-Mail-Einstellungen (.env)
```env
EMAIL_SYNC_ENABLED=true
EMAIL_ADDRESS=your_gmail_address@gmail.com
EMAIL_PASSWORD=your_gmail_app_password
IMAP_SERVER=imap.gmail.com
IMAP_PORT=993
EMAIL_CHECK_INTERVAL=300
DELETE_AFTER_PROCESSING=true
OUTLOOK_SENDER_WHITELIST=trusted_sender@company.com,another@company.com
```

#### E-Mail-Verarbeitung
- **Zeitraum**: 30 Tage Rückblick (erweitert für umfassende Synchronisation)
- **Initial Sync**: 1000 E-Mails aus den letzten 30 Tagen
- **Regelmäßiger Sync**: 200 E-Mails alle 5 Minuten (konfigurierbar)
- **Automatische Bereinigung**: Verarbeitete E-Mails werden gelöscht (optional)

#### Unterstützte E-Mail-Provider
- ✅ **Gmail**: Mit App-Passwort
- ✅ **Google Workspace**: Mit App-Passwort
- ✅ **Outlook** (IMAP): Mit App-Passwort
- ✅ **Exchange Online**: Mit App-Passwort

### E-Mail-Verarbeitung

#### Automatische Erkennung
- **Betreff-Keywords**: `terminweiterleitung`, `calendar forward`, `termin`, `meeting`
- **JSON-Struktur**: Body muss `{` und `\"Action\"` enthalten
- **Sender-Whitelist**: Nur vertrauenswürdige Absender

#### Unterstützte Actions
- `\"Action\": \"CREATE\"`: Neuer Termin
- `\"Action\": \"UPDATE\"`: Termin aktualisieren
- `\"Action\": \"DELETE\"`: Termin löschen
- `\"Action\": \"CANCEL\"`: Termin absagen

#### JSON-Format Beispiel
```json
{
  \"Action\": \"CREATE\",
  \"Subject\": \"Team Meeting\",
  \"StartDateTime\": \"2024-06-15T14:00:00\",
  \"EndDateTime\": \"2024-06-15T15:00:00\",
  \"Organizer\": \"john.doe@company.com\",
  \"ICalUId\": \"unique-event-id-123\"
}
```

---

## 🔧 Konfiguration

### Umgebungsvariablen (.env)

```env
# === BOT CONFIGURATION ===
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TIMEZONE=Europe/Berlin
LANGUAGE=de
LOG_LEVEL=INFO
ENVIRONMENT=production

# === SECURITY ===
AUTHORIZED_USERS=123456789,987654321
ADMIN_USERS=123456789

# === EMAIL INTEGRATION ===
EMAIL_SYNC_ENABLED=true
EMAIL_ADDRESS=your_gmail_address@gmail.com
EMAIL_PASSWORD=your_gmail_app_password
IMAP_SERVER=imap.gmail.com
IMAP_PORT=993
EMAIL_CHECK_INTERVAL=300
DELETE_AFTER_PROCESSING=true
OUTLOOK_SENDER_WHITELIST=trusted@company.com

# === EMAIL PROCESSING ===
EMAIL_SYNC_ENABLED=true
DELETE_AFTER_PROCESSING=true
```

### User-Konfiguration (users_config.json)

```json
{
  \"users\": [
    {
      \"telegram_user_id\": 123456789,
      \"telegram_username\": \"john_doe\",
      \"notion_api_key\": \"secret_abc123...\",
      \"notion_database_id\": \"1a2b3c4d5e6f...\",
      \"shared_notion_api_key\": \"secret_shared123...\",
      \"shared_notion_database_id\": \"shared_db_id...\",
      \"business_notion_api_key\": \"secret_business123...\",
      \"business_notion_database_id\": \"business_db_id...\",
      \"timezone\": \"Europe/Berlin\",
      \"language\": \"de\",
      \"reminder_time\": \"08:00\",
      \"reminder_enabled\": true
    }
  ]
}
```

---

## 🔒 Sicherheitsfeatures

### Benutzer-Autorisierung

#### AUTHORIZED_USERS
- Komma-getrennte Liste von Telegram User IDs
- Leer = alle User erlaubt
- Nur autorisierte User können den Bot verwenden

#### ADMIN_USERS
- Komma-getrennte Liste von Admin User IDs
- Nur Admins können Debug-Kommandos verwenden
- Subset von AUTHORIZED_USERS

### Automatische Validierung

#### User-Config-Validierung
- ✅ **Platzhalter-Erkennung**: `secret_xxx_`, `your_notion_` werden ignoriert
- ✅ **API-Key-Format**: Muss mit `secret_` oder `ntn_` beginnen
- ✅ **Database-ID-Format**: Muss gültige Notion-UUID sein
- ✅ **Mindestens-ein-User**: Bot startet nur mit gültigen Usern

#### E-Mail-Sicherheit
- ✅ **Sender-Whitelist**: Nur vertrauenswürdige Absender
- ✅ **Size-Limits**: E-Mails max 50KB, JSON max 10KB
- ✅ **Format-Validierung**: Strenge JSON-Struktur-Prüfung

### Rate Limiting
- **30 Requests/Minute** pro User
- **Automatische Sperre** bei Überschreitung
- **Graduelle Freigabe** nach Wartezeit

---

## 📊 Terminquellen-Kennzeichnung

### Visueller Indikator
- 👤 **Private Termine**: Aus persönlicher Datenbank
- 🌐 **Shared Termine**: Aus gemeinsamer Datenbank
- 📧 **Business Termine**: Aus E-Mail-Synchronisation

### Terminliste-Beispiel
```
📅 Termine für heute (15.06.2024):

👤 09:00 - Persönlicher Termin
   Private Notiz

🌐 14:00 - Team Meeting
   Wöchentliches Standup

📧 16:00 - Kundentermin
   Automatisch synchronisiert von outlook
   Organizer: john.doe@company.com
```

---

## 🚀 Callback-Queries (Inline-Buttons)

### Hauptmenü-Callbacks
- `today`: Heutige Termine anzeigen
- `tomorrow`: Morgige Termine anzeigen
- `list`: Alle kommenden Termine
- `add`: Neuen Termin hinzufügen
- `reminder`: Erinnerungseinstellungen
- `help`: Hilfe anzeigen

### Erinnerungs-Callbacks
- `reminder_on`: Erinnerungen aktivieren
- `reminder_off`: Erinnerungen deaktivieren
- `reminder_time`: Erinnerungszeit ändern
- `reminder_test`: Test-Erinnerung senden
- `reminder_preview`: Vorschau anzeigen

---

## 📱 Verwendung über Inline-Menü

### Terminerfassung über Menü
1. **Hauptmenü öffnen**: `/start`
2. **\"➕ Neuen Termin hinzufügen\"** klicken
3. **Termin eingeben** (ohne `/add`): `morgen 14:30 Meeting`
4. **Bot** erkennt automatisch Format und erstellt Termin

### Schnellzugriff
- **Heute**: Direkt heutige Termine
- **Morgen**: Direkt morgige Termine
- **Alle**: Übersicht kommender Termine
- **Erinnerungen**: Einstellungen verwalten

---

## 🐛 Fehlercodes und Behandlung

### Häufige Fehler

#### `\"Du bist noch nicht konfiguriert\"`
- **Ursache**: User nicht in users_config.json
- **Lösung**: User mit gültiger Konfiguration hinzufügen

#### `\"Ungültiges Datum\"`
- **Ursache**: Unbekanntes Datumsformat
- **Lösung**: Unterstützte Formate verwenden (siehe `/help`)

#### `\"Notion API Error\"`
- **Ursache**: Ungültiger API-Key oder Database-ID
- **Lösung**: Konfiguration prüfen und korrigieren

#### `\"Rate Limit Exceeded\"`
- **Ursache**: Zu viele Anfragen
- **Lösung**: 1 Minute warten

### Debug-Informationen

#### Bot-Logs
```bash
# Live-Logs anzeigen
docker logs -f calendar-telegram-bot

# Letzte 100 Zeilen
docker logs --tail 100 calendar-telegram-bot
```

#### Notion-Verbindung testen
```bash
/test_notion  # Nur für Admins
```

---

## 🔄 Migration und Updates

### Von Single-User zu Multi-User
1. **Aktuelle Konfiguration sichern**
2. **users_config.json erstellen** (siehe Template)
3. **User-Daten migrieren**
4. **Bot neu starten**

### Datenbank-Schema-Updates
- **Neue Felder hinzufügen** (OutlookID, Organizer) ist optional
- **Bestehende Termine** bleiben unverändert
- **Automatische Erkennung** neuer Felder

---

## 📞 Support und Erweiterte Features

### Erweiterte Terminformate
- **Mehrtägige Events**: Werden als einzelne Termine behandelt
- **Wiederholende Termine**: Müssen manuell erstellt werden
- **Zeitzonen**: Automatische Konvertierung basierend auf User-Timezone

### Leistungsoptimierung
- **Caching**: Häufige Notion-Abfragen werden gecacht
- **Batch-Updates**: Mehrere Termine gleichzeitig verarbeiten
- **Lazy Loading**: Große Terminlisten werden paginiert

---

*Letzte Aktualisierung: 2024-06-15*  
*Version: 2.0.0 - Multi-User mit Business Email Integration*