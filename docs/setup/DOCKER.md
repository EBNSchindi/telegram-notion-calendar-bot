# Docker Deployment Guide

## 🐳 Übersicht

Dieser Bot kann vollständig in Docker betrieben werden, was die Deployment auf Servern (z.B. Proxmox) vereinfacht.

## 📋 Voraussetzungen

- Docker Engine (Version 20.10+)
- Docker Compose Plugin (oder docker-compose standalone)
- `.env` Datei mit Bot-Konfiguration
- `users_config.json` mit Benutzer-Einstellungen

## 🚀 Quick Start

### 1. Repository klonen
```bash
git clone https://github.com/EBNSchindi/telegram-notion-calendar-bot.git
cd telegram-notion-calendar-bot
```

### 2. Konfiguration vorbereiten
```bash
# .env Datei erstellen
cp .env.example .env
# Bot Token eintragen

# Benutzer konfigurieren
cp users_config.example.json users_config.json
# Notion Keys und User IDs eintragen
```

### 3. Container starten
```bash
# Mit Docker Compose (empfohlen)
docker compose up -d

# Logs anzeigen
docker compose logs -f
```

## 📦 Docker-Konfiguration

### Dockerfile
- Basiert auf `python:3.11-slim`
- Non-root User für Sicherheit
- Optimierte Layer für schnelle Builds
- Startet automatisch `src/bot.py`

### docker-compose.yml
```yaml
services:
  calendar-bot:
    build: .
    container_name: calendar-telegram-bot
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./data:/app/data
    networks:
      - bot-network
    healthcheck:
      test: ["CMD", "python", "-c", "import sys; sys.exit(0)"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Volumes
- `./data:/app/data` - Persistente Daten (Logs, Cache)
- `.env` - Umgebungsvariablen
- `users_config.json` - Benutzer-Konfiguration

## 🔧 Verwaltung

### Container-Befehle
```bash
# Status prüfen
docker compose ps

# Container stoppen
docker compose stop

# Container entfernen
docker compose down

# Container neu bauen (nach Code-Änderungen)
docker compose build
docker compose up -d

# In Container einloggen
docker compose exec calendar-bot /bin/bash

# Logs in Echtzeit
docker compose logs -f calendar-bot
```

### Updates durchführen
```bash
# Code aktualisieren
git pull

# Container neu bauen und starten
docker compose down
docker compose build --no-cache
docker compose up -d
```

## 🏠 Deployment auf Proxmox/Server

### 1. Vorbereitung auf lokalem System
```bash
# Repository mit allen Configs zippen
zip -r telegram-bot.zip telegram-notion-calendar-bot/
```

### 2. Auf Server übertragen
```bash
scp telegram-bot.zip user@server:/opt/
ssh user@server
cd /opt && unzip telegram-bot.zip
cd telegram-notion-calendar-bot
```

### 3. Container auf Server starten
```bash
# Docker und Docker Compose installieren (falls noch nicht vorhanden)
curl -fsSL https://get.docker.com | bash
sudo usermod -aG docker $USER

# Bot starten
docker compose up -d
```

### 4. Systemd Service (optional)
```bash
# /etc/systemd/system/telegram-bot.service
[Unit]
Description=Telegram Notion Calendar Bot
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/telegram-notion-calendar-bot
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

Aktivieren:
```bash
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
```

## 🛡️ Sicherheit

### Best Practices
1. **Secrets nicht im Image**: `.env` wird zur Laufzeit gemountet
2. **Non-root User**: Container läuft als `botuser` (UID 1000)
3. **Minimales Base Image**: `python:3.11-slim`
4. **Health Checks**: Automatischer Restart bei Problemen

### Firewall
Der Bot benötigt nur ausgehende Verbindungen:
- Telegram API (HTTPS)
- Notion API (HTTPS)

Keine eingehenden Ports erforderlich!

## 🐛 Troubleshooting

### Container startet nicht
```bash
# Logs prüfen
docker compose logs calendar-bot

# Permissions prüfen
ls -la .env users_config.json
```

### Bot reagiert nicht
1. Token in `.env` prüfen
2. Notion API Keys in `users_config.json` prüfen
3. Container neu starten: `docker compose restart`

### "Permission denied" Fehler
```bash
# Docker Gruppe prüfen
groups

# Falls nicht in docker Gruppe:
sudo usermod -aG docker $USER
# Neu einloggen!
```

### Speicherplatz voll
```bash
# Alte Images aufräumen
docker system prune -a

# Logs begrenzen (in docker-compose.yml bereits konfiguriert)
```

## 📊 Monitoring

### Container-Statistiken
```bash
# CPU/Memory Usage
docker stats calendar-telegram-bot

# Detaillierte Infos
docker compose top
```

### Log-Analyse
```bash
# Fehler suchen
docker compose logs | grep ERROR

# Bestimmten Zeitraum
docker compose logs --since="2025-06-10" --until="2025-06-11"
```

## 🔄 Backup & Restore

### Backup erstellen
```bash
# Stoppen
docker compose stop

# Backup
tar -czf bot-backup-$(date +%Y%m%d).tar.gz .env users_config.json data/

# Wieder starten
docker compose start
```

### Restore
```bash
# Backup entpacken
tar -xzf bot-backup-20250610.tar.gz

# Container neu starten
docker compose up -d
```

---

**Hinweis**: Diese Anleitung wurde für die Deployment auf Proxmox und anderen Linux-Servern optimiert. Bei Fragen siehe [TROUBLESHOOTING.md](TROUBLESHOOTING.md).