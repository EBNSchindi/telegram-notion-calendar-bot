# Notion Setup Guide

Diese Anleitung führt Sie durch die Einrichtung der Notion-Integration für den Calendar Bot.

## 1. Notion Integration erstellen

1. Öffnen Sie https://www.notion.so/my-integrations
2. Klicken Sie auf **"New integration"**
3. Geben Sie der Integration einen Namen (z.B. "Calendar Bot")
4. Wählen Sie den Workspace aus
5. Klicken Sie auf **"Submit"**
6. **Kopieren Sie den "Internal Integration Token"** (beginnt mit `secret_`)

## 2. Notion Datenbank erstellen

### Option A: Neue Datenbank erstellen

1. Erstellen Sie eine neue Seite in Notion
2. Fügen Sie eine Datenbank hinzu (Table, Board, etc.)
3. Fügen Sie folgende Properties hinzu:

   | Property Name | Type | Beschreibung |
   |--------------|------|--------------|
   | Name | Title | Pflichtfeld - Terminbezeichnung |
   | Datum | Date | Pflichtfeld - Termin Datum/Zeit |
   | Beschreibung | Text | Optional - Detaillierte Beschreibung |
   | Ort | Text | Optional - Veranstaltungsort |
   | Tags | Text | Optional - Komma-getrennte Tags |

### Option B: Bestehende Datenbank anpassen

Stellen Sie sicher, dass Ihre Datenbank die oben genannten Felder hat. Die Namen müssen exakt übereinstimmen!

## 3. Integration mit Datenbank verbinden

1. Öffnen Sie Ihre Kalender-Datenbank in Notion
2. Klicken Sie auf **"..."** (drei Punkte) oben rechts
3. Wählen Sie **"Add connections"**
4. Suchen Sie nach Ihrer Integration
5. Klicken Sie auf **"Confirm"**

## 4. Database ID finden

1. Öffnen Sie die Datenbank in Notion
2. Schauen Sie sich die URL an:
   ```
   https://www.notion.so/workspace/1c81778a50cc80f4ae07f9a0fa059292?v=...
   ```
3. Die Database ID ist der Teil zwischen dem letzten `/` und dem `?`:
   ```
   1c81778a50cc80f4ae07f9a0fa059292
   ```

## 5. Bot konfigurieren

Erstellen Sie eine `.env` Datei mit folgenden Werten:

```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=ihr_telegram_bot_token

# Notion Integration
NOTION_API_KEY=secret_ihr_integration_token
NOTION_DATABASE_ID=ihre_database_id

# Optionale Einstellungen
TIMEZONE=Europe/Berlin
LANGUAGE=de
```

## 6. Verbindung testen

Führen Sie das Test-Script aus:

```bash
python scripts/test_notion_connection.py
```

Sie sollten folgende Ausgabe sehen:
- ✅ Connection successful!
- ✅ Required properties found!
- Liste Ihrer Datenbank-Properties

## Troubleshooting

### "Unauthorized" Fehler
- Prüfen Sie, ob der API Key korrekt ist
- Stellen Sie sicher, dass die Integration mit der Datenbank geteilt wurde

### "Database not found" Fehler
- Überprüfen Sie die Database ID
- Stellen Sie sicher, dass die Integration Zugriff hat

### Properties nicht gefunden
- Die Feldnamen müssen exakt übereinstimmen (Groß-/Kleinschreibung!)
- Erforderlich: Name, Datum
- Optional: Beschreibung, Ort, Tags

### Tags werden nicht als Multi-Select erkannt
Der Bot unterstützt sowohl Text als auch Multi-Select für Tags. Bei Text-Feldern werden Tags komma-getrennt gespeichert.

## Erweiterte Konfiguration

### Mehrere Datenbanken
Aktuell unterstützt der Bot nur eine Datenbank. Für mehrere Kalender müssten Sie mehrere Bot-Instanzen betreiben.

### Feldanpassungen
Wenn Sie andere Feldnamen verwenden möchten, müssen Sie `src/models/appointment.py` entsprechend anpassen:
- `to_notion_properties()` - Mapping TO Notion
- `from_notion_page()` - Mapping FROM Notion

### Permissions
Die Integration benötigt folgende Berechtigungen:
- Read content
- Update content
- Insert content

Diese werden automatisch gewährt, wenn Sie die Integration erstellen.