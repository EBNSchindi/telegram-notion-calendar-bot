# Debug Partner Sync Failure - Dachtzelt Appointment

**STATUS: NOT EXECUTED - DRAFT ONLY**

## Bug Context
- User1 created an appointment with title "Dachtzelt" with PartnerRelevant=True
- Appointment was successfully created in private database
- Sync to shared database failed (appointment not appearing in shared DB)
- Testing performed in Docker environment
- Docker logs directory mounted at ./logs:/app/logs

## Technical Investigation Required

### 1. Verify Docker Container State and Logs
- Check Docker container logs: `docker logs calendar-telegram-bot`
- Examine log files in ./logs/ directory for sync-related errors
- Look for patterns: "Partner sync", "Error during sync", "shared database"
- Check if partner sync service started successfully: "Partner sync service started"

### 2. Database Configuration Verification
- Verify user1's configuration in users_config.json:
  - Check if "shared_notion_database_id" is properly set
  - Confirm "notion_api_key" has access to shared database
  - Verify "telegram_user_id" matches user1
- Check if shared database has required properties:
  - SourcePrivateId (Rich Text)
  - SourceUserId (Number)
  - All appointment fields from private DB

### 3. Partner Sync Service Analysis
Based on code analysis at src/services/partner_sync_service.py:
- Sync triggers on appointment creation (line 218-234 in combined_appointment_service.py)
- Sync should happen immediately if PartnerRelevant=True
- Check potential failure points:
  - Line 54: "No shared database configured" warning
  - Line 64: API key access for shared database
  - Line 100: General sync errors
  - Line 265-267: Missing notion_page_id

### 4. Specific Debug Steps
1. Add debug logging to track sync flow:
   ```python
   # In combined_appointment_service.py around line 219
   logger.info(f"Appointment created with partner_relevant={appointment.partner_relevant}")
   logger.info(f"Page ID: {page_id}, Shared service exists: {self.shared_service is not None}")
   ```

2. Check sync single appointment method execution:
   ```python
   # In partner_sync_service.py line 228
   logger.info(f"Attempting to sync appointment {appointment.title} with ID {appointment.notion_page_id}")
   ```

3. Verify Notion API responses:
   - Check if create_appointment in shared DB returns valid page_id
   - Verify update_sync_tracking succeeds (line 387-418)

### 5. Common Failure Scenarios to Check
1. **Missing shared_notion_database_id**: User config incomplete
2. **API Key Permissions**: notion_api_key lacks access to shared database
3. **Database Schema Mismatch**: Shared DB missing required properties
4. **Docker Network Issues**: Container can't reach Notion API
5. **Sync Tracking Failure**: SyncedToSharedId not updating in private DB

### 6. Immediate Fixes to Apply
1. Enable verbose logging for partner sync:
   ```python
   # Add to partner_sync_service.py __init__
   logger.setLevel(logging.DEBUG)
   ```

2. Add error context to sync failures:
   ```python
   # Update line 100 in partner_sync_service.py
   logger.error(f"Error during sync for user {user_config.telegram_user_id}: {e}", exc_info=True)
   ```

3. Implement sync retry mechanism:
   ```python
   # Add retry logic around line 228 in combined_appointment_service.py
   for attempt in range(3):
       try:
           success = await sync_service.sync_single_appointment(...)
           if success:
               break
       except Exception as e:
           logger.warning(f"Sync attempt {attempt+1} failed: {e}")
   ```

### 7. Testing Protocol
1. Create test appointment with specific debug markers:
   ```
   Title: "TEST_SYNC_DEBUG_[timestamp]"
   PartnerRelevant: True
   Description: "Debug sync issue"
   ```

2. Monitor logs in real-time:
   ```bash
   docker logs -f calendar-telegram-bot | grep -E "(sync|Sync|shared|Partner)"
   ```

3. Verify in Notion:
   - Check private DB for SyncedToSharedId field
   - Check shared DB for SourcePrivateId matching private appointment ID

### Success Criteria
- Partner-relevant appointments appear in shared database within 30 seconds
- SyncedToSharedId populated in private database
- No sync errors in logs
- Subsequent updates to appointment reflect in both databases

## Suggested Agent Chain (For Manual Execution)
1. **python-generator** → Add debug logging and error handling → Updates AGENT_LOG.md with code changes
2. **test-engineer** → Create sync failure test cases → Documents test results in AGENT_LOG.md
3. **python-generator** → Implement fixes based on test results → Logs implementation details
4. **doc-writer** → Update troubleshooting guide → References AGENT_LOG.md findings
5. **claude-status** → Aggregate debugging session metrics → Creates final report

## Alternative Debug Chain
1. **code-reviewer** → Analyze partner_sync_service.py for logic issues → Writes findings to AGENT_LOG.md
2. **python-generator** → Fix identified issues → Documents changes
3. **test-engineer** → Verify fixes with integration tests → Logs test results

## Complexity and Duration
- **Estimated Complexity**: Medium (2-3 hours)
- **Root Cause Likely**: Configuration or permission issue (70% probability)

## Quick Execution Summary
"Debug and fix partner sync failure for appointment 'Dachtzelt' from user1 to shared database: User1 created an appointment with title 'Dachtzelt' with PartnerRelevant=True. Appointment was successfully created in private database. Sync to shared database failed. Testing performed in Docker environment. Check Docker logs, verify user configuration, examine partner sync service execution flow, and implement necessary fixes with comprehensive logging."

---

**⚠️ THIS IS A DRAFT - REVIEW BEFORE RUNNING ⚠️**