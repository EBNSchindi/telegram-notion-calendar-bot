# Development Documentation - Telegram-Notion Calendar Bot

## 📋 Projektübersicht

Dieses Projekt ist ein Telegram Bot, der Kalenderereignisse in einer Notion-Datenbank verwaltet. Der Bot wurde mit Test-Driven Development (TDD) entwickelt und bietet eine nahtlose Integration zwischen Telegram und Notion.

## 🏗 Aktuelle Implementierung

### 1. Kernfunktionalität

#### ✅ Implementierte Features

**Telegram Commands:**
- `/start` - Initialisiert den Bot und prüft die Notion-Verbindung
- `/help` - Zeigt Hilfe und Beispiele
- `/add <datum> <zeit> <titel> [beschreibung]` - Erstellt neuen Termin
- `/list` - Zeigt kommende Termine
- `/today` - Zeigt heutige Termine

**Datenfelder (Notion):**
- **Name** (Title) - Terminbezeichnung
- **Datum** (Date) - Datum und Uhrzeit
- **Beschreibung** (Rich Text) - Optionale Beschreibung
- **Ort** (Rich Text) - Optionaler Ort
- **Tags** (Rich Text) - Komma-separierte Tags

**Technische Features:**
- Asynchrone Verarbeitung mit python-telegram-bot
- Notion API Integration mit notion-client
- Timezone-Support (Europe/Berlin)
- Umfassende Fehlerbehandlung
- Detailliertes Logging (Console + Datei)
- Docker-Support

### 2. Architektur

```
src/
├── bot.py                      # Haupteinstiegspunkt
├── models/
│   └── appointment.py          # Datenmodell mit Pydantic-Validierung
├── services/
│   └── notion_service.py       # Notion API Wrapper
└── handlers/
    └── appointment_handler.py  # Telegram Command Handler
```

**Design Patterns:**
- **Service Layer Pattern**: NotionService kapselt API-Zugriffe
- **Handler Pattern**: Separate Handler für verschiedene Commands
- **Model Validation**: Pydantic für Datenvalidierung

### 3. Testing

**Test Coverage:**
- Unit Tests für Models (Appointment)
- Integration Tests für Services (NotionService)
- Handler Tests mit Mocks
- Fixtures für wiederverwendbare Test-Daten

**Test-Struktur:**
```
tests/
├── conftest.py                 # Gemeinsame Fixtures
├── test_appointment_model.py   # Model Tests
├── test_notion_service.py      # Service Tests
└── test_appointment_handler.py # Handler Tests
```

### 4. Konfiguration

**Umgebungsvariablen (.env):**
```
TELEGRAM_BOT_TOKEN=dein_token
NOTION_API_KEY=dein_notion_key
NOTION_DATABASE_ID=deine_database_id
TIMEZONE=Europe/Berlin
LANGUAGE=de
LOG_LEVEL=INFO
ENVIRONMENT=production
```

### 5. Deployment

**Docker:**
- Dockerfile mit Python 3.11
- docker-compose.yml für einfaches Deployment
- Non-root User für Sicherheit

**Scripts:**
- `run_bot.sh` - Bot lokal starten
- `scripts/test_notion_connection.py` - Verbindung testen

## 🚀 Weiterentwicklungsmöglichkeiten

### 1. Kurzfristig (Quick Wins)

#### a) Termin-Bearbeitung
```python
# In appointment_handler.py
async def edit_appointment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Edit existing appointment by ID or selection"""
    # /edit <id> <field> <new_value>
```

#### b) Termin-Löschung
```python
async def delete_appointment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete appointment with confirmation"""
    # /delete <id>
    # Mit Inline-Keyboard für Bestätigung
```

#### c) Erweiterte Suche
```python
async def search_appointments(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search appointments by keyword"""
    # /search <keyword>
    # Sucht in Titel, Beschreibung, Ort
```

### 2. Mittelfristig (Features)

#### a) Erinnerungen/Notifications
```python
# Neuer Service: reminder_service.py
class ReminderService:
    async def check_upcoming_appointments(self):
        """Check for appointments in next X hours"""
        
    async def send_reminder(self, user_id: int, appointment: Appointment):
        """Send reminder to user"""
```

**Implementation:**
- Background Task mit asyncio
- Konfigurierbare Vorlaufzeit
- Persistente Speicherung von User-IDs

#### b) Wiederkehrende Termine
```python
# Erweiterung in appointment.py
class RecurringAppointment(Appointment):
    recurrence_type: str  # daily, weekly, monthly
    recurrence_interval: int
    recurrence_end: Optional[datetime]
```

