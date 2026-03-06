"""
Termux Music Bridge — tiny server that runs on your Android phone.
Ninoclaw sends commands here to control music playback on your phone.

Usage (in Termux):
    pip install flask
    python termux_music_bridge.py

Requirements:
    - Termux (https://termux.dev)
    - Termux:API app installed from F-Droid
    - pkg install termux-api
    - pip install flask

The bridge listens on port 5055 by default.
"""
import subprocess
import os

try:
    from flask import Flask, request, jsonify
except ImportError:
    print("Flask not installed. Run: pip install flask")
    exit(1)

app = Flask(__name__)
PORT = int(os.getenv("MUSIC_BRIDGE_PORT", "5055"))


def run_cmd(cmd):
    """Run a shell command and return output."""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return r.stdout.strip()
    except Exception as e:
        return str(e)


@app.route("/music", methods=["POST"])
def music_control():
    data = request.get_json() or {}
    action = data.get("action", "")

    if action == "play":
        query = data.get("query", "")
        url = data.get("url", "")
        if url:
            # Open YouTube Music in the browser/app
            run_cmd(f'am start -a android.intent.action.VIEW -d "{url}"')
            return jsonify({"result": f"🎵 Opening YouTube Music: **{query}**"})
        return jsonify({"result": "❌ No query provided"}), 400

    elif action == "pause":
        # Send media play/pause key event
        run_cmd("input keyevent 85")  # KEYCODE_MEDIA_PLAY_PAUSE
        return jsonify({"result": "⏯️ Toggled play/pause."})

    elif action == "next":
        run_cmd("input keyevent 87")  # KEYCODE_MEDIA_NEXT
        return jsonify({"result": "⏭️ Skipped to next track."})

    elif action == "previous":
        run_cmd("input keyevent 88")  # KEYCODE_MEDIA_PREVIOUS
        return jsonify({"result": "⏮️ Went to previous track."})

    elif action == "volume":
        level = data.get("level", 50)
        # Android max media volume is usually 15, scale from 0-100
        max_vol = 15
        android_vol = int(round(level / 100 * max_vol))
        run_cmd(f"termux-volume music {android_vol}")
        return jsonify({"result": f"🔊 Volume set to {level}% (Android level {android_vol}/{max_vol})"})

    else:
        return jsonify({"result": f"❌ Unknown action: {action}"}), 400


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "ninoclaw-music-bridge"})


if __name__ == "__main__":
    print(f"""
    🎵 Ninoclaw Music Bridge
    ════════════════════════
    Listening on port {PORT}
    
    Add this to your Ninoclaw .env on your PC:
      MUSIC_BRIDGE_URL=http://<phone-ip>:{PORT}

    To find your phone IP, run: ifconfig | grep inet
    """)
    app.run(host="0.0.0.0", port=PORT)
