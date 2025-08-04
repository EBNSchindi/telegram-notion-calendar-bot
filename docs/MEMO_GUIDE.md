# 📝 Telegram Notion Calendar Bot - MEMO System Guide

## Overview

The MEMO system is a comprehensive task management feature integrated into the Telegram Notion Calendar Bot. It allows users to create, manage, and track tasks/memos through natural language commands, with full Notion database integration and AI-powered text extraction.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Database Setup](#database-setup)
3. [Features](#features)
4. [Usage Guide](#usage-guide)
5. [Technical Documentation](#technical-documentation)
6. [Migration & Updates](#migration--updates)
7. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Creating a Memo
1. Send `/start` to open the main menu
2. Click **"➕ Neues Memo"**
3. Type your task in natural language:
   - "Einkaufsliste: Milch, Brot, Butter"
   - "Präsentation vorbereiten bis Freitag"
   - "Zahnarzttermin buchen"

### Viewing Memos
- **Open tasks only**: `/start` → **"📝 Letzte Memos"**
- **All tasks**: `/show_all`
- **Toggle completion**: `/check_memo`

---

## Database Setup

### Required Notion Properties

Your Notion memo database must have these properties:

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| **Aufgabe** | Title | ✅ | Task name/description |
| **Status** | Status | ✅ | Task status (see values below) |
| **Status Check** | Checkbox | ✅ | Quick completion indicator |
| **Fälligkeitsdatum** | Date | ❌ | Due date |
| **Bereich** | Multi-Select | ❌ | Categories/areas |
| **Projekt** | Multi-Select | ❌ | Project assignment |
| **Notizen** | Rich Text | ❌ | Additional notes |

### Status Values

The Status property must have these exact options:
- `Nicht begonnen` (Not Started) - ⭕
- `In Bearbeitung` (In Progress) - 🔄  
- `Erledigt` (Completed) - ✅
- `Aufgeschoben` (Postponed) - ⏸️

### Status Check Feature

The Status Check checkbox provides:
- Visual indicators in Telegram (☐/☑)
- Quick filtering for open tasks
- Automatic sync with Status field (Erledigt → checked)

---

## Features

### 🤖 AI-Powered Text Extraction
- Natural language processing for task creation
- Automatic due date detection from text
- Fallback to basic extraction if AI unavailable
- Support for German and English inputs

### 📊 Dual Status System
1. **Status Field**: Detailed workflow tracking
2. **Status Check**: Simple completion checkbox

### 🔍 Smart Filtering
- Default view shows only unchecked (open) tasks
- `/show_all` command to see all tasks including completed
- Automatic hiding of completed tasks from main view

### 🔄 Status Synchronization
- When Status = "Erledigt", Status Check automatically becomes checked
- Checking a memo can optionally update Status to "Erledigt"

### 🎨 Visual Formatting
- Emoji indicators for status
- Checkbox indicators for completion
- Clean, organized display in Telegram

---

## Usage Guide

### Main Menu Integration

The memo system is fully integrated into the simplified 2x2+1 main menu:

```
┌─────────────────────┬─────────────────────┐
│ 📅 Termine Heute    │ 📝 Letzte 10 Memos │
│    & Morgen         │                     │
├─────────────────────┼─────────────────────┤
│ ➕ Neuer Termin     │ ➕ Neues Memo       │
├─────────────────────┴─────────────────────┤
│            ❓ Hilfe                        │
└───────────────────────────────────────────┘
```

### Commands

#### `/start` or `/menu`
Opens the main menu with quick access to memo functions

#### `/show_all`
Shows all memos including completed ones:
```
📝 Alle deine Memos:

☐ ⭕ Complete project proposal
📊 Status: Nicht begonnen

☑ ✅ Send weekly report
📊 Status: Erledigt
📅 Fällig: 20.01.2025
```

#### `/check_memo`
Interactive menu to toggle memo completion status

### Creating Memos

After clicking "➕ Neues Memo", send your task as a normal message:

**Simple tasks:**
- "Buy groceries"
- "Call dentist"
- "Review presentation"

**With due dates:**
- "Complete report by Friday"
- "Submit proposal bis Montag"
- "Prepare meeting für morgen"

**With details:**
- "Project X: Review design documents"
- "Website: Fix mobile navigation"
- "Team Meeting: Prepare Q1 agenda"

### Memo Display Format

```
☐ ⭕ *Task Title*
📊 Status: Nicht begonnen
📅 Fällig: 25.01.2025
📁 Projekt: Website Redesign
🏷️ Bereich: Development, Frontend
📝 Notizen: Additional details here
```

---

## Technical Documentation

### Architecture

```
User Input → Telegram Handler → AI Service → Memo Service → Notion API
                                    ↓
                              Fallback Parser
```

### Models

#### Memo Model (src/models/memo.py)
```python
class Memo(BaseModel):
    aufgabe: str  # Task title
    status: str = "Nicht begonnen"
    status_check: Optional[bool] = False
    faelligkeitsdatum: Optional[datetime] = None
    bereich: Optional[List[str]] = []
    projekt: Optional[List[str]] = []
    notizen: Optional[str] = None
    notion_page_id: Optional[str] = None
```

### API Integration

#### Creating a Memo
```python
memo = Memo(
    aufgabe="Complete quarterly review",
    status="In Bearbeitung",
    faelligkeitsdatum=datetime(2025, 2, 1),
    bereich=["Management"]
)

memo_service = MemoService.from_user_config(user_config)
page_id = await memo_service.create_memo(memo)
```

#### Updating Status Check
```python
# Mark as completed
await memo_service.update_memo_status_check(page_id, True)

# Uncheck
await memo_service.update_memo_status_check(page_id, False)
```

### Notion Property Mapping

```python
properties = {
    "Aufgabe": {"title": [{"text": {"content": self.aufgabe}}]},
    "Status": {"status": {"name": self.status}},
    "Status Check": {"checkbox": bool(self.status_check)},
    "Fälligkeitsdatum": {"date": {"start": date_str}} if self.faelligkeitsdatum else {"date": None},
    "Bereich": {"multi_select": [{"name": b} for b in self.bereich]},
    "Projekt": {"multi_select": [{"name": p} for p in self.projekt]},
    "Notizen": {"rich_text": [{"text": {"content": self.notizen}}]} if self.notizen else {"rich_text": []}
}
```

---

## Migration & Updates

### Version History

#### v3.0.0 - Complete MEMO System Implementation
- Full memo management system
- AI-powered text extraction
- German field names support
- Integration with main menu

#### v3.1.0 - Status Check Feature
- Added checkbox field for quick completion tracking
- Smart filtering for open tasks only
- `/show_all` command for viewing all tasks
- Automatic status synchronization

### Database Migration

#### Adding Status Check Field (v3.1.0)

1. Open your Notion memo database
2. Add new property:
   - Name: `Status Check`
   - Type: `Checkbox`
   - Default: Unchecked

3. Optional: Sync existing completed tasks
```python
# For existing "Erledigt" tasks, check the checkbox
async def migrate_completed_tasks():
    completed_memos = await memo_service.get_memos_by_status("Erledigt")
    for memo in completed_memos:
        if not memo.status_check:
            await memo_service.update_memo_status_check(
                memo.notion_page_id, True
            )
```

### Breaking Changes

#### v3.0.0
- Changed from English to German field names
- Status value "In Arbeit" → "In Bearbeitung"
- Added "Aufgeschoben" status

---

## Troubleshooting

### Common Issues

#### 1. "KeyError: 'Status Check'"
**Solution**: Add the Status Check checkbox field to your Notion database

#### 2. Memos not appearing
**Possible causes:**
- Database permissions not set correctly
- Wrong database ID in configuration
- Status values don't match exactly

**Debug steps:**
1. Check bot logs for specific errors
2. Verify database ID in users_config.json
3. Ensure all required fields exist in Notion

#### 3. AI extraction not working
**Fallback behavior**: Bot will save entire message as task title
**Check**: Verify OpenAI API key is configured

#### 4. Status not syncing
**Note**: Automatic sync only works when creating/updating via bot
**Manual fix**: Use `/check_memo` to update status

### Configuration Validation

Test your setup:
```python
from src.services.memo_service import MemoService
from config.user_config import UserConfig

async def test_memo_setup():
    user_config = UserConfig.load_user_config("your_user_id")
    memo_service = MemoService.from_user_config(user_config)
    
    # Test retrieval
    memos = await memo_service.get_recent_memos(limit=1)
    print(f"✅ Setup working: {len(memos)} memos retrieved")
    
    # Test creation
    test_memo = Memo(aufgabe="Test memo")
    page_id = await memo_service.create_memo(test_memo)
    print(f"✅ Creation working: {page_id}")
```

### Performance Tips

1. **Limit queries**: Use appropriate limit values (default: 10)
2. **Filter at source**: Use only_open=True for better performance
3. **Cache results**: Consider caching for frequently accessed data

### Getting Help

When reporting issues, provide:
- Error messages from logs
- Notion database structure (screenshot)
- Configuration excerpt (without API keys)
- Steps to reproduce

---

## Best Practices

### Task Organization
- Use consistent project/area naming
- Set realistic due dates
- Keep task titles concise but descriptive
- Use notes field for additional context

### Workflow Tips
1. **Daily routine**: Check open tasks each morning with default view
2. **Weekly review**: Use `/show_all` to review completed work
3. **Quick updates**: Use `/check_memo` for fast completion marking
4. **Detailed tracking**: Use Status field for workflow stages

### Integration with Calendar
- Tasks with due dates can be viewed alongside appointments
- Use consistent naming between memos and calendar entries
- Consider time blocking for important memos

---

*Last updated: January 2025*  
*Version: 3.1.0*  
*Part of Telegram Notion Calendar Bot*