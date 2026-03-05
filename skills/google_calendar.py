"""
Google Calendar skill — read and manage events via the Google Calendar API.
Requires: GOOGLE_CREDENTIALS_JSON (path to service account JSON or JSON content)
Optional: GOOGLE_CALENDAR_ID (default: "primary")
"""
import os
import json
import time
import datetime

import requests

SKILL_INFO = {
    "name": "google_calendar",
    "description": "Read and manage Google Calendar events",
    "version": "1.0",
    "icon": "📅",
    "author": "ninoclaw",
    "requires_key": True,
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "gcal_list_events",
            "description": "List upcoming Google Calendar events",
            "parameters": {
                "type": "object",
                "properties": {
                    "days_ahead": {
                        "type": "integer",
                        "description": "How many days ahead to look (default: 7)",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of events to return (default: 10)",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "gcal_create_event",
            "description": "Create a new Google Calendar event",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Event title"},
                    "start_time": {
                        "type": "string",
                        "description": "Start time in ISO format or natural language like 'tomorrow 3pm'",
                    },
                    "end_time": {
                        "type": "string",
                        "description": "End time in ISO format or natural language (optional, defaults to 1 hour after start)",
                    },
                    "description": {"type": "string", "description": "Event description (optional)"},
                    "location": {"type": "string", "description": "Event location (optional)"},
                },
                "required": ["title", "start_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "gcal_delete_event",
            "description": "Delete a Google Calendar event by its ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_id": {"type": "string", "description": "The event ID to delete"},
                },
                "required": ["event_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "gcal_find_event",
            "description": "Find Google Calendar events by title or keyword",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search keyword or event title"},
                    "days_ahead": {
                        "type": "integer",
                        "description": "How many days ahead to search (default: 30)",
                    },
                },
                "required": ["query"],
            },
        },
    },
]

_SCOPES = "https://www.googleapis.com/auth/calendar"
_TOKEN_URI = "https://oauth2.googleapis.com/token"
_API_BASE = "https://www.googleapis.com/calendar/v3"

# Module-level token cache
_access_token = None
_token_expiry = 0.0


# ---------------------------------------------------------------------------
# Credential loading
# ---------------------------------------------------------------------------

def _load_credentials():
    """Return the service account credentials dict, or None if not configured."""
    raw = os.getenv("GOOGLE_CREDENTIALS_JSON", "")
    if not raw:
        return None
    # Could be a file path or raw JSON content
    if raw.strip().startswith("{"):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None
    if os.path.isfile(raw):
        try:
            with open(raw) as f:
                return json.load(f)
        except Exception:
            return None
    return None


def _setup_instructions():
    return (
        "⚙️ **Google Calendar setup required**\n\n"
        "Set the following environment variable:\n"
        "  • GOOGLE_CREDENTIALS_JSON — path to your service account JSON file\n"
        "    OR the raw JSON content of the service account key\n"
        "  • GOOGLE_CALENDAR_ID — (optional) calendar ID, default is 'primary'\n\n"
        "**How to create a service account:**\n"
        "1. Go to https://console.cloud.google.com/\n"
        "2. Enable the Google Calendar API for your project\n"
        "3. IAM & Admin → Service Accounts → Create Service Account\n"
        "4. Create a JSON key and download it\n"
        "5. Share your calendar with the service account email\n"
        "   (Settings → Share with specific people → add service account email)\n"
        "6. Set GOOGLE_CREDENTIALS_JSON to the path of the downloaded JSON file"
    )


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

def _get_access_token():
    global _access_token, _token_expiry
    if _access_token and time.time() < _token_expiry - 30:
        return _access_token

    creds = _load_credentials()
    if not creds:
        raise RuntimeError("No credentials")

    # Try google-auth library first
    try:
        from google.oauth2 import service_account
        import google.auth.transport.requests as ga_requests

        sa_creds = service_account.Credentials.from_service_account_info(
            creds, scopes=[_SCOPES]
        )
        sa_creds.refresh(ga_requests.Request())
        _access_token = sa_creds.token
        _token_expiry = sa_creds.expiry.timestamp() if sa_creds.expiry else time.time() + 3600
        return _access_token
    except ImportError:
        pass

    # Fallback: manual JWT via PyJWT or jose
    return _get_access_token_manual_jwt(creds)


