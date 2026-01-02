#!/usr/bin/env python3
"""
Webex CDR Downloader - Initial Setup
One-time configuration for Webex OAuth and SQL Server credentials.
"""

import argparse
import keyring
import requests
import sys
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from threading import Event

# Import our library modules
from lib.auth_manager import WebexAuthManager
from lib.database_manager import SQLServerManager


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
                <h1 style="color: green;">Authorization Successful!</h1>
                <p>You can close this window and return to the terminal.</p>
            </body>
            </html>
            """
            self.wfile.write(success_html.encode())
            callback_event.set()
        else:
            # Error in authorization
            if "error" in params:
                print(f"ERROR: OAuth error: {params.get('error', ['unknown'])[0]}", file=sys.stderr)
                print(f"ERROR: Description: {params.get('error_description', ['none'])[0]}", file=sys.stderr)

            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            error_html = """
            <html>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                <h1 style="color: red;">Authorization Failed</h1>
                <p>Please check the terminal for error details.</p>
            </body>
            </html>
            """
            self.wfile.write(error_html.encode())
            callback_event.set()

    def log_message(self, format, *args):
        # Suppress server logs
        pass


def setup_webex_oauth(client_id: str, client_secret: str, redirect_uri: str = "http://localhost:8080/callback") -> bool:
    """Perform OAuth authorization flow for Webex CDR access."""
    global auth_code, auth_state, callback_event

    # Reset global state for fresh OAuth flow
    auth_code = None
    auth_state = None
    callback_event.clear()

    # Construct authorization URL with required scopes
    # Note: spark-admin:people_read is required for basic API access (admin scope)
    # spark-admin:calling_cdr_read is required for CDR access
    # analytics:read_all provides access to analytics APIs
    scopes = "spark-admin:people_read spark-admin:calling_cdr_read analytics:read_all"
    auth_url = (
        f"https://webexapis.com/v1/authorize?"
        f"client_id={client_id}&"
        f"response_type=code&"
        f"redirect_uri={redirect_uri}&"
        f"scope={scopes}&"
        f"state=webex_cdr_setup"
    )

    print("\n=== Webex OAuth Setup ===")
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
        print("ERROR: No authorization code received.", file=sys.stderr)
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
            print("ERROR: No refresh token received.", file=sys.stderr)
            return False

        # Store credentials using auth manager
        auth_mgr = WebexAuthManager()
        if not auth_mgr.save_credentials(client_id, client_secret, refresh_token):
            return False

        print("Webex OAuth credentials stored securely in keyring")
        return True

    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to exchange authorization code: {e}", file=sys.stderr)
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}", file=sys.stderr)
        return False


def setup_sql_server(server: str, database: str, username: str, password: str, driver: str) -> bool:
    """Configure and test SQL Server credentials."""
    print("\n=== SQL Server Setup ===")

    # Store credentials
    db_mgr = SQLServerManager()
    if not db_mgr.save_credentials(server, database, username, password, driver):
        return False

    print("SQL Server credentials stored securely in keyring")

    # Test connection
    print("Testing SQL Server connection...")
    if not db_mgr.load_credentials():
        return False

    if not db_mgr.connect():
        print("ERROR: Failed to connect to SQL Server. Please check your credentials.", file=sys.stderr)
        return False

    print("SQL Server connection successful")
    db_mgr.disconnect()

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Initial setup for Webex CDR Downloader - Configure OAuth and SQL Server.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Setup Steps:
1. Create a Webex Integration at https://developer.webex.com/my-apps
   - Set Redirect URI to: http://localhost:8080/callback
   - Add scopes: spark-admin:people_read, spark-admin:calling_cdr_read, analytics:read_all
   - Copy your Client ID and Client Secret
   - NOTE: You must be a Webex admin to authorize admin scopes

2. Prepare SQL Server credentials
   - Server hostname/IP
   - Database name
   - SQL Server username and password
   - ODBC driver name (e.g., "ODBC Driver 18 for SQL Server")

3. Run this setup script with all parameters

Example:
  python3 webex_cdr_setup.py \\
    --client-id YOUR_CLIENT_ID \\
    --client-secret YOUR_CLIENT_SECRET \\
    --sql-server your-server.database.windows.net \\
    --sql-database webex_cdr \\
    --sql-username cdr_user \\
    --sql-password 'YourPassword' \\
    --sql-driver 'ODBC Driver 18 for SQL Server'

After setup, initialize the database:
  python3 webex_cdr_downloader.py --init-db
        """
    )

    # Webex OAuth arguments
    parser.add_argument("--client-id", required=True, help="Webex Integration Client ID")
    parser.add_argument("--client-secret", required=True, help="Webex Integration Client Secret")
    parser.add_argument(
        "--redirect-uri",
        default="http://localhost:8080/callback",
        help="OAuth redirect URI (default: http://localhost:8080/callback)"
    )

    # SQL Server arguments
    parser.add_argument("--sql-server", required=True, help="SQL Server hostname or IP")
    parser.add_argument("--sql-database", required=True, help="Database name")
    parser.add_argument("--sql-username", required=True, help="SQL Server username")
    parser.add_argument("--sql-password", required=True, help="SQL Server password")
    parser.add_argument(
        "--sql-driver",
        default="ODBC Driver 18 for SQL Server",
        help="ODBC driver name (default: 'ODBC Driver 18 for SQL Server')"
    )

    args = parser.parse_args()

    print("=== Webex CDR Downloader Setup ===\n")

    # Step 1: Setup Webex OAuth
    if not setup_webex_oauth(args.client_id, args.client_secret, args.redirect_uri):
        print("\nERROR: Webex OAuth setup failed", file=sys.stderr)
        sys.exit(1)

    # Step 2: Setup SQL Server
    if not setup_sql_server(args.sql_server, args.sql_database, args.sql_username,
                           args.sql_password, args.sql_driver):
        print("\nERROR: SQL Server setup failed", file=sys.stderr)
        sys.exit(1)

    # Success
    print("\n" + "="*50)
    print("Setup complete!")
    print("="*50)
    print("\nNext steps:")
    print("1. Initialize the database:")
    print("   python3 webex_cdr_downloader.py --init-db")
    print("\n2. Run your first sync:")
    print("   python3 webex_cdr_downloader.py")
    print("\n3. Schedule periodic runs (e.g., every 15-30 minutes)")
    print("   - macOS/Linux: Use cron")
    print("   - Windows: Use Task Scheduler")
    print()

    sys.exit(0)


if __name__ == "__main__":
    main()
