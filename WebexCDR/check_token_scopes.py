#!/usr/bin/env python3
"""
Diagnostic script to check what scopes your Webex access token has.
"""

import sys
import io
from lib.auth_manager import WebexAuthManager
import requests

# Fix Windows console encoding issues
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def main():
    auth_mgr = WebexAuthManager()

    # Load credentials
    if not auth_mgr.load_credentials():
        print("ERROR: Failed to load credentials from keyring", file=sys.stderr)
        sys.exit(1)

    # Refresh token
    print("Refreshing access token...")
    if not auth_mgr.refresh_access_token():
        print("ERROR: Failed to refresh access token", file=sys.stderr)
        sys.exit(1)

    print("Access token obtained successfully\n")

    # Get information about the current token/user
    print("=" * 60)
    print("Checking token permissions...")
    print("=" * 60)

    # Try to get user info (this should work with any valid token)
    headers = auth_mgr.get_headers()

    try:
        # Get current user/person info
        response = requests.get("https://webexapis.com/v1/people/me", headers=headers)
        if response.status_code == 200:
            person = response.json()
            print(f"\n[OK] Authenticated as: {person.get('displayName')} ({person.get('emails', [''])[0]})")
            print(f"  Organization ID: {person.get('orgId')}")
        else:
            print(f"\n[FAIL] Failed to get user info: {response.status_code}")
            print(f"  Response: {response.text}")
    except Exception as e:
        print(f"\n[ERROR] Error getting user info: {e}")

    # Try to access the CDR endpoint
    print("\n" + "=" * 60)
    print("Testing CDR API access...")
    print("=" * 60)

    from datetime import datetime, timedelta
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=1)

    params = {
        'startTime': start_time.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
        'endTime': end_time.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
        'max': 10
    }

    try:
        response = requests.get(
            "https://analytics.webexapis.com/v1/cdr_feed",
            headers=headers,
            params=params
        )

        print(f"\nCDR API Response Code: {response.status_code}")

        if response.status_code == 200:
            print("[OK] CDR API access is working!")
            data = response.json()
            print(f"  Retrieved {len(data.get('items', []))} records")
        elif response.status_code == 403:
            print("\n[FORBIDDEN] (403): Your token does not have permission to access CDR data")
            print("\nPossible causes:")
            print("  1. Missing 'analytics:read_all' scope on your integration")
            print("  2. Your Webex organization doesn't have CDR API access enabled")
            print("  3. You need a Service App with admin approval instead of an Integration")
            print("  4. Your account lacks the necessary admin privileges")
            print("\nResponse details:")
            print(f"  {response.text}")
        elif response.status_code == 401:
            print("\n[UNAUTHORIZED] (401): Token is invalid or expired")
            print(f"  {response.text}")
        else:
            print(f"\n[ERROR] Unexpected response:")
            print(f"  {response.text}")

    except Exception as e:
        print(f"\n[ERROR] Error accessing CDR API: {e}")

    # Check if we can access other analytics endpoints
    print("\n" + "=" * 60)
    print("Testing other Analytics API endpoints...")
    print("=" * 60)

    # Try the meetings endpoint (might have different permissions)
    try:
        response = requests.get(
            "https://analytics.webexapis.com/v1/meeting/qualities",
            headers=headers,
            params={'from': start_time.strftime('%Y-%m-%d'), 'to': end_time.strftime('%Y-%m-%d'), 'max': 10}
        )
        print(f"\nMeeting Qualities API: {response.status_code}")
        if response.status_code == 200:
            print("  [OK] Access granted")
        elif response.status_code == 403:
            print("  [FORBIDDEN] Access forbidden")
        else:
            print(f"  Response: {response.text[:200]}")
    except Exception as e:
        print(f"  Error: {e}")

    print("\n" + "=" * 60)
    print("Diagnostic Complete")
    print("=" * 60)
    print("\nNext steps if CDR access is forbidden:")
    print("1. Check your integration at https://developer.webex.com/my-apps")
    print("2. Verify 'analytics:read_all' scope is present")
    print("3. Contact Webex admin to verify org has CDR API access")
    print("4. Consider creating a Service App if using an Integration")
    print("5. Check with Cisco account team about CDR API licensing")
    print()

if __name__ == "__main__":
    main()
