# ADR-003: Constants Extraction

## Status

Accepted

## Context

The codebase had numerous magic strings and numbers scattered throughout:
- Button callback data prefixes
- Status values
- Error messages
- UI emojis
- Time constants
- Database field names

This led to:
- Typos causing bugs
- Inconsistent values
- Difficult refactoring
- No single source of truth

## Decision

Create a centralized `constants.py` module containing all magic values organized by category.

### Structure

```python
# constants.py

# Callback Data Prefixes
class CallbackData:
    """Telegram callback data prefixes"""
    APPOINTMENT_SHARE = "appointment_share_"
    APPOINTMENT_SHARE_YES = "appointment_share_yes_"
    APPOINTMENT_SHARE_NO = "appointment_share_no_"
    MEMO_SET_STATUS_PREFIX = "memo_set_status_"
    MEMO_FILTER_STATUS_PREFIX = "memo_filter_status_"

# Status Values
class MemoStatus:
    """Memo status constants matching Notion"""
    NOT_STARTED = "Nicht begonnen"
    IN_PROGRESS = "In Arbeit"
    COMPLETED = "Erledigt"

# UI Elements
class StatusEmoji:
    """Status indicator emojis"""
    NOT_STARTED = "⭕"
    IN_PROGRESS = "🔄"
    COMPLETED = "✅"

# Error Messages
class ErrorMessages:
    """User-facing error messages"""
    GENERAL_ERROR = "❌ Ein Fehler ist aufgetreten. Bitte versuche es später erneut."
    NOT_AUTHORIZED = "❌ Du bist nicht berechtigt, diesen Bot zu verwenden."
    INVALID_DATE = "❌ Ungültiges Datum. Bitte verwende ein Format wie 'morgen 15:00'."

# Time Constants
class TimeConstants:
    """Time-related constants"""
    DEFAULT_REMINDER_TIME = "08:00"
    CACHE_TTL_SECONDS = 300
    RATE_LIMIT_WINDOW = 60
```

## Implementation Examples

### Before

```python
# Scattered throughout multiple files
if callback_data.startswith("appointment_share_"):
    # ...
    
status_emojis = {
    "Nicht begonnen": "⭕",
    "In Arbeit": "🔄",
    "Erledigt": "✅"
}

await update.message.reply_text(
    "❌ Ein Fehler ist aufgetreten. Bitte versuche es später erneut."
)
```

### After

```python
from constants import CallbackData, StatusEmoji, ErrorMessages

if callback_data.startswith(CallbackData.APPOINTMENT_SHARE):
    # ...
    
status_emoji = StatusEmoji.IN_PROGRESS

await update.message.reply_text(ErrorMessages.GENERAL_ERROR)
```

## Benefits

### 1. Type Safety

```python
# IDE autocomplete and type checking
if status == MemoStatus.COMPLETED:  # ✓ Type-safe
    emoji = StatusEmoji.COMPLETED   # ✓ No typos
```

### 2. Easy Refactoring

```python
# Change in one place affects entire codebase
class MemoStatus:
    NOT_STARTED = "Not Started"  # Changed from German
    # All usages automatically updated
```

### 3. Documentation

```python
class DatabaseFields:
    """Notion database field names - must match exactly"""
    TITLE = "Name"              # German: Titel field
    DATE = "Datum"              # German: Date field
    PARTNER_RELEVANT = "PartnerRelevant"  # Checkbox field
```

### 4. Validation

```python
VALID_STATUSES = [
    MemoStatus.NOT_STARTED,
    MemoStatus.IN_PROGRESS,
    MemoStatus.COMPLETED
]

if status not in VALID_STATUSES:
    raise ValueError(f"Invalid status: {status}")
```

## Organization Strategy

### 1. Logical Grouping

```python
# Group by functionality
class CallbackData:      # All callback-related
class MemoStatus:        # All memo-related
class Appointments:      # All appointment-related
```

### 2. Naming Conventions

```python
# Clear, descriptive names
APPOINTMENT_SHARE_YES = "appointment_share_yes_"  # ✓ Clear
ASY = "asy_"  # ✗ Unclear
```

### 3. Comments for Context

```python
class TimeConstants:
    # Used for business hours checking
    BUSINESS_START_HOUR = 8  # 8 AM
    BUSINESS_END_HOUR = 18   # 6 PM
    
    # Email sync intervals
    EMAIL_SYNC_INTERVAL = 300  # 5 minutes in seconds
```

## Consequences

### Positive

- **No Magic Values**: All constants have meaningful names
- **Single Source of Truth**: Change once, affect everywhere
- **Type Safety**: IDE support and validation
- **Documentation**: Self-documenting code
- **Consistency**: Enforced consistent values

### Negative

- **Import Overhead**: Need to import constants
- **Indirection**: Extra lookup for simple values
- **Naming Conflicts**: Potential namespace collisions

### Mitigation

- Use specific imports: `from constants import MemoStatus`
- Group related constants in classes
- Use clear, unique names

## Migration Guide

1. **Identify Magic Values**
   ```bash
   # Find string literals
   grep -r "'" src/ | grep -v "test"
   
   # Find numeric literals
   grep -r "[0-9]" src/ | grep -v "test"
   ```

2. **Create Constant**
   ```python
   # In constants.py
   class NewCategory:
       MY_VALUE = "actual_value"
   ```

3. **Replace Usage**
   ```python
   # Before
   if status == "active":
   
   # After
   from constants import StatusValues
   if status == StatusValues.ACTIVE:
   ```

## Best Practices

1. **Use UPPER_CASE** for constants
2. **Group in classes** for organization
3. **Add docstrings** for complex values
4. **Keep alphabetical order** within groups
5. **Version database schemas** when they change

## Future Considerations

1. **Environment-specific constants**
   ```python
   class EnvironmentConstants:
       DEV = "development"
       PROD = "production"
       TEST = "test"
   ```

2. **Feature flags**
   ```python
   class FeatureFlags:
       ENABLE_AI = True
       ENABLE_EMAIL_SYNC = True
       ENABLE_PARTNER_SHARING = True
   ```

3. **Internationalization**
   ```python
   class Messages:
       def __init__(self, language='de'):
           self.language = language
       
       @property
       def GREETING(self):
           return {
               'de': 'Hallo!',
               'en': 'Hello!'
           }[self.language]
   ```

## Related Decisions

- ADR-001: Repository Pattern
- ADR-002: Handler Decomposition
- ADR-004: Multi-Database Architecture