# 📧 Business Email-Termin-Prozessor

Automatische Verarbeitung geschäftlicher Termine aus weitergeleiteten Outlook-Emails direkt in Ihre Notion-Datenbanken.

## ✨ Features

### 🔄 **Automatische Email-Verarbeitung**
- IMAP-basierter Abruf von Gmail-Konten
- Intelligente JSON-Extraktion aus Email-Body
- Alle 5 Minuten automatische Synchronisation
- Unterstützung für mehrere Benutzer

### 📅 **Geschäftstermin-Management**
- **Create**: Neue Termine automatisch anlegen
- **Update**: Bestehende Termine aktualisieren  
- **Delete**: Termine automatisch löschen
- Duplikat-Vermeidung über Outlook-IDs

### 🎯 **Intelligentes Routing**
- **Geschäftstermine** → Immer in Business-Datenbank
- **Team-Events** → Zusätzlich in Shared-Datenbank
- Automatische Erkennung über Keywords: "Team", "Meeting", "gemeinsam", etc.

### 🛡️ **Sicherheit & Fehlerbehandlung**
- Safeguard: Emails nur nach erfolgreicher Speicherung löschen
- 3 Retry-Versuche bei Notion API-Fehlern
- Automatischer IMAP-Reconnect
- Umfassendes Logging und Monitoring

## 📋 Email-Format

### Erwartetes Format
```
Betreff: Terminweiterleitung (oder ähnlich)

{"Action":"Create","OutlookICalID":"040000008200E00074C5B7101A82E00807E9051B","EventTitle":"Team Meeting - Q1 Planning","EventStart":"2025-06-03T14:30:00.0000000","EventEnd":"2025-06-03T14:55:00.0000000","Organizer":"Daniel.Schindler@dm.de"}

[Firmen-Footer wird ignoriert]
```

### JSON-Struktur
```json
{
  "Action": "Create|Update|Delete",
  "OutlookICalID": "Unique-Outlook-ID",
  "EventTitle": "Termin-Titel",
  "EventStart": "2025-06-03T14:30:00.0000000",
  "EventEnd": "2025-06-03T14:55:00.0000000", 
  "Organizer": "email@firma.de"
}
```

### Unterstützte Actions
- **Create**: Neuen Termin anlegen
- **Update**: Bestehenden Termin aktualisieren (via OutlookICalID)
- **Delete**: Termin löschen (via OutlookICalID)

## ⚙️ Konfiguration

### 1. Umgebungsvariablen (.env)
```env
# Email Sync Configuration
EMAIL_SYNC_ENABLED=true
EMAIL_ADDRESS=business@gmail.com
EMAIL_PASSWORD=your_gmail_app_password
IMAP_SERVER=imap.gmail.com
IMAP_PORT=993
EMAIL_CHECK_INTERVAL=300

# Business Calendar Database
BUSINESS_NOTION_DATABASE_ID=your_business_database_id

# Email Processing Settings
DELETE_AFTER_PROCESSING=false
OUTLOOK_SENDER_WHITELIST=daniel.schindler@dm.de,other@company.com

# Security
AUTHORIZED_USERS=123456789,987654321
```

### 2. Gmail App Password einrichten
1. Google-Konto → Sicherheit → 2-Schritt-Verifizierung aktivieren
2. App-Passwörter → Neues App-Passwort generieren
3. App-Passwort in `EMAIL_PASSWORD` eintragen

### 3. Notion-Datenbank erweitern
Fügen Sie diese Felder zu Ihren Notion-Datenbanken hinzu:

| Feldname | Typ | Beschreibung |
|----------|-----|--------------|
| OutlookID | Text | Outlook Calendar ID (für Duplikat-Vermeidung) |
| Organizer | Text | Email des Organisators |
| Duration | Number | Termindauer in Minuten |
| BusinessEvent | Checkbox | Kennzeichnung für Geschäftstermine |

## 🚀 Setup & Installation

### 1. Dependencies installieren
```bash
pip install -r requirements.txt
```

### 2. Konfiguration testen
```bash
python scripts/test_email_integration.py
```

### 3. Bot mit Email-Integration starten
```bash
python src/bot.py
```

## 📊 Monitoring & Logs

### Log-Ausgaben
```
2025-06-11 20:45:14 - INFO - Business calendar sync started
2025-06-11 20:45:15 - INFO - Found 3 emails
2025-06-11 20:45:16 - INFO - Parsed event: Team Meeting (Create)
2025-06-11 20:45:17 - INFO - Saved business event to business database
2025-06-11 20:45:18 - INFO - Successfully processed email xyz123
```

### Statistiken abrufen
Die Business Calendar Sync sammelt Statistiken:
- Verarbeitete Emails
- Erstellte/Aktualisierte/Gelöschte Termine
- Fehleranzahl
- Letzte Synchronisation

## 🔧 Erweiterte Konfiguration

