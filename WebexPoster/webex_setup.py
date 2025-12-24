#!/usr/bin/env python3
"""
Webex Daily Poster - Initial Setup
One-time OAuth authorization flow to obtain and store refresh token.
"""

import argparse
import keyring
import requests
import sys
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from threading import Event


KEYRING_SERVICE = "webex_daily_poster"
CONFIG_KEYS = {
    "client_id": "client_id",
    "client_secret": "client_secret",
    "refresh_token": "refresh_token",
}

# Global variables for OAuth callback
auth_code = None
auth_state = None
callback_event = Event()


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Handles the OAuth callback from Webex."""

    def do_GET(self):
        global auth_code, auth_state

        # Parse the callback URL
        parsed_path = urlparse(self.path)
        params = parse_qs(parsed_path.query)

        print(f"\n[DEBUG] Received callback: {self.path}")
        print(f"[DEBUG] Parsed params: {params}")

        if "code" in params:
            auth_code = params["code"][0]
            if "state" in params:
                auth_state = params["state"][0]

            # Send success response to browser
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            success_html = """
            <html>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                <h1 style="color: green;">✓ Authorization Successful!</h1>
                <p>You can close this window and return to the terminal.</p>
            </body>
            </html>
            """
            self.wfile.write(success_html.encode())
            callback_event.set()
        else:
            # Error in authorization
            print(f"[DEBUG] No 'code' in params. Checking for error...")
            if "error" in params:
                print(f"[ERROR] OAuth error: {params.get('error', ['unknown'])[0]}")
                print(f"[ERROR] Description: {params.get('error_description', ['none'])[0]}")

            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            error_html = """
            <html>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                <h1 style="color: red;">✗ Authorization Failed</h1>
                <p>Please check the terminal for error details.</p>
            </body>
            </html>
            """
            self.wfile.write(error_html.encode())
            callback_event.set()

    def log_message(self, format, *args):
        # Suppress server logs
        pass


def setup_oauth(client_id: str, client_secret: str, redirect_uri: str = "http://localhost:8080/callback"):
    """Perform OAuth authorization flow."""
    global auth_code

    # Store client credentials in keychain
    print("Storing client credentials in keychain...")
    keyring.set_password(KEYRING_SERVICE, CONFIG_KEYS["client_id"], client_id)
    keyring.set_password(KEYRING_SERVICE, CONFIG_KEYS["client_secret"], client_secret)

    # Construct authorization URL
    # Using only spark:all for simplicity (includes messages_write and rooms_read)
    auth_url = (
        f"https://webexapis.com/v1/authorize?"
        f"client_id={client_id}&"
        f"response_type=code&"
        f"redirect_uri={redirect_uri}&"
        f"scope=spark:all&"
        f"state=webex_setup"
    )

    print("\nOpening browser for Webex authorization...")
    print("If the browser doesn't open automatically, visit this URL:")
    print(f"\n{auth_url}\n")

    # Open browser
    webbrowser.open(auth_url)

    # Start local server to receive callback
    port = 8080
    server = HTTPServer(("localhost", port), OAuthCallbackHandler)
    print(f"Waiting for authorization callback on http://localhost:{port}/callback...")
    print("Please authorize the application in your browser.\n")

    # Wait for callback
    while not callback_event.is_set():
        server.handle_request()

    if not auth_code:
        print("Error: No authorization code received.", file=sys.stderr)
        return False

    print("Authorization code received. Exchanging for tokens...")

    # Exchange authorization code for tokens
    token_url = "https://webexapis.com/v1/access_token"
    data = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "code": auth_code,
        "redirect_uri": redirect_uri,
    }

    try:
        response = requests.post(token_url, data=data)
        response.raise_for_status()

        token_data = response.json()
        refresh_token = token_data.get("refresh_token")

        if not refresh_token:
            print("Error: No refresh token received.", file=sys.stderr)
            return False

        # Store refresh token in keychain
        keyring.set_password(KEYRING_SERVICE, CONFIG_KEYS["refresh_token"], refresh_token)
        print("\n✓ Setup complete! Refresh token stored securely in keychain.")
        print("\nYou can now use webex_daily_post.py to post messages.")
        return True

    except requests.exceptions.RequestException as e:
        print(f"Error exchanging authorization code: {e}", file=sys.stderr)
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Initial setup for Webex Daily Poster - Perform OAuth authorization.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Before running this script:
1. Create an Integration at https://developer.webex.com/my-apps
2. Set Redirect URI to: http://localhost:8080/callback
3. Add scopes: spark:messages_write, spark:rooms_read
4. Copy your Client ID and Client Secret

Example:
  webex_setup.py --client-id YOUR_CLIENT_ID --client-secret YOUR_CLIENT_SECRET
        """
    )

    parser.add_argument("--client-id", required=True, help="Webex Integration Client ID")
    parser.add_argument("--client-secret", required=True, help="Webex Integration Client Secret")
    parser.add_argument(
        "--redirect-uri",
        default="http://localhost:8080/callback",
        help="OAuth redirect URI (default: http://localhost:8080/callback)"
    )

    args = parser.parse_args()

    print("=== Webex Daily Poster Setup ===\n")

    if setup_oauth(args.client_id, args.client_secret, args.redirect_uri):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
