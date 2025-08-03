# Migration Guide: Date Field Update

This guide helps you migrate your Notion databases to support the new separate start and end date fields for appointments.

## Overview

The Telegram-Notion Calendar Bot now supports separate start and end dates for appointments, replacing the single date field. This allows for:
- Multi-day events
- Precise duration tracking
- Better calendar integration

## What's Changed

### Old Structure
- Single field: `Datum` (Date)
- Duration stored separately or assumed to be 60 minutes

### New Structure
- Two fields: `Startdatum` (Start Date) and `Endedatum` (End Date)
- Duration automatically calculated from the difference
- Full backward compatibility maintained

## Migration Steps

### Step 1: Update Your Notion Database Schema

Add the following two new fields to your appointment database:

1. **Startdatum** (Start Date)
   - Type: Date
   - Include time: Yes ✓
   - Required: Yes

2. **Endedatum** (End Date)
   - Type: Date
   - Include time: Yes ✓
   - Required: Yes

### Step 2: Keep Existing Fields (Optional)

You can keep the old `Datum` field for backward compatibility. The bot will:
- Read from new fields if available
- Fall back to old field if new fields are empty
- Automatically populate all fields when creating new appointments

### Step 3: Migrate Existing Data (Optional)

If you want to migrate existing appointments to use the new fields:

#### Option A: Manual Migration
1. For each appointment, copy the `Datum` value to `Startdatum`
2. Set `Endedatum` to `Startdatum` + duration (default 60 minutes if not specified)

#### Option B: Notion Formula (Temporary)
Add these formulas temporarily to help with migration:
```
Startdatum = prop("Datum")
Endedatum = dateAdd(prop("Datum"), prop("Duration") or 60, "minutes")
```

### Step 4: Test the Integration

1. Create a test appointment using the bot
2. Verify both new fields are populated correctly
3. Check that existing appointments still display properly

## Backward Compatibility

The bot maintains full backward compatibility:

- **Reading**: Automatically detects which fields are available
- **Writing**: Populates both old and new fields
- **No immediate action required**: Your bot will continue working without changes

## Benefits of Migration

1. **Multi-day Events**: Create appointments spanning multiple days
2. **Accurate Duration**: Precise tracking of appointment length
3. **Better Visualization**: Notion calendar views show proper time blocks
4. **Future Features**: Enables upcoming features like:
   - Conflict detection
   - Calendar export
   - Time zone handling improvements

## Natural Language Support

The bot now understands duration in natural language:

### German Examples
- "Meeting morgen 14 Uhr für 2 Stunden"
- "Termin heute 15:30 für 30 min"
- "Besprechung um 10 für eine halbe Stunde"

### English Examples
- "Meeting tomorrow 2pm for 2 hours"
- "Appointment at 3:30 for 30 minutes"
- "Call at 10am for half an hour"

## Troubleshooting

### Issue: Old appointments don't show end time
**Solution**: This is normal. Old appointments will continue to work as before. Only new appointments will have separate start/end times.

### Issue: Bot creates appointments with wrong duration
**Solution**: Make sure to specify duration in your message, e.g., "Meeting for 2 hours". Default is 60 minutes.

### Issue: Notion formulas not working
**Solution**: Ensure date fields have "Include time" enabled in Notion.

## Need Help?

If you encounter any issues during migration:
1. Check that all field names match exactly (case-sensitive)
2. Ensure your Notion integration has access to the database
3. Test with a simple appointment first
4. Contact support with error messages if problems persist

## Version Compatibility

- Bot Version 3.0.0+: Full support for new date fields
- Bot Version 2.x: Continue using single date field
- Mixed Environment: Both versions can coexist during migration