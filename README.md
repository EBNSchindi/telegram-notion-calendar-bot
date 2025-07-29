# 🚀 Enhanced Telegram Notion Calendar Bot

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Telegram Bot API](https://img.shields.io/badge/Telegram%20Bot%20API-7.0-blue.svg)](https://core.telegram.org/bots/api)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Type Checked: MyPy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](http://mypy-lang.org/)

Eine professionelle, refactorisierte Telegram-Bot-Lösung für intelligente Kalender- und Memo-Verwaltung mit **Notion-Integration**, **AI-Features** und **Multi-User-Support**.

## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Installation](#️-installation--setup)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Development](#-development)
- [Testing](#-testing)
- [Deployment](#-deployment)
- [Contributing](#-contributing)
- [License](#-license)

## ✨ Features

### 🤖 **AI-Powered Features**
- **GPT-4o-mini Integration**: Natürliche Sprachverarbeitung für Termine und Memos
- **Smart Extraction**: Automatische Extraktion von Terminen und Aufgaben aus beliebigen Texten  
- **Vollständiger Kontexterhalt**: "Feierabendbier mit Peter" → Titel und Beschreibung behalten alle Details
- **Intelligente Memo-Verwaltung**: KI-gestützte Aufgabenerstellung mit deutschen Feldnamen
- **Partner-Relevanz-Abfrage**: Interaktive Buttons für gemeinsam relevante Termine
- **Fallback-Modi**: Robust bei AI-Service-Ausfällen
- **Mehrsprachig**: Deutsch und Englisch mit automatischer Erkennung

### 📝 **Memo-System (NEU)**
- **Strukturierte Memos**: Aufgabe, Status, Fälligkeitsdatum, Bereich, Projekt
- **Status-Management**: "Nicht begonnen", "In Arbeit", "Erledigt"
- **KI-Extraktion**: "Präsentation vorbereiten bis Freitag" → strukturiertes Memo
- **Kategorisierung**: Bereich und Projekt als Multi-Select-Felder
- **Integration**: Nahtlos im vereinfachten 2x2+1 Hauptmenü

### 🎛 **Vereinfachtes Hauptmenü mit Navigation**
```
📊 Datenbank-Status
🔒 Private Datenbank: ✅
👥 Geteilte Datenbank: ✅
📝 Memo Datenbank: ✅

┌─────────────────────┬─────────────────────┐
│ 📅 Termine Heute    │ 📝 Letzte 10 Memos │
│    & Morgen         │                     │
├─────────────────────┼─────────────────────┤
│ ➕ Neuer Termin     │ ➕ Neues Memo       │
├─────────────────────┴─────────────────────┤
│            ❓ Hilfe                        │
└───────────────────────────────────────────┘
```

**Features:**
- ✅ Grün = Verbindung erfolgreich
- ❌ Rot = Verbindungsfehler
- 🔙 "Zurück zum Hauptmenü" Button nach jeder Aktion
- 📝 Vollständige Terminanzeige mit Beschreibung und Ort

### 👥 **Multi-User & Database Support**
- **Private Datenbank**: Persönliche Termine und Memos pro Nutzer
- **Gemeinsame Datenbank**: Termine für alle Nutzer sichtbar  
- **Business Datenbank**: Automatische E-Mail-Synchronisation (Outlook/Gmail)
- **Vereinfachte Konfiguration**: Ein API-Key pro User statt drei separate
- **Email-Löschung**: 100% zuverlässiges Löschen nach Verarbeitung

### 🗓 **Erweiterte Zeit- & Datumsverarbeitung**
- **Wochentag-Erkennung**: `Sonntag`, `Montag` → automatisch nächster Termin
- **Deutsche Formate**: `16 Uhr`, `halb 3`, `viertel vor 5`
- **Englische Formate**: `4 PM`, `quarter past 2`, `half past 3`
- **Standard-Formate**: `14:30`, `14.30`, `1430`
- **Relative Angaben**: `heute`, `morgen`, `übermorgen`

### 📨 **Intelligente Business-Integration**
- **E-Mail-Synchronisation**: Outlook/Gmail → Notion automatisch
- **IMMER löschen**: E-Mails werden nach Verarbeitung gelöscht (unabhängig vom Erfolg)
- **30-Tage-Rückblick**: Umfassende Synchronisation
- **Sender-Whitelist**: Sicherheitsfilter für vertrauenswürdige Absender
- **Intelligente Terminextraktion**: JSON-basiertes Event-Parsing

## 🏗 Architecture

### Project Structure

```
.
├── src/                           # Source code
│   ├── bot.py                    # Main bot application
│   ├── constants.py              # Centralized constants
│   ├── handlers/                 # Message and command handlers
│   │   ├── base_handler.py       # Base handler with common functionality
│   │   ├── enhanced_appointment_handler.py  # Appointment management
│   │   ├── memo_handler.py       # Memo management
│   │   └── debug_handler.py      # Debug utilities
│   ├── services/                 # Business logic services
│   │   ├── combined_appointment_service.py  # Unified Notion API service
│   │   ├── memo_service.py       # Memo CRUD operations
│   │   ├── ai_assistant_service.py         # AI integration
│   │   ├── business_calendar_sync.py       # Email synchronization
│   │   ├── partner_sync_service.py         # Partner sharing logic
│   │   └── enhanced_reminder_service.py    # Reminder system
│   ├── models/                   # Data models
│   │   ├── appointment.py        # Appointment model
│   │   ├── memo.py              # Memo model
│   │   └── shared_appointment.py # Shared appointment model
│   ├── utils/                    # Utility modules
│   │   ├── telegram_helpers.py   # Telegram-specific utilities
│   │   ├── error_handler.py      # Centralized error handling
│   │   ├── input_validator.py    # Input validation
│   │   ├── duplicate_checker.py  # Duplicate detection
│   │   ├── robust_time_parser.py # Date/time parsing
│   │   └── rate_limiter.py       # Rate limiting
│   └── config/                   # Configuration
│       ├── settings.py           # Application settings
│       └── user_config.py        # User management
├── tests/                        # Test suite
│   ├── test_handlers/           # Handler tests
│   ├── test_services/           # Service tests
│   ├── test_integration/        # Integration tests
│   ├── test_e2e/               # End-to-end tests
│   ├── test_performance/        # Performance tests
│   └── test_security/           # Security tests
├── docs/                        # Documentation
│   ├── adr/                     # Architecture Decision Records
│   └── archive/                 # Archived documentation
└── docker-compose.yml           # Docker configuration
```

### Recent Refactoring Improvements

- ✅ **Repository Pattern**: Extracted data access logic into dedicated services
- ✅ **Handler Decomposition**: Split monolithic handlers into focused components
- ✅ **Constants Extraction**: Centralized all magic numbers and strings
- ✅ **Error Handling**: Implemented comprehensive error handling with recovery
- ✅ **Type Safety**: Added type hints throughout the codebase
- ✅ **Test Coverage**: Achieved >80% test coverage with comprehensive test suite

## ⚙️ Installation & Setup

### Prerequisites

- Python 3.10 or higher
- Telegram Bot Token (get from [@BotFather](https://t.me/botfather))
- Notion API Key and Database IDs
- OpenAI API Key (for AI features)
- Docker (optional, for containerized deployment)

### 1. Grundinstallation
```bash
git clone <repository-url>
cd telegram-notion-calendar-bot
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### 2. Umgebungskonfiguration (.env)
```env
# Telegram Bot Token
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

# OpenAI für AI-Features
OPENAI_API_KEY=your_openai_api_key

# Sicherheitseinstellungen
AUTHORIZED_USERS=123456789,987654321
ADMIN_USERS=123456789
ENVIRONMENT=production

# Optional: Business E-Mail-Integration
EMAIL_SYNC_ENABLED=true
EMAIL_ADDRESS=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
```

### 3. Configuration

#### User Configuration (users_config.json)

Create a `users_config.json` file based on the example:
```json
{
  "users": [
    {
      "telegram_user_id": 123456789,
      "telegram_username": "username",
      "notion_api_key": "secret_unified_api_key",
      "notion_database_id": "private_database_id", 
      "memo_database_id": "memo_database_id",
      "shared_notion_database_id": "shared_database_id",
      "business_notion_database_id": "business_database_id",
      "timezone": "Europe/Berlin",
      "language": "de",
      "reminder_time": "08:00",
      "reminder_enabled": true
    }
  ]
}
```

### 4. Notion Database Setup

See [docs/NOTION_SETUP.md](docs/NOTION_SETUP.md) for detailed setup instructions.

#### Memo-Datenbank (NEU)
| Property | Type | Erforderlich | Beschreibung |
|----------|------|-------------|-------------|
| Aufgabe | Title | ✅ | Memo-Titel |
| Status | Status | ✅ | Nicht begonnen, In Arbeit, Erledigt |
| Fälligkeitsdatum | Date | ❌ | Deadline |
| Bereich | Multi-Select | ❌ | Kategorien |
| Projekt | Multi-Select | ❌ | Projekt-Zuordnung |
| Notizen | Rich Text | ❌ | Zusatzinformationen |

#### Termin-Datenbank
| Property | Type | Erforderlich | Beschreibung |
|----------|------|-------------|-------------|
| Name | Title | ✅ | Termintitel |
| Datum | Date | ✅ | Terminzeit |
| Beschreibung | Rich Text | ❌ | Zusatzinfo |
| Ort | Rich Text | ❌ | Terminort |
| PartnerRelevant | Checkbox | ✅ | AI-Feature |
| OutlookID | Rich Text | ❌ | E-Mail-Integration |

## 📱 Usage

### Hauptmenü
Der Bot startet mit einem vereinfachten 2x2+1 Menü:

**Termine:** Heute & Morgen in einer Ansicht
**Memos:** Letzte 10 Memos schnell verfügbar  
**Erstellen:** Separate Buttons für Termine und Memos
**Hilfe:** Zentrale Hilfe für alle Features

### Termine erstellen (AI-gestützt)
```bash
# Natürliche Sprache - der Bot versteht:
"morgen 15 Uhr Zahnarzttermin"
"heute 16:30 Mama im Krankenhaus besuchen"
"nächsten Montag 9 Uhr Meeting mit Team"
"übermorgen 14:30 Friseur"

# Der Bot fragt automatisch:
"Soll dieser Termin auch für Partner sichtbar sein?"
[✅ Ja, für Partner relevant] [❌ Nein, nur privat]
```

### Memos erstellen (AI-gestützt)
```bash
# Natürliche Sprache für Aufgaben:
"Präsentation vorbereiten bis Freitag"
"Einkaufsliste erstellen: Milch, Brot, Butter"  
"Website Projekt: Client Feedback einholen"
"Arbeitsbereich: Meeting notes zusammenfassen"

# Automatische AI-Extraktion:
• Aufgabe: "Präsentation vorbereiten"
• Fälligkeitsdatum: Freitag (nächster)
• Status: "Nicht begonnen" (Standard)
```

### Befehle
| Befehl | Beschreibung |
|--------|-------------|
| `/start` | Hauptmenü öffnen |
| `/today` | Heutige Termine |
| `/tomorrow` | Morgige Termine |
| `/list` | Alle kommenden Termine |
| `/reminder on/off` | Erinnerungen verwalten |
| `/help` | Vollständige Hilfe |

## 🧑‍💻 Development

### Setting up Development Environment

```bash
# Clone the repository
git clone <repository-url>
cd telegram-notion-calendar-bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install development dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development tools

# Set up pre-commit hooks
pre-commit install
```

### Code Style Guidelines

- **Formatter**: Black with line length 100
- **Import Sorter**: isort with Black profile
- **Linter**: flake8 with custom configuration
- **Type Checker**: mypy with strict mode

### Running in Development Mode

```bash
# Set environment to development
export ENVIRONMENT=development

# Run with auto-reload
python -m src.bot
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test categories
pytest tests/test_handlers/  # Handler tests only
pytest tests/test_services/  # Service tests only
pytest tests/test_integration/  # Integration tests

# Run with verbose output
pytest -v -s

# Run parallel tests (faster)
pytest -n auto
```

### Test Categories

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions
- **E2E Tests**: Test complete user workflows
- **Performance Tests**: Test response times and load handling
- **Security Tests**: Test authorization and input validation

### Writing Tests

```python
# Example test structure
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_appointment_creation():
    """Test creating appointment with AI extraction."""
    # Arrange
    service = CombinedAppointmentService(user_config)
    
    # Act
    result = await service.create_appointment(
        "Tomorrow 3pm dentist appointment"
    )
    
    # Assert
    assert result.title == "dentist appointment"
    assert result.date.hour == 15
```

## 🐳 Deployment

### Docker Compose (empfohlen)
```bash
# Starten
docker compose up -d

# Logs verfolgen  
docker compose logs -f calendar-telegram-bot

# Stoppen
docker compose down

# Neu bauen
docker compose build && docker compose up -d
```

### Manuell
```bash
# Bauen
docker build -t telegram-notion-bot .

# Starten
docker run -d \
  --name calendar-telegram-bot \
  --env-file .env \
  -v $(pwd)/users_config.json:/app/users_config.json \
  -v $(pwd)/data:/app/data \
  --restart unless-stopped \
  telegram-notion-bot
```

## 🧪 Tests & Qualitätssicherung

### Umfassende Test-Suite
Das Projekt verfügt über eine vollständige Test-Suite mit über 80% Code-Coverage:

```bash
# Schnell-Installation der Test-Dependencies
pip install pytest pytest-asyncio pytest-mock pytest-cov

# Test-Runner verwenden (empfohlen)
./run_tests.sh          # Alle Tests
./run_tests.sh unit     # Nur Unit-Tests
./run_tests.sh coverage # Mit Coverage-Report
./run_tests.sh memo     # Nur Memo-Tests
./run_tests.sh quick    # Schneller Durchlauf
```

### Test-Kategorien

#### 1. **Unit Tests** (63 Tests)
- `test_memo_service.py` - Memo CRUD-Operationen
- `test_ai_assistant_service.py` - AI-Integration mit Fallback
- `test_memo_handler.py` - Telegram-Handler für Memos
- `test_partner_sync_service.py` - Partner-Sync-Logik
- `test_user_config.py` - Konfigurationsmanagement
- `test_email_processor.py` - E-Mail-Verarbeitung & Löschung

#### 2. **Integration Tests**
- `test_memo_integration.py` - End-to-End Memo-Flow
- `test_menu_navigation.py` - UI/UX Navigation
- `test_error_handling.py` - Fehlerbehandlung

### Code-Qualität
```bash
# Automatische Formatierung
black src/ tests/ --line-length 100
isort src/ tests/ --profile black

# Linting
flake8 src/ tests/ --max-line-length=100 --ignore=E203,W503

# Type-Checking
mypy src/ --ignore-missing-imports

# Security Scan
bandit -r src/ -ll
safety check
```

### Test-Coverage
```bash
# HTML Coverage Report generieren
pytest --cov=src --cov-report=html
# Report öffnen: htmlcov/index.html

# Terminal Coverage
pytest --cov=src --cov-report=term-missing
```

### CI/CD Pipeline
GitHub Actions automatisiert alle Tests:

- ✅ **Tests**: Unit & Integration Tests bei jedem Push
- ✅ **Linting**: Code-Style-Prüfung
- ✅ **Security**: Dependency-Scans
- ✅ **Docker**: Build-Tests
- ✅ **Coverage**: Automatische Reports

### Neue Features testen
```python
# Beispiel: Test für neue Memo-Funktion
@pytest.mark.asyncio
async def test_memo_with_ai_fallback():
    """Test memo creation when AI is unavailable."""
    service = AIAssistantService()
    # AI nicht verfügbar simulieren
    service.client = None
    
    result = await service.extract_memo_from_text(
        "Einkaufen gehen bis morgen"
    )
    
    assert result is not None  # Fallback aktiv
    assert result['aufgabe'] == "Einkaufen gehen bis morgen"
    assert result['faelligkeitsdatum'] is not None
```

## 🔒 Sicherheitsfeatures

### Implementierte Schutzmaßnahmen
- ✅ **Rate Limiting**: 20 Requests/Minute (Menu), 10/Minute (AI)
- ✅ **Input Validation**: Pydantic-basierte Validierung
- ✅ **Error Sanitization**: Keine Exposition interner Details
- ✅ **Authorization**: Whitelist-basierte User-Berechtigung
- ✅ **Safe Operations**: Automatic error handling contexts
- ✅ **Type Safety**: Comprehensive type hints
- ✅ **Secure Logging**: Data sanitization für sensible Informationen

### Sicherheitsklassen
```python
# Centralized error handling
from src.utils.error_handler import BotError, ErrorType, ErrorSeverity

# Safe operation contexts  
async with SafeOperationContext("memo_creation", ErrorType.VALIDATION):
    # Code that might fail safely

# Decorators for error handling
@handle_bot_error(ErrorType.AI_SERVICE, ErrorSeverity.MEDIUM)
async def ai_function():
    # AI operations with automatic error handling
```

## 🔄 Migration & Changelog

### Version 3.0.1 (2025-01-21) - AI Debugging & Test Suite 🧪
- **🧪 Umfassende Test-Suite**
  - 63+ Unit Tests mit >80% Coverage
  - Integration Tests für alle Features
  - Mock-Tests für externe Services
  - CI/CD Pipeline mit GitHub Actions

- **🤖 AI-Service Verbesserungen**
  - Robuster Fallback ohne OpenAI API
  - Verbesserte Fehlerbehandlung
  - Debug-Logging für AI-Operationen
  - Basic Memo-Extraktion als Backup

- **📊 Erweiterte Tests**
  - E-Mail-Löschung vollständig getestet
  - Menu-Navigation Tests
  - Error-Handling Szenarien
  - Partner-Sync Validierung

### Version 3.0.0 (2025-01-20) - Refactoring & Memo Revolution 📝
- **🏗 Code-Refactoring**
  - Neue modulare Architektur mit Base-Handler
  - Zentrale Konstanten und Error Handling
  - DRY-Prinzip konsequent umgesetzt
  - Telegram-Utilities für konsistente Formatierung
  
- **📝 Memo-System**
  - Vollständig integriertes Memo-Management
  - Deutsche Feldnamen (Aufgabe, Status, Fälligkeitsdatum)  
  - AI-gestützte Memo-Extraktion aus natürlicher Sprache
  - Status-Verwaltung mit visuellen Indikatoren
  - Multi-Select-Unterstützung für Bereiche und Projekte

- **🎛 Vereinfachtes Interface**  
  - 2x2+1 Menü-Layout (statt 6 Buttons + Untermenüs)
  - 50% weniger Klicks für Haupt-Aktionen
  - Kombinierte Heute/Morgen-Ansicht
  - Optimierte User Experience

- **⚙️ Konfigurationsvereinfachung**
  - Ein `notion_api_key` statt drei separate Keys
  - Backward-kompatible Migration  
  - Automatische Platzhalter-Erkennung
  - Robuste User-Validierung

- **🔧 Technische Verbesserungen**
  - 100% E-Mail-Löschung nach Verarbeitung
  - Zentrale Error-Handler-Klasse
  - Type-safe operations mit Pydantic
  - Comprehensive logging und monitoring

### Migration von 2.x
1. **Automatisch**: Bestehende Konfigurationen bleiben funktional
2. **Optional**: `notion_api_key` vereinheitlichen in `users_config.json`
3. **Neu**: Memo-Datenbank pro User einrichten
4. **Empfohlen**: Tests ausführen: `pytest tests/`

## 📈 Roadmap

### 🎯 Kurzfristig (Q3 2025)
- [ ] Web-Interface für User-Management
- [ ] Termin-Editing über Bot-Interface
- [ ] Kalender-Export (ICS-Format)
- [ ] Erweiterte Memo-Filter und -Suche

### 🚀 Mittelfristig (Q4 2025)
- [ ] Wiederkehrende Termine mit AI-Erkennung
- [ ] Terminkonflikt-Erkennung
- [ ] Integration mit Google Calendar/Outlook
- [ ] Multi-Language-Support (Französisch, Spanisch)

### 🔬 Langfristig (2026)
- [ ] Machine Learning für Terminpräferenzen  
- [ ] Voice-to-Text Integration
- [ ] Mobile App Companion
- [ ] Team-Collaboration Features

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Quick Start for Contributors

1. **Fork** the repository
2. **Clone** your fork: `git clone <your-fork-url>`
3. **Branch**: `git checkout -b feature/your-feature`
4. **Code**: Make your changes
5. **Test**: Run `pytest` to ensure tests pass
6. **Commit**: Use conventional commits
7. **Push**: `git push origin feature/your-feature`
8. **PR**: Open a pull request

### Commit Message Format

```
type(scope): subject

body

footer
```

Types: feat, fix, docs, style, refactor, test, chore

### Code Review Process

1. Automated checks must pass
2. At least one maintainer approval required
3. All feedback must be addressed
4. Squash and merge preferred

### Entwickler-Guidelines
1. **Code Style**: Black + isort für Formatierung
2. **Testing**: 100% Test-Coverage für neue Features
3. **Documentation**: Docstrings für alle öffentlichen APIs
4. **Type Hints**: Vollständige Typisierung erforderlich
5. **Security**: Input-Validierung und Error-Handling

### Pull Request Prozess
1. Fork das Repository
2. Feature-Branch erstellen (`git checkout -b feature/amazing-feature`)
3. Tests schreiben und ausführen (`pytest`)
4. Code-Quality prüfen (`make lint`)  
5. Pull Request erstellen mit detaillierter Beschreibung

### Code-Architektur-Prinzipien
- **Single Responsibility**: Eine Klasse = ein Zweck
- **DRY (Don't Repeat Yourself)**: Keine Code-Duplikation
- **SOLID Principles**: Besonders Interface Segregation
- **Clean Code**: Selbsterklärender Code vor Kommentaren
- **Error Handling**: Defensive Programmierung mit try/catch

## 📄 License

MIT License - siehe [LICENSE](LICENSE) Datei für Details.

---

<div align="center">

**Built with** ❤️ **by the Open Source Community**

[![GitHub Stars](https://img.shields.io/github/stars/username/telegram-notion-calendar-bot?style=social)](https://github.com/username/telegram-notion-calendar-bot)
[![GitHub Issues](https://img.shields.io/github/issues/username/telegram-notion-calendar-bot)](https://github.com/username/telegram-notion-calendar-bot/issues)
[![GitHub Pull Requests](https://img.shields.io/github/issues-pr/username/telegram-notion-calendar-bot)](https://github.com/username/telegram-notion-calendar-bot/pulls)

[Report Bug](https://github.com/username/telegram-notion-calendar-bot/issues) · [Request Feature](https://github.com/username/telegram-notion-calendar-bot/issues) · [Documentation](docs/)

</div>