# Calendar Telegram Bot mit Notion Integration

Ein Python-basierter Telegram Bot für Kalender-Management mit Notion als Backend. Entwickelt mit Test-Driven Development (TDD) und iterativer Entwicklung.

## ✨ Features

- 📅 Termine über Telegram-Commands erstellen
- 📊 Termine in Notion-Datenbank speichern und verwalten
- 🔍 Termine anzeigen (heute, alle kommenden)
- 🌍 Timezone-Unterstützung (Standard: Europe/Berlin)
- 🐳 Docker-basierte Bereitstellung
- 🧪 Umfassende Test-Abdeckung
- 🔒 Sichere Konfiguration über Umgebungsvariablen

## 🚀 Quick Start

### 1. Repository setup
```bash
git clone <repository-url>
cd calendar-bot-app
make dev  # Installiert Dependencies
```

### 2. Notion Integration einrichten
```bash
make setup-notion  # Zeigt detaillierte Anweisungen
```

### 3. Telegram Bot erstellen
1. Schreibe [@BotFather](https://t.me/botfather) auf Telegram
2. Verwende `/newbot` und folge den Anweisungen
3. Kopiere den Bot Token

### 4. Konfiguration
```bash
cp .env.example .env
# Fülle .env mit deinen API Keys aus:
# TELEGRAM_BOT_TOKEN=dein_bot_token
# NOTION_API_KEY=dein_notion_token  
# NOTION_DATABASE_ID=deine_database_id
```

### 5. Testen
```bash
make test  # Alle Tests ausführen
```

### 6. Bot starten
```bash
make run-local  # Lokal ausführen
# oder
make docker-run  # Mit Docker
```

## 🤖 Bot-Befehle

### Grundlegende Befehle
- `/start` - Bot starten und Verbindungsstatus prüfen
- `/help` - Hilfe und Beispiele anzeigen

### Termine verwalten
- `/add <datum> <zeit> <titel> [beschreibung]` - Neuen Termin erstellen
- `/today` - Heutige Termine anzeigen  
- `/list` - Alle kommenden Termine anzeigen

### Beispiele
```
/add morgen 14:00 Meeting Team-Besprechung
/add heute 15:30 Arzttermin Wichtiger Checkup
/add 25.12.2024 18:00 Weihnachtsfeier Familie
```

### Unterstützte Datum-Formate
- `heute`, `today` - Heutiges Datum
- `morgen`, `tomorrow` - Morgiges Datum  
- `25.12.2024` - Absolutes Datum (DD.MM.YYYY)
- `2024-12-25` - ISO-Format (YYYY-MM-DD)

### Zeit-Formate
- `14:00` oder `14.00` - 24-Stunden Format

## 🧪 Entwicklung & Testing

### Test-Driven Development
Das Projekt folgt TDD-Prinzipien mit umfassender Test-Abdeckung:

```bash
make test              # Alle Tests
make test-unit         # Nur Unit Tests  
make test-integration  # Nur Integration Tests
make test-watch        # Tests im Watch-Modus
```

### Code-Qualität
```bash
make lint              # Code-Linting mit flake8
make format            # Code-Formatierung mit black/isort
make format-check      # Formatierung prüfen
make type-check        # Type-Checking mit mypy
```

### Projekt-Struktur
```
calendar-bot-app/
├── src/
│   ├── models/
│   │   └── appointment.py     # Datenmodell für Termine
│   ├── services/
│   │   └── notion_service.py  # Notion API Integration
│   ├── handlers/
│   │   └── appointment_handler.py # Telegram Command Handler
│   └── bot.py                 # Haupt-Bot-Logik
├── tests/
│   ├── test_appointment_model.py
│   ├── test_notion_service.py
│   └── test_appointment_handler.py
├── config/
│   └── settings.py            # Konfigurationsmanagement
├── docker-compose.yml         # Docker Setup
├── requirements.txt           # Python Dependencies
├── Makefile                   # Entwicklungs-Commands
└── README.md
```

## 🐳 Docker Deployment

### Entwicklung
```bash
make docker-build     # Image bauen
make docker-run       # Produktiv laufen lassen
make docker-dev       # Development-Modus
```

### Produktiv
```bash
docker-compose up -d
docker-compose logs -f calendar-bot  # Logs anzeigen
```

## 🔧 Notion Database Setup

Deine Notion-Datenbank sollte folgende Eigenschaften haben:

| Property | Type | Required |
|----------|------|----------|
| Title | Title | ✅ |
| Date | Date | ✅ |
| Description | Text | ❌ |
| Created | Date | ✅ |

Detaillierte Setup-Anweisungen: `make setup-notion`

## 📊 Test Coverage

```bash
# Test-Coverage anzeigen
pytest --cov=src --cov-report=html
# Öffne htmlcov/index.html im Browser
```

## 🔒 Sicherheit

- Alle Credentials über Umgebungsvariablen
- Niemals `.env` in Git committen
- Bot läuft als Non-Root-User im Container
- Input-Validierung und Error-Handling

## 🚀 Nächste Entwicklungsschritte

1. **Termin-Bearbeitung**: `/edit` und `/delete` Commands
2. **Erinnerungen**: Automatische Benachrichtigungen
3. **Recurring Events**: Wiederholende Termine
4. **Calendar Sync**: Google Calendar Integration
5. **Multi-User**: User-Management und Permissions

## 🐛 Troubleshooting

### Bot antwortet nicht
```bash
docker-compose logs calendar-bot  # Logs prüfen
make test  # Tests laufen lassen
```

### Notion-Verbindung fehlt
1. API Key korrekt? (sollte mit `secret_` beginnen)
2. Database ID korrekt? 
3. Integration mit Datenbank geteilt?
4. Datenbank-Properties korrekt benannt?

### Tests schlagen fehl
```bash
make clean  # Aufräumen
make install  # Dependencies neu installieren
make test  # Tests erneut ausführen
```

## 📝 Beitragen

1. Fork das Repository
2. Erstelle einen Feature-Branch
3. Schreibe Tests für neue Features
4. Stelle sicher dass alle Tests bestehen
5. Erstelle einen Pull Request

## 📄 Lizenz

MIT License - siehe [LICENSE](LICENSE) Datei.