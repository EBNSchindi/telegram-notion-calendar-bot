# ADR-001: Repository Pattern for Data Access

## Status

Accepted

## Context

The original implementation had direct Notion API calls scattered throughout the handlers, leading to:
- Tight coupling between UI logic and data access
- Difficult to test handlers without actual API calls
- Duplicate API error handling code
- No abstraction for different database types (private, shared, business)

## Decision

Implement the Repository pattern using service classes as repositories to abstract all data access logic.

### Implementation Details

1. **Service Layer as Repository**
   - `CombinedAppointmentService` acts as the repository for appointments
   - `MemoService` acts as the repository for memos
   - `NotionService` provides low-level API access

2. **Abstraction Benefits**
   ```python
   # Handler doesn't know about Notion
   appointment = await self.appointment_service.create(data)
   
   # Service handles all data access
   class CombinedAppointmentService:
       async def create(self, data: dict) -> Appointment:
           # Validation
           # Duplicate checking
           # API calls
           # Error handling
           return appointment
   ```

3. **Database Type Abstraction**
   ```python
   # Single interface for all database types
   appointments = await service.get_appointments(
       database_type='shared',  # or 'private' or 'business'
       start_date=today
   )
   ```

## Consequences

### Positive

- **Testability**: Services can be easily mocked in tests
- **Maintainability**: Changes to Notion API only affect service layer
- **Reusability**: Same service methods used by multiple handlers
- **Consistency**: Unified error handling and validation
- **Flexibility**: Easy to add new storage backends

### Negative

- **Additional Layer**: One more abstraction to understand
- **Potential Over-engineering**: Simple CRUD might seem complex
- **Learning Curve**: New developers need to understand the pattern

### Mitigation

- Clear documentation and examples
- Consistent naming conventions
- Comprehensive tests showing usage

## Example

```python
# Before - Direct API calls in handler
class AppointmentHandler:
    async def create_appointment(self, update, context):
        notion = NotionClient(self.api_key)
        try:
            page = notion.pages.create(
                parent={"database_id": self.db_id},
                properties={...}
            )
            # Error handling
            # Formatting
            # Response
        except Exception as e:
            # Duplicate error handling
            
# After - Repository pattern
class AppointmentHandler:
    async def create_appointment(self, update, context):
        appointment = await self.service.create_from_text(text)
        await send_success_message(update, appointment)

class CombinedAppointmentService:
    async def create_from_text(self, text: str) -> Appointment:
        # All data access logic encapsulated
        data = await self.ai_service.extract(text)
        validated = self.validate(data)
        return await self.create(validated)
```

## Related Decisions

- ADR-002: Handler Decomposition
- ADR-003: Constants Extraction
- ADR-005: AI Service with Fallback