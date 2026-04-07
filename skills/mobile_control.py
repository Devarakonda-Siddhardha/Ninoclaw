"""
Mobile Control skill — lets the AI control the user's Android phone
through the Ninoclaw Companion app via queued tasks.

Requires: companion app connected + accessibility service enabled.
"""
import json
import sqlite3
import os

SKILL_INFO = {
    "name": "mobile_control",
    "description": "Control the user's Android phone via the Ninoclaw Companion app",
    "version": "1.0",
    "icon": "📱",
    "author": "ninoclaw",
    "requires_key": False,
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "mobile_open_app",
            "description": "Open an app on the user's Android phone. Use when user says 'open WhatsApp', 'launch Chrome', 'open Spotify on my phone', etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app": {"type": "string", "description": "App name e.g. whatsapp, chrome, youtube, spotify, settings, instagram, telegram, maps, camera"},
                },
                "required": ["app"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mobile_tap",
            "description": "Tap a UI element on the user's Android phone screen by text label, content description, or coordinates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Visible text of the element to tap"},
                    "x": {"type": "number", "description": "X screen coordinate to tap"},
                    "y": {"type": "number", "description": "Y screen coordinate to tap"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mobile_type_text",
            "description": "Type text into a field on the user's Android phone.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to type"},
                    "target": {"type": "string", "description": "Optional: label or placeholder of the target field"},
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mobile_read_screen",
            "description": "Read all visible text on the user's current phone screen. Use to understand what's on screen before tapping.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mobile_press_back",
            "description": "Press the Android back button on the user's phone.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mobile_open_url",
            "description": "Open a URL in the browser on the user's Android phone.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Full URL to open"},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mobile_send_sms",
            "description": "Send an SMS from the user's Android phone.",
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {"type": "string", "description": "Phone number to send to"},
                    "message": {"type": "string", "description": "Message text"},
                },
                "required": ["phone", "message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mobile_dial",
            "description": "Dial a phone number on the user's Android phone.",
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {"type": "string", "description": "Phone number to dial"},
                },
                "required": ["phone"],
            },
        },
    },
]


def _db_path():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "ninoclaw.db")


def _get_primary_device():
    """Return the most recently seen online device_id, or None."""
    try:
        conn = sqlite3.connect(_db_path())
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT device_id FROM mobile_devices ORDER BY last_seen DESC LIMIT 1"
        ).fetchone()
        conn.close()
        return row["device_id"] if row else None
    except Exception:
        return None


def _enqueue(action, payload):
    device_id = _get_primary_device()
    if not device_id:
        return "❌ No phone connected. Open the Ninoclaw Companion app and connect to the dashboard first."
    try:
        conn = sqlite3.connect(_db_path())
        cur = conn.execute(
            """
            INSERT INTO mobile_tasks (device_id, action, payload_json, status, created_at)
            VALUES (?, ?, ?, 'queued', strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
            """,
            (device_id, action, json.dumps(payload)),
        )
        conn.commit()
        task_id = cur.lastrowid
        conn.close()
        return f"✅ Task #{task_id} queued for your phone ({action}). The companion app will execute it within ~8 seconds."
    except Exception as e:
        return f"❌ Failed to queue mobile task: {e}"


def execute(tool_name, arguments):
    if tool_name == "mobile_open_app":
        app = arguments.get("app", "").strip().lower()
        return _enqueue("open_app", {"app": app})

    if tool_name == "mobile_tap":
        payload = {}
        if arguments.get("text"):
            payload["text"] = arguments["text"]
        if arguments.get("x") is not None and arguments.get("y") is not None:
            payload["x"] = arguments["x"]
            payload["y"] = arguments["y"]
        return _enqueue("agent_tap", payload)

    if tool_name == "mobile_type_text":
        return _enqueue("agent_type_text", {
            "text": arguments.get("text", ""),
            "targetText": arguments.get("target", ""),
        })

    if tool_name == "mobile_read_screen":
        return _enqueue("android_agent_status", {})

    if tool_name == "mobile_press_back":
        return _enqueue("agent_press_back", {})

    if tool_name == "mobile_open_url":
        return _enqueue("open_url", {"url": arguments.get("url", "")})

    if tool_name == "mobile_send_sms":
        return _enqueue("send_sms", {
            "phone": arguments.get("phone", ""),
            "message": arguments.get("message", ""),
        })

    if tool_name == "mobile_dial":
        return _enqueue("dial_number", {"phone": arguments.get("phone", "")})

    return f"Unknown mobile tool: {tool_name}"
