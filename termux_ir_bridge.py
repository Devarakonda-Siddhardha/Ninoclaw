#!/usr/bin/env python3
"""
Termux IR Bridge — run this in Termux (NOT inside proot/Debian).

Listens on localhost:7070 and sends IR signals via termux-infrared-transmit.

Setup:
  pkg install termux-api python
  python termux_ir_bridge.py

Keep running in background:
  nohup python termux_ir_bridge.py > /data/data/com.termux/files/home/ir_bridge.log 2>&1 &
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import subprocess
import json
import sys

PORT = 7070


class IRHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[IR Bridge] {fmt % args}")

    def do_GET(self):
        if self.path == "/ping":
            self._respond(200, {"ok": True, "service": "ir_bridge"})
        else:
            self._respond(404, {"error": "Not found"})

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length).decode())
            freq = int(body.get("frequency", 38000))
            pattern = body.get("pattern", [])

            if not pattern:
                self._respond(400, {"error": "No IR pattern provided"})
                return

            pattern_str = " ".join(map(str, pattern))
            result = subprocess.run(
                ["termux-infrared-transmit", "-f", str(freq), pattern_str],
                capture_output=True, text=True, timeout=15
            )

            if result.returncode == 0:
                self._respond(200, {"ok": True})
                print(f"[IR Bridge] ✅ Transmitted {len(pattern)} pulses at {freq}Hz")
            else:
                self._respond(500, {"ok": False, "error": result.stderr.strip()})
                print(f"[IR Bridge] ❌ Error: {result.stderr.strip()}")
        except Exception as e:
            self._respond(500, {"error": str(e)})
            print(f"[IR Bridge] ❌ Exception: {e}")

    def _respond(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    print(f"[IR Bridge] Starting on localhost:{PORT}")
    print(f"[IR Bridge] Requires: pkg install termux-api")
    server = HTTPServer(("127.0.0.1", PORT), IRHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[IR Bridge] Stopped.")
        sys.exit(0)
