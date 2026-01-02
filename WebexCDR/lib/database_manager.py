#!/usr/bin/env python3
"""
SQL Server Database Manager
Handles all SQL Server operations for CDR data storage and state tracking.
"""

import pyodbc
import json
import keyring
import sys
import os
from datetime import datetime
from typing import List, Dict, Optional, Any


KEYRING_SERVICE = "webex_cdr_sql_server"
CONFIG_KEYS = {
    "server": "server",
    "database": "database",
    "username": "username",
    "password": "password",
    "driver": "driver",
}


class SQLServerManager:
    """Manages SQL Server connections and CDR data operations."""

    def __init__(self):
        self.server = None
        self.database = None
        self.username = None
        self.password = None
        self.driver = None
        self.connection = None
        self.cursor = None

    def load_credentials(self) -> bool:
        """Load SQL Server credentials from system keyring."""
        try:
            self.server = keyring.get_password(KEYRING_SERVICE, CONFIG_KEYS["server"])
            self.database = keyring.get_password(KEYRING_SERVICE, CONFIG_KEYS["database"])
            self.username = keyring.get_password(KEYRING_SERVICE, CONFIG_KEYS["username"])
            self.password = keyring.get_password(KEYRING_SERVICE, CONFIG_KEYS["password"])
            self.driver = keyring.get_password(KEYRING_SERVICE, CONFIG_KEYS["driver"])

            if not all([self.server, self.database, self.username, self.password, self.driver]):
                print("ERROR: Missing SQL Server credentials in keyring. Run webex_cdr_setup.py first.", file=sys.stderr)
                return False
            return True
        except Exception as e:
            print(f"ERROR: Failed to load SQL Server credentials from keyring: {e}", file=sys.stderr)
            return False

    def connect(self) -> bool:
        """Establish connection to SQL Server."""
        try:
            connection_string = (
                f"DRIVER={{{self.driver}}};"
                f"SERVER={self.server};"
                f"DATABASE={self.database};"
                f"UID={self.username};"
                f"PWD={self.password};"
                f"TrustServerCertificate=yes;"
            )

            self.connection = pyodbc.connect(connection_string, autocommit=False)
            self.cursor = self.connection.cursor()
            return True
        except pyodbc.Error as e:
            print(f"ERROR: Failed to connect to SQL Server: {e}", file=sys.stderr)
            return False

    def disconnect(self):
        """Close database connection."""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()

    def initialize_database(self) -> bool:
        """
        Create database tables and indexes if they don't exist.
        Reads SQL from sql/create_tables.sql and sql/create_indexes.sql files.
        """
        try:
            # Get the directory where this script is located
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            tables_sql_path = os.path.join(script_dir, 'sql', 'create_tables.sql')
            indexes_sql_path = os.path.join(script_dir, 'sql', 'create_indexes.sql')

            # Create tables
            print("Creating database tables...")
            with open(tables_sql_path, 'r') as f:
                tables_sql = f.read()
                # Execute each batch separately (split by GO statements)
                for batch in tables_sql.split('GO'):
                    batch = batch.strip()
                    if batch:
                        self.cursor.execute(batch)
                self.connection.commit()

            # Create indexes
            print("Creating database indexes...")
            with open(indexes_sql_path, 'r') as f:
                indexes_sql = f.read()
                # Execute each batch separately (split by GO statements)
                for batch in indexes_sql.split('GO'):
                    batch = batch.strip()
                    if batch:
                        self.cursor.execute(batch)
                self.connection.commit()

            print("Database initialization completed successfully")
            return True
        except FileNotFoundError as e:
            print(f"ERROR: SQL file not found: {e}", file=sys.stderr)
            return False
        except pyodbc.Error as e:
            print(f"ERROR: Failed to initialize database: {e}", file=sys.stderr)
            if self.connection:
                self.connection.rollback()
            return False

    def get_last_sync_time(self) -> Optional[datetime]:
        """
        Get the last successful sync end time from cdr_sync_state table.
        Returns None if no previous sync (first run).
        """
        try:
            query = """
                SELECT TOP 1 last_successful_end_time_utc
                FROM cdr_sync_state
                ORDER BY id DESC
            """
            self.cursor.execute(query)
            row = self.cursor.fetchone()

            if row and row[0]:
                return row[0]
            return None
        except pyodbc.Error as e:
            print(f"WARNING: Failed to get last sync time: {e}", file=sys.stderr)
            return None

    def insert_cdr_records(self, records: List[Dict[str, Any]]) -> int:
        """
        Bulk insert CDR records into database.
        Returns number of records successfully inserted.
        Duplicates are skipped via UNIQUE constraint.
        """
        if not records:
            return 0

        insert_query = """
            INSERT INTO cdr_records (
                call_id, correlation_id, local_session_id, final_local_session_id,
                remote_session_id, final_remote_session_id, start_time, answer_time,
                release_time, call_transfer_time, duration, direction, call_type,
                call_outcome, call_outcome_reason, calling_number, calling_line_id,
                called_number, called_line_id, dialed_digits, user_id, user_email,
                user_type, location_id, location_name, department_id, org_id,
                device_mac, client_type, client_version, model, authorization_code,
                inbound_trunk, outbound_trunk, route_group, answered, answer_indicator,
                redirecting_number, redirect_reason, international_country,
                transfer_related_call_id, site_uuid, site_main_number, site_timezone,
                raw_json
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
        """

        inserted_count = 0
        skipped_count = 0

        try:
            for record in records:
                try:
                    # Parse start_time
                    start_time = self._parse_timestamp(record.get('Start time'))

                    # Prepare values tuple
                    values = (
                        record.get('Call ID'),
                        record.get('Correlation ID'),
                        record.get('Local session ID'),
                        record.get('Final local session ID'),
                        record.get('Remote session ID'),
                        record.get('Final remote session ID'),
                        start_time,
                        self._parse_timestamp(record.get('Answer time')),
                        self._parse_timestamp(record.get('Release time')),
                        self._parse_timestamp(record.get('Call transfer time')),
                        self._parse_int(record.get('Duration')),
                        record.get('Direction'),
                        record.get('Call type'),
                        record.get('Call outcome'),
                        record.get('Call outcome reason'),
                        record.get('Calling number'),
                        record.get('Calling line ID'),
                        record.get('Called number'),
                        record.get('Called line ID'),
                        record.get('Dialed digits'),
                        record.get('User ID'),
                        record.get('User'),
                        record.get('User type'),
                        record.get('Location'),
                        record.get('Location name'),
                        record.get('Department ID'),
                        record.get('Organization ID'),
                        record.get('Device MAC'),
                        record.get('Client type'),
                        record.get('Client version'),
                        record.get('Model'),
                        record.get('Authorization code'),
                        record.get('Inbound trunk'),
                        record.get('Outbound trunk'),
                        record.get('Route group'),
                        self._parse_bool(record.get('Answered')),
                        record.get('Answer indicator'),
                        record.get('Redirecting number'),
                        record.get('Redirect reason'),
                        record.get('International country'),
                        record.get('Transfer related call ID'),
                        record.get('Site UUID'),
                        record.get('Site main number'),
                        record.get('Site timezone'),
                        json.dumps(record)  # Store raw JSON
                    )

                    self.cursor.execute(insert_query, values)
                    inserted_count += 1

                except pyodbc.IntegrityError:
                    # Duplicate record (UNIQUE constraint violation)
                    skipped_count += 1
                    continue
                except Exception as e:
                    print(f"WARNING: Failed to insert record {record.get('Call ID')}: {e}", file=sys.stderr)
                    continue

            # Commit transaction
            self.connection.commit()

            if skipped_count > 0:
                print(f"Skipped {skipped_count} duplicate records")

            return inserted_count

        except Exception as e:
            print(f"ERROR: Failed to insert CDR records: {e}", file=sys.stderr)
            if self.connection:
                self.connection.rollback()
            return 0

    def record_sync_success(self, end_time: datetime, records_fetched: int,
                           duration_seconds: int, api_calls: int, notes: str = None) -> bool:
        """Record successful sync metadata in cdr_sync_state table."""
        try:
            query = """
                INSERT INTO cdr_sync_state (
                    last_successful_run_utc, last_successful_end_time_utc,
                    records_fetched, sync_duration_seconds, api_calls_made, notes
                ) VALUES (?, ?, ?, ?, ?, ?)
            """

            now = datetime.utcnow()
            self.cursor.execute(query, (now, end_time, records_fetched, duration_seconds, api_calls, notes))
            self.connection.commit()
            return True
        except pyodbc.Error as e:
            print(f"ERROR: Failed to record sync success: {e}", file=sys.stderr)
            if self.connection:
                self.connection.rollback()
            return False

    def record_sync_error(self, error_type: str, error_message: str, stack_trace: str = None) -> bool:
        """Log sync errors to cdr_sync_errors table."""
        try:
            query = """
                INSERT INTO cdr_sync_errors (error_type, error_message, stack_trace)
                VALUES (?, ?, ?)
            """

            self.cursor.execute(query, (error_type, error_message, stack_trace))
            self.connection.commit()
            return True
        except pyodbc.Error as e:
            print(f"ERROR: Failed to record sync error: {e}", file=sys.stderr)
            if self.connection:
                self.connection.rollback()
            return False

    def get_sync_statistics(self) -> Dict[str, Any]:
        """Get sync statistics for monitoring."""
        try:
            stats = {}

            # Total records
            self.cursor.execute("SELECT COUNT(*) FROM cdr_records")
            stats['total_records'] = self.cursor.fetchone()[0]

            # Last sync info
            query = """
                SELECT TOP 1 last_successful_end_time_utc, sync_duration_seconds,
                       records_fetched, api_calls_made
                FROM cdr_sync_state
                ORDER BY id DESC
            """
            self.cursor.execute(query)
            row = self.cursor.fetchone()

            if row:
                stats['last_sync_time'] = row[0].strftime('%Y-%m-%d %H:%M:%S UTC') if row[0] else 'Never'
                stats['last_duration'] = row[1] or 0
                stats['last_records_fetched'] = row[2] or 0
                stats['last_api_calls'] = row[3] or 0
            else:
                stats['last_sync_time'] = 'Never'
                stats['last_duration'] = 0
                stats['last_records_fetched'] = 0
                stats['last_api_calls'] = 0

            # Total syncs
            self.cursor.execute("SELECT COUNT(*) FROM cdr_sync_state")
            stats['total_syncs'] = self.cursor.fetchone()[0]

            # Total errors
            self.cursor.execute("SELECT COUNT(*) FROM cdr_sync_errors")
            stats['total_errors'] = self.cursor.fetchone()[0]

            return stats
        except pyodbc.Error as e:
            print(f"ERROR: Failed to get sync statistics: {e}", file=sys.stderr)
            return {}

    def save_credentials(self, server: str, database: str, username: str,
                        password: str, driver: str) -> bool:
        """
        Save SQL Server credentials to system keyring.
        Used by setup script.
        """
        try:
            keyring.set_password(KEYRING_SERVICE, CONFIG_KEYS["server"], server)
            keyring.set_password(KEYRING_SERVICE, CONFIG_KEYS["database"], database)
            keyring.set_password(KEYRING_SERVICE, CONFIG_KEYS["username"], username)
            keyring.set_password(KEYRING_SERVICE, CONFIG_KEYS["password"], password)
            keyring.set_password(KEYRING_SERVICE, CONFIG_KEYS["driver"], driver)
            return True
        except Exception as e:
            print(f"ERROR: Failed to save credentials to keyring: {e}", file=sys.stderr)
            return False

    @staticmethod
    def _parse_timestamp(ts_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO 8601 timestamp string to datetime object."""
        if not ts_str:
            return None
        try:
            # Remove 'Z' and parse
            ts_str = ts_str.replace('Z', '+00:00')
            return datetime.fromisoformat(ts_str.replace('+00:00', ''))
        except (ValueError, AttributeError):
            return None

    @staticmethod
    def _parse_int(value: Any) -> Optional[int]:
        """Safely parse integer value."""
        if value is None or value == '':
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_bool(value: Any) -> Optional[bool]:
        """Safely parse boolean value."""
        if value is None or value == '':
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', 'yes', '1')
        return bool(value)
