# Webex CDR Downloader

Platform-independent Python solution for downloading Webex Call Detail Records (CDR) and storing them in SQL Server. Designed to run periodically via scheduled tasks with automatic OAuth token refresh and incremental data synchronization.

## Features

- **OAuth 2.0 Authentication**: Automatic token refresh, no manual intervention needed
- **Secure Credential Storage**: Uses system keyring (macOS Keychain, Windows Credential Manager, Linux Secret Service)
- **Incremental Sync**: Fetches only new records since last run
- **First Run Support**: Automatically pulls all available CDR data (past 48 hours)
- **Platform Independent**: Runs on Windows, macOS, and Linux
- **Automatic Table Creation**: Database schema created automatically
- **Duplicate Prevention**: UNIQUE constraints prevent duplicate records
- **Error Logging**: Comprehensive error tracking in database
- **Retry Logic**: Automatic retry with exponential backoff for API calls
- **12-Hour Window Handling**: Automatically splits requests per API limitations

## Requirements

### Software Requirements

- Python 3.7 or higher
- Microsoft ODBC Driver 18 for SQL Server
- SQL Server (any version with SQL Server Authentication)

### Python Dependencies

```bash
pip3 install -r requirements.txt
```

Dependencies:
- `requests>=2.31.0` - HTTP client for API calls
- `keyring>=24.0.0` - Cross-platform credential storage
- `pyodbc>=5.3.0` - SQL Server ODBC driver
- `python-dateutil>=2.8.2` - Enhanced date/time handling

### ODBC Driver Installation

**macOS:**
```bash
brew tap microsoft/mssql-release https://github.com/Microsoft/homebrew-mssql-release
HOMEBREW_ACCEPT_EULA=Y brew install msodbcsql18
```

**Windows:**

Download and install from:
https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server

**Linux (Ubuntu/Debian):**
```bash
curl https://packages.microsoft.com/keys/microsoft.asc | sudo apt-key add -
curl https://packages.microsoft.com/config/ubuntu/$(lsb_release -rs)/prod.list | sudo tee /etc/apt/sources.list.d/mssql-release.list
sudo apt-get update
sudo ACCEPT_EULA=Y apt-get install -y msodbcsql18
```

## Setup Instructions

### Step 1: Create Webex Integration

1. Visit https://developer.webex.com/my-apps
2. Click "Create a New App" → "Create an Integration"
3. Fill in details:
   - **Redirect URI**: `http://localhost:8080/callback`
   - **Scopes**: `analytics:read_all` (for CDR access)
4. Save your **Client ID** and **Client Secret**

### Step 2: Prepare SQL Server

1. Create a database (e.g., `webex_cdr`)
2. Create a SQL Server user with permissions:
   - `CREATE TABLE` (for initial setup)
   - `INSERT`, `SELECT` on tables

### Step 3: Install Dependencies

```bash
cd WebexCDR
pip3 install -r requirements.txt
```

### Step 4: Run Setup Script

```bash
python3 webex_cdr_setup.py \
    --client-id YOUR_CLIENT_ID \
    --client-secret YOUR_CLIENT_SECRET \
    --sql-server your-server.database.windows.net \
    --sql-database webex_cdr \
    --sql-username cdr_user \
    --sql-password 'YourPassword' \
    --sql-driver 'ODBC Driver 18 for SQL Server'
```

This will:
1. Open your browser for OAuth authorization
2. Store Webex credentials in system keyring
3. Test SQL Server connection
4. Store SQL Server credentials in system keyring

### Step 5: Initialize Database

```bash
python3 webex_cdr_downloader.py --init-db
```

This creates three tables:
- `cdr_records` - Stores CDR data
- `cdr_sync_state` - Tracks successful sync runs
- `cdr_sync_errors` - Logs errors for troubleshooting

### Step 6: Test First Run

```bash
python3 webex_cdr_downloader.py
```

This will fetch all available CDR records (past 48 hours).

### Step 7: Schedule Periodic Runs

**macOS/Linux (cron):**

```bash
crontab -e
```

Add this line to run every 15 minutes:
```bash
*/15 * * * * cd /path/to/webextools/WebexCDR && /usr/bin/python3 webex_cdr_downloader.py >> /var/log/webex_cdr.log 2>&1
```

**Windows (Task Scheduler):**

1. Open Task Scheduler
2. Create Basic Task
   - Name: `Webex CDR Download`
   - Trigger: Daily, repeat every 15 minutes
   - Action: Start a program
     - Program: `python` (or `C:\Python311\python.exe`)
     - Arguments: `webex_cdr_downloader.py`
     - Start in: `C:\Users\...\webextools\WebexCDR`

## Usage

### Basic Commands

**Sync CDR records:**
```bash
python3 webex_cdr_downloader.py
```

**Filter by location:**
```bash
python3 webex_cdr_downloader.py --locations "MainOffice" "Branch1"
```

**View sync statistics:**
```bash
python3 webex_cdr_downloader.py --stats
```

**Re-initialize database:**
```bash
python3 webex_cdr_downloader.py --init-db
```

### Exit Codes

- `0` - Success
- `1` - Error (check stderr and `cdr_sync_errors` table)

## Database Schema

### cdr_records Table

Stores call detail records with 45+ fields including:

**Core Identifiers:**
- `call_id`, `correlation_id`, session IDs

**Timestamps (UTC):**
- `start_time`, `answer_time`, `release_time`, `duration`

**Call Details:**
- `direction`, `call_type`, `call_outcome`, `call_outcome_reason`

**Party Information:**
- `calling_number`, `called_number`, `user_email`

**Location/Organization:**
- `location_name`, `org_id`, `site_uuid`

**Device Information:**
- `device_mac`, `client_type`, `model`

