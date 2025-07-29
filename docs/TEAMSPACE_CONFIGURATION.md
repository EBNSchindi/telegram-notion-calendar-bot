# Teamspace Configuration Guide

## Overview

This guide explains how to configure the Telegram Notion Calendar Bot for Notion Teamspace environments where the shared database requires special API key handling.

## Problem Statement

In Notion Teamspace:
- Shared databases often require the Teamspace owner's API key for access
- Individual users have their own API keys for private databases
- Mixing API keys incorrectly leads to access errors

## Solution: Dual API Key System

The bot now supports two API keys per user:
1. **Personal API Key** (`notion_api_key`): For private and memo databases
2. **Teamspace Owner API Key** (`teamspace_owner_api_key`): For shared database access

## Configuration

### For Teamspace Owner

```json
{
  "telegram_user_id": 123456789,
  "telegram_username": "teamspace_owner",
  "notion_api_key": "secret_xxx_owner_personal_api_key",
  "notion_database_id": "owner_private_database_id",
  "shared_notion_database_id": "shared_database_id_in_teamspace",
  "memo_database_id": "owner_memo_database_id",
  "teamspace_owner_api_key": null,
  "is_owner": true,
  "timezone": "Europe/Berlin",
  "language": "de",
  "reminder_time": "08:00",
  "reminder_enabled": true
}
```

**Key Points:**
- `is_owner`: Set to `true`
- `teamspace_owner_api_key`: Can be `null` (owner uses their own key)
- The owner's `notion_api_key` is used for ALL databases

### For Team Members

```json
{
  "telegram_user_id": 987654321,
  "telegram_username": "team_member",
  "notion_api_key": "secret_xxx_member_personal_api_key",
  "notion_database_id": "member_private_database_id",
  "shared_notion_database_id": "shared_database_id_in_teamspace",
  "memo_database_id": "member_memo_database_id",
  "teamspace_owner_api_key": "secret_xxx_owner_api_key_for_shared_db",
  "is_owner": false,
  "timezone": "Europe/Berlin",
  "language": "de",
  "reminder_time": "09:00",
  "reminder_enabled": true
}
```

**Key Points:**
- `is_owner`: Set to `false`
- `teamspace_owner_api_key`: Must contain the Teamspace owner's API key
- Member's `notion_api_key` is used for private/memo databases only
- `teamspace_owner_api_key` is used ONLY for shared database access

## API Key Usage Logic

The system automatically determines which API key to use:

```python
# For private and memo databases:
api_key = user.notion_api_key  # Always use user's own key

# For shared database:
if user.is_owner:
    api_key = user.notion_api_key  # Owner uses their own key
else:
    api_key = user.teamspace_owner_api_key  # Members use owner's key
```

## Migration from Old Configuration

If you're upgrading from the previous version:

1. **Add new fields to each user:**
   - `teamspace_owner_api_key`: Set to owner's API key (or null for owner)
   - `is_owner`: Set to true/false accordingly

2. **Update API key names for clarity:**
   - Old: `notion_api_key` (used for everything)
   - New: `notion_api_key` (personal databases only)

## Environment Variables (Optional)

For backward compatibility, you can also set via environment:

```bash
# For default user (backward compatibility)
TEAMSPACE_OWNER_API_KEY=secret_xxx_owner_api_key
IS_TEAMSPACE_OWNER=false
```

## Security Best Practices

1. **Never share the owner's API key directly** - Add it to team members' config only
2. **Use environment variables** for sensitive keys in production
3. **Regularly rotate API keys** for security
4. **Limit shared database permissions** to necessary operations only

## Troubleshooting

### Common Issues

1. **"Unauthorized" error on shared database:**
   - Verify `teamspace_owner_api_key` is correct
   - Ensure the owner's API key has access to the shared database

2. **Cannot access private databases:**
   - Check that `notion_api_key` is the user's personal key
   - Verify the user has access to their private databases

3. **Owner cannot access shared database:**
   - Ensure `is_owner` is set to `true`
   - Verify the shared database is in the Teamspace

## Example Scenarios

### Scenario 1: Family Calendar
- Dad (Teamspace owner): Uses his API key for everything
- Mom (Team member): Uses her key for private, Dad's key for shared
- Kids (Team members): Use their keys for private, Dad's key for shared

### Scenario 2: Work Team
- Project Manager (Owner): Full access with own key
- Developers (Members): Private tasks + shared calendar access
- Contractors (Members): Limited access with specific permissions

## Testing Your Configuration

1. **Test Private Database Access:**
   ```
   /neuer_termin Test Private
   ```

2. **Test Shared Database Access:**
   ```
   /neuer_termin Test Shared
   [Select "In gemeinsame Datenbank speichern"]
   ```

3. **Verify Sync Service:**
   - Create appointment with PartnerRelevant = true
   - Check if it syncs to shared database

## Support

If you encounter issues:
1. Check logs for specific error messages
2. Verify all API keys are valid and not placeholders
3. Ensure database IDs are correct
4. Confirm Teamspace permissions are properly set