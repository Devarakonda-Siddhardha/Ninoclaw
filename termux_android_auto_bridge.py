"""
Termux Android Auto bridge.

Run this on the Android phone in Termux so Ninoclaw can trigger practical
driving actions on the phone that feeds Android Auto.

Usage:
    pkg install termux-api python
    pip install flask
    python termux_android_auto_bridge.py

Add to PC .env:
    ANDROID_AUTO_BRIDGE_URL=http://<phone-ip>:5056
"""
import os
import shlex
import subprocess
import urllib.parse

try:
    from flask import Flask, jsonify, request
except ImportError:
    print("Flask not installed. Run: pip install flask")
    raise SystemExit(1)


app = Flask(__name__)
PORT = int(os.getenv("ANDROID_AUTO_BRIDGE_PORT", "5056"))


def run_cmd(command: str):
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()
        return result.returncode, stdout, stderr
    except Exception as e:
        return 1, "", str(e)


def open_url(url: str):
    quoted = shlex.quote(url)
    return run_cmd(f"am start -a android.intent.action.VIEW -d {quoted}")


def media_key(keycode: int):
    return run_cmd(f"input keyevent {int(keycode)}")


@app.route("/android_auto", methods=["POST"])
def android_auto():
    data = request.get_json() or {}
    action = data.get("action", "")

    if action == "open_spotify":
        open_url("spotify:")
        return jsonify({"result": "🎵 Opening Spotify on your phone."})

    if action == "play_spotify":
        query = (data.get("query") or "").strip()
        if not query:
            return jsonify({"result": "❌ No Spotify query provided."}), 400
        encoded = urllib.parse.quote(query)
        open_url(f"spotify:search:{encoded}")
        return jsonify({"result": f"🎵 Opening Spotify search for: **{query}**"})

    if action == "media":
        media_action = (data.get("media_action") or "play_pause").strip()
        keycodes = {
            "play_pause": 85,
            "next": 87,
            "previous": 88,
        }
        keycode = keycodes.get(media_action)
        if keycode is None:
            return jsonify({"result": f"❌ Unknown media action: {media_action}"}), 400
        media_key(keycode)
        labels = {
            "play_pause": "⏯️ Toggled play/pause.",
            "next": "⏭️ Skipped to the next track.",
            "previous": "⏮️ Went to the previous track.",
        }
        return jsonify({"result": labels[media_action]})

    if action == "navigate":
        destination = (data.get("destination") or "").strip()
        if not destination:
            return jsonify({"result": "❌ No destination provided."}), 400
        encoded = urllib.parse.quote(destination)
        open_url(f"google.navigation:q={encoded}")
        return jsonify({"result": f"🗺️ Starting navigation to **{destination}** in Google Maps."})

    if action == "call":
        target = (data.get("target") or "").strip()
        if not target:
            return jsonify({"result": "❌ No call target provided."}), 400
        encoded = urllib.parse.quote(target)
        open_url(f"tel:{encoded}")
        return jsonify({"result": f"📞 Opening dialer for **{target}**."})

    if action == "message":
        target = (data.get("target") or "").strip()
        message = (data.get("message") or "").strip()
        app_name = (data.get("app") or "sms").strip().lower()
        if not target or not message:
            return jsonify({"result": "❌ target and message are required."}), 400
        encoded_target = urllib.parse.quote(target)
        encoded_message = urllib.parse.quote(message)
        if app_name == "whatsapp":
            open_url(f"https://wa.me/{encoded_target}?text={encoded_message}")
            return jsonify({"result": f"💬 Opening WhatsApp message to **{target}**."})
        open_url(f"sms:{encoded_target}?body={encoded_message}")
        return jsonify({"result": f"💬 Opening SMS compose for **{target}**."})

    if action == "commute_mode":
        destination = (data.get("destination") or "").strip()
        spotify_query = (data.get("spotify_query") or "").strip()
        # Open Android Auto app if present; ignore errors if unavailable.
        run_cmd("am start -n com.google.android.projection.gearhead/.companion.connectionservice.CompanionConnectionService")
        if destination:
            encoded = urllib.parse.quote(destination)
            open_url(f"google.navigation:q={encoded}")
        else:
            open_url("geo:0,0?q=")
        if spotify_query:
            encoded_query = urllib.parse.quote(spotify_query)
            open_url(f"spotify:search:{encoded_query}")
        return jsonify({"result": "🚗 Started commute mode on the phone."})

    return jsonify({"result": f"❌ Unknown action: {action}"}), 400


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "ninoclaw-android-auto-bridge"})


if __name__ == "__main__":
    print(
        f"""
🚗 Ninoclaw Android Auto Bridge
===============================
Listening on port {PORT}

Add this to your Ninoclaw .env on your PC:
  ANDROID_AUTO_BRIDGE_URL=http://<phone-ip>:{PORT}

Then ask Ninoclaw things like:
  - open spotify in the car
  - navigate to office
  - call dad
  - send sms to mom I am on the way
"""
    )
    app.run(host="0.0.0.0", port=PORT)
