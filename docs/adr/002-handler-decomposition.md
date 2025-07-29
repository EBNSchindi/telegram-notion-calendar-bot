# ADR-002: Handler Decomposition

## Status

Accepted

## Context

The original `EnhancedAppointmentHandler` had grown to over 1500 lines with multiple responsibilities:
- Command handling
- Message formatting
- Business logic
- Data validation
- API calls
- Error handling
- UI rendering

This violated the Single Responsibility Principle and made the code difficult to maintain and test.

## Decision

Decompose the monolithic handler into focused components with clear responsibilities:

1. **Base Handler** - Common functionality for all handlers
2. **Specific Handlers** - UI coordination only
3. **Service Layer** - Business logic
4. **Utility Modules** - Cross-cutting concerns

### Architecture

```
┌─────────────────┐
│  Telegram Bot   │
└────────┬────────┘
         │
┌────────▼────────┐
│  Base Handler   │ ◄── Common functionality
└────────┬────────┘
         │
┌────────▼────────┐
│Specific Handler │ ◄── UI coordination only
└────────┬────────┘
         │
┌────────▼────────┐
│ Service Layer   │ ◄── Business logic
└────────┬────────┘
         │
┌────────▼────────┐
│ Data Access     │ ◄── Repository pattern
└─────────────────┘
```

## Implementation

### 1. Base Handler

```python
class BaseHandler:
    """Common functionality for all handlers"""
    
    def __init__(self, user_config: UserConfig):
        self.user_config = user_config
        self.timezone = self._setup_timezone(user_config.timezone)
    
    def _setup_timezone(self, tz_name: str) -> ZoneInfo:
        """Shared timezone setup logic"""
        try:
            return ZoneInfo(tz_name)
        except Exception:
            return ZoneInfo("UTC")
    
    def format_date(self, date: datetime) -> str:
        """Shared date formatting"""
        return date.strftime("%d.%m.%Y %H:%M")
```

### 2. Specific Handlers

```python
class EnhancedAppointmentHandler(BaseHandler):
    """Only UI coordination - no business logic"""
    
    def __init__(self, user_config: UserConfig):
        super().__init__(user_config)
        self.service = CombinedAppointmentService(user_config)
    
    async def handle_create(self, update: Update, context: Context):
        # Extract user input
        text = update.message.text
        
        # Delegate to service
        appointment = await self.service.create_from_text(text)
        
        # Format and send response
        await send_appointment_created(update, appointment)
```

### 3. Service Layer

```python
class CombinedAppointmentService:
    """Business logic only - no UI concerns"""
    
    async def create_from_text(self, text: str) -> Appointment:
        # Extract data using AI
        data = await self.ai_service.extract_appointment(text)
        
        # Validate
        validated = self.validate_appointment_data(data)
        
        # Check duplicates
        await self.check_duplicates(validated)
        
        # Create
        return await self.create_appointment(validated)
```

## Consequences

### Positive

- **Single Responsibility**: Each component has one clear purpose
- **Testability**: Components can be tested in isolation
- **Maintainability**: Changes are localized to specific components
- **Reusability**: Base handler functionality shared across all handlers
- **Clarity**: Clear flow from UI → Handler → Service → Data

### Negative

- **More Files**: Increased number of modules
- **Indirection**: More layers to trace through
- **Initial Complexity**: Seems over-engineered for simple operations

### Mitigation

- Clear naming conventions
- Comprehensive documentation
- Logical file organization
- Examples in tests

## Metrics

### Before Decomposition
- Handler file: 1500+ lines
- Methods per class: 30+
- Average method length: 50+ lines
- Test coverage: 45%

### After Decomposition
- Handler file: 300 lines
- Methods per class: 8-12
- Average method length: 15 lines
- Test coverage: 85%

## Example Migration

```python
# Before - Everything in handler
class EnhancedAppointmentHandler:
    async def create_appointment(self, update, context):
        # Extract text
        # Parse with regex
        # Validate dates
        # Check authorization
        # Format for Notion
        # Call Notion API
        # Handle errors
        # Check duplicates
        # Format response
        # Send message
        # Log activity
        # Update metrics
        # ... 100+ lines
        
# After - Clear separation
class EnhancedAppointmentHandler(BaseHandler):
    async def create_appointment(self, update, context):
        text = extract_text(update)
        appointment = await self.service.create_from_text(text)
        await send_success_message(update, appointment)

class CombinedAppointmentService:
    async def create_from_text(self, text: str) -> Appointment:
        data = await self.ai_service.extract(text)
        return await self.create(data)
```

## Related Decisions

- ADR-001: Repository Pattern
- ADR-003: Constants Extraction
- ADR-004: Multi-Database Architecture