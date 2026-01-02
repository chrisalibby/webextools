#!/usr/bin/env python3
"""
Test different scope combinations to find what works with your integration.
This will help identify the correct scopes for CDR access.
"""

import sys
import webbrowser

CLIENT_ID = "C2678539b6fd647ee4c772a36ee2faf375491aa1e1401fc53a8198d82e56e3628"
REDIRECT_URI = "http://localhost:8080/callback"

print("="*70)
print("Webex Scope Testing Tool")
print("="*70)
print("\nThis will help identify which scopes work with your integration.")
print("Try each URL below in your browser and see which ones work:\n")

# Common scope combinations for CDR access
scope_tests = [
    ("Test 1: Basic people read only", "spark:people_read"),
    ("Test 2: People + Analytics", "spark:people_read analytics:read_all"),
    ("Test 3: People + Calling CDR (admin)", "spark:people_read spark-admin:calling_cdr_read"),
    ("Test 4: People + Calling CDR (non-admin)", "spark:people_read spark:calling_cdr_read"),
    ("Test 5: Analytics only", "analytics:read_all"),
    ("Test 6: People + Analytics + Calling", "spark:people_read analytics:read_all spark-admin:calling_cdr_read"),
    ("Test 7: All admin scopes", "spark:people_read spark-admin:calling_cdr_read spark-admin:organizations_read"),
]

for i, (description, scopes) in enumerate(scope_tests, 1):
    print(f"\n{description}")
    print(f"Scopes: {scopes}")

    auth_url = (
        f"https://webexapis.com/v1/authorize?"
        f"client_id={CLIENT_ID}&"
        f"response_type=code&"
        f"redirect_uri={REDIRECT_URI}&"
        f"scope={scopes}&"
        f"state=test_{i}"
    )
    print(f"URL: {auth_url}")
    print("-" * 70)

print("\n" + "="*70)
print("INSTRUCTIONS:")
print("="*70)
print("""
1. Copy each URL above (one at a time) and paste into your browser
2. If you see an 'invalid_scope' error page, that combination doesn't work
3. If you see the authorization page (asking you to approve), that works!
4. Find the first combination that shows the authorization page
5. Note which test number works and report back

IMPORTANT: Don't actually approve the authorization - just see which ones
show the approval page vs. the error page.

Once you identify which test works, we'll update the setup script.
""")

print("\nAlternatively, check your integration settings:")
print("1. Go to https://developer.webex.com/my-apps")
print("2. Click on your integration")
print("3. In the Scopes section, note EXACTLY which scopes are checked")
print("4. Tell me the exact scope names you see")
print()
