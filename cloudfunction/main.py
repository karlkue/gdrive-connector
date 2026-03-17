"""
Drive + Calendar + Gmail + Contacts + Sheets + Tasks relay — Google Cloud Function

Exposes a simple HTTP API so Claude Code can read/write your Google Workspace.
Auth uses a stored OAuth refresh token (set as an env var or Secret Manager).

Environment variables:
  RELAY_SECRET         — shared secret to prevent unauthorized access
  GOOGLE_REFRESH_TOKEN — your OAuth refresh token
  GOOGLE_CLIENT_ID     — from credentials.json
  GOOGLE_CLIENT_SECRET — from credentials.json
  CALENDAR_ID          — calendar to use (default: "primary")
"""

import base64
import json
import os
import time
import functions_framework
import requests as http

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TOKEN_URL      = "https://oauth2.googleapis.com/token"
DRIVE_BASE     = "https://www.googleapis.com/drive/v3"
CALENDAR_BASE  = "https://www.googleapis.com/calendar/v3"
SLIDES_BASE    = "https://slides.googleapis.com/v1"
GMAIL_BASE     = "https://gmail.googleapis.com/gmail/v1"
PEOPLE_BASE    = "https://people.googleapis.com/v1"
SHEETS_BASE    = "https://sheets.googleapis.com/v4"
TASKS_BASE     = "https://tasks.googleapis.com/tasks/v1"
DOCS_BASE      = "https://docs.googleapis.com/v1"

EXPORT_FORMATS = {
    "application/vnd.google-apps.document":     "text/plain",
    "application/vnd.google-apps.spreadsheet":  "text/csv",
    "application/vnd.google-apps.presentation": "text/plain",
}

