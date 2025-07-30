# Memo Fix Applied

## Problem
Memos were failing with error: "Status is expected to be status"

## Root Cause
In `src/services/memo_service.py` line 146, the filter was using `"status"` instead of `"select"` for the Status property type in Notion.

## Fix Applied
Changed line 146 from:
```python
"status": {
    "equals": status
}
```

To:
```python
"select": {
    "equals": status
}
```

## Status
- ✅ Fix has been applied
- ✅ Container restarted
- ✅ The memo model already had correct "select" type for Status field

## Testing
To test if memos work now:
1. Send a message to the bot: "Einkaufen gehen"
2. Or click "➕ Neues Memo" in the menu
3. The bot should create the memo without errors

The Status field in Notion should be a Select type with options:
- Nicht begonnen
- In Arbeit
- Erledigt