# 🚀 Enhanced Telegram Notion Calendar Bot

Eine erweiterte Version des Telegram Notion Calendar Bots mit **Multi-User-Support**, **kombinierten Datenbanken**, **visuellem Menü** und **intelligenter Wochentag-Erkennung**.

## ✨ Features

### 🎛 **Visuelles Hauptmenü**
- Intuitive Bedienung mit Inline-Buttons
- Schneller Zugriff auf alle Funktionen
- Automatische Menü-Öffnung beim Chat-Start
- ForceReply für einfache Terminerfassung

### 👥 **Multi-User & Triple-Database Support**
- **Private Datenbank**: Persönliche Termine pro Nutzer
- **Gemeinsame Datenbank**: Termine für alle Nutzer sichtbar
- **Business Datenbank**: Automatische E-Mail-Synchronisation von Outlook/Gmail
- Automatische Kombination aller Datenquellen
- Individuelle Konfiguration pro Benutzer
- **Intelligente User-Validierung**: Ungültige Platzhalter-Konfigurationen werden automatisch ignoriert

### 🗓 **Intelligente Datums- und Zeitverarbeitung**
- **Wochentag-Erkennung**: `Sonntag`, `Montag`, `Freitag` → automatisch nächster Termin
- **Deutsch**: `16 Uhr`, `halb 3`, `viertel vor 5`
- **English**: `4 PM`, `quarter past 2`, `half past 3`, `Monday`, `Sunday`
- **Standard**: `14:30`, `14.30`, `1430`
- **Relativ**: `heute`, `morgen`, `übermorgen`
- Robuste Fehlerbehandlung

### 📨 **Intelligente Erinnerungen & Business Email Integration**
- Kombiniert Termine aus allen drei Datenbanken
- Kennzeichnung der Terminquelle (👤 privat / 🌐 gemeinsam / 📧 business)
- **Automatische E-Mail-Synchronisation**: Gmail/Outlook-Kalender-Events
- **Sender-Whitelist**: Sicherheitsfilter für vertrauenswürdige E-Mail-Absender
- **JSON-basierte Event-Parsing**: Intelligente Terminextraktion aus E-Mails
- Konfigurierbare Erinnerungszeit
- Vorschau-Funktion

### 🤖 **Bot-Kommandos & Menü**
- Automatisches Kommando-Menü in Telegram
- `/start` öffnet direkt das Hauptmenü
- Alle Befehle über Bot-Menü verfügbar

## 📱 Hauptmenü

Beim Start (`/start`) erscheint ein interaktives Menü:

```
📅 Heutige Termine    🗓️ Termine für morgen
📋 Alle anstehenden   ➕ Neuen Termin hinzufügen  
⚙️ Erinnerungen      ❓ Hilfe
```

## 👥 Multi-User Setup

Der Bot unterstützt **mehrere Benutzer** mit individuellen Konfigurationen:

### Neuen Benutzer hinzufügen

#### 1. **Telegram User ID ermitteln**
```
Neuer Benutzer tippt: /start
Bot antwortet: "❌ Du bist noch nicht konfiguriert. Deine User ID: 987654321"
```

