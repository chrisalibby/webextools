#!/usr/bin/env python3
"""
List all Webex rooms you have access to.
"""

import sys
sys.path.insert(0, '/Users/clibby/Projects/mytools')

from webex_daily_post import WebexPoster

def main():
    poster = WebexPoster()

    if not poster.load_credentials():
        sys.exit(1)

    print("Refreshing access token...")
    if not poster.refresh_access_token():
        sys.exit(1)

    import requests
    response = requests.get(
        "https://webexapis.com/v1/rooms",
        headers={"Authorization": f"Bearer {poster.access_token}"}
    )

    if response.status_code == 200:
        rooms = response.json()["items"]
        print(f"\nFound {len(rooms)} rooms:\n")
        for room in rooms:
            room_type = room.get("type", "unknown")
            print(f"Title: {room['title']}")
            print(f"Type:  {room_type}")
            print(f"ID:    {room['id']}")
            print("-" * 80)
    else:
        print(f"Error: {response.status_code} - {response.text}")
        sys.exit(1)

if __name__ == "__main__":
    main()
