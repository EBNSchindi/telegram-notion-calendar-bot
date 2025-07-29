#!/bin/bash
# Docker Start Script for Telegram Notion Calendar Bot

echo "🚀 Starting Telegram Notion Calendar Bot with Docker..."
echo ""
echo "⚠️  WICHTIG: Dieses Skript benötigt Docker-Zugriff!"
echo ""
echo "Falls Sie einen Fehler erhalten, führen Sie bitte aus:"
echo "  1. sudo usermod -aG docker $USER"
echo "  2. Melden Sie sich ab und wieder an"
echo "  3. Oder verwenden Sie: sudo docker compose up -d"
echo ""
echo "📋 Prüfe Docker-Status..."

# Check if docker is accessible
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker ist nicht erreichbar. Bitte führen Sie dieses Skript mit sudo aus:"
    echo "   sudo ./start_docker.sh"
    echo ""
    echo "Oder fügen Sie Ihren Benutzer zur Docker-Gruppe hinzu:"
    echo "   sudo usermod -aG docker $USER"
    echo "   (Danach ab- und wieder anmelden)"
    exit 1
fi

echo "✅ Docker ist verfügbar"
echo ""

# Check for .env file
if [ ! -f .env ]; then
    echo "❌ .env Datei nicht gefunden!"
    echo "   Bitte kopieren Sie .env.example zu .env und konfigurieren Sie die Werte:"
    echo "   cp .env.example .env"
    exit 1
fi

echo "✅ .env Datei gefunden"
echo ""

# Check for users_config.json
if [ ! -f users_config.json ]; then
    echo "⚠️  users_config.json nicht gefunden!"
    echo "   Erstelle aus Beispieldatei..."
    cp users_config.example.json users_config.json
    echo "   ⚠️  Bitte konfigurieren Sie users_config.json mit Ihren Notion-Daten!"
fi

echo "📦 Baue Docker Image..."
docker compose build

if [ $? -ne 0 ]; then
    echo "❌ Docker Build fehlgeschlagen!"
    exit 1
fi

echo ""
echo "🚀 Starte Container..."
docker compose up -d

if [ $? -ne 0 ]; then
    echo "❌ Container Start fehlgeschlagen!"
    exit 1
fi

echo ""
echo "✅ Bot erfolgreich gestartet!"
echo ""
echo "📊 Container Status:"
docker compose ps
echo ""
echo "📝 Logs anzeigen mit: docker compose logs -f"
echo "🛑 Bot stoppen mit: docker compose down"
echo ""
echo "💡 Tipp: Mit den neuen Teamspace-Features können Sie jetzt:"
echo "   - Eigene API Keys für private Datenbanken verwenden"
echo "   - Owner API Key nur für Shared Database nutzen"
echo "   - Klare Trennung der Zugriffsrechte"