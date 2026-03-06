"""
YouTube Music skill — control music playback via Telegram.
  • PC:    Opens YouTube Music in browser + system media keys
  • Phone: Sends commands to Termux music bridge (optional)

No API key needed. No Spotify Premium needed. 100% free.

Env vars (optional):
  MUSIC_BRIDGE_URL — URL of the Termux music bridge, e.g. http://192.168.1.45:5055
                     Leave empty to control PC only.
"""
import os
import sys
import urllib.parse
import webbrowser
import requests

SKILL_INFO = {
    "name": "youtube_music",
    "description": "Control YouTube Music — play, pause, skip, volume. Works on PC and phone.",
    "version": "1.0",
    "icon": "🎵",
    "author": "ninoclaw",
    "requires_key": False,
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "music_play",
            "description": "Search and play a song, artist, or playlist on YouTube Music. Example: 'play Blinding Lights by The Weeknd'",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Song name, artist, or search query"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "music_pause",
            "description": "Pause or resume the currently playing music",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "music_next",
            "description": "Skip to the next track",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "music_previous",
            "description": "Go back to the previous track",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "music_volume",
            "description": "Set the music volume (0-100)",
            "parameters": {
                "type": "object",
                "properties": {
                    "level": {"type": "integer", "description": "Volume level from 0 to 100"},
                },
                "required": ["level"],
            },
        },
    },
]

# ── Bridge URL (phone control) ──────────────────────────────────────────────

_BRIDGE_URL = os.getenv("MUSIC_BRIDGE_URL", "").strip().rstrip("/")

def _use_bridge():
    return bool(_BRIDGE_URL)


# ── PC media keys (Windows) ─────────────────────────────────────────────────

_IS_WIN = sys.platform == "win32"

VK_MEDIA_PLAY_PAUSE = 0xB3
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_VOLUME_UP        = 0xAF
VK_VOLUME_DOWN      = 0xAE
VK_VOLUME_MUTE      = 0xAD

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP       = 0x0002

def _press_media_key(vk_code):
    """Send a media key press on Windows."""
    if not _IS_WIN:
        return False
    import ctypes
    ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY, 0)
    ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
    return True

def _set_volume_win(level):
    """Set system volume on Windows using pycaw, or fallback to key presses."""
    try:
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        from comtypes import CLSCTX_ALL
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = interface.QueryInterface(IAudioEndpointVolume)
        volume.SetMasterVolumeLevelScalar(max(0, min(100, level)) / 100.0, None)
        return True
    except ImportError:
        # pycaw not installed — use volume key presses as fallback (approximate)
        return False


# ── Bridge commands (phone control) ─────────────────────────────────────────

def _bridge_cmd(action, **kwargs):
    """Send a command to the Termux music bridge."""
    try:
        payload = {"action": action, **kwargs}
        r = requests.post(f"{_BRIDGE_URL}/music", json=payload, timeout=5)
        return r.json().get("result", f"✅ {action}")
    except requests.ConnectionError:
        return f"❌ Cannot reach music bridge at {_BRIDGE_URL}. Is the bridge running on your phone?"
    except Exception as e:
        return f"❌ Bridge error: {e}"


# ── Skill actions ────────────────────────────────────────────────────────────

def _music_play(query):
    encoded = urllib.parse.quote(query)
    url = f"https://music.youtube.com/search?q={encoded}"

    if _use_bridge():
        return _bridge_cmd("play", query=query, url=url)

    # PC: open YouTube Music in browser
    webbrowser.open(url)
    return f"🎵 Searching YouTube Music for: **{query}**\n🌐 Opened in your browser — click the first result to play!"


def _music_pause():
    if _use_bridge():
        return _bridge_cmd("pause")

    if _IS_WIN:
        _press_media_key(VK_MEDIA_PLAY_PAUSE)
        return "⏯️ Toggled play/pause."
    return "❌ Media key control is only supported on Windows. Set MUSIC_BRIDGE_URL for phone control."


def _music_next():
    if _use_bridge():
        return _bridge_cmd("next")

    if _IS_WIN:
        _press_media_key(VK_MEDIA_NEXT_TRACK)
        return "⏭️ Skipped to the next track."
    return "❌ Media key control is only supported on Windows."


def _music_previous():
    if _use_bridge():
        return _bridge_cmd("previous")

    if _IS_WIN:
        _press_media_key(VK_MEDIA_PREV_TRACK)
        return "⏮️ Went back to the previous track."
    return "❌ Media key control is only supported on Windows."


def _music_volume(level):
    level = max(0, min(100, int(level)))

    if _use_bridge():
        return _bridge_cmd("volume", level=level)

    if _IS_WIN:
        if _set_volume_win(level):
            return f"🔊 Volume set to {level}%."
        else:
            return f"🔊 Volume control requires `pycaw`. Run: pip install pycaw"
    return "❌ Volume control is only supported on Windows."


# ── Skill entry point ────────────────────────────────────────────────────────

def execute(tool_name, arguments):
    try:
        if tool_name == "music_play":
            return _music_play(arguments.get("query", ""))
        elif tool_name == "music_pause":
            return _music_pause()
        elif tool_name == "music_next":
            return _music_next()
        elif tool_name == "music_previous":
            return _music_previous()
        elif tool_name == "music_volume":
            return _music_volume(arguments.get("level", 50))
    except Exception as e:
        return f"❌ Music error: {e}"
    return None
