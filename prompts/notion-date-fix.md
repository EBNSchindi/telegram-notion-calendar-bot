# Fix Notion Date Field Structure and JSON Parsing Error

**STATUS: NOT EXECUTED - DRAFT ONLY**

## Context
This is a Telegram bot that integrates with Notion databases for calendar management. The system uses:
- Python with python-telegram-bot framework
- Notion API for database operations
- OpenAI GPT-4o-mini for natural language processing
- Multi-database architecture (private, shared, business calendars)

## Requirements to Implement

### 1. Update Notion Date Field Structure
**Current State**: The appointment model uses a single "Datum" field with date/time
**Required State**: Notion databases now exclusively use "Startdatum" and "Endedatum" fields

Changes needed:
- Update `src/models/appointment.py` to support both start_date and end_date fields
- Modify the `to_notion_properties()` method to use "Startdatum" and "Endedatum" instead of "Datum"
- Update `from_notion_page()` to read from the new field names
- Ensure backward compatibility during migration

### 2. Implement Default 60-Minute Duration
**Requirement**: Appointments should default to 60 minutes duration unless specified otherwise

Implementation approach:
- When only start time is provided, calculate end_date as start_date + 60 minutes
- Allow duration override if explicitly mentioned in user input
- Update AI prompt in `ai_assistant_service.py` to extract duration when mentioned
- Add duration calculation logic in appointment creation flow

### 3. Fix JSON Parsing Error
**Error**: "Failed to parse AI response: Extra data: line 8 column 6 (char 187)"

Root cause analysis needed for:
- Line 199 in `ai_assistant_service.py` where JSON parsing occurs
- The AI response sometimes includes extra text after the JSON object
- Current regex extraction pattern may be insufficient

Fix approach:
- Strengthen JSON extraction regex to handle multi-line responses
- Add more robust error handling for malformed AI responses
- Implement stricter prompt instructions to ensure JSON-only responses
- Add validation to ensure no trailing data after JSON object

## Detailed Implementation Steps

### Step 1: Update Appointment Model
```python
# In src/models/appointment.py
class Appointment(BaseModel):
    # Add new fields
    start_date: datetime = Field(..., description="Appointment start date and time")
    end_date: datetime = Field(..., description="Appointment end date and time")
    # Keep 'date' for backward compatibility during migration
    date: Optional[datetime] = Field(None, description="Legacy date field")
```

### Step 2: Update Notion Properties Mapping
```python
def to_notion_properties(self, timezone: str = "Europe/Berlin") -> dict:
    # Convert to timezone
    tz = pytz.timezone(timezone)
    local_start = self.start_date.astimezone(tz) if self.start_date.tzinfo else tz.localize(self.start_date)
    local_end = self.end_date.astimezone(tz) if self.end_date.tzinfo else tz.localize(self.end_date)
    
    properties = {
        "Name": {...},
        "Startdatum": {
            "date": {
                "start": local_start.isoformat(),
                "end": None  # Notion expects null for time-only events
            }
        },
        "Endedatum": {
            "date": {
                "start": local_end.isoformat(),
                "end": None
            }
        }
    }
```

### Step 3: Implement Duration Logic
```python
# In ai_assistant_service.py, update appointment extraction
async def extract_appointment_from_text(self, text: str, user_timezone: str = 'Europe/Berlin'):
    # Update prompt to include duration extraction
    prompt = f"""...
    Extract and return a JSON object with the following structure:
    {{
        "title": "appointment title",
        "date": "YYYY-MM-DD",
        "time": "HH:MM",
        "duration_minutes": 60 (default if not specified),
        "description": "additional details",
        "location": "location if mentioned",
        "confidence": 0.0 to 1.0
    }}
    
    DURATION RULES:
    1. Default duration is 60 minutes if not specified
    2. Extract duration if mentioned (e.g., "2 Stunden" = 120 minutes)
    3. Common patterns: "30 min", "1.5h", "2 Stunden", "halbe Stunde"
    """
```

### Step 4: Fix JSON Parsing
```python
# In ai_assistant_service.py, improve JSON extraction
try:
    content = response.choices[0].message.content.strip()
    
    # More robust JSON extraction
    # First try to find JSON block
    json_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
    if not json_match:
        # Try without code block
        json_match = re.search(r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})', content, re.DOTALL)
    
    if json_match:
        json_str = json_match.group(1) if '```' in content else json_match.group(0)
        # Clean up any trailing content
        json_str = json_str.strip()
        # Remove any content after the last closing brace
        last_brace = json_str.rfind('}')
        if last_brace != -1:
            json_str = json_str[:last_brace + 1]
        
        result = json.loads(json_str)
    else:
        raise json.JSONDecodeError("No valid JSON found in response", content, 0)
```

### Step 5: Update Enhanced Appointment Handler
- Modify appointment creation to calculate end_date from start_date + duration
- Update all database operations to use new field names
- Add migration logic to handle existing appointments

## Testing Requirements
1. Test appointment creation with various duration inputs
2. Verify JSON parsing handles all AI response formats
3. Test backward compatibility with existing Notion databases
4. Validate field name changes across all database types
5. Test edge cases: appointments crossing midnight, different timezones

## Migration Considerations
1. Check existing Notion databases for field presence
2. Create migration script if needed to add new fields
3. Handle gracefully if old "Datum" field still exists
4. Log warnings for databases needing manual updates

## Suggested Agent Chain (For Manual Execution)
Since no predefined agents are available, you would need to:
1. Execute this implementation directly in the codebase
2. Or create custom agents for:
   - code-modifier → Updates appointment model and handlers
   - test-creator → Creates tests for new functionality
   - migration-assistant → Handles database field migration
   - documentation-updater → Updates API docs and user guides

## Quick Execution Summary
"Fix Notion date field structure and JSON parsing error: Update appointment model to use Startdatum/Endedatum fields instead of single Datum field, implement 60-minute default duration, and fix JSON parsing error 'Extra data: line 8 column 6' in AI response handling"

---

**⚠️ THIS IS A DRAFT - REVIEW BEFORE RUNNING ⚠️**