### Team-Event-Erkennung anpassen
Bearbeiten Sie `src/services/json_parser.py`:
```python
def is_team_event(self) -> bool:
    team_keywords = [
        'gemeinsam', 'team', 'meeting', 'besprechung',
        'workshop', 'betriebsausflug', 'firmenevent',
        # Fügen Sie Ihre Keywords hinzu
        'custom_keyword'
    ]
```

### Whitelist für Absender erweitern
```env
OUTLOOK_SENDER_WHITELIST=user1@company.com,user2@company.com,calendar@company.com
```

### Sync-Intervall anpassen
```env
EMAIL_CHECK_INTERVAL=120  # Alle 2 Minuten (nicht empfohlen < 60s)
```

## 🐛 Troubleshooting

### "Email sync disabled"
- Setzen Sie `EMAIL_SYNC_ENABLED=true` in `.env`
- Überprüfen Sie Email-Zugangsdaten

### "IMAP authentication failed"
- Überprüfen Sie Gmail App-Passwort
- Stellen Sie sicher, dass 2FA aktiviert ist
- Prüfen Sie Email-Adresse auf Tippfehler

### "Notion connection test failed"
- Überprüfen Sie Notion API Keys
- Stellen Sie sicher, dass Datenbank-IDs korrekt sind
- Prüfen Sie Database-Berechtigungen

### "No JSON pattern found"
- Email-Format überprüfen
- JSON muss in der ersten Zeile stehen
- Firmen-Footer wird automatisch ignoriert

### Emails werden nicht gelöscht
- `DELETE_AFTER_PROCESSING=true` setzen (Vorsicht!)
- Standardmäßig werden Emails nur als gelesen markiert

## 📁 Code-Struktur

```
src/services/
├── json_parser.py              # JSON-Extraktion aus Emails
├── email_processor.py          # IMAP Email-Verarbeitung  
├── business_calendar_sync.py   # Hauptlogik für Sync
└── notion_service.py          # Erweitert um Business-Felder

src/models/
└── appointment.py             # Erweitert um OutlookID, Organizer, etc.

scripts/
└── test_email_integration.py  # Test-Suite
```

## 🔒 Sicherheitshinweise

### Sensible Daten
- Gmail App-Passwörter sind sensibel → Niemals committen
- Notion API Keys niemals in Logs ausgeben
- Outlook-IDs können IDs enthalten → Logs prüfen

### Authorisierung
```env
AUTHORIZED_USERS=123456789,987654321  # Nur diese User IDs
OUTLOOK_SENDER_WHITELIST=domain.com   # Nur von diesen Absendern
```

### Email-Sicherheit
- Emails werden nur nach erfolgreicher Notion-Speicherung gelöscht
- Fehlgeschlagene Emails bleiben zur manuellen Prüfung erhalten
- Safeguard verhindert Datenverlust

## 📈 Performance

### Optimierungen
- Email-Abruf läuft in separatem asyncio-Task
- IMAP-Connection-Pooling mit automatischem Reconnect
- Caching von verarbeiteten Outlook-IDs
- Batch-Verarbeitung mehrerer Emails

### Limits beachten
- Gmail IMAP: Max 15 GB/Tag Traffic
- Notion API: 3 Requests/Sekunde
- Email-Check-Intervall: Minimum 60 Sekunden empfohlen

## 🎯 Workflow-Beispiel

1. **Outlook-Event** wird per Weiterleitung an Gmail gesendet
2. **Email-Processor** erkennt Kalender-Email automatisch  
3. **JSON-Parser** extrahiert Termindaten
4. **Routing-Logic** entscheidet: Business + evtl. Shared DB
5. **Notion-Service** speichert Termin in entsprechenden DBs
6. **Email wird gelöscht** (optional) oder als verarbeitet markiert
7. **Statistiken** werden aktualisiert

## ✅ Definition of Done Checklist

- [x] Email-Abruf funktioniert für alle konfigurierten User
- [x] JSON wird zuverlässig extrahiert und geparst  
- [x] Geschäftstermine landen in der Business-DB
- [x] Relevante Termine werden zusätzlich geteilt
- [x] Duplikate werden via OutlookID verhindert
- [x] Emails werden nur nach Erfolg gelöscht
- [x] Comprehensive Logging implementiert
- [x] Test-Suite für alle Komponenten
- [x] Integration in bestehenden Bot
- [x] Läuft stabil im Docker-Container

🎉 **Business Email-Termin-Prozessor ist einsatzbereit!**

---

Für weitere Fragen oder Anpassungen siehe auch:
- [NOTION_SETUP.md](./NOTION_SETUP.md) - Notion-Datenbank einrichten
- [TROUBLESHOOTING.md](../TROUBLESHOOTING.md) - Allgemeine Fehlerbehandlung
- [README.md](../README.md) - Projekt-Übersicht