#!/usr/bin/env python3
"""
Webex CDR Downloader
Downloads CDR records from Webex and stores them in SQL Server.
Designed to run via scheduled tasks (cron, Task Scheduler, etc.)
"""

import sys
import argparse
import traceback
from datetime import datetime

# Import library modules
from lib.auth_manager import WebexAuthManager
from lib.database_manager import SQLServerManager
from lib.cdr_fetcher import CDRFetcher
from lib.state_manager import StateManager


def print_statistics(stats: dict):
    """Print sync statistics in readable format."""
    print("\n" + "="*50)
    print("Webex CDR Sync Statistics")
    print("="*50)
    print(f"Total CDR Records:      {stats.get('total_records', 0):,}")
    print(f"Last Sync:              {stats.get('last_sync_time', 'Never')}")
    print(f"Last Sync Duration:     {stats.get('last_duration', 0)} seconds")
    print(f"Last Records Fetched:   {stats.get('last_records_fetched', 0):,}")
    print(f"Last API Calls:         {stats.get('last_api_calls', 0)}")
    print(f"Total Sync Runs:        {stats.get('total_syncs', 0)}")
    print(f"Total Errors:           {stats.get('total_errors', 0)}")
    print("="*50 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Download Webex CDR records to SQL Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Initialize database (first time only)
  python3 webex_cdr_downloader.py --init-db

  # Run sync (fetch new CDR records)
  python3 webex_cdr_downloader.py

  # Filter by location
  python3 webex_cdr_downloader.py --locations "MainOffice" "Branch1"

  # View statistics
  python3 webex_cdr_downloader.py --stats

Exit Codes:
  0 - Success
  1 - Error (check stderr and cdr_sync_errors table)
        """
    )

    parser.add_argument(
        '--locations',
        nargs='+',
        help='Filter by location names (optional, max 10)'
    )
    parser.add_argument(
        '--init-db',
        action='store_true',
        help='Initialize database tables (run once after setup)'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show sync statistics and exit'
    )

    args = parser.parse_args()

    # Initialize managers
    auth_mgr = WebexAuthManager()
    db_mgr = SQLServerManager()

    try:
        # Step 1: Load Webex credentials
        if not auth_mgr.load_credentials():
            print("ERROR: Failed to load Webex credentials from keyring", file=sys.stderr)
            print("Run webex_cdr_setup.py first to configure credentials", file=sys.stderr)
            sys.exit(1)

        # Step 2: Load SQL Server credentials
        if not db_mgr.load_credentials():
            print("ERROR: Failed to load SQL Server credentials from keyring", file=sys.stderr)
            print("Run webex_cdr_setup.py first to configure credentials", file=sys.stderr)
            sys.exit(1)

        # Step 3: Refresh OAuth token
        print("Refreshing Webex access token...")
        if not auth_mgr.refresh_access_token():
            print("ERROR: Failed to refresh Webex access token", file=sys.stderr)
            sys.exit(1)

        # Step 4: Connect to database
        print("Connecting to SQL Server...")
        if not db_mgr.connect():
            print("ERROR: Failed to connect to SQL Server", file=sys.stderr)
            print("Check your database credentials and server connectivity", file=sys.stderr)
            sys.exit(1)

        # Handle --init-db flag
        if args.init_db:
            print("\n=== Initializing Database ===")
            if db_mgr.initialize_database():
                print("\nDatabase initialization completed successfully")
                sys.exit(0)
            else:
                print("\nERROR: Database initialization failed", file=sys.stderr)
                sys.exit(1)

        # Handle --stats flag
        if args.stats:
            stats = db_mgr.get_sync_statistics()
            print_statistics(stats)
            sys.exit(0)

        # Main sync process
        print("\n=== Starting CDR Sync ===\n")

        # Step 5: Determine sync window
        state_mgr = StateManager(db_mgr)
        start_time, end_time = state_mgr.get_sync_window()

        if start_time >= end_time:
            print("No new CDR data to fetch")
            sys.exit(0)

        # Step 6: Fetch CDR records
        cdr_fetcher = CDRFetcher(auth_mgr)
        sync_start = datetime.utcnow()

        result = cdr_fetcher.fetch_cdr_records(
            start_time,
            end_time,
            locations=args.locations
        )

        print(f"\nFetched {result['total_count']} CDR records in {result['api_calls']} API call(s)")

        # Step 7: Insert records into database
        if result['records']:
            print(f"Inserting records into database...")
            records_inserted = db_mgr.insert_cdr_records(result['records'])
            print(f"Inserted {records_inserted} new records")
        else:
            records_inserted = 0
            print("No records to insert")

        sync_end = datetime.utcnow()
        duration = int((sync_end - sync_start).total_seconds())

        # Step 8: Record sync success
        notes = f"Inserted {records_inserted} new records"
        if result['total_count'] != records_inserted:
            notes += f" (skipped {result['total_count'] - records_inserted} duplicates)"

        db_mgr.record_sync_success(
            end_time=end_time,
            records_fetched=result['total_count'],
            duration_seconds=duration,
            api_calls=result['api_calls'],
            notes=notes
        )

        # Step 9: Print summary
        print("\n" + "="*50)
        print("Sync Completed Successfully")
        print("="*50)
        print(f"Time Window:     {start_time} to {end_time}")
        print(f"Records Fetched: {result['total_count']:,}")
        print(f"Records Inserted: {records_inserted:,}")
        print(f"API Calls:       {result['api_calls']}")
        print(f"Duration:        {duration} seconds")
        print("="*50 + "\n")

        sys.exit(0)

    except KeyboardInterrupt:
        print("\n\nSync interrupted by user", file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        # Step 10: Handle errors
        error_msg = str(e)
        stack = traceback.format_exc()

        print(f"\nERROR: {error_msg}", file=sys.stderr)
        print(f"\nStack trace:\n{stack}", file=sys.stderr)

        # Try to log error to database
        try:
            if db_mgr.connection:
                db_mgr.record_sync_error(
                    error_type='SYNC_ERROR',
                    error_message=error_msg,
                    stack_trace=stack
                )
        except:
            pass  # Ignore if we can't log to database

        sys.exit(1)

    finally:
        # Always disconnect from database
        db_mgr.disconnect()


if __name__ == "__main__":
    main()
