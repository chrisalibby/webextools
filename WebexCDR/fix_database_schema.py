#!/usr/bin/env python3
"""
Fix the answer_indicator column size in the database.
Run this once to update the existing database schema.
"""

import sys
import io
from lib.database_manager import SQLServerManager

# Fix Windows console encoding issues
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def main():
    db_mgr = SQLServerManager()

    # Load SQL Server credentials
    if not db_mgr.load_credentials():
        print("ERROR: Failed to load SQL Server credentials from keyring", file=sys.stderr)
        sys.exit(1)

    # Connect to database
    print("Connecting to SQL Server...")
    if not db_mgr.connect():
        print("ERROR: Failed to connect to SQL Server", file=sys.stderr)
        sys.exit(1)

    try:
        print("Fixing answer_indicator column size...")

        # Alter the column to increase its size
        sql = "ALTER TABLE cdr_records ALTER COLUMN answer_indicator NVARCHAR(50);"

        db_mgr.cursor.execute(sql)
        db_mgr.connection.commit()

        print("[OK] Column answer_indicator resized to NVARCHAR(50)")
        print("\nDatabase schema fixed successfully!")
        print("You can now re-run the CDR downloader to insert the failed records.")

    except Exception as e:
        print(f"ERROR: Failed to fix schema: {e}", file=sys.stderr)
        db_mgr.connection.rollback()
        sys.exit(1)
    finally:
        db_mgr.disconnect()

if __name__ == "__main__":
    main()
