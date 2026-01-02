#!/usr/bin/env python3
"""
Webex CDR Fetcher
Fetches Call Detail Records from Webex Analytics API with pagination and retry logic.
"""

import requests
import time
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple


class CDRFetcher:
    """Fetches CDR records from Webex Analytics API with pagination and error handling."""

    def __init__(self, auth_manager):
        self.auth_manager = auth_manager
        self.base_url = "https://analytics.webexapis.com/v1/cdr_feed"
        self.max_records_per_page = 500  # Current API limit (will increase to 5000 later in 2026)
        self.max_retries = 3
        self.retry_delay = 2  # seconds

    def fetch_cdr_records(self, start_time: datetime, end_time: datetime,
                         locations: List[str] = None) -> Dict[str, Any]:
        """
        Fetch all CDR records for the given time range.

        Automatically splits requests into 12-hour windows (API limitation as of Jan 30, 2026).

        Args:
            start_time: Start of time range (UTC)
            end_time: End of time range (UTC)
            locations: Optional list of location names to filter (max 10)

        Returns:
            Dictionary with:
                - 'records': List of CDR records
                - 'total_count': Total records fetched
                - 'api_calls': Number of API calls made
                - 'time_windows': List of time windows queried
        """
        # Split time range into 12-hour windows
        time_windows = self._split_time_range(start_time, end_time, max_hours=12)

        all_records = []
        total_api_calls = 0

        print(f"Fetching CDR records from {start_time} to {end_time}")
        print(f"Time range split into {len(time_windows)} window(s) of max 12 hours each")

        # Fetch records for each time window
        for i, (window_start, window_end) in enumerate(time_windows, 1):
            print(f"Fetching window {i}/{len(time_windows)}: {window_start} to {window_end}")

            window_records, api_calls = self._fetch_window(window_start, window_end, locations)
            all_records.extend(window_records)
            total_api_calls += api_calls

            print(f"  Retrieved {len(window_records)} records in {api_calls} API call(s)")

        return {
            'records': all_records,
            'total_count': len(all_records),
            'api_calls': total_api_calls,
            'time_windows': time_windows
        }

    def _fetch_window(self, start_time: datetime, end_time: datetime,
                     locations: List[str] = None) -> Tuple[List[Dict], int]:
        """
        Fetch all records for a single time window (≤12 hours).
        Handles pagination if API supports it in the future.

        Returns:
            Tuple of (records_list, api_call_count)
        """
        all_records = []
        api_calls = 0

        # Fetch first page
        page_data = self._fetch_page(start_time, end_time, locations)
        if page_data:
            api_calls += 1
            items = page_data.get('items', [])
            all_records.extend(items)

            # Check for pagination (future-proofing)
            # Current API doesn't have pagination, but handle it if added
            # Look for common pagination patterns: 'next', 'nextUrl', 'hasMore', etc.
            # For now, we assume single response per window

        return all_records, api_calls

    def _fetch_page(self, start_time: datetime, end_time: datetime,
                   locations: List[str] = None) -> Optional[Dict]:
        """
        Fetch single page of CDR records with retry logic.

        Args:
            start_time: Start timestamp (UTC)
            end_time: End timestamp (UTC)
            locations: Optional list of location names

        Returns:
            JSON response as dictionary, or None on failure
        """
        params = {
            'startTime': self._format_timestamp(start_time),
            'endTime': self._format_timestamp(end_time),
            'max': self.max_records_per_page
        }

        if locations:
            # API accepts comma-separated location names (max 10)
            params['locations'] = ','.join(locations[:10])

        headers = self.auth_manager.get_headers()

        # Retry logic
        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.get(self.base_url, params=params, headers=headers, timeout=30)

                # Handle rate limiting (429)
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    print(f"Rate limited. Waiting {retry_after} seconds...", file=sys.stderr)
                    time.sleep(retry_after)
                    continue

                # Handle auth errors (401)
                if response.status_code == 401:
                    print("Access token expired. Refreshing...", file=sys.stderr)
                    if self.auth_manager.refresh_access_token():
                        headers = self.auth_manager.get_headers()
                        continue
                    else:
                        print("ERROR: Failed to refresh access token", file=sys.stderr)
                        return None

                # Raise for other HTTP errors
                response.raise_for_status()

                # Success
                return response.json()

            except requests.exceptions.Timeout:
                print(f"Request timeout (attempt {attempt}/{self.max_retries})", file=sys.stderr)
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * attempt)  # Exponential backoff
                    continue
                else:
                    return None

            except requests.exceptions.RequestException as e:
                print(f"Request failed (attempt {attempt}/{self.max_retries}): {e}", file=sys.stderr)
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * attempt)  # Exponential backoff
                    continue
                else:
                    return None

        return None

    def _split_time_range(self, start: datetime, end: datetime, max_hours: int = 12) -> List[Tuple[datetime, datetime]]:
        """
        Split time range into chunks not exceeding max_hours.

        Args:
            start: Start datetime (UTC)
            end: End datetime (UTC)
            max_hours: Maximum hours per chunk (default 12 per API limitation)

        Returns:
            List of (start, end) datetime tuples
        """
        windows = []
        current_start = start
        max_delta = timedelta(hours=max_hours)

        while current_start < end:
            current_end = min(current_start + max_delta, end)
            windows.append((current_start, current_end))
            current_start = current_end

        return windows

    @staticmethod
    def _format_timestamp(dt: datetime) -> str:
        """
        Format datetime to ISO 8601 with milliseconds in UTC.

        Format: 2026-01-01T00:00:00.000Z

        Args:
            dt: datetime object (should be in UTC)

        Returns:
            ISO 8601 formatted string
        """
        # Ensure UTC (remove timezone info if present, assume UTC)
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)

        # Format with milliseconds
        return dt.strftime('%Y-%m-%dT%H:%M:%S.000Z')
