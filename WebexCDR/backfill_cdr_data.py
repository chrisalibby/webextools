#!/usr/bin/env python3
"""
Webex CDR Backfill Script
Downloads all available historical CDR data that hasn't been downloaded yet.

The Webex CDR API provides data for the past 48 hours maximum.
This script will download all available data from 48 hours ago up to the
last successful sync point (or current time if no syncs have been done).
"""

import sys
import io
import argparse
from datetime import datetime, timedelta

# Fix Windows console encoding issues
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Import library modules
from lib.auth_manager import WebexAuthManager
from lib.database_manager import SQLServerManager
from lib.cdr_fetcher import CDRFetcher
from lib.state_manager import StateManager


def get_backfill_window(db_mgr, hours_back=48):
    """
    Determine the time window for backfilling data.

    Args:
        db_mgr: Database manager instance
        hours_back: How many hours back to fetch (default 48, which is API max)

    Returns:
        Tuple of (start_time, end_time) in UTC
    """
    now = datetime.utcnow()

    # API allows up to 48 hours of historical data
    max_start_time = now - timedelta(hours=hours_back)

    # Check if there's a last successful sync
    last_sync = db_mgr.get_last_sync_time()

    if last_sync:
        # If we have a last sync, start from 48 hours ago and go up to last sync
        # This will capture any data we might have missed
        start_time = max_start_time
        end_time = last_sync
        print(f"Last sync was at: {last_sync}")
        print(f"Backfilling from {start_time} to {end_time}")

        if start_time >= end_time:
            print("No backfill needed - last sync is older than available data window")
            return None, None
    else:
        # No previous sync - fetch all available data (past 48 hours)
        start_time = max_start_time
        end_time = now - timedelta(minutes=5)  # End time must be at least 5 minutes in past
        print("No previous sync found")
        print(f"Fetching all available data from {start_time} to {end_time}")

    return start_time, end_time


def main():
    parser = argparse.ArgumentParser(
        description="Backfill historical Webex CDR data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Backfill all available data (past 48 hours)
  python backfill_cdr_data.py

  # Backfill with location filter
  python backfill_cdr_data.py --locations "MainOffice" "Branch1"

  # Custom time range (must be within past 48 hours)
  python backfill_cdr_data.py --hours-back 24

  # Dry run - see what would be fetched without inserting
  python backfill_cdr_data.py --dry-run

Notes:
  - Webex CDR API only provides data from the past 48 hours
  - Data older than 48 hours is not available via the API
  - This script will skip any records that already exist in the database
  - End time must be at least 5 minutes in the past (API requirement)
        """
    )

    parser.add_argument(
        '--hours-back',
        type=int,
        default=48,
        help='How many hours back to fetch (max 48, default: 48)'
    )
    parser.add_argument(
        '--locations',
        nargs='+',
        help='Filter by location names (optional, max 10)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Fetch data but do not insert into database'
    )

    args = parser.parse_args()

    # Validate hours_back
    if args.hours_back > 48:
        print("WARNING: Webex CDR API only provides 48 hours of data. Setting to 48 hours.", file=sys.stderr)
        args.hours_back = 48
    elif args.hours_back < 1:
        print("ERROR: --hours-back must be at least 1", file=sys.stderr)
        sys.exit(1)

    # Initialize managers
    auth_mgr = WebexAuthManager()
    db_mgr = SQLServerManager()

    try:
        # Step 1: Load Webex credentials
        print("Loading Webex credentials...")
        if not auth_mgr.load_credentials():
            print("ERROR: Failed to load Webex credentials from keyring", file=sys.stderr)
            print("Run webex_cdr_setup.py first to configure credentials", file=sys.stderr)
            sys.exit(1)

        # Step 2: Load SQL Server credentials
        print("Loading SQL Server credentials...")
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
            sys.exit(1)

        # Step 5: Determine backfill window
        print("\n" + "="*60)
        print("Determining backfill window...")
        print("="*60)

        start_time, end_time = get_backfill_window(db_mgr, args.hours_back)

        if start_time is None or end_time is None:
            print("\nNothing to backfill.")
            sys.exit(0)

        # Calculate time window
        time_span = end_time - start_time
        hours = time_span.total_seconds() / 3600
        print(f"Time window: {hours:.1f} hours ({time_span.days} days, {time_span.seconds // 3600} hours)")

        # Step 6: Fetch CDR records
        print("\n" + "="*60)
        print("Starting CDR Backfill")
        print("="*60)

        sync_start = datetime.utcnow()
        cdr_fetcher = CDRFetcher(auth_mgr)

        result = cdr_fetcher.fetch_cdr_records(
            start_time,
            end_time,
            locations=args.locations
        )

        print(f"\n" + "="*60)
        print(f"Fetched {result['total_count']:,} CDR records in {result['api_calls']} API call(s)")
        print("="*60)

        # Step 7: Insert records into database (unless dry-run)
        if args.dry_run:
            print("\nDRY RUN - Not inserting records into database")
            print(f"Would have attempted to insert {result['total_count']:,} records")

            # Show sample records
            if result['records']:
                print("\nSample of first 3 records:")
                for i, record in enumerate(result['records'][:3], 1):
                    print(f"\n  Record {i}:")
                    print(f"    Call ID: {record.get('Call_ID', 'N/A')}")
                    print(f"    Start Time: {record.get('Start_time', 'N/A')}")
                    print(f"    Calling Number: {record.get('Calling_number', 'N/A')}")
                    print(f"    Called Number: {record.get('Called_number', 'N/A')}")
                    print(f"    Duration: {record.get('Duration', 'N/A')} seconds")
        else:
            if result['records']:
                print(f"\nInserting records into database...")
                records_inserted = db_mgr.insert_cdr_records(result['records'])
                skipped = result['total_count'] - records_inserted

                print(f"  Inserted: {records_inserted:,} new records")
                if skipped > 0:
                    print(f"  Skipped:  {skipped:,} duplicates (already in database)")

                sync_end = datetime.utcnow()
                duration = int((sync_end - sync_start).total_seconds())

                # Record the backfill in sync state
                notes = f"Backfill: Inserted {records_inserted:,} records, skipped {skipped:,} duplicates"
                db_mgr.record_sync_success(
                    end_time=end_time,
                    records_fetched=result['total_count'],
                    duration_seconds=duration,
                    api_calls=result['api_calls'],
                    notes=notes
                )

                print(f"\nBackfill completed in {duration} seconds")
            else:
                print("\nNo records to insert")

        # Step 8: Print summary
        print("\n" + "="*60)
        print("Backfill Summary")
        print("="*60)
        print(f"Time Window:      {start_time} to {end_time}")
        print(f"Duration:         {hours:.1f} hours")
        print(f"Records Fetched:  {result['total_count']:,}")
        if not args.dry_run and result['records']:
            print(f"Records Inserted: {records_inserted:,}")
            print(f"Records Skipped:  {skipped:,} (duplicates)")
        print(f"API Calls Made:   {result['api_calls']}")
        print("="*60)

        if args.locations:
            print(f"Location Filter:  {', '.join(args.locations)}")
            print("="*60)

        print("\nNext steps:")
        print("  - Run 'python webex_cdr_downloader.py --stats' to see updated statistics")
        print("  - Check your database for the new records")
        print("  - The regular sync will now continue from the last sync point")
        print()

        sys.exit(0)

    except KeyboardInterrupt:
        print("\n\nBackfill interrupted by user", file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        # Always disconnect from database
        db_mgr.disconnect()


if __name__ == "__main__":
    main()
