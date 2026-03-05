"""
Spotify skill — control Spotify playback via the Spotify Web API.
Requires: SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REFRESH_TOKEN
"""
import os
import time
import requests

SKILL_INFO = {
    "name": "spotify",
    "description": "Control Spotify playback — play, pause, skip, search",
    "version": "1.0",
    "icon": "🎵",
    "author": "ninoclaw",
    "requires_key": True,
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "spotify_current",
            "description": "Get the currently playing Spotify track",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "spotify_play_pause",
            "description": "Toggle Spotify play/pause",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "spotify_next",
            "description": "Skip to the next track on Spotify",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "spotify_previous",
            "description": "Go back to the previous track on Spotify",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "spotify_search_play",
            "description": "Search the Spotify CATALOG for a song, artist, or public playlist and start playing it. Do NOT use this for playlists from the user's own library — use spotify_play_my_playlist instead.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query, e.g. 'Bohemian Rhapsody Queen'"},
                    "type": {
                        "type": "string",
                        "enum": ["track", "artist", "playlist"],
                        "description": "Type of content to search for (default: track)",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "spotify_volume",
            "description": "Set the Spotify playback volume",
            "parameters": {
                "type": "object",
                "properties": {
                    "level": {"type": "integer", "description": "Volume level from 0 to 100"},
                },
                "required": ["level"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "spotify_my_playlists",
            "description": "List playlists from the user's Spotify library",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "spotify_play_my_playlist",
            "description": "Play a playlist from the user's OWN Spotify library by name. Use this whenever the user says 'play my playlist', 'play [playlist name]', or refers to a playlist they own. Do NOT use spotify_search_play for this.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name (or partial name) of the playlist to play"},
                },
                "required": ["name"],
            },
        },
    },
]

_API = "https://api.spotify.com/v1"
_TOKEN_URL = "https://accounts.spotify.com/api/token"

# Module-level token cache
_access_token = None
_token_expiry = 0.0


def _credentials_missing():
    return not (
        os.getenv("SPOTIFY_CLIENT_ID")
        and os.getenv("SPOTIFY_CLIENT_SECRET")
        and os.getenv("SPOTIFY_REFRESH_TOKEN")
    )


def _setup_instructions():
    return (
        "⚙️ **Spotify setup required**\n\n"
        "Set these environment variables:\n"
        "  • SPOTIFY_CLIENT_ID — from https://developer.spotify.com/dashboard\n"
        "  • SPOTIFY_CLIENT_SECRET — from the same dashboard app\n"
        "  • SPOTIFY_REFRESH_TOKEN — obtained via OAuth flow:\n\n"
        "**Quick OAuth steps:**\n"
        "1. Create an app at https://developer.spotify.com/dashboard\n"
        "2. Add `http://localhost:8888/callback` as a Redirect URI\n"
        "3. Visit:\n"
        "   https://accounts.spotify.com/authorize"
        "?client_id=YOUR_ID&response_type=code"
        "&redirect_uri=http://localhost:8888/callback"
        "&scope=user-read-playback-state+user-modify-playback-state+playlist-read-private+playlist-read-collaborative\n"
        "4. After login, copy the `code` from the redirect URL\n"
        "5. Exchange it:\n"
        "   curl -X POST https://accounts.spotify.com/api/token \\\n"
        "     -d 'grant_type=authorization_code&code=CODE"
        "&redirect_uri=http://localhost:8888/callback' \\\n"
        "     -u CLIENT_ID:CLIENT_SECRET\n"
        "6. Save the `refresh_token` from the response."
    )


def _get_access_token():
    global _access_token, _token_expiry
    if _access_token and time.time() < _token_expiry - 30:
        return _access_token
    resp = requests.post(
        _TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": os.getenv("SPOTIFY_REFRESH_TOKEN"),
        },
        auth=(os.getenv("SPOTIFY_CLIENT_ID"), os.getenv("SPOTIFY_CLIENT_SECRET")),
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    _access_token = data["access_token"]
    _token_expiry = time.time() + data.get("expires_in", 3600)
    return _access_token


def _headers():
    return {"Authorization": f"Bearer {_get_access_token()}"}


