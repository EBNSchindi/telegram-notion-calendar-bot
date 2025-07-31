# Memo Status Check Feature - Migration Guide & Documentation

## Table of Contents
1. [Migration Guide](#migration-guide)
2. [Feature Overview](#feature-overview)
3. [API Changes](#api-changes)
4. [Usage Examples](#usage-examples)
5. [Troubleshooting](#troubleshooting)

---

## Migration Guide

### 1. Notion Database Setup

#### Adding the Status Check Field

1. **Open your Memo Database in Notion**
   - Navigate to your Notion workspace
   - Locate your memo/task database (configured as `memo_database_id` in your bot)

2. **Add Status Check Property**
   - Click the `+` button to add a new property
   - Name: `Status Check`
   - Type: `Checkbox`
   - Description: "Checkbox indicator for task completion status"

3. **Configure Property Settings**
   ```
   Property Name: Status Check
   Property Type: Checkbox
   Default Value: Unchecked (false)
   ```

#### Visual Guide

```
Notion Database Properties:
┌─────────────────┬─────────────────┬──────────────┐
│ Aufgabe (Title) │ Status (Status) │ Status Check │
│                 │                 │ (Checkbox)   │
├─────────────────┼─────────────────┼──────────────┤
│ Complete Report │ In Arbeit       │ ☐            │
│ Review Meeting  │ Erledigt        │ ☑            │
│ Send Email      │ Nicht begonnen  │ ☐            │
└─────────────────┴─────────────────┴──────────────┘
```

### 2. Backward Compatibility

#### For Existing Databases
- **No data loss**: Existing memos will continue to work
- **Default values**: New Status Check field defaults to `false` (unchecked) for existing records
- **Automatic sync**: When Status field is set to "Erledigt", Status Check automatically becomes `true`

#### Migration Script (Optional)
If you want to synchronize existing "Erledigt" (completed) tasks:

```python
# Optional: Run this script to sync existing completed tasks
import asyncio
from src.services.memo_service import MemoService
from config.user_config import UserConfig

async def migrate_existing_memos():
    """Sync existing completed memos with status_check field."""
    user_config = UserConfig.load_user_config("your_user_id")
    memo_service = MemoService.from_user_config(user_config)
    
    # Get all completed memos
    completed_memos = await memo_service.get_memos_by_status("Erledigt")
    
    for memo in completed_memos:
        if not memo.status_check:  # If not already checked
            await memo_service.update_memo_status_check(
                memo.notion_page_id, 
                True
            )
            print(f"Updated memo: {memo.aufgabe}")

# Run migration
asyncio.run(migrate_existing_memos())
```

---

## Feature Overview

### What is Status Check?

The Status Check feature adds a checkbox field to your memos, providing a quick visual indicator of task completion status that works alongside the existing Status field.

### Key Benefits

1. **Visual Clarity**: Quick checkbox indicators (☐/☑) in Telegram
2. **Dual Status System**: 
   - Status field: Detailed workflow status ("Nicht begonnen", "In Arbeit", "Erledigt", "Verschoben")
   - Status Check: Simple binary completion indicator
3. **Smart Filtering**: New commands to show only unchecked (active) tasks
4. **Automatic Sync**: When Status = "Erledigt", Status Check automatically becomes checked

### How It Works

#### Status Field vs. Status Check
```
Traditional Status Field:
⭕ Nicht begonnen (Not Started)
🔄 In Arbeit (In Progress)
✅ Erledigt (Completed)
⏸️ Verschoben (Postponed)

New Status Check Field:
☐ Unchecked (Task active/pending)
☑ Checked (Task completed)
```

#### Combined Display
```
☐ ⭕ *Task Title*        (Not started, unchecked)
☐ 🔄 *Task Title*        (In progress, unchecked)
☑ ✅ *Task Title*        (Completed, checked)
☐ ⏸️ *Task Title*        (Postponed, unchecked)
```

### New Commands

#### `/memo` - Show Open Tasks Only
- **Before**: Showed all recent memos
- **After**: Shows only unchecked memos (status_check = false)
- **Benefit**: Focus on active tasks without completed items cluttering the view

#### `/show_all` - Show All Tasks
- **Purpose**: Display all recent memos regardless of status_check
- **Usage**: When you need to see completed tasks too
- **Display**: Uses checkbox indicators for all memos

#### `/check_memo` - Toggle Checkbox Status
- **Purpose**: Quickly check/uncheck memos
- **Usage**: Mark tasks as done without changing detailed status
- **Smart Sync**: Checking a memo can optionally update Status to "Erledigt"

---

## API Changes

### Model Changes (src/models/memo.py)

#### New Field
```python
class Memo(BaseModel):
    # ... existing fields ...
    status_check: Optional[bool] = Field(default=False, description="Checkbox indicator for task completion")
```

#### New Validation
```python
@field_validator('status_check')
@classmethod
def sync_status_fields(cls, v, info):
    """Synchronize status_check with status field."""
    if hasattr(info, 'data') and info.data and 'status' in info.data:
        status = info.data['status']
        # When status is "Erledigt", set status_check to True
        if status == MEMO_STATUS_COMPLETED:
            return True
    return v if v is not None else False
```

#### New Display Method
```python
def format_for_telegram_with_checkbox(self, timezone: str = "Europe/Berlin") -> str:
    """Format memo for Telegram display with checkbox indicators."""
    checkbox_indicator = "☑" if self.status_check else "☐"
    # ... formatting logic ...
```

### Service Changes (src/services/memo_service.py)

#### Modified get_recent_memos
```python
async def get_recent_memos(self, limit: int = 10, only_open: bool = True) -> List[Memo]:
    """
    Get recent memos from Notion database.
    
    Args:
        limit: Maximum number of memos to retrieve (default: 10)
        only_open: If True, only return memos with status_check=False (default: True)
    """
```

#### New Methods
```python
async def get_all_memos_including_checked(self, limit: int = 10) -> List[Memo]:
    """Get all recent memos regardless of status_check."""

async def update_memo_status_check(self, page_id: str, checked: bool) -> bool:
    """Update only the status_check (checkbox) of a memo."""
```

#### Enhanced Filtering
```python
# Filter for open memos (unchecked) 
filter_dict = {
    "property": "Status Check",
    "checkbox": {
        "equals": False
    }
}
```

### Notion Properties
```python
# In to_notion_properties()
properties["Status Check"] = {
    "checkbox": bool(self.status_check)
}

# In from_notion_page()
status_check = False
status_check_prop = properties.get('Status Check', {})
if status_check_prop.get('checkbox') is not None:
    status_check = status_check_prop['checkbox']
```

---

## Usage Examples

### Command Examples

#### 1. Viewing Open Tasks
```
User: /memo
Bot: 📝 *Deine offenen Memos:*

☐ ⭕ *Complete project proposal*
📊 Status: Nicht begonnen
📅 Fällig: 25.01.2025

☐ 🔄 *Review team feedback*
📊 Status: In Arbeit
📁 Projekt: Website Redesign
```

#### 2. Viewing All Tasks
```
User: /show_all
Bot: 📝 *Alle deine Memos:*

☐ ⭕ *Complete project proposal*
📊 Status: Nicht begonnen

☑ ✅ *Send weekly report*
📊 Status: Erledigt
📅 Fällig: 20.01.2025

☐ 🔄 *Review team feedback*
📊 Status: In Arbeit
```

#### 3. Checking a Memo
```
User: /check_memo
Bot: Wähle ein Memo zum Abhaken:
[Interactive buttons for each unchecked memo]

User: [Clicks "Complete project proposal"]
Bot: ✅ Memo erfolgreich als erledigt markiert!

☑ ⭕ *Complete project proposal*
📊 Status: Nicht begonnen
```

### Integration Examples

#### Creating Memos with Status Check
```python
# Creating a new memo
memo = Memo(
    aufgabe="Complete quarterly review",
    status="In Arbeit",
    status_check=False,  # Default for new tasks
    faelligkeitsdatum=datetime(2025, 2, 1),
    bereich="Management"
)

memo_service = MemoService.from_user_config(user_config)
page_id = await memo_service.create_memo(memo)
```

#### Updating Status Check
```python
# Mark memo as checked
await memo_service.update_memo_status_check(page_id, True)

# Uncheck memo
await memo_service.update_memo_status_check(page_id, False)
```

#### Smart Status Sync
```python
# When creating a completed memo
memo = Memo(
    aufgabe="Already finished task",
    status="Erledigt",  # This automatically sets status_check=True
    # status_check will be True due to validation
)
```

### Workflow Examples

#### 1. Daily Task Management
```
Morning: /memo                    # See today's open tasks
Work on tasks...
Evening: /check_memo             # Mark completed tasks
Next day: /memo                  # Only see remaining tasks
```

#### 2. Weekly Review
```
/show_all                        # Review all tasks
/check_memo                      # Clean up any missed completions
Filter by checked items to see accomplishments
```

#### 3. Project Tracking
```
Create project memos with status_check=False
Use /memo to see active project tasks
Use /check_memo for quick completion marking
Use detailed status field for workflow tracking
```

---

## Troubleshooting

### Common Issues

#### 1. Status Check Field Not Found
**Error**: `KeyError: 'Status Check'`
**Solution**: 
- Ensure you've added the "Status Check" checkbox property to your Notion database
- Property name must be exactly "Status Check" (case-sensitive)
- Property type must be "Checkbox"

#### 2. Existing Memos Not Showing Checkboxes
**Issue**: Old memos don't have checkbox indicators
**Solution**: 
- Notion automatically assigns `false` to existing records
- Run the migration script above to sync completed tasks
- Or manually check completed tasks in Notion

#### 3. Status Check Not Syncing with Status
**Issue**: Setting Status to "Erledigt" doesn't check the box
**Solution**: 
- This sync only works when creating new memos via the bot
- For existing memos, use `/check_memo` command
- Or update manually in Notion

#### 4. /memo Command Shows No Results
**Issue**: All memos are checked, so no open tasks to display
**Solution**: 
- Use `/show_all` to see all memos
- Create new memos for new tasks
- Uncheck completed memos if they need attention

### Configuration Validation

#### Check Database Setup
```python
# Test your database configuration
from src.services.memo_service import MemoService
from config.user_config import UserConfig

async def test_status_check_field():
    user_config = UserConfig.load_user_config("your_user_id")
    memo_service = MemoService.from_user_config(user_config)
    
    # This will fail if Status Check field is missing
    memos = await memo_service.get_recent_memos(limit=1)
    print(f"✅ Status Check field working: {len(memos)} memos retrieved")
```

#### Verify Field Type
1. Open your Notion database
2. Check that "Status Check" property shows as "Checkbox" type
3. Verify it appears in the property list

### Performance Considerations

#### Filtering Impact
- New filtering on Status Check field is indexed by Notion
- No significant performance impact expected
- Consider limiting `limit` parameter for large databases

#### Memory Usage
- Additional boolean field adds minimal memory overhead
- Checkbox data is lightweight in Notion API responses

### Migration Rollback

If you need to revert the changes:

1. **Remove Status Check Column** (Optional)
   - In Notion, delete the "Status Check" property
   - Bot will gracefully handle missing field

2. **Revert Code Changes**
   ```bash
   git checkout previous-version
   # or remove status_check related code
   ```

3. **Update Commands**
   - `/memo` will return to showing all memos
   - `/show_all` and `/check_memo` will not be available

---

## Support

### Getting Help

1. **Check Logs**: Look for error messages in bot logs
2. **Validate Configuration**: Ensure Notion database has correct fields
3. **Test Connection**: Use `test_notion_connection.py` script
4. **Review Examples**: See usage examples above

### Reporting Issues

When reporting issues, include:
- Error messages from logs
- Notion database configuration
- Steps to reproduce the problem
- Expected vs actual behavior

### Additional Resources

- [Notion API Documentation](https://developers.notion.com/)
- [Bot Configuration Guide](./NOTION_SETUP.md)
- [Architecture Documentation](../ARCHITECTURE.md)

---

*Last updated: January 2025*
*Version: 1.0*