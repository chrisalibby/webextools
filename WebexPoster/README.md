# Webex Daily Poster

Automatically post messages to Webex Teams spaces using OAuth authentication. Messages post as you (not a bot) and support markdown formatting, date/time placeholders, and @all mentions.

## Features

- **OAuth Authentication**: Posts as you using secure OAuth flow with automatic token refresh
- **Secure Credential Storage**: Client ID, secret, and refresh token stored in system keychain
- **Date/Time Placeholders**: Dynamic message content with date and time variables
- **Markdown Support**: Full markdown formatting
- **@all Mentions**: Notify everyone in the space
- **Cross-Platform**: Works on macOS and Windows

## Prerequisites

1. Python 3.7 or higher
2. A Webex account
3. A Webex Integration (created at https://developer.webex.com/my-apps)

## Installation

### 1. Install Python Dependencies

```bash
pip3 install -r requirements_webex.txt
```

### 2. Create Webex Integration

1. Go to https://developer.webex.com/my-apps
2. Click "Create a New App" → "Integration"
3. Fill in the details:
   - **Integration Name**: "Daily Message Poster" (or any name)
   - **Icon**: Upload an icon or use default
   - **Description**: "Automated daily messages"
   - **Redirect URI**: `http://localhost:8080/callback`
   - **Scopes**: Select `spark:all` (or at minimum `spark:messages_write`)
4. Click "Add Integration"
5. **Save your Client ID and Client Secret** - you'll need these next

### 3. Run Initial Setup

```bash
python3 webex_setup.py --client-id YOUR_CLIENT_ID --client-secret YOUR_CLIENT_SECRET
```

This will:
- Open your browser for Webex authorization
- Store credentials securely in your system keychain
- Save the refresh token for automatic access

### 4. Find Your Room ID

You need the Room ID where you want to post messages. Here's how to find it:

**Option A: Use Webex API (Quick)**

1. Go to https://developer.webex.com/docs/api/v1/rooms/list-rooms
2. Click "Run" (you'll be logged in with your account)
3. Find your room in the response and copy the `id` field

**Option B: Use Python Script**

Create a small script to list your rooms:

```python
import requests
import keyring

# Get access token (after setup)
from webex_daily_post import WebexPoster
poster = WebexPoster()
poster.load_credentials()
poster.refresh_access_token()

# List rooms
response = requests.get(
    "https://webexapis.com/v1/rooms",
    headers={"Authorization": f"Bearer {poster.access_token}"}
)

for room in response.json()["items"]:
    print(f"{room['title']}: {room['id']}")
```

## Command Line Alias Setup

To make the script easier to run, you can create an alias in your shell configuration.

### For zsh (macOS default)

Add this line to your `~/.zshrc` file:

```bash
alias webexpost='python3 /Users/clibby/Projects/webextools/WebexPoster/webex_daily_post.py'
```

Then reload your configuration:

```bash
source ~/.zshrc
```

### For bash

Add this line to your `~/.bashrc` (Linux) or `~/.bash_profile` (macOS):

```bash
alias webexpost='python3 /Users/clibby/Projects/webextools/WebexPoster/webex_daily_post.py'
```

Then reload your configuration:

```bash
# For .bashrc
source ~/.bashrc

# For .bash_profile
source ~/.bash_profile
```

After setting up the alias, you can use it like this:

```bash
webexpost ROOM_ID "Your message here"
```

## Usage

### Basic Message

```bash
python3 webex_daily_post.py ROOM_ID "Hello, team! Today is {day}, {date_long}"
```

Or with the alias:

```bash
webexpost ROOM_ID "Hello, team! Today is {day}, {date_long}"
```

### Message with @all Mention

Include `<@all>` directly in your message text:

```bash
python3 webex_daily_post.py ROOM_ID "<@all> **Daily Standup** - {day_short} {date}"
```

### Markdown Formatting

```bash
python3 webex_daily_post.py ROOM_ID "**Good morning!**

Today's agenda:
- Standup at 9 AM
- Sprint planning at 2 PM

Have a great {day}!"
```

## Available Placeholders

Use these placeholders in your messages for dynamic content:

| Placeholder | Example Output | Description |
|-------------|----------------|-------------|
| `{date}` | 2025-12-22 | YYYY-MM-DD format |
| `{date_long}` | December 22, 2025 | Full date |
| `{day}` | Monday | Full day name |
| `{day_short}` | Mon | Abbreviated day |
| `{time}` | 14:30 | 24-hour time |
| `{time_12h}` | 02:30 PM | 12-hour time with AM/PM |
| `{month}` | December | Full month name |
| `{month_short}` | Dec | Abbreviated month |
| `{year}` | 2025 | Year |
| `{week}` | 51 | Week number of year |

## Scheduling

### macOS/Linux (cron)

Edit your crontab:

```bash
crontab -e
```

Add a line to run every weekday at 9 AM:

```cron
0 9 * * 1-5 cd /Users/clibby/Projects/mytools && /usr/bin/python3 webex_daily_post.py YOUR_ROOM_ID "<@all> Good morning team! Today is {day}, {date_long}. Have a great day!" >> /tmp/webex_daily_post.log 2>&1
```

To run every day at 9 AM:

```cron
0 9 * * * cd /Users/clibby/Projects/mytools && /usr/bin/python3 webex_daily_post.py YOUR_ROOM_ID "<@all> Good morning! Happy {day}!" >> /tmp/webex_daily_post.log 2>&1
```

### Windows (Task Scheduler)

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger (e.g., "Daily" at 9:00 AM)
4. Action: "Start a program"
   - Program: `python3` (or `python` or full path like `C:\Python39\python.exe`)
   - Arguments: `webex_daily_post.py ROOM_ID "<@all> Your message here"`
   - Start in: `C:\Users\YourName\Projects\mytools`

## Troubleshooting

### "Missing credentials in keychain"

Run the setup script again:

```bash
python3 webex_setup.py --client-id YOUR_CLIENT_ID --client-secret YOUR_CLIENT_SECRET
```

### "Error refreshing access token"

Your refresh token may have expired or been revoked. Run setup again to reauthorize.

### Message doesn't mention @all

Make sure you:

1. Include `<@all>` in your message text
2. Are a moderator/admin of the space

### Can't find Room ID

Use the Webex API developer site (Option A above) or check the room URL in the Webex app.

## Security Notes

- **Client Secret**: Stored in system keychain (macOS Keychain, Windows Credential Manager)
- **Refresh Token**: Also stored in system keychain, automatically rotated
- **Access Token**: Generated on-demand, never stored permanently
- Never commit credentials to version control

## Example Messages

```bash
# Simple daily greeting
python3 webex_daily_post.py ROOM_ID "<@all> Happy {day}! Today is {date_long}"

# Morning standup reminder
python3 webex_daily_post.py ROOM_ID "<@all> **Daily Standup** in 10 minutes!

Join here: [Webex Meeting](https://meet.webex.com/your-meeting)"

# Weekly reminder (Monday only - use in cron)
python3 webex_daily_post.py ROOM_ID "<@all> **Week {week} of {year}**

Happy {day}! Let's make it a great week!"

# Custom formatted message
python3 webex_daily_post.py ROOM_ID "<@all> ### Good morning team!

**Date**: {date_long}
**Day**: {day}

Today's focus:
1. Complete sprint goals
2. Review PRs
3. Team sync at {time}

Let's do this!"
```

## Files

- `webex_setup.py` - One-time OAuth setup script
- `webex_daily_post.py` - Main script to post messages
- `requirements_webex.txt` - Python dependencies
- `README.md` - This file

## Support

For issues with:
- **Webex API**: https://developer.webex.com/support
- **OAuth Flow**: Check your Integration settings at https://developer.webex.com/my-apps
- **Scripts**: Check logs and error messages

## License

Free to use and modify for your needs.
