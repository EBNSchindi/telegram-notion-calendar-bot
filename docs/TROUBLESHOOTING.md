# 🔧 Troubleshooting Guide - Telegram Notion Calendar Bot

## 📋 Table of Contents
- [Time Format Problems](#time-format-problems)
- [Database Problems](#database-problems)
- [Partner Sync Issues](#partner-sync-issues)
- [Appointment Creation Problems](#appointment-creation-problems)
- [Reminder Problems](#reminder-problems)
- [Menu Problems](#menu-problems)
- [Debug Commands](#debug-commands)
- [Date Field Migration](#date-field-migration)
- [Configuration Problems](#configuration-problems)
- [Debug Logging](#debug-logging)
- [Docker-Specific Issues](#docker-specific-issues)
- [Common Error Messages](#common-error-messages)

## 🕐 Time Format Problems

### Problem: "Invalid time format" error

**Symptom:** The bot doesn't accept your time input.

**Quick Solution:**
1. **Test your time format:** `/test_time 16 Uhr`
2. **Show all formats:** `/formats`
3. **Validate complete command:** `/validate tomorrow 16 Uhr Meeting`

### Common Time Format Errors

| ❌ Wrong | ✅ Correct | Result |
|-----------|------------|----------|
| `16` | `16 Uhr` or `16:00` | 16:00 |
| `4 pm` (with space) | `4pm` or `4 PM` | 16:00 |
| `2,30` | `2:30` or `2.30` | 02:30 |
| `halb3` | `halb 3` | 02:30 |
| `viertelvor5` | `viertel vor 5` | 04:45 |

### Supported Time Formats

#### 🕐 Standard Formats
```
14:30    → 14:30
14.30    → 14:30  
1430     → 14:30
930      → 09:30
```

#### 🇩🇪 German Formats
```
16 Uhr              → 16:00
16 Uhr 30           → 16:30
16:30 Uhr           → 16:30
halb 3              → 02:30
viertel vor 5       → 04:45
viertel nach 3      → 03:15
```

#### 🇺🇸 English Formats
```
4 PM                → 16:00
8 AM                → 08:00
4:30 PM             → 16:30
12 AM               → 00:00 (midnight)
12 PM               → 12:00 (noon)
quarter past 2      → 02:15
half past 3         → 03:30
quarter to 5        → 04:45
```

## 🗂 Database Problems

### Problem: "You are not configured yet"

**Cause:** Your Telegram User ID is not in `users_config.json`.

**Solution:**
1. Find your User ID with `/start` (will be displayed)
2. Administrator must add you to `users_config.json`
3. Restart bot

### Problem: Appointments from shared database not showing

**Possible Causes:**
- Missing `shared_notion_api_key` or `shared_notion_database_id`
- No permission for shared database
- Shared database is empty

**Debugging:**
1. Check database status with `/start`
2. Test connection with `/reminder test`

## 📅 Appointment Creation Problems

### Problem: "Appointment must be in the future"

**Cause:** You're trying to create an appointment in the past.

**Solution:**
```bash
# Wrong (if it's already after 14:30)
/add today 14:30 Meeting

# Correct
/add tomorrow 14:30 Meeting
# or
/add today 16:00 Meeting  # if it's still before 16:00
```

### Problem: Appointment not created

**Debugging Steps:**
1. **Validate input:** `/validate tomorrow 16 Uhr Meeting`
2. **Test time format:** `/test_time 16 Uhr`
3. **Check database status:** `/start`

## 📨 Reminder Problems

### Problem: No reminders received

**Checklist:**
1. ✅ Reminders enabled: `/reminder`
2. ✅ Correct time set: `/reminder time 08:00`
3. ✅ Bot is running and online
4. ✅ Appointments exist for today/tomorrow

**Test:** `/reminder test` - should send reminder immediately

### Problem: Reminder shows wrong appointments

**Possible Causes:**
- Wrong timezone configured
- Data in wrong database

**Solution:**
- Check timezone in `users_config.json`
- Test with `/reminder preview`

## 🎛 Menu Problems

### Problem: Inline buttons don't work

**Cause:** Old Telegram version or bot update

**Solution:**
1. Update Telegram app
2. Restart bot with `/start`
3. Alternative: Use direct commands (`/today`, `/list`, etc.)

## 🔍 Debug Commands

### Test Time Format
```bash
/test_time 16 Uhr
# Shows: ✅ Success: 16:00 (16:00)

/test_time 4 PM  
# Shows: ✅ Success: 16:00 (16:00)

/test_time halb 3
# Shows: ✅ Success: 02:30 (02:30)
```

### Show All Formats
```bash
/formats
# Shows complete list of all supported time formats
```

### Validate Appointment Input
```bash
/validate tomorrow 16 Uhr Meeting
# Checks date, time and title before creation
```

## 👥 Partner Sync Issues

### Problem: Partner sync not working (appointments not appearing in shared database)

**Symptoms:**
- Appointments marked as "Partner Relevant" stay only in private database
- No error messages in Telegram
- Shared database remains empty or doesn't update

**Common Causes:**
1. Missing or incorrect shared database configuration
2. API key permissions insufficient
3. Date field migration issue (old `Datum` vs new `Startdatum`/`Endedatum`)
4. Network connectivity issues in Docker environment

### Solution 1: Verify Configuration

Check your `users_config.json` for the affected user:

```json
{
  "users": [
    {
      "telegram_user_id": 123456789,
      "notion_api_key": "secret_...",
      "notion_database_id": "your-private-db-id",
      "shared_notion_database_id": "your-shared-db-id"  // ← Must be present!
    }
  ]
}
```

**Requirements:**
- `shared_notion_database_id` must be configured
- The `notion_api_key` must have access to BOTH databases
- Both databases must have compatible schemas

### Solution 2: Check Database Schema

The shared database must have these properties:

**Required Fields:**
- `Titel` (Title) - Text
- `Startdatum` (Date) - Date field with time
- `Endedatum` (Date) - Date field with time
- `Beschreibung` (Rich Text) - Optional
- `Ort` (Rich Text) - Optional
- `SourcePrivateId` (Rich Text) - For sync tracking
- `SourceUserId` (Number) - To identify sync source

**Legacy Support:**
- `Datum` (Date) - Old date field, still supported for backward compatibility

### Solution 3: Enable Debug Logging

To diagnose sync issues, enable debug logging:

1. **For Docker deployments:**
```bash
# View real-time logs
docker logs -f calendar-telegram-bot | grep -E "(sync|Sync|shared|Partner)"

# Check log files
cat ./logs/bot_enhanced.log | grep "Partner sync"
```

2. **Look for these log patterns:**
```
INFO - Partner sync service started
DEBUG - Attempting to sync appointment "Meeting" with ID page_xxx
ERROR - Error during sync for user 123456789: [error details]
WARNING - No shared database configured for user 123456789
```

### Solution 4: Test Sync with Debug Markers

Create a test appointment with specific markers:

```
/add morgen 14:00 TEST_SYNC_[timestamp]
```

Then mark it as partner relevant and monitor logs:
- Check private database for `SyncedToSharedId` field
- Check shared database for matching `SourcePrivateId`
- Sync should complete within 30 seconds

## 📅 Date Field Migration

### Background
The bot migrated from a single `Datum` field to separate `Startdatum` and `Endedatum` fields. This change affected partner sync functionality.

### Problem: Old appointments not syncing

**Symptom:** Appointments created before the migration don't sync to shared database

**Solution:**
The bot now handles both formats automatically:
- New appointments use `Startdatum`/`Endedatum`
- Old appointments with only `Datum` are still readable
- Partner sync converts old format to new during sync

**No manual intervention needed** - the bot handles this transparently.

### Verification
Check if an appointment has been migrated:
1. Open Notion
2. Check if appointment has both `Startdatum` and `Endedatum` fields populated
3. Old appointments may only have `Datum` - these will be migrated during next sync

## ⚙️ Configuration Problems

### Problem: "Du bist noch nicht konfiguriert" error

**Solution:**
1. Get your Telegram User ID: Send `/start` to the bot
2. Add your ID to `users_config.json`
3. Restart the bot

### Problem: Shared database access denied

**Symptoms:**
- `403 Forbidden` errors in logs
- "Unauthorized" messages

**Solution:**
1. Ensure your Notion API key has access to the shared database
2. In Notion: Share the database with your integration
3. Check if the database is in a shared workspace/teamspace

### Teamspace Configuration

If your shared database is in a Notion teamspace:

```json
{
  "telegram_user_id": 123456789,
  "notion_api_key": "secret_...",
  "notion_database_id": "private-db-id",
  "shared_notion_database_id": "shared-db-id",
  "teamspace_config": {
    "enabled": true,
    "private_in_teamspace": false,
    "shared_in_teamspace": true
  }
}
```

## 🐛 Debug Logging

### Enable Detailed Logging

1. **Environment Variable:**
```bash
export LOG_LEVEL=DEBUG
```

2. **Docker Compose:**
```yaml
environment:
  - LOG_LEVEL=DEBUG
```

3. **Key Log Locations:**
- `./logs/bot_enhanced.log` - Main application logs
- `./logs/sync_debug.log` - Partner sync specific logs (if configured)

### Useful Debug Commands

```bash
# Show all sync attempts
grep "sync_single_appointment" logs/bot_enhanced.log

# Show sync errors only
grep -E "ERROR.*sync" logs/bot_enhanced.log

# Show successful syncs
grep "Successfully synced appointment" logs/bot_enhanced.log

# Check retry attempts
grep "Retrying in" logs/bot_enhanced.log
```

## 🐳 Docker-Specific Issues

### Problem: Sync works locally but not in Docker

**Common Causes:**
1. Network isolation
2. DNS resolution issues
3. Timezone mismatches

**Solutions:**

1. **Check Docker network:**
```bash
# Verify internet connectivity
docker exec calendar-telegram-bot ping -c 3 api.notion.com
```

2. **Timezone configuration:**
```yaml
# docker-compose.yml
environment:
  - TZ=Europe/Berlin
```

3. **DNS issues:**
```yaml
# docker-compose.yml
dns:
  - 8.8.8.8
  - 8.8.4.4
```

### Problem: Logs not visible

**Solution:**
Ensure volume mounting in `docker-compose.yml`:
```yaml
volumes:
  - ./logs:/app/logs
  - ./data:/app/data
```

## ❗ Common Error Messages

### "Error during sync: 429 Too Many Requests"
**Cause:** Notion API rate limit
**Solution:** The bot now implements automatic retry with exponential backoff. No action needed.

### "Duplicate appointment detected"
**Cause:** Appointment already exists in shared database
**Solution:** This is normal behavior preventing duplicates. Check logs for details.

### "Missing notion_page_id"
**Cause:** Appointment creation failed
**Solution:** Check private database creation succeeded first

### "JSON decode error" or "Extra data"
**Cause:** AI response parsing issue
**Solution:** Fixed in latest version with robust JSON parsing

## 🔄 Retry Mechanism

The bot implements intelligent retry logic for partner sync:

1. **Automatic Retries:** 3 attempts with exponential backoff
2. **Delays:** 1s → 2s → 4s (with jitter)
3. **Permanent Failures:** Validation errors won't retry
4. **Temporary Failures:** Network/rate limit errors will retry

Monitor retry behavior:
```bash
grep "Retrying in" logs/bot_enhanced.log
```

## 💡 Quick Diagnostics Checklist

When partner sync isn't working:

1. ✅ Check `/start` shows shared database as connected
2. ✅ Verify `shared_notion_database_id` in config
3. ✅ Test with simple appointment: `/add morgen 14:00 TEST`
4. ✅ Mark as partner relevant
5. ✅ Check logs within 30 seconds
6. ✅ Verify in Notion shared database

If all checks pass but sync still fails, enable DEBUG logging and check for specific error messages.

## 📞 Getting Help

If problems persist:
1. Collect relevant log entries
2. Note your configuration (sanitize API keys)
3. Document the exact steps to reproduce
4. Check GitHub issues for similar problems

Remember: Most sync issues are configuration-related and can be resolved by verifying the shared database setup and API key permissions.

## 📞 Support

### If nothing helps:

1. **Check logs:** Bot administrator can check `bot.log`
2. **Restart:** Restart bot and/or Telegram app
3. **Test commands:** Use debug commands for diagnosis
4. **Check config:** Validate `users_config.json` and `.env`

### Common Solutions:
- Restart bot
- Update Telegram app  
- Reload configuration
- Clear user cache (restart bot)

---

💡 **Tip:** Use debug commands (`/test_time`, `/formats`, `/validate`) to quickly identify problems\!
