# Drive Chat

Chat with Claude while it browses and reads your **Google Drive** files on demand.

---

## How it works

Claude has three Drive tools it can call during a conversation:

| Tool | What it does |
|---|---|
| `drive_list_files` | Browse recent files or filter by Drive query syntax |
| `drive_read_file` | Read the full text of a file (up to 100 KB) |
| `drive_search_files` | Full-text search across file names and content |

A small **Cloud Run relay** bridges Claude to Google Drive. Claude calls the relay; the relay exchanges your stored OAuth refresh token for a fresh access token and forwards the Drive API request.

```
Claude Code  →  Cloud Run relay  →  Google Drive API
```

---

## Accounts you will need

| What | Which Google account | Why |
|---|---|---|
| **OAuth credentials** (Client ID + Secret) | **Work** Google account | This is where you create the OAuth app and enable the Drive API |
| **Refresh token** (Drive access) | **Work** Google account | The token authorizes access to your work Drive files |
| **Cloud Run** (hosts the relay) | **Personal** Google account | Keeps the relay infrastructure separate from your work account |

> **Key point:** The OAuth app and Drive API are enabled in your **work** GCP project. You authorize access via Claude Code (no local installs needed) to get a refresh token. The relay itself runs on your **personal** GCP using Cloud Run.

---

## Setup

### Step 1 — Create OAuth credentials (work GCP)

Sign in to [console.cloud.google.com](https://console.cloud.google.com) with your **work account**.

**1a. Enable Google Workspace APIs**

Go to `APIs & Services → Library` and enable each of these (search by name, click Enable):

| API | What it unlocks |
|---|---|
| **Google Drive API** | Read and browse files (required) |
| **Google Slides API** | Create and edit Presentations |
| **Google Docs API** | Create and edit Documents |
| **Google Sheets API** | Create and edit Spreadsheets |
| **Google Calendar API** | Read and create calendar events |
| **Gmail API** | Read and send email |

Enable all of them now — it costs nothing and saves you from coming back later.

**1b. Configure the OAuth consent screen**

```
APIs & Services → OAuth consent screen
```

- User Type: **External**
- App name: `Drive Chat`
- User support email: your work email
- Developer contact email: your work email
- Click **Save and Continue** through all screens
- On the **Test users** screen → **+ Add users** → add your work email
- Click **Save and Continue → Back to Dashboard**

**1c. Create OAuth 2.0 credentials**

```
APIs & Services → Credentials → + Create Credentials → OAuth client ID
```

- Application type: **Desktop app**
- Name: `Drive Chat`
- Click **Create**
- Save the **Client ID** and **Client Secret** — you need them in Step 2

---

### Step 2 — Get a refresh token (via Claude Code)

Ask Claude Code to generate the auth URL for you. Run this in a Claude Code session:

```
Generate an OAuth URL for my Google Drive relay with these scopes:
- https://www.googleapis.com/auth/drive.readonly

Client ID: YOUR_CLIENT_ID
Client Secret: YOUR_CLIENT_SECRET
Redirect URI: http://localhost:8888
```

Claude will print an auth URL. **Open it in your browser**, sign in with your **work account**, and approve access.

Your browser will then try to redirect to `http://localhost:8888/?code=...` — **that page won't load, which is expected.** Copy the full URL from your browser's address bar and paste it back to Claude.

Claude will exchange the code for tokens and print your **refresh token**.

---

### Step 3 — Generate a relay secret

This is a random password that prevents unauthorized access to your relay.

Ask Claude Code: *"Generate a random relay secret for me"* — or run this in any terminal that has Python:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(24))"
```

Save it — you'll need it in the next step.

---

### Step 4 — Deploy the Cloud Run relay (personal GCP)

Sign in to [console.cloud.google.com](https://console.cloud.google.com) with your **personal account** and open Cloud Shell (`>_` top-right).

**Enable Cloud Run:**

```bash
gcloud services enable run.googleapis.com
```

**Create the relay files:**

```bash
mkdir drive-chat && cd drive-chat

cat > main.py << 'PYEOF'
import json, os, functions_framework, requests as http

TOKEN_URL = "https://oauth2.googleapis.com/token"
DRIVE_BASE = "https://www.googleapis.com/drive/v3"
EXPORT_FORMATS = {
    "application/vnd.google-apps.document": "text/plain",
    "application/vnd.google-apps.spreadsheet": "text/csv",
    "application/vnd.google-apps.presentation": "text/plain",
}

def get_access_token():
    r = http.post(TOKEN_URL, data={
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    })
    r.raise_for_status()
    return r.json()["access_token"]

