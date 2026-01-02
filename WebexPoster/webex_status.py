#!/usr/bin/env python3
"""
Webex Status Manager
Manages your Webex status message with OAuth authentication.

Note: The Webex API does not support programmatically setting presence states
(active, busy, DND, away) via API. This script can only:
- Set custom status messages
- Query your current presence status
- Clear your status message

To set DND, busy, or away states, you must use the Webex app directly.
"""

import argparse
import json
import keyring
import requests
import sys
from datetime import datetime
from typing import Optional, Dict, Any


KEYRING_SERVICE = "webex_daily_poster"
CONFIG_KEYS = {
    "client_id": "client_id",
    "client_secret": "client_secret",
    "refresh_token": "refresh_token",
}


class WebexStatusManager:
    """Handles Webex OAuth and status management."""

    def __init__(self):
        self.client_id = None
        self.client_secret = None
        self.refresh_token = None
        self.access_token = None
        self.person_id = None

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

            return True
        except requests.exceptions.RequestException as e:
            print(f"Error refreshing access token: {e}", file=sys.stderr)
            if hasattr(e.response, 'text'):
                print(f"Response: {e.response.text}", file=sys.stderr)
            return False

    def get_my_details(self) -> Optional[Dict[str, Any]]:
        """Get current user details including status."""
        me_url = "https://webexapis.com/v1/people/me"

        headers = {
            "Authorization": f"Bearer {self.access_token}",
        }

        try:
            response = requests.get(me_url, headers=headers)
            response.raise_for_status()
            data = response.json()
            self.person_id = data.get("id")
            return data
        except requests.exceptions.RequestException as e:
            print(f"Error getting user details: {e}", file=sys.stderr)
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}", file=sys.stderr)
            return None

    def show_status(self) -> bool:
        """Display current user status."""
        details = self.get_my_details()
        if not details:
            return False

        print(f"\nCurrent Webex Status:")
        print(f"  Name: {details.get('displayName', 'N/A')}")
        print(f"  Email: {details.get('emails', ['N/A'])[0]}")

        status_val = details.get('status', 'unknown')
        print(f"  Presence: {status_val}")

        # Status message (if set)
        if 'statusMessage' in details:
            print(f"  Status Message: {details.get('statusMessage', '')}")

        # Last activity (if available)
        if 'lastActivity' in details:
            print(f"  Last Activity: {details.get('lastActivity', 'N/A')}")

        print()
        return True

    def set_status_message(self, message: str) -> bool:
        """
        Set a custom status message.

        Note: This only sets the status message text, not the presence state
        (active/busy/DND/away). Presence states cannot be set via API.
        """
        if not self.person_id:
            # Get person ID first
            if not self.get_my_details():
                return False

        people_url = f"https://webexapis.com/v1/people/{self.person_id}"

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        # Note: We're only updating the statusMessage field
        # The API requires a PUT with the person ID
        payload = {
            "statusMessage": message
        }

        try:
            response = requests.put(people_url, headers=headers, json=payload)
            response.raise_for_status()
            print(f"Status message set to: {message}")
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error setting status message: {e}", file=sys.stderr)
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}", file=sys.stderr)
                print("\nNote: The Webex API may not support setting custom status messages.", file=sys.stderr)
                print("You may need to use the Webex app to set custom status.", file=sys.stderr)
            return False

    def clear_status_message(self) -> bool:
        """Clear the custom status message."""
        return self.set_status_message("")


def main():
    parser = argparse.ArgumentParser(
        description="Manage your Webex status with OAuth authentication.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  show              Display your current status and presence
  message TEXT      Set a custom status message
  clear             Clear your status message

Important Limitations:
  The Webex API does NOT support setting presence states (active, busy, DND, away)
  programmatically. You can only:
  - View your current presence status (read-only)
  - Set/clear custom status messages (if supported by your org)

  To change your presence to busy, DND, or away, you must use the Webex app.

Examples:
  webex_status.py show
  webex_status.py message "In a meeting until 3pm"
  webex_status.py message "Working from home today"
  webex_status.py clear
        """
    )

    parser.add_argument(
        "command",
        choices=["show", "message", "clear"],
        help="Action to perform"
    )
    parser.add_argument(
        "text",
        nargs="?",
        help="Status message text (required for 'message' command)"
    )

    args = parser.parse_args()

    # Validate arguments
    if args.command == "message" and not args.text:
        parser.error("'message' command requires status text")

    # Initialize status manager
    manager = WebexStatusManager()

    # Load credentials
    if not manager.load_credentials():
        sys.exit(1)

    # Refresh access token
    if not manager.refresh_access_token():
        sys.exit(1)

    # Execute command
    if args.command == "show":
        if not manager.show_status():
            sys.exit(1)
    elif args.command == "message":
        if not manager.set_status_message(args.text):
            sys.exit(1)
    elif args.command == "clear":
        if not manager.clear_status_message():
            sys.exit(1)
        print("Status message cleared")


if __name__ == "__main__":
    main()
