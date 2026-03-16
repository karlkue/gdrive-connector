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

A small **Cloud Function relay** bridges Claude to Google Drive. Claude calls the relay; the relay exchanges your stored OAuth refresh token for a fresh access token and forwards the Drive API request.

```
Claude Code  →  Cloud Function (relay)  →  Google Drive API
```

No local installs needed. Everything runs in your browser via GCP Cloud Shell.

---

## Accounts you will need

| What | Which Google account | Why |
|---|---|---|
| **GCP project** (hosts the relay) | **Personal** Google account | Workspace org policies often block Cloud Function deployments — use personal to avoid this |
| **Google Drive access** (the files Claude reads) | **Work / Workspace** account | This is the account whose Drive files you want Claude to search |

> **Key point:** You create the OAuth *client* in your personal GCP project, but you authorize it as your *work* account. The resulting refresh token gives read-only access to your work Drive, without touching GCP permissions.

---

## Setup (~15 minutes, browser only)

### Step 1 — Create a free GCP account

> ⚠️ **Use your personal Google account for GCP, not your work Workspace account.**

1. Go to [cloud.google.com](https://cloud.google.com) → **Get started for free**
2. Sign in with your **personal** Google account
3. Complete the sign-up wizard — a credit card is required for identity verification but **you will not be charged**. Cloud Functions has a permanent free tier (2 million invocations/month).
4. Create a project when prompted — name it anything, e.g. `drive-chat`

---

### Step 2 — Enable the Drive API and create OAuth credentials

> Still your **personal GCP account**.

**2a. Enable the Google Drive API**

```
console.cloud.google.com → APIs & Services → Library → "Google Drive API" → Enable
```

**2b. Configure the OAuth consent screen**

```
APIs & Services → OAuth consent screen
```

- User Type: **External**
- App name: `Drive Chat`
- User support email: your personal email
- Developer contact email: your personal email
- Click **Save and Continue** through all screens
- On the **Test users** screen → **+ Add users** → enter your **work email address**
  *(This is the account whose Drive you want to read)*
- Click **Save and Continue → Back to Dashboard**

**2c. Create OAuth 2.0 credentials**

```
APIs & Services → Credentials → + Create Credentials → OAuth client ID
```

- Application type: **Desktop app**
- Name: `Drive Chat`
- Click **Create**
- Save the **Client ID** and **Client Secret** — you need them in Step 3

---

### Step 3 — Get a refresh token

> ⚠️ You will sign in here with your **work account** to authorize Drive access.

This uses the [Google OAuth Playground](https://developers.google.com/oauthplayground) — a browser tool, no installs needed.

1. Open [developers.google.com/oauthplayground](https://developers.google.com/oauthplayground)

2. Click the **gear icon** (⚙️ top right) → enable **"Use your own OAuth credentials"**
   - Paste your **Client ID** and **Client Secret** from Step 2c

3. In the **Step 1** panel on the left, scroll to **Drive API v3** and select:
   ```
   https://www.googleapis.com/auth/drive.readonly
   ```

4. Click **Authorize APIs** → when the sign-in prompt appears, choose your **work Google account**
   *(The account whose Drive files you want Claude to read)*

5. Click **Exchange authorization code for tokens**

6. Copy the **Refresh token** — it looks like `1//04abc...`

---

### Step 4 — Generate a relay secret

This is a random password that prevents unauthorized access to your relay.

Run this in any terminal, or in GCP Cloud Shell (next step):

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(24))"
```

Or just pick any random string, e.g. `my-relay-secret-2024`. Save it.

---

### Step 5 — Deploy the Cloud Function

> Back to your **personal GCP account** — use the browser-based Cloud Shell.

1. Open [console.cloud.google.com](https://console.cloud.google.com) and click **`>_`** (top-right toolbar) to open Cloud Shell

2. Enable the Cloud Functions API:
   ```bash
   gcloud services enable cloudfunctions.googleapis.com
   ```

3. Create the function files (paste this entire block):
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

4. Deploy — replace the four `YOUR_*` placeholders with your actual values:
   ```bash
   gcloud functions deploy drive-chat-relay \
     --gen2 --runtime=python311 --region=us-central1 \
     --source=. --entry-point=relay \
     --trigger-http --allow-unauthenticated \
     --set-env-vars="RELAY_SECRET=YOUR_RELAY_SECRET,GOOGLE_CLIENT_ID=YOUR_CLIENT_ID,GOOGLE_CLIENT_SECRET=YOUR_CLIENT_SECRET,GOOGLE_REFRESH_TOKEN=YOUR_REFRESH_TOKEN"
   ```

   When it finishes, the output includes a URL like:
   ```
   url: https://us-central1-YOUR_PROJECT_ID.cloudfunctions.net/drive-chat-relay
   ```

5. **Verify it works** (replace the placeholders):
   ```bash
   curl "https://YOUR_FUNCTION_URL?secret=YOUR_RELAY_SECRET&action=list"
   ```
   You should see a JSON array of your 20 most recent Drive files.

---

### Step 6 — Connect to Claude Code

Paste this into a Claude Code chat (replace the two placeholders):

```
I have a Google Drive relay set up. Please use it to access my files.

Relay URL: https://YOUR_FUNCTION_URL
Secret: YOUR_RELAY_SECRET

API:
- List files:   GET ?action=list&secret=SECRET[&query=DRIVE_QUERY][&max=N]
- Search:       GET ?action=search&query=SEARCH_TERMS&secret=SECRET[&max=N]
- Read a file:  GET ?action=read&id=FILE_ID&secret=SECRET

Please confirm by listing my 5 most recent files.
```

Claude will immediately start using the relay to browse and read your Drive.

---

## Project structure

```
.
├── cloudfunction/
│   ├── main.py         # Cloud Function source (same code as Step 5 above)
│   └── requirements.txt
├── drive.py            # Drive tool definitions for the Claude API
├── app.py              # Optional FastAPI chat server
├── static/
│   └── index.html      # Optional web chat UI
├── requirements.txt
├── .env.example
└── .gitignore
```

The `cloudfunction/` folder is just for reference — you create the files directly in Cloud Shell during setup (Step 5).

---

## Environment variables (for the optional local server)

Copy `.env.example` to `.env` and fill in:

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key from [console.anthropic.com](https://console.anthropic.com) |
| `RELAY_URL` | The Cloud Function URL from Step 5 |
| `RELAY_SECRET` | The secret you generated in Step 4 |

---

## Security notes

- The relay checks `?secret=` on every request — requests without your secret get a `403`
- The refresh token is scoped to **read-only** Drive access (`drive.readonly`)
- Your Cloud Function URL is public but useless without the secret
- Never commit `.env` or `credentials.json` — both are in `.gitignore`
- To revoke access at any time: [myaccount.google.com/permissions](https://myaccount.google.com/permissions) → remove `Drive Chat`

---

## Troubleshooting

**`403 forbidden` from relay** — Wrong or missing `secret=` in the URL.

**`invalid_client` during OAuth** — Client ID / Secret mismatch in the OAuth Playground gear settings.

**`invalid_grant` when getting the refresh token** — Authorization code expired (they're single-use, ~10 min). Click **Authorize APIs** again and immediately exchange.

**Relay returns empty array** — The refresh token authorized the wrong Google account. Redo Step 3 and confirm you signed in with your **work account**.

**Cloud Function deploy fails with auth error** — Run `gcloud auth login` in Cloud Shell and follow the link it prints, then retry the deploy command.

**`quota exceeded` error from Drive API** — The Drive API has a default quota of 1,000 requests/100 seconds. Normal chat usage won't hit this. If you do, wait a minute and retry.
