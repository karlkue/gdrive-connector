"""
Google Drive integration.

Supports two backends, selected by environment variable:

  DRIVE_BACKEND=relay   (default when RELAY_URL is set)
    Calls a Google Apps Script web app relay deployed in your Google account.
    No local credentials needed. Works from any network including Claude Code.

  DRIVE_BACKEND=sdk     (default when RELAY_URL is not set)
    Uses the Google Drive Python SDK with OAuth2 (credentials.json / token.json).
    Requires a browser for first-time auth. Does NOT work from Claude Code's
    sandboxed environment due to proxy restrictions on Google APIs.
"""

import io
import json
import os
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---------------------------------------------------------------------------
# Backend selection
# ---------------------------------------------------------------------------

RELAY_URL = os.getenv("RELAY_URL", "")
RELAY_SECRET = os.getenv("RELAY_SECRET", "")
DRIVE_BACKEND = os.getenv("DRIVE_BACKEND", "relay" if RELAY_URL else "sdk")


# ---------------------------------------------------------------------------
# Relay backend (Apps Script web app)
# ---------------------------------------------------------------------------

def _relay(params: dict) -> dict | list:
    if not RELAY_URL:
        raise RuntimeError(
            "RELAY_URL is not set. Add it to .env — see README for setup."
        )
    params["secret"] = RELAY_SECRET
    resp = requests.get(RELAY_URL, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _relay_list(query: str = "", max_results: int = 20) -> list[dict]:
    return _relay({"action": "list", "query": query, "max": max_results})


def _relay_search(query: str, max_results: int = 10) -> list[dict]:
    return _relay({"action": "search", "query": query, "max": max_results})


def _relay_read(file_id: str) -> str:
    result = _relay({"action": "read", "id": file_id})
    return result.get("content", "")


# ---------------------------------------------------------------------------
# SDK backend (Google Drive Python SDK)
# ---------------------------------------------------------------------------

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
]

EXPORT_FORMATS = {
    "application/vnd.google-apps.document": ("text/plain", ".txt"),
    "application/vnd.google-apps.spreadsheet": ("text/csv", ".csv"),
    "application/vnd.google-apps.presentation": ("text/plain", ".txt"),
}


def _get_sdk_service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
    token_path = os.getenv("GOOGLE_TOKEN_PATH", "token.json")

    creds = None
    if Path(token_path).exists():
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not Path(creds_path).exists():
                raise FileNotFoundError(
                    f"Google credentials file not found at '{creds_path}'. "
                    "See README for setup instructions."
                )
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            flow.redirect_uri = "http://localhost:8888"
            auth_url, _ = flow.authorization_url(access_type="offline", prompt="consent")
            print("\nOpen this URL in your browser, approve, then paste the redirect URL:")
            print(f"\n{auth_url}\n")
            redirect = input("Paste the full redirect URL: ").strip()
            from urllib.parse import urlparse, parse_qs
            code = parse_qs(urlparse(redirect).query)["code"][0]
            flow.fetch_token(code=code)
            creds = flow.credentials
        with open(token_path, "w") as f:
            f.write(creds.to_json())

    return build("drive", "v3", credentials=creds)


def _sdk_list(query: str = "", max_results: int = 20) -> list[dict]:
    from googleapiclient.http import MediaIoBaseDownload
    service = _get_sdk_service()
    base_query = "trashed = false"
    full_query = f"{base_query} and ({query})" if query.strip() else base_query
    results = (
        service.files()
        .list(
            q=full_query,
            pageSize=max(1, min(100, max_results)),
            fields="files(id, name, mimeType, modifiedTime, size, webViewLink)",
            orderBy="modifiedTime desc",
        )
        .execute()
    )
    return results.get("files", [])


def _sdk_search(query: str, max_results: int = 10) -> list[dict]:
    return _sdk_list(
        query=f"fullText contains '{query.replace(chr(39), '')}'",
        max_results=max_results,
    )


