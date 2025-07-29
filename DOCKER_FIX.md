# Docker Fix - Fehlerbehebung

## 🔧 Durchgeführte Korrekturen

### 1. **Dockerfile angepasst**
- `users_config.json` wird jetzt mit ins Docker Image kopiert
- Dies war der Hauptgrund, warum der Bot nicht startete

### 2. **docker-compose.yml verbessert**
- `users_config.json` als Read-Only Volume gemountet
- `logs` Verzeichnis hinzugefügt für besseres Debugging

### 3. **Verzeichnisse erstellt**
- `data/` - für persistente Daten
- `logs/` - für Log-Dateien

## 🚀 Docker starten

```bash
# 1. Image neu bauen (wichtig nach Dockerfile-Änderung!)
docker-compose build --no-cache

# 2. Container starten
docker-compose up -d

# 3. Logs prüfen
docker-compose logs -f calendar-bot
```

## 🔍 Debugging bei Problemen

```bash
# Container Status prüfen
docker ps -a

# Detaillierte Logs anzeigen
docker-compose logs --tail=50 calendar-bot

# In Container einsteigen
docker exec -it calendar-telegram-bot bash

# Python-Imports testen
docker exec -it calendar-telegram-bot python -c "import src.bot; print('Import OK')"
```

## ✅ Checkliste vor dem Start

1. **.env Datei vorhanden?**
   - `cp .env.example .env` (falls nicht vorhanden)
   - Telegram Bot Token eintragen

2. **users_config.json vorhanden?**
   - `cp users_config.example.json users_config.json` (falls nicht vorhanden)
   - Notion API Keys und Database IDs eintragen

3. **Berechtigungen korrekt?**
   ```bash
   chmod 644 .env users_config.json
   ```

## 🛠️ Häufige Fehler

### "Module not found" Fehler
- Lösung: `docker-compose build --no-cache` ausführen

### "Permission denied" Fehler
- Lösung: User ID im Dockerfile anpassen oder Berechtigungen korrigieren

### Bot startet nicht
- Prüfen Sie die Logs: `docker-compose logs calendar-bot`
- Verifizieren Sie alle Credentials in `.env` und `users_config.json`

Der Bot sollte jetzt in Docker laufen!