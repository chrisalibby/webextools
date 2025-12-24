#!/usr/bin/env python3
"""
Webex Daily Message Poster
Posts a message to a Webex space with OAuth authentication and automatic token refresh.
"""

import argparse
import json
import keyring
import requests
import sys
from datetime import datetime
from typing import Optional


KEYRING_SERVICE = "webex_daily_poster"
CONFIG_KEYS = {
    "client_id": "client_id",
    "client_secret": "client_secret",
    "refresh_token": "refresh_token",
}


class WebexPoster:
    """Handles Webex OAuth and message posting."""

    def __init__(self):
        self.client_id = None
        self.client_secret = None
        self.refresh_token = None
        self.access_token = None

    def load_credentials(self) -> bool:
        """Load credentials from system keychain."""
        try:
            self.client_id = keyring.get_password(KEYRING_SERVICE, CONFIG_KEYS["client_id"])
            self.client_secret = keyring.get_password(KEYRING_SERVICE, CONFIG_KEYS["client_secret"])
            self.refresh_token = keyring.get_password(KEYRING_SERVICE, CONFIG_KEYS["refresh_token"])

            if not all([self.client_id, self.client_secret, self.refresh_token]):
                print("Error: Missing credentials in keychain. Run webex_setup.py first.", file=sys.stderr)
                return False
            return True
        except Exception as e:
            print(f"Error loading credentials: {e}", file=sys.stderr)
            return False

    def refresh_access_token(self) -> bool:
        """Refresh the access token using the refresh token."""
        token_url = "https://webexapis.com/v1/access_token"

        data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
        }

        try:
            response = requests.post(token_url, data=data)
            response.raise_for_status()

            token_data = response.json()
            self.access_token = token_data["access_token"]

            # Update refresh token if a new one is provided
            if "refresh_token" in token_data:
                new_refresh_token = token_data["refresh_token"]
                keyring.set_password(KEYRING_SERVICE, CONFIG_KEYS["refresh_token"], new_refresh_token)
                self.refresh_token = new_refresh_token
                print("Refresh token updated in keychain.")

            return True
        except requests.exceptions.RequestException as e:
            print(f"Error refreshing access token: {e}", file=sys.stderr)
            if hasattr(e.response, 'text'):
                print(f"Response: {e.response.text}", file=sys.stderr)
            return False

    def format_message(self, template: str) -> str:
        """Format message with date/time placeholders."""
        now = datetime.now()

        # Available placeholders
        replacements = {
            "{date}": now.strftime("%Y-%m-%d"),
            "{date_long}": now.strftime("%B %d, %Y"),
            "{day}": now.strftime("%A"),
            "{day_short}": now.strftime("%a"),
            "{time}": now.strftime("%H:%M"),
            "{time_12h}": now.strftime("%I:%M %p"),
            "{month}": now.strftime("%B"),
            "{month_short}": now.strftime("%b"),
            "{year}": now.strftime("%Y"),
            "{week}": now.strftime("%U"),
        }

        message = template
        for placeholder, value in replacements.items():
            message = message.replace(placeholder, value)

        return message

    def post_message(self, room_id: str, message: str) -> bool:
        """Post a message to a Webex room."""
        messages_url = "https://webexapis.com/v1/messages"

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        payload = {
            "roomId": room_id,
            "markdown": message,
        }

        try:
            response = requests.post(messages_url, headers=headers, json=payload)
            response.raise_for_status()
            print("Message posted successfully!")
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error posting message: {e}", file=sys.stderr)
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}", file=sys.stderr)
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Post a message to a Webex space with OAuth authentication.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available message placeholders:
  {date}        - YYYY-MM-DD (e.g., 2025-12-22)
  {date_long}   - Month DD, YYYY (e.g., December 22, 2025)
  {day}         - Full day name (e.g., Monday)
  {day_short}   - Short day name (e.g., Mon)
  {time}        - HH:MM 24-hour format
  {time_12h}    - HH:MM AM/PM
  {month}       - Full month name
  {month_short} - Short month name
  {year}        - YYYY
  {week}        - Week number of year

Examples:
  webex_daily_post.py ROOM_ID "Good morning! Today is {day}, {date_long}"
  webex_daily_post.py ROOM_ID "<@all> **Daily Standup** - {day_short} {date}"
        """
    )

    parser.add_argument("room_id", help="Webex room ID to post to")
    parser.add_argument("message", help="Message to post (supports markdown and placeholders)")

    args = parser.parse_args()

    # Initialize poster
    poster = WebexPoster()

    # Load credentials
    if not poster.load_credentials():
        sys.exit(1)

    # Refresh access token
    print("Refreshing access token...")
    if not poster.refresh_access_token():
        sys.exit(1)

    # Format message
    formatted_message = poster.format_message(args.message)
    print(f"Posting message: {formatted_message}")

    # Post message
    if not poster.post_message(args.room_id, formatted_message):
        sys.exit(1)


if __name__ == "__main__":
    main()
