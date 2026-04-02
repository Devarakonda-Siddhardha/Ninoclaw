"""
WhatsApp bridge management for Ninoclaw.

Supports:
- local Baileys bridge (default, easier setup)
- WAHA-compatible HTTP bridge
"""
import base64
import os
import shlex
import subprocess
import threading
import time
from typing import Any, Dict, Optional

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

ROOT_DIR = os.path.dirname(__file__)


def _default_bridge_command(cfg: Dict[str, str]) -> str:
    bridge_type = (cfg.get("type") or "").strip().lower()
    if bridge_type == "baileys":
        script = os.path.join(ROOT_DIR, "whatsapp_baileys_bridge", "bridge.cjs")
        if os.name == "nt":
            return f'node "{script}"'
        return f"node {shlex.quote(script)}"
    return ""


def _env() -> Dict[str, str]:
    try:
        from config import get_runtime_env
        env = get_runtime_env()
    except Exception:
        env = dict(os.environ)
        env_file = os.path.join(ROOT_DIR, ".env")
        if os.path.exists(env_file):
            try:
                with open(env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        key, value = line.split("=", 1)
                        env[key.strip()] = value.strip().strip('"').strip("'")
            except OSError:
                pass
    return env


def _boolish(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _normalize_base_url(url: str) -> str:
    return (url or "http://127.0.0.1:3001").rstrip("/")


def _webhook_url(cfg: Dict[str, str]) -> str:
    explicit = cfg.get("webhook_url", "").strip()
    if explicit:
        return explicit
    host = cfg.get("webhook_host", "127.0.0.1").strip() or "127.0.0.1"
    port = cfg.get("webhook_port", "8091").strip() or "8091"
    path = cfg.get("webhook_path", "/whatsapp/webhook").strip() or "/whatsapp/webhook"
    if not path.startswith("/"):
        path = "/" + path
    return f"http://{host}:{port}{path}"


class WhatsAppBridgeManager:
    def __init__(self):
        self._process = None
        self._lock = threading.Lock()

    def _cfg(self) -> Dict[str, str]:
        env = _env()
        return {
            "type": env.get("WHATSAPP_BRIDGE_TYPE", "baileys").strip().lower() or "baileys",
            "base_url": _normalize_base_url(env.get("WHATSAPP_BRIDGE_URL", "")),
            "token": env.get("WHATSAPP_BRIDGE_TOKEN", "").strip(),
            "session": env.get("WHATSAPP_SESSION_NAME", "ninoclaw").strip() or "ninoclaw",
            "command": env.get("WHATSAPP_BRIDGE_COMMAND", "").strip(),
            "auto_start": env.get("WHATSAPP_AUTO_START_BRIDGE", "true").strip(),
            "webhook_host": env.get("WHATSAPP_WEBHOOK_HOST", "127.0.0.1").strip() or "127.0.0.1",
            "webhook_port": str(env.get("WHATSAPP_WEBHOOK_PORT", "8091")).strip() or "8091",
            "webhook_path": env.get("WHATSAPP_WEBHOOK_PATH", "/whatsapp/webhook").strip() or "/whatsapp/webhook",
            "webhook_url": env.get("WHATSAPP_WEBHOOK_URL", "").strip(),
            "webhook_secret": env.get("WHATSAPP_WEBHOOK_SECRET", "").strip(),
        }

    def _headers(self) -> Dict[str, str]:
        cfg = self._cfg()
        headers = {"Accept": "application/json"}
        if cfg["token"]:
            headers["X-Api-Key"] = cfg["token"]
            headers["Authorization"] = f"Bearer {cfg['token']}"
        return headers

    def _request(self, method: str, path: str, timeout: int = 10, **kwargs):
        if requests is None:
            raise RuntimeError("requests is not installed. Run pip install -e . or ninoclaw fixenv first.")
        cfg = self._cfg()
        url = cfg["base_url"] + path
        headers = dict(self._headers())
        headers.update(kwargs.pop("headers", {}) or {})
        return requests.request(method, url, headers=headers, timeout=timeout, **kwargs)

    def _wait_until_ready(self, timeout: int = 20) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                resp = self._request("GET", "/health", timeout=3)
                if resp.ok:
                    return True
            except Exception:
                pass
            try:
                resp = self._request("GET", "/api/sessions", timeout=3)
                if resp.ok:
                    return True
            except Exception:
                pass
            time.sleep(1)
        return False

    def is_running(self) -> bool:
        with self._lock:
            return self._process is not None and self._process.poll() is None

    def start(self) -> Dict[str, Any]:
        cfg = self._cfg()
        command = cfg["command"] or _default_bridge_command(cfg)
        if not command:
            return {
                "ok": False,
                "message": "WHATSAPP_BRIDGE_COMMAND is not set. Configure a WAHA command or use the built-in Baileys bridge.",
            }

        with self._lock:
            if self._process is not None and self._process.poll() is None:
                return {"ok": True, "message": "WhatsApp bridge is already running.", "pid": self._process.pid}
            try:
                self._process = subprocess.Popen(
                    shlex.split(command, posix=os.name != "nt"),
                    cwd=ROOT_DIR,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                if self._wait_until_ready():
                    return {"ok": True, "message": "WhatsApp bridge started.", "pid": self._process.pid}
                return {
                    "ok": False,
                    "message": "WhatsApp bridge process started but did not become ready in time.",
                    "pid": self._process.pid,
                }
            except Exception as exc:
                self._process = None
                return {"ok": False, "message": f"Failed to start WhatsApp bridge: {exc}"}

    def stop(self) -> Dict[str, Any]:
        cfg = self._cfg()
        session = cfg["session"]

        try:
            self._request("POST", f"/api/sessions/{session}/stop", timeout=10)
        except Exception:
            pass

        with self._lock:
            if self._process is None or self._process.poll() is not None:
                self._process = None
                return {"ok": True, "message": "WhatsApp bridge is not running."}
            try:
                self._process.terminate()
                self._process.wait(timeout=10)
                pid = self._process.pid
                self._process = None
                return {"ok": True, "message": "WhatsApp bridge stopped.", "pid": pid}
            except Exception as exc:
                return {"ok": False, "message": f"Failed to stop WhatsApp bridge cleanly: {exc}"}

    def _session_payload(self) -> Dict[str, Any]:
        cfg = self._cfg()
        webhook = {
            "url": _webhook_url(cfg),
            "events": ["message", "session.status"],
        }
        if cfg["webhook_secret"]:
            webhook["customHeaders"] = [{"name": "X-Ninoclaw-Secret", "value": cfg["webhook_secret"]}]
        return {
            "name": cfg["session"],
            "config": {
                "webhooks": [webhook]
            },
        }

    def ensure_session(self) -> Dict[str, Any]:
        cfg = self._cfg()
        session = cfg["session"]
        payload = self._session_payload()
        try:
            resp = self._request("POST", "/api/sessions", json=payload, timeout=15)
            if resp.ok:
                return {"ok": True, "message": "WhatsApp session created or already exists.", "data": resp.json()}

            if resp.status_code in {409, 422, 500}:
                update = self._request("PUT", f"/api/sessions/{session}", json=payload, timeout=15)
                data = {}
                try:
                    data = update.json()
                except Exception:
                    data = {"raw": (update.text or "").strip()[:500]}
                return {
                    "ok": update.ok,
                    "message": "WhatsApp session updated." if update.ok else "Failed to update WhatsApp session.",
                    "data": data,
                }

            data = {}
            try:
                data = resp.json()
            except Exception:
                data = {"raw": (resp.text or "").strip()[:500]}
            return {"ok": False, "message": "Failed to create WhatsApp session.", "data": data}
        except Exception as exc:
            return {"ok": False, "message": f"Could not ensure WhatsApp session: {exc}"}

    def start_session(self) -> Dict[str, Any]:
        cfg = self._cfg()
        session = cfg["session"]
        try:
            resp = self._request("POST", f"/api/sessions/{session}/start", timeout=15)
            data = {}
            try:
                data = resp.json()
            except Exception:
                data = {"raw": (resp.text or "").strip()[:500]}
            return {
                "ok": resp.ok,
                "message": "WhatsApp session started." if resp.ok else "Failed to start WhatsApp session.",
                "data": data,
            }
        except Exception as exc:
            return {"ok": False, "message": f"Could not start WhatsApp session: {exc}"}

    def status(self) -> Dict[str, Any]:
        cfg = self._cfg()
        result = {
            "ok": False,
            "session": cfg["session"],
            "base_url": cfg["base_url"],
            "webhook_url": _webhook_url(cfg),
            "managed_process_running": self.is_running(),
        }
        try:
            sessions_resp = self._request("GET", "/api/sessions", timeout=5)
            sessions = sessions_resp.json() if sessions_resp.ok else []
            session_obj = None
            if isinstance(sessions, list):
                for item in sessions:
                    if isinstance(item, dict) and item.get("name") == cfg["session"]:
                        session_obj = item
                        break
            result.update({
                "ok": sessions_resp.ok,
                "http_status": sessions_resp.status_code,
                "bridge_status": session_obj or sessions,
                "message": "WhatsApp bridge reachable." if sessions_resp.ok else "WhatsApp bridge responded with an error.",
            })
            return result
        except Exception as exc:
            result["message"] = f"WhatsApp bridge not reachable: {exc}"
            return result

    def login_info(self) -> Dict[str, Any]:
        ensure = self.ensure_session()
        start = self.start_session()
        screenshot = self.get_qr_screenshot()
        return {
            "ok": ensure.get("ok") and start.get("ok"),
            "message": "Session prepared. Scan the QR screenshot if present.",
            "ensure": ensure,
            "start": start,
            "qr": screenshot,
        }

    def get_qr_screenshot(self) -> Dict[str, Any]:
        cfg = self._cfg()
        session = cfg["session"]
        deadline = time.time() + 20
        last_error = None
        while time.time() < deadline:
            try:
                resp = self._request("GET", "/api/screenshot", timeout=20, params={"session": session})
                if not resp.ok:
                    last_error = {"ok": False, "message": "Failed to fetch WhatsApp QR screenshot.", "http_status": resp.status_code}
                    time.sleep(1)
                    continue
                data = {}
                try:
                    data = resp.json()
                except Exception:
                    data = {"raw": (resp.text or "").strip()[:1000]}
                b64 = data.get("data") or data.get("screenshot") or data.get("base64")
                if not b64:
                    last_error = {"ok": False, "message": "Bridge did not return a QR screenshot payload.", "data": data}
                    time.sleep(1)
                    continue

                out_dir = os.path.join(ROOT_DIR, "assets")
                os.makedirs(out_dir, exist_ok=True)
                out_path = os.path.join(out_dir, "whatsapp_qr.png")
                with open(out_path, "wb") as f:
                    f.write(base64.b64decode(b64))
                return {"ok": True, "message": "QR screenshot saved.", "path": out_path}
            except Exception as exc:
                last_error = {"ok": False, "message": f"Could not fetch WhatsApp QR screenshot: {exc}"}
                time.sleep(1)
        return last_error or {"ok": False, "message": "QR screenshot was not ready in time."}

    def send_text(self, to: str, text: str) -> Dict[str, Any]:
        cfg = self._cfg()
        chat_id = str(to or "").strip()
        if chat_id.startswith("+"):
            chat_id = chat_id[1:]
        if chat_id.endswith("@s.whatsapp.net"):
            chat_id = chat_id[:-15] + "@c.us"
        elif chat_id.isdigit():
            chat_id = chat_id + "@c.us"
        payload = {
            "session": cfg["session"],
            "chatId": chat_id,
            "text": text,
        }
        try:
            resp = self._request("POST", "/api/sendText", json=payload, timeout=20)
            data = {}
            try:
                data = resp.json()
            except Exception:
                data = {"raw": (resp.text or "").strip()[:500]}
            return {
                "ok": resp.ok,
                "http_status": resp.status_code,
                "data": data,
                "message": "Message sent." if resp.ok else "Bridge rejected WhatsApp send request.",
            }
        except Exception as exc:
            return {"ok": False, "message": f"Failed to send WhatsApp message: {exc}"}

    def maybe_start_for_runtime(self) -> Dict[str, Any]:
        cfg = self._cfg()
        if not _boolish(cfg["auto_start"], default=True):
            return {"ok": True, "message": "Auto-start disabled for WhatsApp bridge."}
        return self.start()


bridge_manager = WhatsAppBridgeManager()