**Routing:**
- `inbound_trunk`, `outbound_trunk`, `route_group`

**Raw Data:**
- `raw_json` - Complete API response (future-proofing)

**Metadata:**
- `id` (auto-increment), `ingestion_timestamp`

**Constraints:**
- `UNIQUE (call_id, start_time)` - Prevents duplicates

### Performance Indexes

Indexes on: `start_time`, `calling_number`, `called_number`, `user_email`, `direction`, `call_outcome`, `location_name`, `correlation_id`

Composite index: `(start_time, direction)`

### State Tracking Tables

**cdr_sync_state:**
- Tracks last successful sync timestamp
- Records sync duration, API calls, records fetched

**cdr_sync_errors:**
- Logs errors with timestamps and stack traces
- Enables troubleshooting and monitoring

## How It Works

### First Run (No Previous Sync)

1. Loads credentials from system keyring
2. Refreshes OAuth access token
3. Connects to SQL Server
4. Queries `cdr_sync_state` (returns NULL - no previous run)
5. Calculates sync window: **48 hours ago to 5 minutes ago** (API limits)
6. Splits window into 12-hour chunks (4 API calls)
7. Fetches CDR records for each chunk
8. Inserts records into database (transaction)
9. Records sync success with `end_time`

### Incremental Run (Subsequent Syncs)

1. Loads credentials from system keyring
2. Refreshes OAuth access token
3. Connects to SQL Server
4. Queries `cdr_sync_state` (returns last `end_time`)
5. Calculates sync window: **last `end_time` to 5 minutes ago**
6. Fetches CDR records (single API call if < 12 hours)
7. Inserts new records (duplicates skipped via UNIQUE constraint)
8. Records sync success with new `end_time`

### Error Handling

**Network/API Errors:**
- Retry with exponential backoff (max 3 attempts)
- HTTP 429 (rate limit): Wait and retry
- HTTP 401 (auth error): Refresh token and retry

**Database Errors:**
- Transaction-based inserts (all-or-nothing)
- Rollback on failure
- Next run re-fetches from last successful `end_time`

**Duplicate Records:**
- Skipped silently via UNIQUE constraint
- Idempotent operation (safe to re-run)

## API Constraints (as of January 2026)

- **Data Availability**: 48 hours ago to 5 minutes ago
- **Max Window**: 12-hour chunks per request
- **Max Records**: 500 per page (will increase to 5000 later in 2026)
- **OAuth Scope**: `analytics:read_all`

## Useful SQL Queries

**Total records:**
```sql
SELECT COUNT(*) FROM cdr_records;
```

**Records by day:**
```sql
SELECT CAST(start_time AS DATE) AS call_date, COUNT(*) AS record_count
FROM cdr_records
GROUP BY CAST(start_time AS DATE)
ORDER BY call_date DESC;
```

**Check for duplicates:**
```sql
SELECT call_id, start_time, COUNT(*) AS dup_count
FROM cdr_records
GROUP BY call_id, start_time
HAVING COUNT(*) > 1;
```

**Sync health:**
```sql
SELECT TOP 10
    last_successful_end_time_utc,
    records_fetched,
    sync_duration_seconds,
    api_calls_made,
    notes,
    created_at
FROM cdr_sync_state
ORDER BY id DESC;
```

**Error summary:**
```sql
SELECT
    error_type,
    COUNT(*) AS error_count,
    MAX(error_timestamp) AS last_occurrence
FROM cdr_sync_errors
WHERE recovered = 0
GROUP BY error_type;
```

**Call volume by direction:**
```sql
SELECT direction, COUNT(*) AS call_count
FROM cdr_records
WHERE start_time >= DATEADD(day, -7, GETUTCDATE())
GROUP BY direction;
```

## Troubleshooting

### OAuth Errors

**Problem**: "ERROR: Failed to refresh access token"

**Solution**:
1. Check if Integration is still active at developer.webex.com/my-apps
2. Re-run setup: `python3 webex_cdr_setup.py ...`

### Database Connection Errors

**Problem**: "ERROR: Failed to connect to SQL Server"

**Solution**:
1. Verify server is accessible: `ping your-server.database.windows.net`
2. Check credentials and permissions
3. Verify ODBC driver is installed: `odbcinst -q -d`
4. Test connection manually with a SQL client

### No Records Fetched

**Problem**: Sync runs but fetches 0 records

**Possible Causes**:
1. No call activity in your Webex instance
2. Sync window too recent (wait 5+ minutes after calls)
3. API lag - try again in a few minutes

### Duplicate Records Error

**Problem**: "Skipped X duplicate records"

**This is normal!** The script is designed to skip duplicates. This happens when:
- Running the script multiple times quickly
- Overlapping time windows
- Re-running after a failed sync

## Security Notes

1. **Credentials**: All credentials stored in system keyring, never in files
2. **Access Tokens**: Refreshed on each run, not stored permanently
3. **SQL Injection**: Uses parameterized queries throughout
4. **Database Permissions**: Use dedicated user with minimal permissions

## Platform Compatibility

Tested and supported on:
- ✅ macOS 10.15+ (Catalina and later)
- ✅ Windows 10/11
- ✅ Linux (Ubuntu 20.04+, Debian 10+, RHEL 8+)

## License

Internal tool for Webex CDR management.

## Support

For issues or questions:
1. Check the `cdr_sync_errors` table for error details
2. View sync statistics: `python3 webex_cdr_downloader.py --stats`
3. Review logs if running via cron/Task Scheduler

## Version History

- **v1.0** (January 2026)
  - Initial release
  - OAuth 2.0 authentication
  - SQL Server integration
  - Cross-platform support
  - 12-hour window handling
