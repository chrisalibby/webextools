#!/usr/bin/env python3
"""
Sync State Manager
Manages sync state logic for incremental CDR fetching.
"""

from datetime import datetime, timedelta
from typing import Tuple


class StateManager:
    """Manages sync state and determines time windows for CDR fetching."""

    def __init__(self, db_manager):
        self.db_manager = db_manager

    def get_sync_window(self) -> Tuple[datetime, datetime]:
        """
        Determine the time window for CDR sync.

        Logic:
        - First run (no previous sync): Pull from 48 hours ago to 5 minutes ago
        - Incremental run: Pull from last sync end time to 5 minutes ago
        - API constraints: Data available from 48 hours ago to 5 minutes ago

        Returns:
            Tuple of (start_time, end_time) as datetime objects in UTC
        """
        now = datetime.utcnow()

        # API constraints (as of Jan 2026)
        earliest_available = now - timedelta(hours=48)  # Data only available for past 48 hours
        latest_available = now - timedelta(minutes=5)  # Data lag of 5 minutes

        # Get last successful sync time
        last_sync_end = self.db_manager.get_last_sync_time()

        if last_sync_end is None:
            # First run: pull all available data
            start_time = earliest_available
            print("First run detected: fetching all available CDR records (past 48 hours)")
        else:
            # Incremental run: from last sync
            start_time = last_sync_end

            # Safety check: don't go beyond API's 48-hour limit
            if start_time < earliest_available:
                print(f"WARNING: Last sync was more than 48 hours ago. "
                      f"Data before {earliest_available} is no longer available.")
                start_time = earliest_available

        # End time is always 5 minutes ago (API freshness limit)
        end_time = latest_available

        # Validate time window
        if start_time >= end_time:
            print("WARNING: No new data to fetch (start time >= end time)")
            # Return empty window
            return (end_time, end_time)

        return (start_time, end_time)
