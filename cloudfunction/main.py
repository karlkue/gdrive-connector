"""
Drive Chat relay — Google Cloud Function

Exposes a simple HTTP API so Claude Code can read your Google Drive files.
Auth uses a stored OAuth refresh token (set as a Secret Manager secret).

Environment variables (set in Cloud Function config):
  RELAY_SECRET   — shared secret to prevent unauthorized access
  GOOGLE_REFRESH_TOKEN — your OAuth refresh token
  GOOGLE_CLIENT_ID     — from credentials.json
  GOOGLE_CLIENT_SECRET — from credentials.json
"""

import json
import os
import functions_framework
import requests as http

# ---------------------------------------------------------------------------
# Auth — exchange refresh token for a fresh access token
# ---------------------------------------------------------------------------

TOKEN_URL = "https://oauth2.googleapis.com/token"
DRIVE_BASE = "https://www.googleapis.com/drive/v3"

EXPORT_FORMATS = {
    "application/vnd.google-apps.document":     "text/plain",
    "application/vnd.google-apps.spreadsheet":  "text/csv",
    "application/vnd.google-apps.presentation": "text/plain",
}


def get_access_token() -> str:
    resp = http.post(TOKEN_URL, data={
        "client_id":     os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
        "grant_type":    "refresh_token",
    })
    resp.raise_for_status()
    return resp.json()["access_token"]


def drive_get(path: str, token: str, params: dict = None) -> dict:
    r = http.get(f"{DRIVE_BASE}{path}", headers={"Authorization": f"Bearer {token}"},
                 params=params or {})
    r.raise_for_status()
    return r


# ---------------------------------------------------------------------------
# Cloud Function entry point
# ---------------------------------------------------------------------------

@functions_framework.http
def relay(request):
    # CORS pre-flight
    if request.method == "OPTIONS":
        return ("", 204, {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET",
            "Access-Control-Allow-Headers": "Content-Type",
        })

    args = request.args

    # Auth check
    if args.get("secret") != os.environ.get("RELAY_SECRET", ""):
        return (json.dumps({"error": "forbidden"}), 403,
                {"Content-Type": "application/json"})

    action = args.get("action", "list")

    try:
        token = get_access_token()

        if action == "list":
            query   = args.get("query", "")
            max_res = min(int(args.get("max", 20)), 100)
            base_q  = "trashed = false"
            q       = f"{base_q} and ({query})" if query else base_q
            data    = drive_get("/files", token, {
                "q": q, "pageSize": max_res,
                "fields": "files(id,name,mimeType,modifiedTime,size)",
                "orderBy": "modifiedTime desc",
            }).json()
            return _json(data.get("files", []))

        elif action == "search":
            query   = args.get("query", "")
            max_res = min(int(args.get("max", 10)), 100)
            q       = f"fullText contains '{query.replace(chr(39), '')}' and trashed = false"
            data    = drive_get("/files", token, {
                "q": q, "pageSize": max_res,
                "fields": "files(id,name,mimeType,modifiedTime)",
                "orderBy": "modifiedTime desc",
            }).json()
            return _json(data.get("files", []))

        elif action == "read":
            file_id = args.get("id")
            if not file_id:
                return _json({"error": "id required"}, 400)

            meta     = drive_get(f"/files/{file_id}", token,
                                  {"fields": "name,mimeType"}).json()
            mime     = meta.get("mimeType", "")
            MAX_BYTES = 100_000

            if mime in EXPORT_FORMATS:
                export_mime = EXPORT_FORMATS[mime]
                r = drive_get(f"/files/{file_id}/export", token,
                               {"mimeType": export_mime})
                content = r.content[:MAX_BYTES].decode("utf-8", errors="replace")
            else:
                r = http.get(
                    f"{DRIVE_BASE}/files/{file_id}",
                    headers={"Authorization": f"Bearer {token}"},
                    params={"alt": "media"},
                )
                r.raise_for_status()
                content = r.content[:MAX_BYTES].decode("utf-8", errors="replace")

            if len(r.content) > MAX_BYTES:
                content += f"\n\n[truncated at 100 KB]"

            return _json({"content": content})

        else:
            return _json({"error": f"unknown action: {action}"}, 400)

    except Exception as exc:  # noqa: BLE001
        return _json({"error": str(exc)}, 500)


def _json(data, status=200):
    return (json.dumps(data), status, {"Content-Type": "application/json",
                                       "Access-Control-Allow-Origin": "*"})
