# API Reference

## Telegram Commands

### `/start`
Initialisiert den Bot und prüft die Verbindung zu Notion.

**Response:**
```
Hallo [Name]! 👋

Ich bin dein Kalender-Bot mit Notion-Integration ✅

Verfügbare Befehle:
• /start - Bot starten
• /help - Hilfe anzeigen
• /today - Heutige Termine anzeigen
• /add - Neuen Termin hinzufügen
• /list - Alle kommenden Termine anzeigen
```

### `/help`
Zeigt detaillierte Hilfe und Beispiele.

**Response:**
Detaillierte Befehlsübersicht mit Beispielen für alle Commands.

### `/add <datum> <zeit> <titel> [beschreibung]`
Erstellt einen neuen Termin in der Notion-Datenbank.

**Parameter:**
- `datum` (required): "heute", "morgen", oder DD.MM.YYYY
- `zeit` (required): HH:MM oder HH.MM
- `titel` (required): Terminbezeichnung
- `beschreibung` (optional): Weitere Details zum Termin

**Beispiele:**
```
/add morgen 14:00 Meeting Team-Besprechung
/add heute 15:30 Arzttermin
/add 25.12.2024 18:00 Weihnachtsfeier
```

**Response:**
```
✅ Termin erfolgreich erstellt!

📅 *Meeting*
🕐 06.06.2025 um 14:00
📝 Team-Besprechung
```

### `/list`
Zeigt die nächsten 5 kommenden Termine.

**Response:**
```
📋 *Kommende Termine:*

1. 📅 *Meeting*
   🕐 06.06.2025 um 14:00
   📝 Team-Besprechung
   
2. 📅 *Arzttermin*
   🕐 07.06.2025 um 09:00
   📍 Praxis Dr. Schmidt
```

### `/today`
Zeigt alle Termine für den aktuellen Tag.

**Response:**
```
📅 *Termine für heute (05.06.2025):*

1. 📅 *Standup*
   🕐 09:00
   📝 Daily Standup Meeting
```

## Python API

### Models

#### `Appointment`
```python
from src.models.appointment import Appointment

appointment = Appointment(
    title="Meeting",
    date=datetime(2025, 6, 6, 14, 0),
    description="Team meeting",
    location="Office",
    tags=["work", "important"]
)
```

**Methods:**
- `to_notion_properties(timezone: str) -> dict`: Convert to Notion properties
- `from_notion_page(page: dict) -> Appointment`: Create from Notion page
- `format_for_telegram(timezone: str) -> str`: Format for Telegram display

### Services

#### `NotionService`
```python
from src.services.notion_service import NotionService
from config.settings import Settings

service = NotionService(Settings())
```

**Methods:**
- `async create_appointment(appointment: Appointment) -> str`
  - Creates appointment in Notion
  - Returns: Notion page ID
  
- `async get_appointments(limit: int = 10) -> List[Appointment]`
  - Retrieves appointments sorted by date
  - Returns: List of Appointment objects
  
- `async update_appointment(page_id: str, appointment: Appointment) -> bool`
  - Updates existing appointment
  - Returns: Success status
  
- `async delete_appointment(page_id: str) -> bool`
  - Archives appointment (soft delete)
  - Returns: Success status
  
- `async test_connection() -> bool`
  - Tests Notion API connection
  - Returns: Connection status

### Handlers

#### `AppointmentHandler`
```python
from src.handlers.appointment_handler import AppointmentHandler
from config.settings import Settings

handler = AppointmentHandler(Settings())
```

**Methods:**
- `async add_appointment(update: Update, context: Context)`
- `async list_appointments(update: Update, context: Context)`
- `async today_appointments(update: Update, context: Context)`

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | - | Telegram Bot API Token |
| `NOTION_API_KEY` | Yes | - | Notion Integration Token |
| `NOTION_DATABASE_ID` | Yes | - | Target Notion Database ID |
| `TIMEZONE` | No | Europe/Berlin | Default timezone |
| `LANGUAGE` | No | de | UI language |
| `LOG_LEVEL` | No | INFO | Logging level |
| `ENVIRONMENT` | No | production | Environment mode |

## Error Handling

### Common Errors

#### Invalid Date Format
```
❌ Fehler: Ungültiges Datumsformat: 32.13.2024
```
**Lösung:** Verwenden Sie DD.MM.YYYY Format

#### Past Date
```
❌ Fehler: Termin muss in der Zukunft liegen
```
**Lösung:** Wählen Sie ein zukünftiges Datum

#### Missing Arguments
```
❌ Bitte gib einen Termin an.
Format: /add <Datum> <Zeit> <Titel> [Beschreibung]
```
**Lösung:** Alle erforderlichen Parameter angeben

#### Notion Connection Error
```
❌ Fehler beim Erstellen des Termins. Bitte versuche es erneut.
```
**Lösung:** Prüfen Sie Notion API Key und Database ID

## Logging

### Log Levels
- `DEBUG`: Detaillierte Informationen für Debugging
- `INFO`: Allgemeine Informationen über Bot-Aktivitäten
- `WARNING`: Warnungen über potenzielle Probleme
- `ERROR`: Fehler, die behandelt wurden

### Log Format
```
2025-06-05 14:30:00,123 - __main__ - INFO - Starting Telegram Bot with Notion integration...
2025-06-05 14:30:05,456 - src.handlers.appointment_handler - INFO - Created appointment: Meeting at 2025-06-06 14:00:00
```

### Log Files
- Console output: Echtzeit-Logs
- `bot.log`: Persistente Log-Datei mit Rotation