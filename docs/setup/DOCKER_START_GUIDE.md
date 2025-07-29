# 🐳 Docker Start Guide

## Schnellstart

```bash
# Option 1: Mit sudo (empfohlen für ersten Start)
sudo docker compose up -d

# Option 2: Benutzer zur Docker-Gruppe hinzufügen (dauerhaft)
sudo usermod -aG docker $USER
# Dann ab- und wieder anmelden
docker compose up -d
```

## Schritt-für-Schritt Anleitung

### 1. Voraussetzungen prüfen

```bash
# Docker Version prüfen
docker --version

# Docker Compose prüfen
docker compose version
```

### 2. Konfiguration vorbereiten

```bash
# .env Datei erstellen (falls nicht vorhanden)
cp .env.example .env

# users_config.json erstellen
cp users_config.example.json users_config.json
```

⚠️ **WICHTIG**: Bearbeiten Sie beide Dateien mit Ihren echten Werten!

### 3. Bot mit Docker starten

```bash
# Container bauen und starten
sudo docker compose up -d --build

# Oder wenn Sie in der Docker-Gruppe sind:
docker compose up -d --build
```

### 4. Status prüfen

```bash
# Container Status
sudo docker compose ps

# Logs anzeigen
sudo docker compose logs -f
```

## Nützliche Docker Befehle

```bash
# Bot stoppen
sudo docker compose down

# Bot neu starten
sudo docker compose restart

# Logs der letzten 100 Zeilen
sudo docker compose logs --tail=100

# In Container einloggen (für Debugging)
sudo docker compose exec calendar-bot /bin/bash

# Container und Images aufräumen
sudo docker compose down --rmi all --volumes
```

## Fehlerbehandlung

### "Permission denied" Fehler

```bash
# Lösung 1: Mit sudo ausführen
sudo docker compose up -d

# Lösung 2: Benutzer zur Docker-Gruppe hinzufügen
sudo usermod -aG docker $USER
# Logout und wieder einloggen
```

### Container startet nicht

1. Logs prüfen:
   ```bash
   sudo docker compose logs
   ```

2. Konfiguration prüfen:
   - `.env` Datei vorhanden und konfiguriert?
   - `users_config.json` vorhanden und konfiguriert?
   - Alle API Keys korrekt?

3. Container neu bauen:
   ```bash
   sudo docker compose down
   sudo docker compose build --no-cache
   sudo docker compose up -d
   ```

## Teamspace-Konfiguration

Die neue Teamspace-Unterstützung ist bereits im Docker Image enthalten:

1. **Für Teamspace-Besitzer:**
   - `is_owner: true` in `users_config.json`
   - Nur eigenen API Key angeben

2. **Für Team-Mitglieder:**
   - `is_owner: false` in `users_config.json`
   - `teamspace_owner_api_key` mit Owner-Key konfigurieren

## Produktions-Tipps

1. **Automatischer Neustart:**
   Der Container ist mit `restart: unless-stopped` konfiguriert

2. **Volumes:**
   - Daten werden in `./data` gespeichert
   - Bei Updates bleiben Daten erhalten

3. **Healthcheck:**
   - Automatische Überwachung alle 30 Sekunden
   - Container wird bei Problemen neu gestartet

4. **Updates:**
   ```bash
   git pull
   sudo docker compose down
   sudo docker compose up -d --build
   ```

## Support

Bei Problemen:
1. Logs prüfen: `sudo docker compose logs`
2. Konfiguration validieren
3. Container neu starten
4. GitHub Issues checken