#### 2. **Notion für neuen Benutzer einrichten**
- [notion.com](https://notion.com) → **"My integrations"**
- **"New integration"** erstellen
- **API-Key kopieren** (beginnt mit `secret_`)
- **Kalender-Datenbank** erstellen
- **Integration zur Datenbank hinzufügen**

#### 3. **Benutzer konfigurieren**
In `users_config.json` hinzufügen:
```json
{
  "bestehender_user_id": { ... },
  "987654321": {
    "telegram_user_id": 987654321,
    "telegram_username": "neuer_username", 
    "notion_api_key": "secret_neuer_key_hier",
    "notion_database_id": "neue_database_id",
    "timezone": "Europe/Berlin",
    "language": "de"
  }
}
```

#### 4. **Berechtigung erteilen**
In `.env` die User ID hinzufügen:
```env
AUTHORIZED_USERS=bestehende_id,987654321
```

#### 5. **Bot testen**
```
Neuer Benutzer tippt: /start
Bot antwortet: "Hallo [Name]! 👋 Dein Kalender-Bot ist bereit!"
```

### 🔐 Sicherheitseinstellungen

```env
# Berechtigte Benutzer (komma-getrennte User IDs)
AUTHORIZED_USERS=123456,789012

# Admin-Benutzer für Debug-Befehle
ADMIN_USERS=123456
```

### 📊 Datentrennung
- **Jeder Benutzer** hat seine eigene Notion-Datenbank
- **Getrennte Kalender** - Benutzer sehen nur ihre Termine
- **Optional**: Gemeinsame Team-Datenbank für alle

---

## ⚙️ Installation & Konfiguration

### 1. Grundsetup
```bash
git clone <repository-url>
cd telegram-notion-calendar-bot
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oder venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 2. Umgebungsvariablen (.env)

⚠️ **Wichtig**: Kopiere `.env.example` zu `.env` und trage deine echten Credentials ein.

```env
# Telegram Bot Token (für alle Nutzer gleich)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

# Business Email Integration (optional)
EMAIL_SYNC_ENABLED=true
EMAIL_ADDRESS=your_gmail_address@gmail.com
EMAIL_PASSWORD=your_gmail_app_password
OUTLOOK_SENDER_WHITELIST=trusted_sender@company.com

# Sicherheitseinstellungen
AUTHORIZED_USERS=123456789,987654321
```

### 3. Benutzerkonfiguration (users_config.json)

⚠️ **Wichtig**: Kopiere `users_config.example.json` zu `users_config.json` und trage echte Credentials ein.

```json
{
  "users": [
    {
      "telegram_user_id": 123456789,
      "telegram_username": "user1",
      "notion_api_key": "secret_private_api_key_user1",
      "notion_database_id": "private_database_id_user1",
      "shared_notion_api_key": "secret_shared_api_key",
      "shared_notion_database_id": "shared_database_id",
      "business_notion_api_key": "secret_business_api_key",
      "business_notion_database_id": "business_database_id",
      "timezone": "Europe/Berlin",
      "language": "de",
      "reminder_time": "08:00",
      "reminder_enabled": true
    }
  ]
}
```

🔒 **Sicherheitsfeatures:**
- **Automatische Platzhalter-Erkennung**: Ungültige Configs werden ignoriert
- **Mindestens-ein-User-Validierung**: Bot startet nur mit gültigen Usern
- **API-Key-Validierung**: Prüft auf echte Notion-API-Keys (beginnen mit `secret_` oder `ntn_`)
- **Database-ID-Validierung**: Prüft auf gültige Notion-Database-IDs

### 4. Bot starten
```bash
# Enhanced Version mit allen Features
python src/bot.py

# oder mit Skript
./run_bot.sh
```

## 📋 Befehle & Nutzung

### Hauptbefehle
| Befehl | Beschreibung |
|--------|-------------|
| `/start` | Hauptmenü anzeigen |
| `/menu` | Menü anzeigen (Alias) |
| `/help` | Ausführliche Hilfe |
| `/today` | Heutige Termine (👤 + 🌐) |
| `/tomorrow` | Morgige Termine (👤 + 🌐) |
| `/list` | Alle kommenden Termine |

### Termine erstellen
```bash
/add <Datum> <Zeit> <Titel> [Beschreibung]
```

**Neue Beispiele mit Wochentag-Erkennung:**
```bash
# Wochentage (automatisch nächster Termin)
/add Sonntag 17 Uhr Sasi
/add Montag 9 Uhr Meeting
/add Freitag 14:30 Besprechung

# Deutsch
/add morgen 16 Uhr Meeting
/add heute halb 10 Frühstück
/add 25.12.2024 viertel vor 8 Weihnachtsfeier

# English
/add Sunday 4 PM Meeting
/add Monday quarter past 9 Breakfast
/add Friday half past 2 Team Call

# Standard
/add morgen 14:30 Besprechung
/add heute 1430 Termin
```

### Über das Menü
1. Klicke "➕ Neuen Termin hinzufügen"
2. Gib deinen Termin ein (ohne `/add`): `Sonntag 17 Uhr Sasi`
3. Der Bot erkennt automatisch alle Formate

### Erinnerungen verwalten
```bash
/reminder              # Aktuelle Einstellungen
/reminder on           # Aktivieren
/reminder off          # Deaktivieren
/reminder time 09:00   # Zeit ändern
/reminder test         # Test senden
/reminder preview      # Vorschau anzeigen
```

## 🗂 Datenbank-Setup

### Private Datenbank (pro Nutzer)
Jeder Nutzer benötigt eine eigene Notion-Datenbank mit:

| Property | Type | Erforderlich | Zweck |
|----------|------|-------------|-------|
| Name | Title | ✅ | Termintitel |
| Datum | Date | ✅ | Terminzeit |
| Beschreibung | Text | ❌ | Zusatzinfo |
| OutlookID | Text | ❌ | Business Email Integration |
| Organizer | Text | ❌ | Business Email Integration |
| Created | Date | ✅ | Erstellzeit |

### Gemeinsame Datenbank
Eine zentrale Datenbank für alle Nutzer mit derselben Struktur wie die Private Datenbank.

### Business Datenbank (optional)
Für automatische E-Mail-Synchronisation:
- **Gleiche Struktur** wie Private/Shared Datenbank
- **OutlookID**: Eindeutige Identifikation von E-Mail-Events
- **Organizer**: Automatisch aus E-Mail-Absender extrahiert
- **Automatische Updates**: Termine werden bei E-Mail-Änderungen aktualisiert

## 🎯 Features im Detail

### Intelligente Wochentag-Erkennung
```bash
# Heutiger Tag: Freitag
/add Sonntag 17 Uhr Sasi        → Nächster Sonntag
/add Montag 9 Uhr Meeting       → Nächster Montag  
/add Freitag 14 Uhr Termin      → Nächster Freitag (nächste Woche)
```

Unterstützte Wochentage:
- **Deutsch**: Montag, Dienstag, Mittwoch, Donnerstag, Freitag, Samstag, Sonntag
- **English**: Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday

### Kombinierte Terminanzeige
```
📋 Termine für heute (06.06.2025):

📅 Heute (06.06.2025)
👤 09:00 - Privater Termin
   Persönliche Notiz
🌐 14:00 - Team Meeting
   Gemeinsamer Termin für alle
📧 16:00 - Daily Standup
   Automatisch aus E-Mail synchronisiert

👤 Private Termine | 🌐 Gemeinsame Termine | 📧 Business Termine
```

### Erweiterte Zeitformate
| Format | Beispiel | Ergebnis |
|--------|----------|----------|
| Standard | `14:30`, `14.30`, `1430` | 14:30 |
| Einfach | `15` | 15:00 |
| Deutsch | `16 Uhr`, `halb 3`, `viertel vor 5` | 16:00, 2:30, 4:45 |
| English | `4 PM`, `quarter past 2`, `half past 3` | 16:00, 2:15, 3:30 |

## 🧪 Tests & Entwicklung

### Tests ausführen
```bash
# Alle Tests
make test

# Spezifische Module
pytest tests/test_enhanced_time_parser.py
pytest tests/test_user_config.py

# Mit Coverage
pytest --cov=src tests/
```

### Code-Qualität
```bash
make lint              # Linting mit flake8
make format            # Formatierung mit black/isort
make type-check        # Type-Checking mit mypy
```

### Projekt-Struktur
```
telegram-notion-calendar-bot/
├── src/
│   ├── bot.py                           # Haupt-Bot (Enhanced)
│   ├── handlers/
│   │   ├── enhanced_appointment_handler.py # Terminverwaltung + Menü
│   │   └── debug_handler.py             # Debug-Tools
│   ├── services/
│   │   ├── combined_appointment_service.py # Dual-DB Support
│   │   ├── enhanced_reminder_service.py    # Intelligente Erinnerungen
│   │   └── notion_service.py            # Notion API
│   ├── models/
│   │   └── appointment.py               # Datenmodell
│   └── utils/
│       └── robust_time_parser.py        # Erweiterte Zeitverarbeitung
├── tests/                               # Umfassende Tests
├── config/                              # Konfiguration
├── docs/                                # Dokumentation
└── requirements.txt                     # Dependencies
```

## 🐳 Docker Deployment

### Docker Compose
```bash
# Produktiv starten (neuere Docker-Versionen)
docker compose up -d

# Für ältere Docker-Versionen:
# docker-compose up -d

# Logs anzeigen
docker compose logs -f

# Container stoppen
docker compose down

# Container neu bauen und starten
docker compose build
docker compose up -d
```

### Manuell
```bash
# Bild erstellen
docker build -t telegram-notion-bot .

# Container starten
docker run -d \
  --name notion-bot \
  --env-file .env \
  -v $(pwd)/users_config.json:/app/users_config.json \
  --restart unless-stopped \
  telegram-notion-bot
```

### Wichtige Hinweise
- Der Bot startet automatisch `src/bot.py` 
- Die `.env` Datei wird über `--env-file` eingebunden
- `users_config.json` wird als Volume gemountet
- Container startet automatisch neu bei Fehlern

## 🐛 Fehlerbehebung

### "Du bist noch nicht konfiguriert"
1. Telegram User ID ermitteln (wird beim ersten `/start` angezeigt)
2. User in `users_config.json` hinzufügen
3. Bot neu starten

### "Ungültiges Datum: Sonntag"
✅ **Behoben!** Der Bot erkennt jetzt automatisch Wochentage und wählt den nächsten Termin.

### Zeitformat wird nicht erkannt
Unterstützte Formate mit `/help` überprüfen. Der RobustTimeParser unterstützt viele Formate.

### Termine aus gemeinsamer DB werden nicht angezeigt
- `shared_notion_api_key` und `shared_notion_database_id` prüfen
- Berechtigung für gemeinsame Datenbank sicherstellen

### Erinnerungen kommen nicht an
1. `reminder_enabled: true` in Konfiguration
2. Bot-Logs auf Fehler prüfen: `tail -f bot.log`
3. Mit `/reminder test` testen

## 🔄 Migration & Upgrades

### Von älteren Versionen
1. Alte Bot-Dateien wurden automatisch bereinigt
2. Nur noch `src/bot.py` verwenden
3. Cache-Dateien wurden aufgeräumt
4. Tests aktualisiert

### Neue Features in dieser Version
- ✅ **Wochentag-Erkennung**: "Sonntag", "Montag", etc.
- ✅ **Automatisches Menü**: Öffnet sich beim Chat-Start
- ✅ **Bereinigter Code**: Alte Dateien entfernt
- ✅ **Verbesserte Dokumentation**: Konsolidiert und aktuell

## 🔒 Sicherheitsfeatures

### Implementierte Sicherheitsmaßnahmen
- ✅ **Rate Limiting**: Schutz vor DoS-Angriffen (30 Anfragen/Minute)
- ✅ **Input-Validierung**: Pydantic-basierte Eingabeprüfung
- ✅ **Admin-Berechtigung**: Debug-Befehle nur für autorisierte Admins
- ✅ **JSON Size Limits**: Schutz vor großen Payloads (50KB Email, 10KB JSON)
- ✅ **Sichere Fehlerbehandlung**: Keine Exposition interner Fehlerdetails
- ✅ **HTML-Escaping**: XSS-Schutz für alle Benutzereingaben
- ✅ **Automatische Config-Validierung**: Ungültige Platzhalter-User werden ignoriert
- ✅ **Mindestens-ein-User-Validierung**: Bot startet nur mit gültigen Konfigurationen
- ✅ **E-Mail-Sender-Whitelist**: Nur vertrauenswürdige Absender können Events erstellen
- ✅ **Credential-Schutz**: .env und users_config.json werden automatisch von Version Control ausgeschlossen

### Sicherheitskonfiguration
```env
# .env Datei
AUTHORIZED_USERS=123456,789012  # Berechtigte Bot-Nutzer
ADMIN_USERS=123456              # Admin für Debug-Befehle
ENVIRONMENT=production          # production/development/testing
```

### Debug-Befehle (nur für Admins)
```bash
/test_time 16 Uhr       # Zeitformat testen
/formats               # Alle unterstützten Formate
/validate morgen 14:00 Meeting  # Eingabe validieren
/test_notion           # Notion-Verbindung testen
```

### Empfohlene Sicherheitspraktiken
1. **API-Keys regelmäßig rotieren**
2. **ADMIN_USERS auf Minimum beschränken**
3. **Bot-Logs regelmäßig überprüfen**
4. **Dependencies aktuell halten**
5. **Rate-Limits bei Bedarf anpassen**

## 📈 Geplante Features

- [ ] Termine bearbeiten/löschen über Menü
- [ ] Kalender-Export (ICS)
- [ ] Wiederkehrende Termine
- [ ] Web-Interface für Benutzerverwaltung
- [ ] Mehrsprachige Oberfläche
- [ ] Erweiterte Terminfilter
- [ ] Encrypted Config Storage
- [ ] Exchange/Office365 Integration
- [ ] Kalender-Synchronisation zwischen Usern
- [ ] Erweiterte E-Mail-Parsing-Regeln

## 🚀 Makefile Commands

```bash
make help          # Alle verfügbaren Commands
make install       # Dependencies installieren
make test          # Tests ausführen
make lint          # Code-Linting
make format        # Code-Formatierung
make run-local     # Bot lokal starten
make docker-run    # Bot mit Docker starten
make clean         # Aufräumen
```

## 🤝 Beitragen

Pull Requests sind willkommen! Für größere Änderungen bitte zuerst ein Issue erstellen.

### Entwicklung
1. Fork das Repository
2. Erstelle einen Feature-Branch
3. Schreibe Tests für neue Features
4. Stelle sicher dass `make test` und `make lint` bestehen
5. Erstelle einen Pull Request

## 📄 Lizenz

MIT License - siehe [LICENSE](LICENSE) Datei

---

**Enhanced by:** Multi-User Support, Visual Menu, Combined Databases, Smart Reminders, Weekday Recognition 🚀

**Current Version:** Enhanced Single-Bot Multi-User with Intelligent Date Parsing