# Migration Guide: Memo Functionality & Unified API Keys

## Overview
This update adds memo/task functionality and simplifies the configuration by using a single Notion API key per user instead of separate keys for different databases.

## Breaking Changes

### UserConfig Structure Changes
**REMOVED fields:**
- `shared_notion_api_key` 
- `business_notion_api_key`

**ADDED fields:**
- `memo_database_id` (optional)

**UPDATED logic:**
- All databases now use the single `notion_api_key` per user

## Migration Steps

### 1. Update users_config.json

**Before:**
```json
{
  "notion_api_key": "secret_xxx_private_key",
  "shared_notion_api_key": "secret_xxx_shared_key", 
  "business_notion_api_key": "secret_xxx_business_key"
}
```

**After:**
```json
{
  "notion_api_key": "secret_xxx_unified_key",
  "memo_database_id": "your_memo_database_id"
}
```

### 2. Notion Integration Setup

#### Option A: Use Existing Integration (Recommended)
If you have a Notion integration with access to all databases:
1. Use that integration's API key as the unified `notion_api_key`
2. Remove the separate API key fields
3. Add `memo_database_id` if you want memo functionality

#### Option B: Create New Integration
If your current integrations have limited database access:
1. Create a new Notion integration in https://www.notion.so/my-integrations
2. Give it access to ALL databases you want to use (private, shared, business, memo)
3. Use this new API key as the unified `notion_api_key`

### 3. Create Memo Database (Optional)

If you want memo functionality:

1. **Create Memo Database in Notion:**
   - Title: "Memos" or similar
   - Add these properties:
     - `Aufgabe` (Title) - Required
     - `Status` (Status) - Options: "Nicht begonnen", "In Arbeit", "Erledigt" 
     - `Fälligkeitsdatum` (Date) - Optional
     - `Bereich` (Text) - Optional
     - `Projekt` (Text) - Optional  
     - `Notizen` (Text) - Optional

2. **Copy Database ID:**
   - Share the database and copy the ID from the URL
   - Add it as `memo_database_id` in your user config

3. **Share with Integration:**
   - Make sure your Notion integration has access to this database

## New Features

### Simplified Menu
- **Before:** 6 buttons with submenus
- **After:** 4 main buttons + Help (2x2+1 grid)
  - 📅 Termine Heute & Morgen
  - 📝 Letzte 10 Memos  
  - ➕ Neuer Termin
  - ➕ Neues Memo
  - ❓ Hilfe

### Memo Functionality
- AI-powered task extraction from natural language
- Status tracking (Nicht begonnen, In Arbeit, Erledigt)
- Due date support
- Project and area categorization
- Quick access to last 10 memos

### Email Processing 
- **IMPORTANT:** All emails are now deleted after processing (success or failure)
- More robust error handling

## Example Migration

**users_config.json before:**
```json
{
  "telegram_user_id": 123456789,
  "notion_api_key": "secret_abc_private", 
  "notion_database_id": "private_db_id",
  "shared_notion_api_key": "secret_def_shared",
  "shared_notion_database_id": "shared_db_id",
  "business_notion_api_key": "secret_ghi_business", 
  "business_notion_database_id": "business_db_id"
}
```

**users_config.json after:**
```json
{
  "telegram_user_id": 123456789,
  "notion_api_key": "secret_unified_key_with_all_access",
  "notion_database_id": "private_db_id", 
  "shared_notion_database_id": "shared_db_id",
  "business_notion_database_id": "business_db_id",
  "memo_database_id": "memo_db_id"
}
```

## Troubleshooting

### "Database not found" errors
- Verify your unified API key has access to all databases
- Check database IDs are correct
- Ensure databases are properly shared with the integration

### Memo functionality not working  
- Verify `memo_database_id` is set and valid
- Check memo database has all required fields
- Ensure Notion integration has access to memo database

### Email processing issues
- All emails are now deleted after processing - this is expected
- Check logs for specific error details
- Verify email credentials and database access

## Rollback Plan

If you need to rollback:
1. Restore previous `users_config.json` 
2. Use git to revert to the previous commit
3. Restart the bot

## Support

For issues with this migration:
1. Check the logs for specific errors
2. Verify Notion integration permissions  
3. Test database access manually
4. Review the updated `users_config.example.json` for reference

---
*Generated for Telegram Notion Calendar Bot v2.0 - Memo Update*