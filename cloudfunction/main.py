"""
Drive + Calendar relay — Google Cloud Function

Exposes a simple HTTP API so Claude Code can read your Google Drive files
and manage Google Calendar events.
Auth uses a stored OAuth refresh token (set as a Secret Manager secret).

Environment variables (set in Cloud Function config):
  RELAY_SECRET         — shared secret to prevent unauthorized access
  GOOGLE_REFRESH_TOKEN — your OAuth refresh token
  GOOGLE_CLIENT_ID     — from credentials.json
  GOOGLE_CLIENT_SECRET — from credentials.json
  CALENDAR_ID          — calendar to use (default: "primary")
"""

import json
import os
import time
import functions_framework
import requests as http

# ---------------------------------------------------------------------------
# Auth — exchange refresh token for a fresh access token
# ---------------------------------------------------------------------------

TOKEN_URL = "https://oauth2.googleapis.com/token"
DRIVE_BASE = "https://www.googleapis.com/drive/v3"
CALENDAR_BASE = "https://www.googleapis.com/calendar/v3"
SLIDES_BASE = "https://slides.googleapis.com/v1"

EXPORT_FORMATS = {
    "application/vnd.google-apps.document":     "text/plain",
    "application/vnd.google-apps.spreadsheet":  "text/csv",
    "application/vnd.google-apps.presentation": "text/plain",
}

CALENDAR_ID = os.environ.get("CALENDAR_ID", "primary")


def get_access_token() -> str:
    resp = http.post(TOKEN_URL, data={
        "client_id":     os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
        "grant_type":    "refresh_token",
    })
    resp.raise_for_status()
    return resp.json()["access_token"]


def drive_get(path: str, token: str, params: dict = None):
    r = http.get(f"{DRIVE_BASE}{path}", headers={"Authorization": f"Bearer {token}"},
                 params=params or {})
    r.raise_for_status()
    return r


def cal_get(path: str, token: str, params: dict = None):
    r = http.get(f"{CALENDAR_BASE}{path}", headers={"Authorization": f"Bearer {token}"},
                 params=params or {})
    r.raise_for_status()
    return r