def _sdk_read(file_id: str) -> str:
    from googleapiclient.http import MediaIoBaseDownload
    service = _get_sdk_service()
    meta = service.files().get(fileId=file_id, fields="name, mimeType").execute()
    mime_type = meta.get("mimeType", "")
    name = meta.get("name", file_id)
    MAX_BYTES = 100_000

    if mime_type in EXPORT_FORMATS:
        export_mime, _ = EXPORT_FORMATS[mime_type]
        request = service.files().export_media(fileId=file_id, mimeType=export_mime)
    else:
        request = service.files().get_media(fileId=file_id)

    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()

    content_bytes = buffer.getvalue()
    content = content_bytes[:MAX_BYTES].decode("utf-8", errors="replace")
    if len(content_bytes) > MAX_BYTES:
        content += f"\n\n[truncated at 100 KB — '{name}' is larger]"
    return content


# ---------------------------------------------------------------------------
# Public API — dispatches to the active backend
# ---------------------------------------------------------------------------

def list_files(query: str = "", max_results: int = 20) -> list[dict]:
    if DRIVE_BACKEND == "relay":
        return _relay_list(query, max_results)
    return _sdk_list(query, max_results)


def read_file(file_id: str) -> str:
    if DRIVE_BACKEND == "relay":
        return _relay_read(file_id)
    return _sdk_read(file_id)


def search_files(query: str, max_results: int = 10) -> list[dict]:
    if DRIVE_BACKEND == "relay":
        return _relay_search(query, max_results)
    return _sdk_search(query, max_results)


# ---------------------------------------------------------------------------
# Tool definitions for the Claude API
# ---------------------------------------------------------------------------

DRIVE_TOOLS = [
    {
        "name": "drive_list_files",
        "description": (
            "List files in the user's Google Drive. "
            "Returns file names, IDs, MIME types, and last-modified times. "
            "Supports Drive query syntax in the 'query' parameter "
            "(e.g. \"name contains 'budget'\" or \"mimeType = 'application/pdf'\")."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Optional Drive query to filter files.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of files to return (1–100). Default 20.",
                },
            },
        },
    },
    {
        "name": "drive_read_file",
        "description": (
            "Read the text content of a specific Google Drive file by its file ID. "
            "Works with Google Docs, Sheets, Slides, and plain-text files. "
            "Returns the file content as text (up to 100 KB)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "The Google Drive file ID.",
                }
            },
            "required": ["file_id"],
        },
    },
    {
        "name": "drive_search_files",
        "description": (
            "Full-text search across the user's Google Drive — searches both "
            "file names and file contents."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search terms to look for in file names and contents.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (1–100). Default 10.",
                },
            },
            "required": ["query"],
        },
    },
]


def execute_drive_tool(tool_name: str, tool_input: dict) -> str:
    try:
        if tool_name == "drive_list_files":
            files = list_files(
                query=tool_input.get("query", ""),
                max_results=tool_input.get("max_results", 20),
            )
            if not files:
                return "No files found matching that query."
            lines = ["Found files:\n"]
            for f in files:
                size = f.get("size", "—")
                size_str = f"{int(size):,} bytes" if size and size != "—" else "Google Doc"
                lines.append(
                    f"• {f['name']}\n"
                    f"  ID: {f['id']}\n"
                    f"  Type: {f['mimeType']}\n"
                    f"  Modified: {f.get('modifiedTime', 'unknown')}\n"
                    f"  Size: {size_str}"
                )
            return "\n".join(lines)

        elif tool_name == "drive_read_file":
            return read_file(tool_input["file_id"])

        elif tool_name == "drive_search_files":
            files = search_files(
                query=tool_input["query"],
                max_results=tool_input.get("max_results", 10),
            )
            if not files:
                return f"No files found matching '{tool_input['query']}'."
            lines = [f"Search results for '{tool_input['query']}':\n"]
            for f in files:
                lines.append(f"• {f['name']}  (ID: {f['id']})  [{f['mimeType']}]")
            return "\n".join(lines)

        else:
            return f"Unknown tool: {tool_name}"

    except Exception as exc:  # noqa: BLE001
        return f"Drive error: {exc}"
