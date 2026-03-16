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

List recent files:     GET ?action=list&secret=SECRET[&query=DRIVE_QUERY][&max=N]
Search file content:   GET ?action=search&query=TERMS&secret=SECRET[&max=N]
Read a file:           GET ?action=read&id=FILE_ID&secret=SECRET
```

The `secret` is a shared token set in your `.env` file — it prevents unauthorized access to your Drive via the relay.

## Setup

See README.md for full setup instructions, including:
- Deploying the relay (local or cloud)
- Configuring Google OAuth credentials
- Setting the `RELAY_URL` and `SECRET` environment variables in your Claude Code project
