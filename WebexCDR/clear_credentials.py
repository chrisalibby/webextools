#!/usr/bin/env python3
"""
Clear stored Webex credentials from keyring.
Use this before re-running setup.
"""

import keyring
import sys

KEYRING_SERVICE = "webex_cdr_downloader"

def main():
    print("Clearing Webex CDR credentials from keyring...")

    try:
        # Delete Webex credentials
        keyring.delete_password(KEYRING_SERVICE, "client_id")
        keyring.delete_password(KEYRING_SERVICE, "client_secret")
        keyring.delete_password(KEYRING_SERVICE, "refresh_token")
        print("[OK] Webex credentials deleted")
    except keyring.errors.PasswordDeleteError:
        print("[INFO] Some Webex credentials were not found (already deleted)")
    except Exception as e:
        print(f"[ERROR] Failed to delete Webex credentials: {e}", file=sys.stderr)

    try:
        # Delete SQL credentials
        keyring.delete_password(KEYRING_SERVICE, "sql_server")
        keyring.delete_password(KEYRING_SERVICE, "sql_database")
        keyring.delete_password(KEYRING_SERVICE, "sql_username")
        keyring.delete_password(KEYRING_SERVICE, "sql_password")
        keyring.delete_password(KEYRING_SERVICE, "sql_driver")
        print("[OK] SQL Server credentials deleted")
    except keyring.errors.PasswordDeleteError:
        print("[INFO] Some SQL credentials were not found (already deleted)")
    except Exception as e:
        print(f"[ERROR] Failed to delete SQL credentials: {e}", file=sys.stderr)

    print("\n" + "="*60)
    print("Credentials cleared successfully!")
    print("="*60)
    print("\nNext steps:")
    print("1. Update your Webex integration at https://developer.webex.com/my-apps")
    print("   - Ensure 'spark:people_read' scope is added")
    print("   - Ensure 'analytics:read_all' scope is added")
    print("   - Verify redirect URI is: http://localhost:8080/callback")
    print("\n2. Re-run setup with your updated credentials:")
    print("   python webex_cdr_setup.py --client-id YOUR_ID --client-secret YOUR_SECRET ...")
    print()

if __name__ == "__main__":
    main()
