#!/usr/bin/env python3
"""
Webex OAuth Authentication Manager
Handles OAuth 2.0 authentication with automatic token refresh for CDR API access.
"""

import keyring
import requests
import sys
from typing import Dict, Optional


KEYRING_SERVICE = "webex_cdr_downloader"
CONFIG_KEYS = {
    "client_id": "client_id",
    "client_secret": "client_secret",
    "refresh_token": "refresh_token",
}


class WebexAuthManager:
    """Manages Webex OAuth authentication with automatic token refresh."""

    def __init__(self):
        self.client_id = None
        self.client_secret = None
        self.refresh_token = None
        self.access_token = None

    def load_credentials(self) -> bool:
        """Load OAuth credentials from system keyring."""
        try:
            self.client_id = keyring.get_password(KEYRING_SERVICE, CONFIG_KEYS["client_id"])
            self.client_secret = keyring.get_password(KEYRING_SERVICE, CONFIG_KEYS["client_secret"])
            self.refresh_token = keyring.get_password(KEYRING_SERVICE, CONFIG_KEYS["refresh_token"])

            if not all([self.client_id, self.client_secret, self.refresh_token]):
                print("ERROR: Missing Webex credentials in keyring. Run webex_cdr_setup.py first.", file=sys.stderr)
                return False
            return True
        except Exception as e:
            print(f"ERROR: Failed to load credentials from keyring: {e}", file=sys.stderr)
            return False

    def refresh_access_token(self) -> bool:
        """
        Refresh the access token using the refresh token.
        Automatically updates refresh token in keyring if a new one is provided.
        """
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

            # Update refresh token if a new one is provided (token rotation)
            if "refresh_token" in token_data:
                new_refresh_token = token_data["refresh_token"]
                keyring.set_password(KEYRING_SERVICE, CONFIG_KEYS["refresh_token"], new_refresh_token)
                self.refresh_token = new_refresh_token

            return True
        except requests.exceptions.RequestException as e:
            print(f"ERROR: Failed to refresh access token: {e}", file=sys.stderr)
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}", file=sys.stderr)
            return False

    def get_headers(self) -> Dict[str, str]:
        """Return authorization headers for API requests."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    def save_credentials(self, client_id: str, client_secret: str, refresh_token: str) -> bool:
        """
        Save OAuth credentials to system keyring.
        Used by setup script.
        """
        try:
            keyring.set_password(KEYRING_SERVICE, CONFIG_KEYS["client_id"], client_id)
            keyring.set_password(KEYRING_SERVICE, CONFIG_KEYS["client_secret"], client_secret)
            keyring.set_password(KEYRING_SERVICE, CONFIG_KEYS["refresh_token"], refresh_token)
            return True
        except Exception as e:
            print(f"ERROR: Failed to save credentials to keyring: {e}", file=sys.stderr)
            return False
