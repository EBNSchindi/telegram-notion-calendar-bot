# 🤝 Contributing Guidelines

Willkommen! Wir freuen uns über deine Beiträge zum **Enhanced Telegram Notion Calendar Bot**. Diese Richtlinien helfen dabei, einen konsistenten und hochwertigen Code zu gewährleisten.

## 📋 Inhaltsverzeichnis

1. [Code-Standards](#-code-standards)
2. [Entwicklungsumgebung](#-entwicklungsumgebung)
3. [Pull Request Prozess](#-pull-request-prozess)
4. [Testing](#-testing)
5. [Architektur-Prinzipien](#-architektur-prinzipien)
6. [Sicherheitsrichtlinien](#-sicherheitsrichtlinien)
7. [Dokumentation](#-dokumentation)

## 🎯 Code-Standards

### Code Style
Wir verwenden **Black** und **isort** für konsistente Formatierung:

```bash
# Automatische Formatierung
black src/ tests/
isort src/ tests/

# Linting
flake8 src/ tests/
mypy src/
```

### Naming Conventions
```python
# Classes: PascalCase
class AppointmentHandler:
    pass

# Functions/Variables: snake_case
def create_appointment():
    user_id = 123

# Constants: UPPER_SNAKE_CASE  
MAX_RETRIES = 3

# Private methods: _leading_underscore
def _internal_method(self):
    pass
```

### Type Hints
**Vollständige Typisierung ist erforderlich:**

```python
from typing import Optional, List, Dict, Any
from datetime import datetime

async def get_appointments(
    user_id: int,
    date_filter: Optional[datetime] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """Get appointments with proper type annotations."""
    pass
```

### Docstrings
Verwende **Google-Style Docstrings** für alle öffentlichen APIs:

```python
def create_memo(title: str, due_date: Optional[datetime] = None) -> bool:
    """Create a new memo in Notion database.
    
    Args:
        title: The memo title (required)
        due_date: Optional due date for the memo
        
    Returns:
        True if memo was created successfully, False otherwise
        
    Raises:
        ValidationError: If title is empty or invalid
        NotionAPIError: If Notion API call fails
        
    Example:
        >>> create_memo("Prepare presentation", datetime(2025, 7, 25))
        True
    """
    pass
```

## 🛠 Entwicklungsumgebung

### Setup
```bash
# Repository clonen
git clone https://github.com/your-username/telegram-notion-calendar-bot.git
cd telegram-notion-calendar-bot

# Virtuelle Umgebung erstellen
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oder venv\Scripts\activate  # Windows

# Dependencies installieren
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies

# Pre-commit hooks installieren
pre-commit install
```

### Konfiguration
```bash
# .env Datei erstellen
cp .env.example .env
# → Fülle echte API-Keys ein

# Test-Konfiguration erstellen
cp users_config.example.json users_config.json
# → Fülle Test-User-Daten ein
```

### Development Tools
```bash
# Code-Qualität prüfen
make lint              # Linting mit flake8
make format            # Formatierung mit black/isort  
make type-check        # Type-checking mit mypy

# Tests ausführen
make test              # Alle Tests
make test-cov          # Mit Coverage-Report
make test-watch        # Tests im Watch-Modus

# Bot lokal starten
make run-dev           # Development-Modus mit Reload
make run-prod          # Production-Modus
```

## 🔄 Pull Request Prozess

### 1. Issue erstellen (bei größeren Features)
```markdown
## Feature Request: Erweiterte Memo-Filter

**Beschreibung:** 
Benutzer sollen Memos nach Status und Bereich filtern können.

**Acceptance Criteria:**
- [ ] Filter-UI im Telegram-Bot
- [ ] Backend-Implementierung 
- [ ] Tests für alle Filter-Optionen
- [ ] Dokumentation aktualisiert

**Technical Notes:**
- Verwendung der bestehenden `MemoService` Klasse
- Neue Methode `get_filtered_memos()`
- Integration in `memo_handler.py`
```

### 2. Feature Branch erstellen
```bash
# Branch naming convention: type/description
git checkout -b feature/memo-advanced-filters
git checkout -b bugfix/timezone-parsing-error
git checkout -b refactor/memo-service-optimization
git checkout -b docs/api-documentation-update
```

### 3. Code schreiben & testen
```bash
# Während der Entwicklung
git add .
git commit -m "feat: add basic memo filtering structure

- Add filter parameters to MemoService
- Implement get_filtered_memos method
- Add unit tests for filtering logic"

# Commit message format: type: description
# Types: feat, fix, docs, style, refactor, test, chore
```

### 4. Code Review vorbereiten
```bash
# Vor dem Push: Qualität prüfen
make lint
make type-check  
make test
make format

# Self-review
git log --oneline -10  # Commit-Historie prüfen
git diff main...HEAD   # Alle Änderungen reviewen
```

### 5. Pull Request erstellen
```markdown
## 🎯 Memo Advanced Filters

### Änderungen
- ✅ Filter nach Status (Nicht begonnen, In Arbeit, Erledigt)
- ✅ Filter nach Bereich (Multi-Select Unterstützung)
- ✅ Kombinierte Filter (Status + Bereich)
- ✅ Neue Telegram-Commands: `/memos status:erledigt`

### Testing
- [x] Unit-Tests für `MemoService.get_filtered_memos()`
- [x] Integration-Tests für Telegram-Handler
- [x] Manual testing mit verschiedenen Filter-Kombinationen

### Breaking Changes
Keine - alle Änderungen sind backward-kompatibel.

### Code-Qualität
```bash
✅ make lint       # 0 errors
✅ make type-check # 0 errors  
✅ make test       # 42/42 passed
```

### Screenshots
[Optional: Screenshots der neuen Filter-UI]

### Checklist
- [x] Code follows project conventions
- [x] Tests added for new functionality
- [x] Documentation updated
- [x] No breaking changes (or clearly marked)
- [x] Self-reviewed all changes
```

## 🧪 Testing

### Test-Struktur
```
tests/
├── unit/                    # Unit-Tests für einzelne Komponenten
│   ├── test_memo_service.py
│   ├── test_appointment_handler.py
│   └── test_ai_assistant.py
├── integration/             # Integration-Tests
│   ├── test_notion_api.py
│   └── test_telegram_flow.py
├── fixtures/                # Test-Daten
│   ├── sample_memos.json
│   └── sample_appointments.json
└── conftest.py              # Pytest-Konfiguration
```

### Test Guidelines
```python
import pytest
from unittest.mock import Mock, AsyncMock
from src.services.memo_service import MemoService

class TestMemoService:
    """Test cases for MemoService functionality."""
    
    @pytest.fixture
    def memo_service(self, mock_user_config):
        """Create MemoService instance for testing."""
        return MemoService(mock_user_config)
    
    @pytest.mark.asyncio
    async def test_create_memo_success(self, memo_service):
        """Test successful memo creation."""
        # Arrange
        memo_data = {
            "aufgabe": "Test Memo",
            "status": "Nicht begonnen"
        }
        
        # Act
        result = await memo_service.create_memo(memo_data)
        
        # Assert
        assert result is True
        # Weitere Assertions...
    
    @pytest.mark.asyncio 
    async def test_create_memo_validation_error(self, memo_service):
        """Test memo creation with invalid data."""
        # Arrange
        invalid_data = {"aufgabe": ""}  # Empty title
        
        # Act & Assert
        with pytest.raises(ValidationError):
            await memo_service.create_memo(invalid_data)

    @pytest.mark.parametrize("status,expected", [
        ("Nicht begonnen", True),
        ("In Arbeit", True), 
        ("Erledigt", True),
        ("Invalid Status", False)
    ])
    def test_validate_status(self, status, expected):
        """Test status validation with various inputs."""
        result = MemoService.validate_status(status)
        assert result == expected
```

### Mocking Guidelines
```python
# Externe APIs mocken
@pytest.fixture
def mock_notion_client():
    """Mock Notion API client."""
    client = Mock()
    client.databases.query = AsyncMock(return_value={
        "results": [{"id": "test-id", "properties": {...}}]
    })
    return client

# AI-Services mocken
@pytest.fixture  
def mock_ai_service():
    """Mock AI service for predictable testing."""
    service = Mock()
    service.extract_memo_from_text = AsyncMock(return_value={
        "aufgabe": "Test Task",
        "faelligkeitsdatum": "2025-07-25"
    })
    return service
```

### Coverage Requirements
- **Minimum**: 80% Code-Coverage für alle neuen Features
- **Target**: 90% für kritische Komponenten (Services, Models)
- **Ausnahmen**: Utility-Functions mit trivialer Logik

```bash
# Coverage-Report generieren
pytest --cov=src --cov-report=html tests/
# → Öffne htmlcov/index.html im Browser
```

## 🏗 Architektur-Prinzipien

### SOLID Principles

#### Single Responsibility Principle
```python
# ✅ Good: Eine Verantwortlichkeit pro Klasse
class MemoValidator:
    """Validates memo data only."""
    def validate(self, memo_data: dict) -> bool:
        pass

class MemoNotionService:
    """Handles Notion API calls only."""  
    def create_memo(self, memo_data: dict) -> bool:
        pass

# ❌ Bad: Mehrere Verantwortlichkeiten
class MemoHandler:
    def validate_and_create_memo(self, memo_data: dict):
        # Validation UND API-Calls in einer Methode
        pass
```

#### Dependency Injection
```python
# ✅ Good: Dependencies werden injiziert
class AppointmentService:
    def __init__(self, notion_client: NotionClient, ai_service: AIService):
        self.notion_client = notion_client
        self.ai_service = ai_service

# ❌ Bad: Hard-coded Dependencies  
class AppointmentService:
    def __init__(self):
        self.notion_client = NotionClient()  # Hard-coded
        self.ai_service = AIService()        # Hard-coded
```

### Error Handling Patterns
```python
from src.utils.error_handler import BotError, ErrorType, ErrorSeverity

# ✅ Good: Verwendung der zentralen Error-Klassen
@handle_bot_error(ErrorType.NOTION_API, ErrorSeverity.HIGH)
async def create_appointment(appointment_data: dict) -> bool:
    """Create appointment with automatic error handling."""
    # Implementation
    pass

# Safe Operation Context für kritische Operationen
async with SafeOperationContext("memo_creation", ErrorType.VALIDATION):
    result = await memo_service.create_memo(memo_data)
```

### Async/Await Best Practices
```python
# ✅ Good: Proper async/await usage
async def process_multiple_memos(memo_list: List[dict]) -> List[bool]:
    """Process multiple memos concurrently."""
    tasks = [create_memo(memo) for memo in memo_list]
    return await asyncio.gather(*tasks)

# ✅ Good: Error handling in async functions
async def safe_api_call():
    try:
        result = await api_client.call()
        return result
    except APIError as e:
        logger.error(f"API call failed: {e}")
        raise BotError("API temporarily unavailable", ErrorType.NETWORK)
```

## 🔒 Sicherheitsrichtlinien

### Input Validation
```python
from pydantic import BaseModel, Field, validator

# ✅ Good: Pydantic für Input-Validierung
class MemoCreateRequest(BaseModel):
    aufgabe: str = Field(..., min_length=1, max_length=200)
    status: str = Field(default="Nicht begonnen")
    
    @validator('aufgabe')
    def validate_aufgabe(cls, v):
        # XSS-Schutz
        if '<script' in v.lower() or 'javascript:' in v.lower():
            raise ValueError('Invalid characters in memo title')
        return v.strip()
```

### Secret Management
```python
# ✅ Good: Secrets aus Environment-Variablen
import os
from typing import Optional

def get_api_key() -> Optional[str]:
    """Get API key from environment with validation."""
    api_key = os.getenv('NOTION_API_KEY')
    if not api_key or api_key.startswith('secret_placeholder'):
        return None
    return api_key

# ❌ Bad: Hardcoded secrets
API_KEY = "secret_abc123"  # Niemals!
```

### Rate Limiting
```python
from src.utils.rate_limiter import rate_limit

# ✅ Good: Rate-Limiting für alle User-facing APIs
@rate_limit(max_requests=10, time_window=60)  # 10 requests per minute
async def ai_extract_memo(text: str) -> dict:
    """Extract memo with rate limiting."""
    pass
```

### Authorization
```python
def require_admin(func):
    """Decorator für Admin-only Funktionen."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in settings.admin_users:
            await update.message.reply_text("❌ Nicht autorisiert")
            return
        return await func(update, context)
    return wrapper

@require_admin
async def debug_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Debug-Befehl nur für Admins."""
    pass
```

## 📚 Dokumentation

### API Documentation
```python
class MemoService:
    """Service for managing memos in Notion database.
    
    This service provides CRUD operations for memos with automatic
    validation and error handling. All methods are async and use
    the configured Notion API client.
    
    Attributes:
        user_config: User configuration with API keys and database IDs
        notion_client: Authenticated Notion client instance
        
    Example:
        >>> service = MemoService(user_config)
        >>> memo_id = await service.create_memo({
        ...     "aufgabe": "Buy groceries",
        ...     "status": "Nicht begonnen"
        ... })
    """
    
    async def create_memo(self, memo_data: dict) -> Optional[str]:
        """Create a new memo in the user's Notion database.
        
        Args:
            memo_data: Dictionary containing memo fields:
                - aufgabe (str): Memo title (required)
                - status (str): Status (default: "Nicht begonnen")  
                - faelligkeitsdatum (datetime, optional): Due date
                - bereich (str, optional): Category/area
                - projekt (str, optional): Project assignment
                
        Returns:
            Notion page ID if successful, None if failed
            
        Raises:
            ValidationError: If memo_data is invalid
            NotionAPIError: If Notion API call fails
            
        Example:
            >>> memo_id = await service.create_memo({
            ...     "aufgabe": "Prepare presentation", 
            ...     "faelligkeitsdatum": datetime(2025, 7, 25),
            ...     "bereich": "Work"
            ... })
            >>> print(memo_id)  # "abc123-def456-..."
        """
        pass
```

### Code Comments
```python
# ✅ Good: Comments erklären das "Warum", nicht das "Was"
def calculate_next_reminder_time(user_config: UserConfig) -> datetime:
    # We add a random delay (0-300s) to prevent all users from being
    # reminded at exactly the same time, which would cause API rate limits
    base_time = datetime.strptime(user_config.reminder_time, "%H:%M")
    random_delay = random.randint(0, 300)  
    return base_time + timedelta(seconds=random_delay)

# ❌ Bad: Comments wiederholen den Code
def calculate_next_reminder_time(user_config: UserConfig) -> datetime:
    # Parse the reminder time from string
    base_time = datetime.strptime(user_config.reminder_time, "%H:%M")
    # Add random seconds
    random_delay = random.randint(0, 300)
    # Return time plus delay
    return base_time + timedelta(seconds=random_delay)
```

## 🚀 Release Process

### Version Numbering
Wir verwenden **Semantic Versioning** (SemVer):
- `MAJOR.MINOR.PATCH` (z.B. `3.1.2`)
- **MAJOR**: Breaking changes
- **MINOR**: Neue Features (backward-kompatibel)
- **PATCH**: Bug fixes (backward-kompatibel)

### Changelog Updates
```markdown
# CHANGELOG.md

## [3.1.0] - 2025-07-22

### Added
- ✨ Erweiterte Memo-Filter nach Status und Bereich
- 🔍 Volltext-Suche in Memo-Titeln  
- 📊 Usage-Analytics für Admins

### Changed
- ⚡ Performance-Verbesserung bei Notion-API-Calls (30% schneller)
- 🎨 Vereinfachte Filter-UI im Telegram-Bot

### Fixed  
- 🐛 Timezone-Bug bei Terminen in verschiedenen Zeitzonen
- 🔧 Memory-Leak in Business-Calendar-Sync

### Deprecated
- ⚠️ Legacy-Method `get_memos()` → verwende `get_filtered_memos()`

### Security
- 🔒 Verbesserte Input-Validation für User-Messages
- 🛡️ Rate-Limiting für AI-Service-Calls
```

## ❓ Hilfe & Support

### Development Questions
- **Slack**: #telegram-bot-dev (für Team-Mitglieder)
- **GitHub Discussions**: Für öffentliche Fragen
- **Issues**: Für Bug-Reports und Feature-Requests

### Code Review Guidelines
- **Response Time**: Innerhalb von 48 Stunden
- **Approval**: Mindestens ein Approve von Core-Maintainer erforderlich
- **Automated Checks**: Alle CI-Checks müssen grün sein

### Contribution Recognition
Alle Contributors werden in der README.md genannt und bekommen:
- 🏆 **Major Contributors**: Eigene Sektion mit Profilbild
- 🌟 **Regular Contributors**: Erwähnung in "Contributors" Liste  
- 💫 **First-time Contributors**: Willkommens-Badge

## 🎉 Danke!

Jeder Beitrag macht das Projekt besser - von Typo-Fixes bis hin zu großen Features. Danke, dass du Teil der Community bist!

---

**Fragen?** Erstelle ein [GitHub Issue](https://github.com/your-username/telegram-notion-calendar-bot/issues) oder starte eine [Discussion](https://github.com/your-username/telegram-notion-calendar-bot/discussions).