# Google Drive Connector for Claude Code

## What this repo does

This repo provides a relay that lets Claude Code (on web projects) search and read files from Google Drive on demand. It acts as a bridge between Claude's web sessions and your Drive, so Claude can look up documents, slides, or any Drive content during a conversation.

## How to use Google Drive from Claude Code

Once the relay is deployed and configured (see README.md), Claude can search and read your Drive files using the relay API.

### Search for a file

Ask Claude:
```
Search Google Drive for [topic or filename]
```

Claude will call:
```
GET ?action=search&query=TERMS&secret=SECRET
```

### Read a specific file by ID

Ask Claude:
```
Read the Drive file with ID: FILE_ID
```

Claude will call:
```
GET ?action=read&id=FILE_ID&secret=SECRET
```

### List recent files

```
GET ?action=list&secret=SECRET[&query=DRIVE_QUERY][&max=N]
```

## Relay API (quick reference)

```
Base URL: [set in .env as RELAY_URL]

--- Drive ---
List recent files:     GET  ?action=list&secret=SECRET[&query=DRIVE_QUERY][&max=N]
Search file content:   GET  ?action=search&query=TERMS&secret=SECRET[&max=N]
Read a file:           GET  ?action=read&id=FILE_ID&secret=SECRET

--- Calendar ---
List upcoming events:  GET  ?action=calendar_list&secret=SECRET[&max=N][&timeMin=RFC3339]
Create an event:       POST ?action=calendar_create&secret=SECRET
                            body: { "summary": "...", "start": {...}, "end": {...} }
```

The `secret` is a shared token set in your `.env` file — it prevents unauthorized access to your Drive and Calendar via the relay.

## Calendar usage

Ask Claude naturally:

- "What's on my calendar this week?"
- "Add a meeting called Sync on Friday at 2pm Manila time"
- "Create an event: Untitled Event, Wednesday 8am Philippine time"

Claude will use the `calendar_list_events` and `calendar_create_event` tools automatically. Timezones are inferred from context — "Philippine time" maps to `Asia/Manila`.

### OAuth scope note

The relay's refresh token needs the `https://www.googleapis.com/auth/calendar.events` scope in addition to Drive scopes. If you set up the relay before calendar support was added, re-authenticate to get an updated token.

## Setup

See README.md for full setup instructions, including:
- Deploying the relay (local or cloud)
- Configuring Google OAuth credentials
- Setting the `RELAY_URL` and `SECRET` environment variables in your Claude Code project