CALENDAR_ID = os.environ.get("CALENDAR_ID", "primary")


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def get_access_token() -> str:
    resp = http.post(TOKEN_URL, data={
        "client_id":     os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
        "grant_type":    "refresh_token",
    })
    resp.raise_for_status()
    return resp.json()["access_token"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get(url, token, params=None):
    r = http.get(url, headers={"Authorization": f"Bearer {token}"}, params=params or {})
    r.raise_for_status()
    return r


def _post(url, token, body=None, **kwargs):
    r = http.post(url, headers={"Authorization": f"Bearer {token}"}, json=body, **kwargs)
    r.raise_for_status()
    return r


def _patch(url, token, body):
    r = http.patch(url, headers={"Authorization": f"Bearer {token}"}, json=body)
    r.raise_for_status()
    return r


def _delete(url, token):
    r = http.delete(url, headers={"Authorization": f"Bearer {token}"})
    r.raise_for_status()
    return r


def drive_get(path, token, params=None):
    return _get(f"{DRIVE_BASE}{path}", token, params)


def cal_get(path, token, params=None):
    return _get(f"{CALENDAR_BASE}{path}", token, params)


def cal_post(path, token, body):
    return _post(f"{CALENDAR_BASE}{path}", token, body)


# ---------------------------------------------------------------------------
# Cloud Function entry point
# ---------------------------------------------------------------------------

@functions_framework.http
def relay(request):
    # CORS pre-flight
    if request.method == "OPTIONS":
        return ("", 204, {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PATCH, DELETE",
            "Access-Control-Allow-Headers": "Content-Type",
        })

    args = request.args

    if args.get("secret") != os.environ.get("RELAY_SECRET", ""):
        return _json({"error": "forbidden"}, 403)

    action = args.get("action", "list")

    try:
        token = get_access_token()

        # ================================================================
        # DRIVE
        # ================================================================

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

        elif action == "drive_upload":
            # Upload a file to Drive.
            # Body: { "name": "...", "content_base64": "...", "mime": "..." }
            if request.method != "POST":
                return _json({"error": "drive_upload requires POST"}, 405)
            body    = request.get_json(silent=True) or {}
            name    = body.get("name", "Untitled")
            mime    = body.get("mime", "application/octet-stream")
            b64     = body.get("content_base64", "")
            content = base64.b64decode(b64) if b64 else body.get("content", "").encode()
            boundary = "gdrive_upload_boundary"
            metadata = json.dumps({"name": name}).encode()
            multipart = (
                f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n"
            ).encode() + metadata + (
                f"\r\n--{boundary}\r\nContent-Type: {mime}\r\n\r\n"
            ).encode() + content + f"\r\n--{boundary}--".encode()
            upload = http.post(
                "https://www.googleapis.com/upload/drive/v3/files",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": f"multipart/related; boundary={boundary}",
                },
                params={"uploadType": "multipart", "fields": "id,name,webViewLink,webContentLink"},
                data=multipart,
            )
            upload.raise_for_status()
            return _json(upload.json())

        elif action == "drive_delete":
            # Permanently delete a Drive file.
            # Query: ?id=FILE_ID
            file_id = args.get("id")
            if not file_id:
                return _json({"error": "id required"}, 400)
            _delete(f"{DRIVE_BASE}/files/{file_id}", token)
            return _json({"status": "deleted", "id": file_id})

        # ================================================================
        # DOCS
        # ================================================================

        elif action == "doc_create":
            if request.method != "POST":
                return _json({"error": "doc_create requires POST"}, 405)
            body     = request.get_json(silent=True) or {}
            if not body.get("content"):
                return _json({"error": "title and content required"}, 400)
            title    = body.get("title", "Untitled Document")
            content  = body.get("content", "")
            src_mime = body.get("mime", "text/html")
            doc_mime = "application/vnd.google-apps.document"
            boundary = "gdrive_relay_doc_boundary"
            metadata = json.dumps({"name": title, "mimeType": doc_mime}).encode()
            multipart_body = (
                f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n"
            ).encode() + metadata + (
                f"\r\n--{boundary}\r\nContent-Type: {src_mime}\r\n\r\n"
            ).encode() + content.encode("utf-8") + f"\r\n--{boundary}--".encode()
            upload = http.post(
                "https://www.googleapis.com/upload/drive/v3/files",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": f"multipart/related; boundary={boundary}",
                },
                params={"uploadType": "multipart", "fields": "id,name,webViewLink"},
                data=multipart_body,
            )
            upload.raise_for_status()
            uploaded = upload.json()
            return _json({
                "status": "ok",
                "file_id": uploaded.get("id"),
                "name": uploaded.get("name"),
                "url": uploaded.get("webViewLink"),
            })

        elif action == "doc_read":
            # Read a Google Doc as markdown-ish plain text.
            # Query: ?id=DOC_ID
            doc_id = args.get("id")
            if not doc_id:
                return _json({"error": "id required"}, 400)
            r = _get(f"{DOCS_BASE}/documents/{doc_id}", token)
            return _json(r.json())

        elif action == "doc_append":
            # Append text to an existing Google Doc.
            # Body: { "id": "DOC_ID", "text": "..." }
            if request.method != "POST":
                return _json({"error": "doc_append requires POST"}, 405)
            body = request.get_json(silent=True) or {}
            doc_id = body.get("id")
            text   = body.get("text", "")
            if not doc_id:
                return _json({"error": "id required"}, 400)
            # Get current end index
            doc = _get(f"{DOCS_BASE}/documents/{doc_id}", token).json()
            end_index = doc["body"]["content"][-1]["endIndex"] - 1
            requests_payload = [{"insertText": {"location": {"index": end_index}, "text": text}}]
            r = _post(f"{DOCS_BASE}/documents/{doc_id}:batchUpdate", token,
                      {"requests": requests_payload})
            return _json({"status": "ok", "doc_id": doc_id})

        # ================================================================
        # SLIDES
        # ================================================================

        elif action == "slides_create":
            body  = request.get_json(silent=True) or {}
            title = body.get("title", "Untitled Presentation")
            r = http.post(
                f"{SLIDES_BASE}/presentations",
                headers={"Authorization": f"Bearer {token}"},
                json={"title": title},
            )
            r.raise_for_status()
            pres    = r.json()
            pres_id = pres.get("presentationId")
            return _json({
                "status": "ok",
                "presentation_id": pres_id,
                "url": f"https://docs.google.com/presentation/d/{pres_id}/edit",
            })

        elif action == "slides_append":
            if request.method != "POST":
                return _json({"error": "slides_append requires POST"}, 405)
            body = request.get_json(silent=True) or {}
            if not body:
                return _json({"error": "JSON body required"}, 400)
            presentation_id = body.get("presentation_id")
            slides_data     = body.get("slides")
            if not presentation_id or not slides_data:
                return _json({"error": "presentation_id and slides required"}, 400)

            headers = {"Authorization": f"Bearer {token}"}

            ts       = int(time.time() * 1000)
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

            pres = http.get(
                f"{SLIDES_BASE}/presentations/{presentation_id}",
                headers=headers,
                params={"fields": "slides(objectId,pageElements(objectId,shape(placeholder(type))))"},
            )
            pres.raise_for_status()
            slides_index = {s["objectId"]: s for s in pres.json().get("slides", [])}

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
            file_id = args.get("id")
            if not file_id:
                return _json({"error": "id required"}, 400)

            meta = drive_get(f"/files/{file_id}", token, {"fields": "name"}).json()
            name = meta.get("name", "presentation") + ".pptx"

            pptx_mime = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            r = http.get(
                f"{DRIVE_BASE}/files/{file_id}/export",
                headers={"Authorization": f"Bearer {token}"},
                params={"mimeType": pptx_mime},
            )
            r.raise_for_status()
            pptx_bytes = r.content

            import io
            boundary = "gdrive_relay_boundary"
            metadata = json.dumps({"name": name, "mimeType": pptx_mime}).encode()
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

        # ================================================================
        # SHEETS
        # ================================================================

        elif action == "sheets_read":
            # Read values from a Google Sheet.
            # Query: ?id=SPREADSHEET_ID&range=Sheet1!A1:Z100
            sheet_id = args.get("id")
            range_   = args.get("range", "A1:Z1000")
            if not sheet_id:
                return _json({"error": "id required"}, 400)
            r = _get(f"{SHEETS_BASE}/spreadsheets/{sheet_id}/values/{range_}", token)
            return _json(r.json())

        elif action == "sheets_write":
            # Write values to a Google Sheet.
            # Body: { "id": "...", "range": "Sheet1!A1", "values": [[...], [...]] }
            if request.method != "POST":
                return _json({"error": "sheets_write requires POST"}, 405)
            body     = request.get_json(silent=True) or {}
            sheet_id = body.get("id")
            range_   = body.get("range", "A1")
            values   = body.get("values", [])
            if not sheet_id:
                return _json({"error": "id required"}, 400)
            r = http.put(
                f"{SHEETS_BASE}/spreadsheets/{sheet_id}/values/{range_}",
                headers={"Authorization": f"Bearer {token}"},
                json={"values": values, "majorDimension": "ROWS"},
                params={"valueInputOption": "USER_ENTERED"},
            )
            r.raise_for_status()
            return _json(r.json())

        elif action == "sheets_append":
            # Append rows to a Google Sheet.
            # Body: { "id": "...", "range": "Sheet1", "values": [[...]] }
            if request.method != "POST":
                return _json({"error": "sheets_append requires POST"}, 405)
            body     = request.get_json(silent=True) or {}
            sheet_id = body.get("id")
            range_   = body.get("range", "Sheet1")
            values   = body.get("values", [])
            if not sheet_id:
                return _json({"error": "id required"}, 400)
            r = http.post(
                f"{SHEETS_BASE}/spreadsheets/{sheet_id}/values/{range_}:append",
                headers={"Authorization": f"Bearer {token}"},
                json={"values": values, "majorDimension": "ROWS"},
                params={"valueInputOption": "USER_ENTERED", "insertDataOption": "INSERT_ROWS"},
            )
            r.raise_for_status()
            return _json(r.json())

        elif action == "sheets_create":
            # Create a new Google Spreadsheet.
            # Body: { "title": "...", "sheets": ["Sheet1", "Sheet2"] }
            if request.method != "POST":
                return _json({"error": "sheets_create requires POST"}, 405)
            body   = request.get_json(silent=True) or {}
            title  = body.get("title", "Untitled Spreadsheet")
            sheets = body.get("sheets", [])
            payload = {"properties": {"title": title}}
            if sheets:
                payload["sheets"] = [{"properties": {"title": s}} for s in sheets]
            r = _post(f"{SHEETS_BASE}/spreadsheets", token, payload)
            data = r.json()
            return _json({
                "status": "ok",
                "spreadsheet_id": data.get("spreadsheetId"),
                "url": data.get("spreadsheetUrl"),
            })

        # ================================================================
        # CALENDAR
        # ================================================================

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
            missing = {"summary", "start", "end"} - body.keys()
            if missing:
                return _json({"error": f"Missing: {missing}"}, 400)
            event = cal_post(f"/calendars/{CALENDAR_ID}/events", token, body).json()
            return _json(event)

        elif action == "calendar_delete":
            # Delete a calendar event.
            # Query: ?event_id=EVENT_ID
            event_id = args.get("event_id")
            if not event_id:
                return _json({"error": "event_id required"}, 400)
            _delete(f"{CALENDAR_BASE}/calendars/{CALENDAR_ID}/events/{event_id}", token)
            return _json({"status": "deleted", "event_id": event_id})

        elif action == "calendar_update":
            # Update an existing calendar event.
            # Body: { "event_id": "...", ...event fields... }
            if request.method != "POST":
                return _json({"error": "calendar_update requires POST"}, 405)
            body     = request.get_json(silent=True) or {}
            event_id = body.pop("event_id", None)
            if not event_id:
                return _json({"error": "event_id required in body"}, 400)
            r = _patch(f"{CALENDAR_BASE}/calendars/{CALENDAR_ID}/events/{event_id}", token, body)
            return _json(r.json())

        elif action == "calendar_list_calendars":
            # List all calendars in the user's calendar list.
            r = _get(f"{CALENDAR_BASE}/users/me/calendarList", token)
            items = r.json().get("items", [])
            return _json([{"id": c["id"], "summary": c.get("summary"), "primary": c.get("primary", False)} for c in items])

        # ================================================================
        # GMAIL
        # ================================================================

        elif action == "gmail_list":
            # List recent emails.
            # Query: ?max=10&q=GMAIL_SEARCH_QUERY&label=INBOX
            max_res = min(int(args.get("max", 10)), 50)
            q       = args.get("q", "")
            label   = args.get("label", "INBOX")
            params  = {"maxResults": max_res, "labelIds": label}
            if q:
                params["q"] = q
            r    = _get(f"{GMAIL_BASE}/users/me/messages", token, params)
            msgs = r.json().get("messages", [])
            # Fetch snippet + headers for each
            result = []
            for m in msgs:
                detail = _get(f"{GMAIL_BASE}/users/me/messages/{m['id']}", token,
                              {"format": "metadata",
                               "metadataHeaders": ["Subject", "From", "Date"]}).json()
                headers = {h["name"]: h["value"] for h in detail.get("payload", {}).get("headers", [])}
                result.append({
                    "id":      m["id"],
                    "subject": headers.get("Subject", ""),
                    "from":    headers.get("From", ""),
                    "date":    headers.get("Date", ""),
                    "snippet": detail.get("snippet", ""),
                })
            return _json(result)

        elif action == "gmail_read":
            # Read full email content.
            # Query: ?id=MESSAGE_ID
            msg_id = args.get("id")
            if not msg_id:
                return _json({"error": "id required"}, 400)
            r    = _get(f"{GMAIL_BASE}/users/me/messages/{msg_id}", token, {"format": "full"})
            data = r.json()

            def _decode_part(part):
                body_data = part.get("body", {}).get("data", "")
                if body_data:
                    return base64.urlsafe_b64decode(body_data + "==").decode("utf-8", errors="replace")
                return ""

            def _extract_body(payload):
                mime = payload.get("mimeType", "")
                if mime == "text/plain":
                    return _decode_part(payload)
                if mime == "text/html":
                    return _decode_part(payload)
                for part in payload.get("parts", []):
                    text = _extract_body(part)
                    if text:
                        return text
                return ""

            headers = {h["name"]: h["value"] for h in data.get("payload", {}).get("headers", [])}
            body    = _extract_body(data.get("payload", {}))
            MAX_BODY = 50_000
            if len(body) > MAX_BODY:
                body = body[:MAX_BODY] + "\n\n[truncated]"
            return _json({
                "id":      msg_id,
                "subject": headers.get("Subject", ""),
                "from":    headers.get("From", ""),
                "to":      headers.get("To", ""),
                "date":    headers.get("Date", ""),
                "body":    body,
            })

        elif action == "gmail_send":
            # Send an email.
            # Body: { "to": "...", "subject": "...", "body": "...", "cc": "...", "bcc": "..." }
            if request.method != "POST":
                return _json({"error": "gmail_send requires POST"}, 405)
            body = request.get_json(silent=True) or {}
            to      = body.get("to", "")
            subject = body.get("subject", "")
            text    = body.get("body", "")
            cc      = body.get("cc", "")
            bcc     = body.get("bcc", "")
            if not to:
                return _json({"error": "to required"}, 400)
            raw_lines = [f"To: {to}", f"Subject: {subject}"]
            if cc:
                raw_lines.append(f"Cc: {cc}")
            if bcc:
                raw_lines.append(f"Bcc: {bcc}")
            raw_lines += ["Content-Type: text/plain; charset=utf-8", "", text]
            raw = "\r\n".join(raw_lines)
            encoded = base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")
            r = _post(f"{GMAIL_BASE}/users/me/messages/send", token, {"raw": encoded})
            return _json({"status": "sent", "id": r.json().get("id")})

        elif action == "gmail_reply":
            # Reply to an email thread.
            # Body: { "thread_id": "...", "message_id": "...", "to": "...", "subject": "Re: ...", "body": "..." }
            if request.method != "POST":
                return _json({"error": "gmail_reply requires POST"}, 405)
            body       = request.get_json(silent=True) or {}
            thread_id  = body.get("thread_id", "")
            message_id = body.get("message_id", "")
            to         = body.get("to", "")
            subject    = body.get("subject", "")
            text       = body.get("body", "")
            if not (thread_id and to):
                return _json({"error": "thread_id and to required"}, 400)
            raw_lines = [
                f"To: {to}",
                f"Subject: {subject}",
                f"In-Reply-To: {message_id}",
                f"References: {message_id}",
                "Content-Type: text/plain; charset=utf-8",
                "",
                text,
            ]
            raw     = "\r\n".join(raw_lines)
            encoded = base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")
            r = _post(f"{GMAIL_BASE}/users/me/messages/send", token,
                      {"raw": encoded, "threadId": thread_id})
            return _json({"status": "sent", "id": r.json().get("id")})

        elif action == "gmail_trash":
            # Move a message to trash.
            # Query: ?id=MESSAGE_ID
            msg_id = args.get("id")
            if not msg_id:
                return _json({"error": "id required"}, 400)
            r = _post(f"{GMAIL_BASE}/users/me/messages/{msg_id}/trash", token)
            return _json({"status": "trashed", "id": msg_id})

        elif action == "gmail_labels":
            # List all Gmail labels.
            r = _get(f"{GMAIL_BASE}/users/me/labels", token)
            return _json(r.json().get("labels", []))

        # ================================================================
        # CONTACTS (People API)
        # ================================================================

        elif action == "contacts_list":
            # List contacts.
            # Query: ?max=50&page_token=TOKEN
            max_res    = min(int(args.get("max", 50)), 1000)
            page_token = args.get("page_token", "")
            params = {
                "resourceName": "people/me",
                "pageSize": max_res,
                "personFields": "names,emailAddresses,phoneNumbers,organizations,addresses,birthdays",
            }
            if page_token:
                params["pageToken"] = page_token
            r    = _get(f"{PEOPLE_BASE}/people/me/connections", token, params)
            data = r.json()
            return _json({
                "contacts": data.get("connections", []),
                "next_page_token": data.get("nextPageToken"),
                "total": data.get("totalItems"),
            })

        elif action == "contacts_search":
            # Search contacts by name or email.
            # Query: ?q=SEARCH_TERM&max=10
            query   = args.get("q", "")
            max_res = min(int(args.get("max", 10)), 30)
            if not query:
                return _json({"error": "q required"}, 400)
            r = _get(f"{PEOPLE_BASE}/people:searchContacts", token, {
                "query": query,
                "pageSize": max_res,
                "readMask": "names,emailAddresses,phoneNumbers,organizations",
            })
            return _json(r.json().get("results", []))

        elif action == "contacts_get":
            # Get a single contact by resource name.
            # Query: ?resource=people/PERSON_ID
            resource = args.get("resource")
            if not resource:
                return _json({"error": "resource required (e.g. people/c12345)"}, 400)
            r = _get(f"{PEOPLE_BASE}/{resource}", token, {
                "personFields": "names,emailAddresses,phoneNumbers,organizations,addresses,birthdays,biographies,urls,relations",
            })
            return _json(r.json())

        elif action == "contacts_create":
            # Create a new contact.
            # Body: { "name": "...", "email": "...", "phone": "...", "company": "..." }
            if request.method != "POST":
                return _json({"error": "contacts_create requires POST"}, 405)
            body    = request.get_json(silent=True) or {}
            person  = {}
            if body.get("name"):
                person["names"] = [{"displayName": body["name"],
                                     "givenName": body.get("first_name", body["name"]),
                                     "familyName": body.get("last_name", "")}]
            if body.get("email"):
                person["emailAddresses"] = [{"value": body["email"]}]
            if body.get("phone"):
                person["phoneNumbers"] = [{"value": body["phone"]}]
            if body.get("company"):
                person["organizations"] = [{"name": body["company"], "title": body.get("title", "")}]
            r = _post(f"{PEOPLE_BASE}/people:createContact", token, person)
            return _json(r.json())

        elif action == "contacts_update":
            # Update an existing contact.
            # Body: { "resource": "people/cXXX", "name": "...", "email": "...", ... }
            if request.method != "POST":
                return _json({"error": "contacts_update requires POST"}, 405)
            body     = request.get_json(silent=True) or {}
            resource = body.get("resource")
            if not resource:
                return _json({"error": "resource required"}, 400)
            # Get current etag
            current = _get(f"{PEOPLE_BASE}/{resource}", token,
                           {"personFields": "names,emailAddresses,phoneNumbers,organizations"}).json()
            etag    = current.get("etag", "")
            person  = {"etag": etag, "resourceName": resource}
            update_fields = []
            if "name" in body:
                person["names"] = [{"displayName": body["name"]}]
                update_fields.append("names")
            if "email" in body:
                person["emailAddresses"] = [{"value": body["email"]}]
                update_fields.append("emailAddresses")
            if "phone" in body:
                person["phoneNumbers"] = [{"value": body["phone"]}]
                update_fields.append("phoneNumbers")
            if "company" in body:
                person["organizations"] = [{"name": body["company"]}]
                update_fields.append("organizations")
            r = http.patch(
                f"{PEOPLE_BASE}/{resource}:updateContact",
                headers={"Authorization": f"Bearer {token}"},
                json=person,
                params={"updatePersonFields": ",".join(update_fields)},
            )
            r.raise_for_status()
            return _json(r.json())

        # ================================================================
        # TASKS
        # ================================================================

        elif action == "tasks_list":
            # List task lists or tasks in a list.
            # Query: ?tasklist_id=TASKLIST_ID (omit for all task lists)
            tasklist_id = args.get("tasklist_id")
            if not tasklist_id:
                r = _get(f"{TASKS_BASE}/users/@me/lists", token, {"maxResults": 100})
                return _json(r.json().get("items", []))
            max_res = min(int(args.get("max", 100)), 100)
            show_completed = args.get("show_completed", "false")
            r = _get(f"{TASKS_BASE}/lists/{tasklist_id}/tasks", token, {
                "maxResults": max_res,
                "showCompleted": show_completed,
                "showHidden": "false",
            })
            return _json(r.json().get("items", []))

        elif action == "tasks_create":
            # Create a task.
            # Body: { "tasklist_id": "...", "title": "...", "notes": "...", "due": "RFC3339" }
            if request.method != "POST":
                return _json({"error": "tasks_create requires POST"}, 405)
            body        = request.get_json(silent=True) or {}
            tasklist_id = body.get("tasklist_id", "@default")
            task        = {"title": body.get("title", "Untitled Task")}
            if body.get("notes"):
                task["notes"] = body["notes"]
            if body.get("due"):
                task["due"] = body["due"]
            r = _post(f"{TASKS_BASE}/lists/{tasklist_id}/tasks", token, task)
            return _json(r.json())

        elif action == "tasks_complete":
            # Mark a task as completed.
            # Body: { "tasklist_id": "...", "task_id": "..." }
            if request.method != "POST":
                return _json({"error": "tasks_complete requires POST"}, 405)
            body        = request.get_json(silent=True) or {}
            tasklist_id = body.get("tasklist_id", "@default")
            task_id     = body.get("task_id")
            if not task_id:
                return _json({"error": "task_id required"}, 400)
            r = _patch(
                f"{TASKS_BASE}/lists/{tasklist_id}/tasks/{task_id}",
                token,
                {"status": "completed"},
            )
            return _json(r.json())

        elif action == "tasks_delete":
            # Delete a task.
            # Query: ?tasklist_id=...&task_id=...
            tasklist_id = args.get("tasklist_id", "@default")
            task_id     = args.get("task_id")
            if not task_id:
                return _json({"error": "task_id required"}, 400)
            _delete(f"{TASKS_BASE}/lists/{tasklist_id}/tasks/{task_id}", token)
            return _json({"status": "deleted", "task_id": task_id})

        # ================================================================
        # PEOPLE / DIRECTORY
        # ================================================================

        elif action == "directory_search":
            # Search the Google Workspace directory (org contacts).
            # Query: ?q=SEARCH_TERM&max=10
            query   = args.get("q", "")
            max_res = min(int(args.get("max", 10)), 30)
            r = _get(f"{PEOPLE_BASE}/people:searchDirectoryPeople", token, {
                "query": query,
                "pageSize": max_res,
                "readMask": "names,emailAddresses,phoneNumbers,organizations,photos",
                "sources": "DIRECTORY_SOURCE_TYPE_DOMAIN_PROFILE",
            })
            return _json(r.json().get("people", []))

        elif action == "profile":
            # Get the authenticated user's profile.
            r = _get(f"{PEOPLE_BASE}/people/me", token, {
                "personFields": "names,emailAddresses,phoneNumbers,organizations,photos,coverPhotos",
            })
            return _json(r.json())

        else:
            return _json({"error": f"unknown action: {action}"}, 400)

    except Exception as exc:  # noqa: BLE001
        return _json({"error": str(exc)}, 500)


def _json(data, status=200):
    return (json.dumps(data), status, {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
    })