def cal_post(path: str, token: str, body: dict):
    r = http.post(f"{CALENDAR_BASE}{path}", headers={"Authorization": f"Bearer {token}"},
                  json=body)
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
            "Access-Control-Allow-Methods": "GET, POST",
            "Access-Control-Allow-Headers": "Content-Type",
        })

    args = request.args

    # Auth check
    if args.get("secret") != os.environ.get("RELAY_SECRET", ""):
        return _json({"error": "forbidden"}, 403)

    action = args.get("action", "list")

    try:
        token = get_access_token()

        # ---- Drive actions ------------------------------------------------

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
                content += "\n\n[truncated at 100 KB]"

            return _json({"content": content})

        # ---- Calendar actions ---------------------------------------------

        elif action == "calendar_list":
            import datetime
            max_res  = min(int(args.get("max", 10)), 100)
            time_min = args.get("timeMin", datetime.datetime.utcnow().isoformat() + "Z")
            data = cal_get(f"/calendars/{CALENDAR_ID}/events", token, {
                "timeMin":      time_min,
                "maxResults":   max_res,
                "singleEvents": "true",
                "orderBy":      "startTime",
                "fields":       "items(id,summary,start,end,location,description,htmlLink)",
            }).json()
            return _json(data.get("items", []))

        elif action == "calendar_create":
            if request.method != "POST":
                return _json({"error": "calendar_create requires POST"}, 405)
            body = request.get_json(silent=True)
            if not body:
                return _json({"error": "JSON body required"}, 400)
            required = {"summary", "start", "end"}
            missing = required - body.keys()
            if missing:
                return _json({"error": f"Missing required fields: {missing}"}, 400)
            event = cal_post(f"/calendars/{CALENDAR_ID}/events", token, body).json()
            return _json(event)

        elif action == "slides_append":
            if request.method != "POST":
                return _json({"error": "slides_append requires POST"}, 405)
            body = request.get_json(silent=True)
            if not body:
                return _json({"error": "JSON body required"}, 400)
            presentation_id = body.get("presentation_id")
            slides_data = body.get("slides")
            if not presentation_id or not slides_data:
                return _json({"error": "presentation_id and slides required"}, 400)

            headers = {"Authorization": f"Bearer {token}"}

            # Step 1 — create blank slides (no placeholder mappings)
            ts = int(time.time() * 1000)
            slide_ids = [f"s{ts}_{i}" for i in range(len(slides_data))]
            create_requests = [
                {
                    "createSlide": {
                        "objectId": sid,
                        "slideLayoutReference": {"predefinedLayout": "TITLE_AND_BODY"},
                    }
                }
                for sid in slide_ids
            ]
            r = http.post(
                f"{SLIDES_BASE}/presentations/{presentation_id}:batchUpdate",
                headers=headers,
                json={"requests": create_requests},
            )
            r.raise_for_status()

            # Step 2 — read back the presentation to get auto-assigned placeholder IDs
            pres = http.get(
                f"{SLIDES_BASE}/presentations/{presentation_id}",
                headers=headers,
                params={"fields": "slides(objectId,pageElements(objectId,shape(placeholder(type))))"},
            )
            pres.raise_for_status()
            slides_index = {s["objectId"]: s for s in pres.json().get("slides", [])}

            # Step 3 — insert text into title + body placeholders
            insert_requests = []
            for sid, slide in zip(slide_ids, slides_data):
                elements = slides_index.get(sid, {}).get("pageElements", [])
                title_id = body_id = None
                for el in elements:
                    ph = el.get("shape", {}).get("placeholder", {})
                    if ph.get("type") == "TITLE":
                        title_id = el["objectId"]
                    elif ph.get("type") in ("BODY", "OBJECT"):
                        body_id = el["objectId"]
                if title_id and slide.get("title"):
                    insert_requests.append({"insertText": {"objectId": title_id, "text": slide["title"]}})
                if body_id and slide.get("body"):
                    insert_requests.append({"insertText": {"objectId": body_id, "text": slide["body"]}})

            if insert_requests:
                r2 = http.post(
                    f"{SLIDES_BASE}/presentations/{presentation_id}:batchUpdate",
                    headers=headers,
                    json={"requests": insert_requests},
                )
                r2.raise_for_status()

            return _json({"status": "ok", "slides_added": len(slides_data)})

        elif action == "slides_export":
            # Export a Google Slides presentation as PPTX, upload back to Drive,
            # and return the download URL.
            file_id = args.get("id")
            if not file_id:
                return _json({"error": "id required"}, 400)

            # 1 — Get presentation name
            meta = drive_get(f"/files/{file_id}", token,
                             {"fields": "name"}).json()
            name = meta.get("name", "presentation") + ".pptx"

            # 2 — Export as PPTX
            pptx_mime = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            r = http.get(
                f"{DRIVE_BASE}/files/{file_id}/export",
                headers={"Authorization": f"Bearer {token}"},
                params={"mimeType": pptx_mime},
            )
            r.raise_for_status()
            pptx_bytes = r.content

            # 3 — Upload PPTX back to Drive
            import io
            metadata = json.dumps({"name": name, "mimeType": pptx_mime}).encode()
            boundary = "gdrive_relay_boundary"
            body = (
                f"--{boundary}\r\n"
                f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
            ).encode() + metadata + (
                f"\r\n--{boundary}\r\n"
                f"Content-Type: {pptx_mime}\r\n\r\n"
            ).encode() + pptx_bytes + f"\r\n--{boundary}--".encode()

            upload = http.post(
                "https://www.googleapis.com/upload/drive/v3/files",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": f"multipart/related; boundary={boundary}",
                },
                params={"uploadType": "multipart", "fields": "id,name,webContentLink,webViewLink"},
                data=body,
            )
            upload.raise_for_status()
            uploaded = upload.json()
            return _json({
                "status": "ok",
                "file_id": uploaded.get("id"),
                "name": uploaded.get("name"),
                "download_url": uploaded.get("webContentLink"),
                "view_url": uploaded.get("webViewLink"),
            })

        else:
            return _json({"error": f"unknown action: {action}"}, 400)

    except Exception as exc:  # noqa: BLE001
        return _json({"error": str(exc)}, 500)


def _json(data, status=200):
    return (json.dumps(data), status, {"Content-Type": "application/json",
                                       "Access-Control-Allow-Origin": "*"})