@functions_framework.http
def relay(request):
    if request.method == "OPTIONS":
        return ("", 204, {"Access-Control-Allow-Origin": "*"})
    args = request.args
    if args.get("secret") != os.environ.get("RELAY_SECRET", ""):
        return (json.dumps({"error": "forbidden"}), 403, {"Content-Type": "application/json"})
    action = args.get("action", "list")
    try:
        token = get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        if action == "search":
            q = f"fullText contains '{args.get('query','').replace(chr(39),'')}' and trashed=false"
            r = http.get(f"{DRIVE_BASE}/files", headers=headers, params={"q": q, "pageSize": int(args.get("max", 10)), "fields": "files(id,name,mimeType,modifiedTime)", "orderBy": "modifiedTime desc"})
            return (json.dumps(r.json().get("files", [])), 200, {"Content-Type": "application/json"})
        elif action == "list":
            q = f"trashed=false and ({args.get('query','')})" if args.get("query") else "trashed=false"
            r = http.get(f"{DRIVE_BASE}/files", headers=headers, params={"q": q, "pageSize": int(args.get("max", 20)), "fields": "files(id,name,mimeType,modifiedTime)", "orderBy": "modifiedTime desc"})
            return (json.dumps(r.json().get("files", [])), 200, {"Content-Type": "application/json"})
        elif action == "read":
            fid = args.get("id")
            meta = http.get(f"{DRIVE_BASE}/files/{fid}", headers=headers, params={"fields": "name,mimeType"}).json()
            mime = meta.get("mimeType", "")
            export_mime = EXPORT_FORMATS.get(mime)
            if export_mime:
                r = http.get(f"{DRIVE_BASE}/files/{fid}/export", headers=headers, params={"mimeType": export_mime})
            else:
                r = http.get(f"{DRIVE_BASE}/files/{fid}", headers=headers, params={"alt": "media"})
            content = r.content[:100000].decode("utf-8", errors="replace")
            return (json.dumps({"content": content}), 200, {"Content-Type": "application/json"})
    except Exception as e:
        return (json.dumps({"error": str(e)}), 500, {"Content-Type": "application/json"})
PYEOF

cat > requirements.txt << 'EOF'
functions-framework==3.*
requests>=2.31.0
EOF
```

**Deploy — replace the four `YOUR_*` placeholders:**

```bash
gcloud functions deploy drive-chat-relay \
  --gen2 --runtime=python311 --region=us-central1 \
  --source=. --entry-point=relay \
  --trigger-http --allow-unauthenticated \
  --set-env-vars="RELAY_SECRET=YOUR_RELAY_SECRET,GOOGLE_CLIENT_ID=YOUR_CLIENT_ID,GOOGLE_CLIENT_SECRET=YOUR_CLIENT_SECRET,GOOGLE_REFRESH_TOKEN=YOUR_REFRESH_TOKEN"
```

When it finishes, copy the URL from the output — it looks like:
```
https://drive-chat-relay-XXXXXXXXXX.us-central1.run.app
```

**Verify it works:**
```bash
curl "https://YOUR_RELAY_URL?secret=YOUR_RELAY_SECRET&action=list"
```

You should see a JSON array of your 20 most recent Drive files.

---

### Step 5 — Connect to Claude Code

Paste this into a Claude Code chat (replace the two placeholders):

```
I have a Google Drive relay set up. Please use it to access my files.

Relay URL: https://YOUR_RELAY_URL
Secret: YOUR_RELAY_SECRET

API:
- List files:   GET ?action=list&secret=SECRET[&query=DRIVE_QUERY][&max=N]
- Search:       GET ?action=search&query=SEARCH_TERMS&secret=SECRET[&max=N]
- Read a file:  GET ?action=read&id=FILE_ID&secret=SECRET

Please confirm by listing my 5 most recent files.
```

---

## Adding write access (e.g. Google Slides)

The default setup is **read-only**. To add write access (e.g. to create Google Slides):

**1. Check APIs are enabled in work GCP:**
If you followed Step 1a and enabled all APIs upfront, skip this. Otherwise go to `APIs & Services → Library` and enable any API you need (Slides, Docs, Sheets, etc.).

**2. Get a new refresh token with expanded scopes** — ask Claude Code to generate the auth URL with these three scopes:

```
https://www.googleapis.com/auth/drive.readonly
https://www.googleapis.com/auth/drive.file
https://www.googleapis.com/auth/presentations
```

Follow the same flow as Step 2: open the URL in your browser (work account), copy the redirect URL from the address bar, paste it back to Claude. Claude will print a new refresh token.

**3. Update the relay with the new token** — in Cloud Shell on your **personal GCP**:

```bash
gcloud run services update drive-chat-relay \
  --region=us-central1 \
  --update-env-vars="GOOGLE_REFRESH_TOKEN=YOUR_NEW_TOKEN"
```

---

## Project structure

```
.
├── cloudfunction/
│   ├── main.py         # Relay source code
│   └── requirements.txt
├── drive.py            # Drive tool definitions for the Claude API
├── app.py              # Optional FastAPI chat server
├── static/
│   └── index.html      # Optional web chat UI
├── spx-style-guide.md  # SPX PH Update style guide (synthesized from 18 decks)
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## Environment variables

Copy `.env.example` to `.env` and fill in:

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key from [console.anthropic.com](https://console.anthropic.com) |
| `RELAY_URL` | The Cloud Run URL from Step 4 |
| `RELAY_SECRET` | The secret you generated in Step 3 |

---

## Security notes

- The relay checks `?secret=` on every request — requests without your secret get a `403`
- The default refresh token is scoped to **read-only** Drive access (`drive.readonly`)
- Your relay URL is public but useless without the secret
- Never commit `.env` or `credentials.json` — both are in `.gitignore`
- To revoke access at any time: [myaccount.google.com/permissions](https://myaccount.google.com/permissions) → remove `Drive Chat`

---

## Troubleshooting

**`403 forbidden` from relay** — Wrong or missing `secret=` in the URL.

**`invalid_grant` when getting the refresh token** — Redo Step 2 and make sure you sign in with your **work account** when approving.

**Relay returns empty array** — The refresh token authorized the wrong Google account. Redo Step 2 and confirm you signed in with your work account.

**Deploy fails with auth error** — Run `gcloud auth login` in Cloud Shell and retry.

**`quota exceeded` error from Drive API** — The Drive API has a default quota of 1,000 requests/100 seconds. Normal chat usage won't hit this. If you do, wait a minute and retry.