def _get_device_id():
    """Get the first available Spotify device ID."""
    r = requests.get(f"{_API}/me/player/devices", headers=_headers(), timeout=10)
    if r.status_code != 200:
        return None, f"❌ Could not fetch devices (status {r.status_code})"
    devices = r.json().get("devices", [])
    if not devices:
        return None, "❌ No Spotify devices found. Open the Spotify app on your phone, play anything briefly, then try again."
    # Prefer active device, else pick first
    active = next((d for d in devices if d.get("is_active")), devices[0])
    return active["id"], None


def _ensure_active(device_id):
    """Transfer playback to device so it becomes active."""
    r = requests.get(f"{_API}/me/player", headers=_headers(), timeout=10)
    if r.status_code == 200 and r.content:
        current_device = r.json().get("device", {}).get("id", "")
        if current_device == device_id and r.json().get("is_playing") is not None:
            return  # already active and connected
    requests.put(
        f"{_API}/me/player",
        headers={**_headers(), "Content-Type": "application/json"},
        json={"device_ids": [device_id], "play": True},
        timeout=10,
    )
    import time; time.sleep(2)


def _spotify_current():
    r = requests.get(f"{_API}/me/player/currently-playing", headers=_headers(), timeout=10)
    if r.status_code == 204 or not r.content:
        return "⏸️ Nothing is currently playing on Spotify."
    data = r.json()
    if not data or not data.get("item"):
        return "⏸️ Nothing is currently playing on Spotify."
    item = data["item"]
    title = item.get("name", "Unknown")
    artists = ", ".join(a["name"] for a in item.get("artists", []))
    album = item.get("album", {}).get("name", "")
    is_playing = data.get("is_playing", False)
    state = "▶️ Playing" if is_playing else "⏸️ Paused"
    progress_ms = data.get("progress_ms", 0)
    duration_ms = item.get("duration_ms", 0)

    def _fmt(ms):
        s = ms // 1000
        return f"{s // 60}:{s % 60:02d}"

    return (
        f"{state}: **{title}**\n"
        f"👤 {artists}\n"
        f"💿 {album}\n"
        f"⏱️ {_fmt(progress_ms)} / {_fmt(duration_ms)}"
    )


def _spotify_play_pause():
    device_id, err = _get_device_id()
    if err:
        return err
    r = requests.get(f"{_API}/me/player", headers=_headers(), timeout=10)
    is_playing = r.json().get("is_playing", False) if r.status_code == 200 and r.content else False
    params = {"device_id": device_id} if device_id else {}
    if is_playing:
        requests.put(f"{_API}/me/player/pause", headers=_headers(), params=params, timeout=10)
        return "⏸️ Spotify paused."
    else:
        requests.put(f"{_API}/me/player/play", headers=_headers(), params=params, timeout=10)
        return "▶️ Spotify resumed."


def _spotify_next():
    device_id, err = _get_device_id()
    if err:
        return err
    r = requests.post(f"{_API}/me/player/next", headers=_headers(),
                      params={"device_id": device_id}, timeout=10)
    if r.status_code in (200, 204):
        return "⏭️ Skipped to the next track."
    return f"❌ Could not skip track (status {r.status_code}): {r.text}"


def _spotify_previous():
    device_id, err = _get_device_id()
    if err:
        return err
    r = requests.post(f"{_API}/me/player/previous", headers=_headers(),
                      params={"device_id": device_id}, timeout=10)
    if r.status_code in (200, 204):
        return "⏮️ Went back to the previous track."
    return f"❌ Could not go to previous track (status {r.status_code}): {r.text}"


def _spotify_search_play(query, search_type="track"):
    if search_type not in ("track", "artist", "playlist"):
        search_type = "track"
    r = requests.get(
        f"{_API}/search",
        headers=_headers(),
        params={"q": query, "type": search_type, "limit": 1},
        timeout=10,
    )
    r.raise_for_status()
    results = r.json()
    key = f"{search_type}s"
    items = [i for i in results.get(key, {}).get("items", []) if i]
    if not items:
        return f"❌ No {search_type} found for: {query}"
    item = items[0]
    uri = item["uri"]
    name = item.get("name", uri)

    if search_type == "track":
        payload = {"uris": [uri]}
    else:
        payload = {"context_uri": uri}

    device_id, err = _get_device_id()
    if err:
        return err
    _ensure_active(device_id)
    play_resp = requests.put(
        f"{_API}/me/player/play",
        headers={**_headers(), "Content-Type": "application/json"},
        params={"device_id": device_id} if device_id else {},
        json=payload,
        timeout=10,
    )
    if play_resp.status_code == 404:
        return "❌ No active Spotify device found. Open the Spotify app on your phone first, then try again."
    if play_resp.status_code not in (200, 204):
        return f"❌ Spotify play failed (status {play_resp.status_code}): {play_resp.text}"
    type_emoji = {"track": "🎵", "artist": "👤", "playlist": "📋"}.get(search_type, "🎵")
    return f"{type_emoji} Now playing {search_type}: **{name}**"


