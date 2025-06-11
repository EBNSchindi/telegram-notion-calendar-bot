#!/bin/bash

# 🚀 Telegram Notion Calendar Bot Setup Script
# Automatische Installation und Konfiguration

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo -e "${BLUE}============================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Main setup function
main() {
    print_header "Telegram Notion Calendar Bot Setup"
    
    echo "Dieses Script hilft dir beim Setup des Telegram Notion Calendar Bots"
    echo "mit Business Email Integration."
    echo ""
    
    # Check Python version
    check_python
    
    # Check dependencies
    check_dependencies
    
    # Setup virtual environment
    setup_venv
    
    # Install requirements
    install_requirements
    
    # Setup configuration files
    setup_config_files
    
    # Show next steps
    show_next_steps
}

check_python() {
    print_info "Überprüfe Python Installation..."
    
    if ! command_exists python3; then
        print_error "Python 3 ist nicht installiert. Bitte installiere Python 3.8 oder höher."
        exit 1
    fi
    
    python_version=$(python3 --version | cut -d' ' -f2)
    print_success "Python $python_version gefunden"
    
    # Check if version is 3.8+
    if python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
        print_success "Python Version ist kompatibel (>= 3.8)"
    else
        print_error "Python 3.8 oder höher wird benötigt. Gefunden: $python_version"
        exit 1
    fi
}

check_dependencies() {
    print_info "Überprüfe System-Dependencies..."
    
    # Check git
    if command_exists git; then
        print_success "Git ist installiert"
    else
        print_warning "Git ist nicht installiert - empfohlen für Updates"
    fi
    
    # Check docker (optional)
    if command_exists docker; then
        print_success "Docker ist installiert"
        if command_exists docker-compose || docker compose version >/dev/null 2>&1; then
            print_success "Docker Compose ist verfügbar"
        else
            print_warning "Docker Compose nicht gefunden - Docker Deployment nicht verfügbar"
        fi
    else
        print_warning "Docker nicht installiert - nur lokale Installation verfügbar"
    fi
    
    # Check make (optional)
    if command_exists make; then
        print_success "Make ist installiert - Makefile Commands verfügbar"
    else
        print_warning "Make nicht installiert - nutze direkte Python Commands"
    fi
}

setup_venv() {
    print_info "Richte Python Virtual Environment ein..."
    
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        print_success "Virtual Environment erstellt"
    else
        print_info "Virtual Environment existiert bereits"
    fi
    
    # Activate venv
    source venv/bin/activate
    print_success "Virtual Environment aktiviert"
    
    # Upgrade pip
    python -m pip install --upgrade pip
    print_success "Pip aktualisiert"
}

install_requirements() {
    print_info "Installiere Python Dependencies..."
    
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        print_success "Alle Dependencies installiert"
    else
        print_error "requirements.txt nicht gefunden"
        exit 1
    fi
}

setup_config_files() {
    print_info "Richte Konfigurationsdateien ein..."
    
    # Setup .env file
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_success ".env Datei aus .env.example erstellt"
            print_warning "Bitte bearbeite .env und füge deine API Keys hinzu!"
        else
            print_error ".env.example nicht gefunden"
        fi
    else
        print_info ".env Datei existiert bereits"
    fi
    
    # Setup users_config.json
    if [ ! -f "users_config.json" ]; then
        if [ -f "users_config.example.json" ]; then
            cp users_config.example.json users_config.json
            print_success "users_config.json aus users_config.example.json erstellt"
            print_warning "Bitte bearbeite users_config.json und füge deine Notion Keys hinzu!"
        else
            print_error "users_config.example.json nicht gefunden"
        fi
    else
        print_info "users_config.json existiert bereits"
    fi
    
    # Setup Docker Compose
    if [ ! -f "docker-compose.yml" ] && [ -f "docker-compose.example.yml" ]; then
        cp docker-compose.example.yml docker-compose.yml
        print_success "docker-compose.yml aus docker-compose.example.yml erstellt"
    fi
}

show_next_steps() {
    print_header "Setup abgeschlossen! 🎉"
    
    echo "Nächste Schritte:"
    echo ""
    echo "1. 🤖 Telegram Bot erstellen:"
    echo "   - Gehe zu @BotFather in Telegram"
    echo "   - Erstelle einen neuen Bot mit /newbot"
    echo "   - Kopiere den Bot Token in .env"
    echo ""
    echo "2. 📊 Notion Integration einrichten:"
    echo "   - Gehe zu https://www.notion.so/my-integrations"
    echo "   - Erstelle eine neue Integration"
    echo "   - Kopiere den API Key in users_config.json"
    echo "   - Erstelle Notion Datenbanken (siehe docs/NOTION_SETUP.md)"
    echo ""
    echo "3. 📧 Gmail Integration (optional):"
    echo "   - Aktiviere 2-Faktor-Authentifizierung in Gmail"
    echo "   - Erstelle App-Passwort in Google Account Settings"
    echo "   - Konfiguriere EMAIL_* Variablen in .env"
    echo ""
    echo "4. 🚀 Bot starten:"
    echo "   - Lokal: source venv/bin/activate && python src/bot.py"
    echo "   - Docker: docker compose up -d"
    echo "   - Make: make run-local"
    echo ""
    echo "5. 📖 Weitere Dokumentation:"
    echo "   - README.md - Vollständige Dokumentation"
    echo "   - docs/BUSINESS_EMAIL_INTEGRATION.md - Email Integration"
    echo "   - docs/NOTION_SETUP.md - Notion Setup Guide"
    echo ""
    print_success "Setup erfolgreich! Viel Erfolg mit deinem Calendar Bot! 🗓️"
    
    # Show config file locations
    echo ""
    print_info "Konfigurationsdateien:"
    echo "📝 .env - Umgebungsvariablen und Telegram Token"
    echo "👥 users_config.json - Multi-User Konfiguration"
    echo "🐳 docker-compose.yml - Docker Deployment"
    echo ""
    
    # Show useful commands
    print_info "Nützliche Commands:"
    if command_exists make; then
        echo "make help          - Alle verfügbaren Commands"
        echo "make test          - Tests ausführen"
        echo "make lint          - Code-Qualität prüfen"
        echo "make run-local     - Bot lokal starten"
    else
        echo "python src/bot.py                 - Bot starten"
        echo "pytest                           - Tests ausführen"
        echo "flake8 src tests                 - Code-Qualität prüfen"
    fi
    echo ""
}

# Run setup if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi