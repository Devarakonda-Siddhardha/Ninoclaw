"""
Android Auto companion skill.

This does not bypass Android Auto restrictions. Instead, it controls an Android
phone connected to the car by talking to a tiny Termux bridge running on the
phone. That gives Ninoclaw practical driving actions like opening Spotify,
starting navigation, calling contacts, and sending messages.

Setup:
  1. Run termux_android_auto_bridge.py on the Android phone in Termux
  2. Set ANDROID_AUTO_BRIDGE_URL in Ninoclaw .env
     Example: ANDROID_AUTO_BRIDGE_URL=http://192.168.29.140:5056
"""
import os
import requests


SKILL_INFO = {
    "name": "android_auto",
    "description": "Android Auto companion controls for Spotify, navigation, calls, and driving routines",
    "version": "1.0",
    "icon": "🚗",
    "author": "ninoclaw",
    "requires_key": False,
}


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "android_auto_status",
            "description": "Check whether the Android Auto bridge on the phone is reachable.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "android_auto_open_spotify",
            "description": "Open Spotify on the Android phone connected to the car.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "android_auto_play_spotify",
            "description": "Open Spotify and search for a song, artist, album, or playlist on the Android phone.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Spotify search query, like a song name, artist, or playlist",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "android_auto_media",
            "description": "Control media playback on the Android phone while driving.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["play_pause", "next", "previous"],
                        "description": "Media action to trigger",
                    }
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "android_auto_navigate",
            "description": "Start navigation in Google Maps on the Android phone.",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {
                        "type": "string",
                        "description": "Destination to navigate to",
                    }
                },
                "required": ["destination"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "android_auto_call",
            "description": "Start a phone call from the Android phone.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "Phone number or contact hint to dial",
                    }
                },
                "required": ["target"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "android_auto_message",
            "description": "Open SMS or WhatsApp compose flow for a driving-safe message.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "Phone number for SMS/WhatsApp target",
                    },
                    "message": {
                        "type": "string",
                        "description": "Message text to prefill",
                    },
                    "app": {
                        "type": "string",
                        "enum": ["sms", "whatsapp"],
                        "description": "Which app to use. Default sms.",
                    },
                },
                "required": ["target", "message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "android_auto_commute_mode",
            "description": "Start a driving routine: open Android Auto or Maps and optionally start Spotify.",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {
                        "type": "string",
                        "description": "Optional destination for Maps navigation",
                    },
                    "spotify_query": {
                        "type": "string",
                        "description": "Optional Spotify search query to open",
                    },
                },
                "required": [],
            },
        },
    },
]


_BRIDGE_URL = os.getenv("ANDROID_AUTO_BRIDGE_URL", "").strip().rstrip("/")


def _bridge_missing():
    return (
        "⚙️ Android Auto bridge not configured.\n\n"
        "Set `ANDROID_AUTO_BRIDGE_URL` in your `.env`, for example:\n"
        "`ANDROID_AUTO_BRIDGE_URL=http://<phone-ip>:5056`\n\n"
        "Then run `termux_android_auto_bridge.py` in Termux on your phone."
    )


def _post(action, **payload):
    if not _BRIDGE_URL:
        return _bridge_missing()
    try:
        response = requests.post(
            f"{_BRIDGE_URL}/android_auto",
            json={"action": action, **payload},
            timeout=8,
        )
        data = response.json()
        return data.get("result", f"✅ {action}")
    except requests.ConnectionError:
        return f"❌ Cannot reach Android Auto bridge at {_BRIDGE_URL}. Is the phone bridge running?"
    except Exception as e:
        return f"❌ Android Auto bridge error: {e}"


def _status():
    if not _BRIDGE_URL:
        return _bridge_missing()
    try:
        response = requests.get(f"{_BRIDGE_URL}/health", timeout=5)
        data = response.json()
        service = data.get("service", "unknown")
        return f"✅ Android Auto bridge is reachable: `{service}`"
    except requests.ConnectionError:
        return f"❌ Cannot reach Android Auto bridge at {_BRIDGE_URL}."
    except Exception as e:
        return f"❌ Bridge status error: {e}"


def execute(tool_name, arguments):
    try:
        if tool_name == "android_auto_status":
            return _status()
        if tool_name == "android_auto_open_spotify":
            return _post("open_spotify")
        if tool_name == "android_auto_play_spotify":
            return _post("play_spotify", query=arguments.get("query", ""))
        if tool_name == "android_auto_media":
            return _post("media", media_action=arguments.get("action", "play_pause"))
        if tool_name == "android_auto_navigate":
            return _post("navigate", destination=arguments.get("destination", ""))
        if tool_name == "android_auto_call":
            return _post("call", target=arguments.get("target", ""))
        if tool_name == "android_auto_message":
            return _post(
                "message",
                target=arguments.get("target", ""),
                message=arguments.get("message", ""),
                app=arguments.get("app", "sms"),
            )
        if tool_name == "android_auto_commute_mode":
            return _post(
                "commute_mode",
                destination=arguments.get("destination", ""),
                spotify_query=arguments.get("spotify_query", ""),
            )
    except Exception as e:
        return f"❌ Android Auto skill error: {e}"
    return None
