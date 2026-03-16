"""
Google Calendar integration.

Supports two backends, selected by environment variable:

  CALENDAR_BACKEND=relay   (default when RELAY_URL is set)
    Calls the same relay deployed in your Google account (Cloud Function or
    Apps Script). No local credentials needed.

  CALENDAR_BACKEND=sdk     (default when RELAY_URL is not set)
    Uses the Google Calendar Python SDK with OAuth2 (credentials.json / token.json).
    Requires a browser for first-time auth. Does NOT work from Claude Code's
    sandboxed environment due to proxy restrictions on Google APIs.

Environment variables:
  RELAY_URL        — base URL of your relay (shared with Drive)
  RELAY_SECRET     — shared secret
  CALENDAR_ID      — which calendar to use (default: "primary")
"""

import os
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

RELAY_URL = os.getenv("RELAY_URL", "")
RELAY_SECRET = os.getenv("RELAY_SECRET", "")
CALENDAR_BACKEND = os.getenv("CALENDAR_BACKEND", "relay" if RELAY_URL else "sdk")
CALENDAR_ID = os.getenv("CALENDAR_ID", "primary")


# ---------------------------------------------------------------------------
# Relay backend
# ---------------------------------------------------------------------------

def _relay_get(params: dict) -> dict | list:
    if not RELAY_URL:
        raise RuntimeError("RELAY_URL is not set. Add it to .env — see README for setup.")
    params["secret"] = RELAY_SECRET
    resp = requests.get(RELAY_URL, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _relay_post(params: dict, body: dict) -> dict:
    if not RELAY_URL:
        raise RuntimeError("RELAY_URL is not set. Add it to .env — see README for setup.")
    params["secret"] = RELAY_SECRET
    resp = requests.post(RELAY_URL, params=params, json=body, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _relay_list_events(max_results: int = 10, time_min: str = None) -> list[dict]:
    params = {"action": "calendar_list", "max": max_results}
    if time_min:
        params["timeMin"] = time_min
    return _relay_get(params)


def _relay_create_event(
    summary: str,
    start: str,
    end: str,
    timezone: str = "UTC",
    description: str = "",
    location: str = "",
) -> dict:
    body = {
        "summary": summary,
        "start": {"dateTime": start, "timeZone": timezone},
        "end": {"dateTime": end, "timeZone": timezone},
    }
    if description:
        body["description"] = description
    if location:
        body["location"] = location
    return _relay_post({"action": "calendar_create"}, body)


# ---------------------------------------------------------------------------
# SDK backend
# ---------------------------------------------------------------------------

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


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
            from urllib.parse import parse_qs, urlparse
            code = parse_qs(urlparse(redirect).query)["code"][0]
            flow.fetch_token(code=code)
            creds = flow.credentials
        with open(token_path, "w") as f:
            f.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def _sdk_list_events(max_results: int = 10, time_min: str = None) -> list[dict]:
    import datetime

    service = _get_sdk_service()
    if not time_min:
        time_min = datetime.datetime.utcnow().isoformat() + "Z"
    result = (
        service.events()
        .list(
            calendarId=CALENDAR_ID,
            timeMin=time_min,
            maxResults=max(1, min(100, max_results)),
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    return result.get("items", [])


def _sdk_create_event(
    summary: str,
    start: str,
    end: str,
    timezone: str = "UTC",
    description: str = "",
    location: str = "",
) -> dict:
    service = _get_sdk_service()
    event = {
        "summary": summary,
        "start": {"dateTime": start, "timeZone": timezone},
        "end": {"dateTime": end, "timeZone": timezone},
    }
    if description:
        event["description"] = description
    if location:
        event["location"] = location
    return service.events().insert(calendarId=CALENDAR_ID, body=event).execute()


# ---------------------------------------------------------------------------
# Public API — dispatches to the active backend
# ---------------------------------------------------------------------------

def list_events(max_results: int = 10, time_min: str = None) -> list[dict]:
    if CALENDAR_BACKEND == "relay":
        return _relay_list_events(max_results, time_min)
    return _sdk_list_events(max_results, time_min)


def create_event(
    summary: str,
    start: str,
    end: str,
    timezone: str = "UTC",
    description: str = "",
    location: str = "",
) -> dict:
    if CALENDAR_BACKEND == "relay":
        return _relay_create_event(summary, start, end, timezone, description, location)
    return _sdk_create_event(summary, start, end, timezone, description, location)


# ---------------------------------------------------------------------------
# Tool definitions for the Claude API
# ---------------------------------------------------------------------------

CALENDAR_TOOLS = [
    {
        "name": "calendar_list_events",
        "description": (
            "List upcoming events from the user's Google Calendar. "
            "Returns event titles, start/end times, and event IDs. "
            "Defaults to events starting from now."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of events to return (1–100). Default 10.",
                },
                "time_min": {
                    "type": "string",
                    "description": (
                        "Lower bound for event start time in RFC3339 format "
                        "(e.g. '2026-03-16T00:00:00+08:00'). Defaults to now."
                    ),
                },
            },
        },
    },
    {
        "name": "calendar_create_event",
        "description": "Create a new event in the user's Google Calendar.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "Title/name of the event.",
                },
                "start": {
                    "type": "string",
                    "description": "Start datetime in RFC3339 format (e.g. '2026-03-18T08:00:00+08:00').",
                },
                "end": {
                    "type": "string",
                    "description": "End datetime in RFC3339 format (e.g. '2026-03-18T09:00:00+08:00'). If not specified, default to 1 hour after start.",
                },
                "timezone": {
                    "type": "string",
                    "description": "IANA timezone name (e.g. 'Asia/Manila'). Default 'UTC'.",
                },
                "description": {
                    "type": "string",
                    "description": "Optional event description/notes.",
                },
                "location": {
                    "type": "string",
                    "description": "Optional event location.",
                },
            },
            "required": ["summary", "start", "end"],
        },
    },
]


def execute_calendar_tool(tool_name: str, tool_input: dict) -> str:
    try:
        if tool_name == "calendar_list_events":
            events = list_events(
                max_results=tool_input.get("max_results", 10),
                time_min=tool_input.get("time_min"),
            )
            if not events:
                return "No upcoming events found."
            lines = ["Upcoming events:\n"]
            for e in events:
                start = e.get("start", {}).get("dateTime") or e.get("start", {}).get("date", "?")
                end = e.get("end", {}).get("dateTime") or e.get("end", {}).get("date", "?")
                lines.append(
                    f"• {e.get('summary', '(no title)')}\n"
                    f"  Start: {start}\n"
                    f"  End:   {end}\n"
                    f"  ID:    {e.get('id', '?')}"
                )
            return "\n".join(lines)

        elif tool_name == "calendar_create_event":
            event = create_event(
                summary=tool_input["summary"],
                start=tool_input["start"],
                end=tool_input["end"],
                timezone=tool_input.get("timezone", "UTC"),
                description=tool_input.get("description", ""),
                location=tool_input.get("location", ""),
            )
            link = event.get("htmlLink", "")
            return (
                f"Event created: {event.get('summary', '?')}\n"
                f"  Start: {event.get('start', {}).get('dateTime', '?')}\n"
                f"  End:   {event.get('end', {}).get('dateTime', '?')}\n"
                f"  Link:  {link}"
            )

        else:
            return f"Unknown calendar tool: {tool_name}"

    except Exception as exc:  # noqa: BLE001
        return f"Calendar error: {exc}"