def _spotify_my_playlists(limit=20):
    """Fetch the user's own saved playlists."""
    r = requests.get(
        f"{_API}/me/playlists",
        headers=_headers(),
        params={"limit": limit},
        timeout=10,
    )
    if r.status_code != 200:
        return f"❌ Could not fetch playlists (status {r.status_code})"
    items = [i for i in r.json().get("items", []) if i]
    if not items:
        return "📭 No playlists found in your library."
    lines = [f"📋 Your Spotify playlists ({len(items)} found):"]
    for i, pl in enumerate(items, 1):
        name = pl.get("name", "Unknown")
        total = pl.get("tracks", {}).get("total", "?")
        lines.append(f"  {i}. {name} ({total} tracks)")
    return "\n".join(lines)


def _spotify_play_my_playlist(name):
    """Play a playlist from the user's library by name (fuzzy match)."""
    r = requests.get(
        f"{_API}/me/playlists",
        headers=_headers(),
        params={"limit": 50},
        timeout=10,
    )
    if r.status_code != 200:
        return f"❌ Could not fetch playlists (status {r.status_code})"
    items = [i for i in r.json().get("items", []) if i]
    if not items:
        return "📭 No playlists found in your library."
    name_lower = name.lower()
    match = next(
        (pl for pl in items if name_lower in pl.get("name", "").lower()),
        None
    )
    if not match:
        names = ", ".join(pl.get("name", "") for pl in items[:10])
        return f"❌ No playlist matching '{name}' found. Your playlists: {names}"
    uri = match["uri"]
    pl_name = match.get("name", uri)
    device_id, err = _get_device_id()
    if err:
        return err
    _ensure_active(device_id)
    play_resp = requests.put(
        f"{_API}/me/player/play",
        headers={**_headers(), "Content-Type": "application/json"},
        params={"device_id": device_id} if device_id else {},
        json={"context_uri": uri},
        timeout=10,
    )
    if play_resp.status_code == 404:
        return "❌ No active Spotify device found. Open the Spotify app first."
    if play_resp.status_code not in (200, 204):
        return f"❌ Spotify play failed (status {play_resp.status_code}): {play_resp.text}"
    return f"📋 Now playing your playlist: **{pl_name}**"


def _spotify_volume(level):
    device_id, err = _get_device_id()
    if err:
        return err
    level = max(0, min(100, int(level)))
    r = requests.put(f"{_API}/me/player/volume", headers=_headers(),
                     params={"volume_percent": level, "device_id": device_id}, timeout=10)
    if r.status_code in (200, 204):
        return f"🔊 Volume set to {level}%."
    return f"❌ Could not set volume (status {r.status_code}): {r.text}"


def execute(tool_name, arguments):
    if _credentials_missing():
        return _setup_instructions()
    try:
        if tool_name == "spotify_current":
            return _spotify_current()
        elif tool_name == "spotify_play_pause":
            return _spotify_play_pause()
        elif tool_name == "spotify_next":
            return _spotify_next()
        elif tool_name == "spotify_previous":
            return _spotify_previous()
        elif tool_name == "spotify_search_play":
            return _spotify_search_play(
                arguments.get("query", ""),
                arguments.get("type", "track"),
            )
        elif tool_name == "spotify_volume":
            return _spotify_volume(arguments.get("level", 50))
        elif tool_name == "spotify_my_playlists":
            return _spotify_my_playlists()
        elif tool_name == "spotify_play_my_playlist":
            return _spotify_play_my_playlist(arguments.get("name", ""))
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 401:
            return "❌ Spotify auth failed. Check your credentials and refresh token."
        return f"❌ Spotify API error: {e}"
    except Exception as e:
        return f"❌ Spotify error: {e}"
    return None