def _get_access_token_manual_jwt(creds):
    global _access_token, _token_expiry

    private_key = creds.get("private_key", "")
    client_email = creds.get("client_email", "")
    if not private_key or not client_email:
        raise RuntimeError("Invalid credentials JSON (missing private_key or client_email)")

    now = int(time.time())
    payload = {
        "iss": client_email,
        "sub": client_email,
        "aud": _TOKEN_URI,
        "iat": now,
        "exp": now + 3600,
        "scope": _SCOPES,
    }

    # Try PyJWT
    jwt_token = None
    try:
        import jwt as pyjwt
        jwt_token = pyjwt.encode(payload, private_key, algorithm="RS256")
        if isinstance(jwt_token, bytes):
            jwt_token = jwt_token.decode("utf-8")
    except ImportError:
        pass

    if jwt_token is None:
        # Try python-jose
        try:
            from jose import jwt as jose_jwt
            jwt_token = jose_jwt.encode(payload, private_key, algorithm="RS256")
        except ImportError:
            pass

    if jwt_token is None:
        raise RuntimeError(
            "No JWT library available. Install one: pip install PyJWT cryptography"
        )

    resp = requests.post(
        _TOKEN_URI,
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": jwt_token,
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    _access_token = data["access_token"]
    _token_expiry = time.time() + data.get("expires_in", 3600)
    return _access_token


def _headers():
    return {"Authorization": f"Bearer {_get_access_token()}"}


def _calendar_id():
    return os.getenv("GOOGLE_CALENDAR_ID", "primary")


# ---------------------------------------------------------------------------
# Time parsing
# ---------------------------------------------------------------------------

def _parse_time(value):
    """Parse a time string into a datetime. Returns naive local datetime."""
    if not value:
        return None

    # Try dateutil first
    try:
        from dateutil import parser as du_parser
        return du_parser.parse(value)
    except (ImportError, ValueError):
        pass

    # Simple ISO fallback
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(value, fmt)
        except ValueError:
            pass

    # Natural language patterns
    value_lower = value.strip().lower()
    now = datetime.datetime.now()

    if value_lower.startswith("tomorrow"):
        base = now + datetime.timedelta(days=1)
        rest = value_lower.replace("tomorrow", "").strip()
    elif value_lower.startswith("today"):
        base = now
        rest = value_lower.replace("today", "").strip()
    else:
        base = now
        rest = value_lower

    if rest:
        # Try to parse time portion like "3pm", "15:00", "3:30pm"
        import re
        m = re.match(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", rest)
        if m:
            hour = int(m.group(1))
            minute = int(m.group(2)) if m.group(2) else 0
            ampm = m.group(3)
            if ampm == "pm" and hour < 12:
                hour += 12
            elif ampm == "am" and hour == 12:
                hour = 0
            return base.replace(hour=hour, minute=minute, second=0, microsecond=0)

    return base


def _to_rfc3339(dt):
    """Convert datetime to RFC3339 string with local timezone offset."""
    if dt.tzinfo is None:
        # Add local UTC offset
        utc_offset = datetime.datetime.now() - datetime.datetime.utcnow()
        total_seconds = int(utc_offset.total_seconds())
        sign = "+" if total_seconds >= 0 else "-"
        total_seconds = abs(total_seconds)
        h, m = divmod(total_seconds // 60, 60)
        tz_str = f"{sign}{h:02d}:{m:02d}"
        return dt.strftime("%Y-%m-%dT%H:%M:%S") + tz_str
    return dt.isoformat()


# ---------------------------------------------------------------------------
# Event formatting
# ---------------------------------------------------------------------------

def _fmt_event(event):
    title = event.get("summary", "(No title)")
    start_raw = event.get("start", {})
    end_raw = event.get("end", {})
    location = event.get("location", "")
    event_id = event.get("id", "")

    def _parse_dt(raw):
        val = raw.get("dateTime") or raw.get("date", "")
        try:
            from dateutil import parser as du
            return du.parse(val)
        except Exception:
            return None

    def _fmt_dt(dt, all_day=False):
        if dt is None:
            return "?"
        if all_day:
            return dt.strftime("%a %-d %b")
        return dt.strftime("%a %-d %b, %-I:%M %p")

    all_day = "date" in start_raw and "dateTime" not in start_raw
    start_dt = _parse_dt(start_raw)
    end_dt = _parse_dt(end_raw)

    start_str = _fmt_dt(start_dt, all_day)
    end_str = _fmt_dt(end_dt, all_day) if not all_day else ""

    time_str = start_str
    if end_str and not all_day:
        # Show end time without date if same day
        if start_dt and end_dt and start_dt.date() == end_dt.date():
            end_time_only = end_dt.strftime("%-I:%M %p")
            time_str = f"{start_str} - {end_time_only}"
        else:
            time_str = f"{start_str} → {end_str}"

    lines = [f"📅 **{title}**", f"   🕐 {time_str}"]
    if location:
        lines.append(f"   📍 {location}")
    lines.append(f"   🆔 `{event_id}`")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def _gcal_list_events(days_ahead=7, max_results=10):
    now = datetime.datetime.utcnow()
    time_min = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    time_max = (now + datetime.timedelta(days=days_ahead)).strftime("%Y-%m-%dT%H:%M:%SZ")

    r = requests.get(
        f"{_API_BASE}/calendars/{_calendar_id()}/events",
        headers=_headers(),
        params={
            "timeMin": time_min,
            "timeMax": time_max,
            "maxResults": max_results,
            "singleEvents": "true",
            "orderBy": "startTime",
        },
        timeout=10,
    )
    r.raise_for_status()
    items = r.json().get("items", [])
    if not items:
        return f"📅 No events in the next {days_ahead} day(s)."
    lines = [f"📅 **Upcoming events (next {days_ahead} day(s)):**\n"]
    for ev in items:
        lines.append(_fmt_event(ev))
    return "\n\n".join(lines)


def _gcal_create_event(title, start_time, end_time=None, description=None, location=None):
    start_dt = _parse_time(start_time)
    if start_dt is None:
        return f"❌ Could not parse start time: {start_time}"

    if end_time:
        end_dt = _parse_time(end_time)
        if end_dt is None:
            end_dt = start_dt + datetime.timedelta(hours=1)
    else:
        end_dt = start_dt + datetime.timedelta(hours=1)

    event_body = {
        "summary": title,
        "start": {"dateTime": _to_rfc3339(start_dt)},
        "end": {"dateTime": _to_rfc3339(end_dt)},
    }
    if description:
        event_body["description"] = description
    if location:
        event_body["location"] = location

    r = requests.post(
        f"{_API_BASE}/calendars/{_calendar_id()}/events",
        headers={**_headers(), "Content-Type": "application/json"},
        json=event_body,
        timeout=10,
    )
    r.raise_for_status()
    ev = r.json()
    ev_id = ev.get("id", "")
    return (
        f"✅ Event created!\n"
        f"📅 **{title}**\n"
        f"🕐 {_to_rfc3339(start_dt)} → {_to_rfc3339(end_dt)}\n"
        f"🆔 `{ev_id}`"
    )


def _gcal_delete_event(event_id):
    r = requests.delete(
        f"{_API_BASE}/calendars/{_calendar_id()}/events/{event_id}",
        headers=_headers(),
        timeout=10,
    )
    if r.status_code == 204:
        return f"🗑️ Event `{event_id}` deleted successfully."
    if r.status_code == 404:
        return f"❌ Event not found: `{event_id}`"
    r.raise_for_status()
    return f"❌ Unexpected response: {r.status_code}"


def _gcal_find_event(query, days_ahead=30):
    now = datetime.datetime.utcnow()
    time_min = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    time_max = (now + datetime.timedelta(days=days_ahead)).strftime("%Y-%m-%dT%H:%M:%SZ")

    r = requests.get(
        f"{_API_BASE}/calendars/{_calendar_id()}/events",
        headers=_headers(),
        params={
            "q": query,
            "timeMin": time_min,
            "timeMax": time_max,
            "maxResults": 10,
            "singleEvents": "true",
            "orderBy": "startTime",
        },
        timeout=10,
    )
    r.raise_for_status()
    items = r.json().get("items", [])
    if not items:
        return f"🔍 No events found matching '{query}' in the next {days_ahead} day(s)."
    lines = [f"🔍 **Events matching '{query}':**\n"]
    for ev in items:
        lines.append(_fmt_event(ev))
    return "\n\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def execute(tool_name, arguments):
    if _load_credentials() is None:
        return _setup_instructions()
    try:
        if tool_name == "gcal_list_events":
            return _gcal_list_events(
                days_ahead=int(arguments.get("days_ahead", 7)),
                max_results=int(arguments.get("max_results", 10)),
            )
        elif tool_name == "gcal_create_event":
            return _gcal_create_event(
                title=arguments.get("title", ""),
                start_time=arguments.get("start_time", ""),
                end_time=arguments.get("end_time"),
                description=arguments.get("description"),
                location=arguments.get("location"),
            )
        elif tool_name == "gcal_delete_event":
            return _gcal_delete_event(event_id=arguments.get("event_id", ""))
        elif tool_name == "gcal_find_event":
            return _gcal_find_event(
                query=arguments.get("query", ""),
                days_ahead=int(arguments.get("days_ahead", 30)),
            )
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 401:
            return "❌ Google Calendar auth failed. Check your service account credentials."
        return f"❌ Google Calendar API error: {e}"
    except RuntimeError as e:
        return f"❌ Auth error: {e}"
    except Exception as e:
        return f"❌ Google Calendar error: {e}"
    return None