#### c) Multi-User Support
```python
# Neue Tabelle/Database für User-Management
class UserSettings(BaseModel):
    telegram_id: int
    notion_database_id: str
    timezone: str
    language: str
```

### 3. Langfristig (Advanced)

#### a) Calendar Sync
- Google Calendar Integration
- CalDAV Support (Nextcloud, etc.)
- iCal Export/Import

#### b) Natural Language Processing
```python
# Mit dateparser oder ähnlichen Libraries
# "Morgen nachmittag Meeting" → 15:00
# "Nächsten Montag Zahnarzt" → Datum berechnen
```

#### c) Web-Interface
- Flask/FastAPI Dashboard
- Notion-unabhängige Ansicht
- Statistiken und Analysen

## 🛠 Entwicklungsumgebung Setup

### 1. Projekt klonen
```bash
git clone https://github.com/EBNSchindi/telegram-notion-calendar-bot.git
cd telegram-notion-calendar-bot
```

### 2. Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### 3. Konfiguration
```bash
cp .env.example .env
# .env mit eigenen Keys ausfüllen
```

### 4. Notion Setup
- Neue Integration erstellen: https://www.notion.so/my-integrations
- Datenbank mit folgenden Properties erstellen:
  - Name (Title)
  - Datum (Date)
  - Beschreibung (Text)
  - Ort (Text)  
  - Tags (Text)
- Integration mit Datenbank teilen

### 5. Tests ausführen
```bash
make test               # Alle Tests
make test-watch        # Watch Mode
pytest -v -k "test_name" # Einzelner Test
```

### 6. Bot starten
```bash
./run_bot.sh
# oder
python src/bot.py
```

## 📝 Code-Konventionen

### Python Style
- Black für Formatierung
- isort für Imports
- Type Hints wo möglich
- Docstrings für alle public Methods

### Git Workflow
- Feature Branches: `feature/add-delete-command`
- Commit Messages: Conventional Commits
- Tests vor jedem Commit

### Testing
- Mindestens 80% Coverage
- Unit Tests für neue Features
- Integration Tests für API-Calls

## 🐛 Bekannte Limitierungen

1. **Tags als Text**: Notion-Datenbank nutzt Rich Text statt Multi-Select für Tags
2. **Keine Datei-Anhänge**: Aktuell nur Text-basierte Termine
3. **Single Database**: Ein Bot kann nur eine Notion-Datenbank verwalten
4. **Keine Gruppen-Chats**: Bot funktioniert nur in privaten Chats

## 📚 Nützliche Ressourcen

### APIs & Dokumentation
- [python-telegram-bot Docs](https://docs.python-telegram-bot.org/)
- [Notion API Reference](https://developers.notion.com/reference)
- [Telegram Bot API](https://core.telegram.org/bots/api)

### Beispiel-Implementierungen
- Inline Keyboards: Für Bestätigungen und Auswahl
- Conversation Handler: Für mehrstufige Dialoge
- Job Queue: Für zeitgesteuerte Tasks

## 🔧 Debugging & Troubleshooting

### Logs prüfen
```bash
tail -f bot.log           # Live-Logs
grep ERROR bot.log        # Nur Fehler
```

### Notion-Verbindung testen
```bash
python scripts/test_notion_connection.py
```

### Bot-Status prüfen
```bash
ps aux | grep bot.py      # Läuft der Bot?
netstat -tulpn | grep 443 # Netzwerk-Verbindungen
```

## 💡 Feature-Ideen für die Zukunft

1. **Voice Messages**: Sprachnachrichten zu Text konvertieren
2. **Location Sharing**: Ort aus Telegram-Location übernehmen
3. **Kalender-Ansicht**: Inline-Kalender mit python-telegram-calendar
4. **Export-Funktionen**: PDF, CSV, iCal Export
5. **Teamkalender**: Gemeinsame Kalender für Gruppen
6. **Kategorien**: Farbcodierung und Kategorisierung
7. **Zeiterfassung**: Start/Stop Timer für Termine
8. **Statistiken**: Auswertungen über Terminnutzung

## 🤝 Contribution Guidelines

1. Fork das Repository
2. Feature Branch erstellen
3. Tests schreiben (TDD!)
4. Code committen
5. Pull Request erstellen

Bitte beachte:
- Alle neuen Features brauchen Tests
- Code muss Black/isort-formatiert sein
- PR-Beschreibung sollte das "Warum" erklären

---

**Letzte Aktualisierung**: 5. Juni 2025
**Version**: 1.0.0
**Maintainer**: @EBNSchindi