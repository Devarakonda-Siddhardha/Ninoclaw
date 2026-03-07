"""
Expo app management for Ninoclaw.

Creates, edits, starts, stops, and lists Expo apps stored under mobile_apps/.
"""
import json
import os
import re
import shutil
import signal
import socket
import sqlite3
import subprocess
import time
from datetime import datetime
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
APPS_DIR = ROOT_DIR / "mobile_apps"
LOGS_DIR = APPS_DIR / "_logs"
DB_FILE = ROOT_DIR / "ninoclaw.db"
DEFAULT_EXPO_TEMPLATE = "blank@sdk-54"


def _get_conn():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    APPS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    conn = _get_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS expo_apps (
            name TEXT PRIMARY KEY,
            template TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'stopped',
            pid INTEGER,
            port INTEGER,
            launch_url TEXT,
            tunnel_url TEXT,
            web_url TEXT,
            log_path TEXT,
            last_error TEXT
        )
        """
    )
    conn.commit()
    conn.close()


_init_db()


def _sanitize_name(name: str) -> str:
    safe = re.sub(r"[^a-z0-9_-]", "-", (name or "").strip().lower())
    safe = re.sub(r"-{2,}", "-", safe).strip("-")
    return safe[:50] or "expo-app"


def _project_dir(name: str) -> Path:
    return APPS_DIR / _sanitize_name(name)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _npx_command():
    return "npx.cmd" if os.name == "nt" else "npx"


def _resolve_template(template: str = "") -> str:
    raw = (template or "").strip()
    if not raw or raw == "blank":
        return DEFAULT_EXPO_TEMPLATE
    return raw


def _find_free_port(start: int = 8081) -> int:
    for port in range(start, start + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError("No free port found for Expo")


def _is_process_alive(pid) -> bool:
    if not pid:
        return False
    try:
        os.kill(int(pid), 0)
        return True
    except OSError:
        return False


def _stop_process(pid: int):
    if not pid:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    else:
        try:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
        except ProcessLookupError:
            pass


def _wait_for_process_exit(pid: int, timeout_sec: int = 8) -> bool:
    if not pid:
        return True
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if not _is_process_alive(pid):
            return True
        time.sleep(0.5)
    return not _is_process_alive(pid)


def _upsert_app(name: str, **fields):
    safe_name = _sanitize_name(name)
    conn = _get_conn()
    row = conn.execute("SELECT name FROM expo_apps WHERE name=?", (safe_name,)).fetchone()
    now = _now()
    if row:
        fields["updated_at"] = now
        assignments = ", ".join(f"{key}=?" for key in fields)
        values = list(fields.values()) + [safe_name]
        conn.execute(f"UPDATE expo_apps SET {assignments} WHERE name=?", values)
    else:
        payload = {
            "name": safe_name,
            "template": fields.pop("template", "blank"),
            "created_at": now,
            "updated_at": now,
            "status": fields.pop("status", "stopped"),
            "pid": fields.pop("pid", None),
            "port": fields.pop("port", None),
            "launch_url": fields.pop("launch_url", ""),
            "tunnel_url": fields.pop("tunnel_url", ""),
            "web_url": fields.pop("web_url", ""),
            "log_path": fields.pop("log_path", ""),
            "last_error": fields.pop("last_error", ""),
        }
        payload.update(fields)
        conn.execute(
            """
            INSERT INTO expo_apps (
                name, template, created_at, updated_at, status, pid, port,
                launch_url, tunnel_url, web_url, log_path, last_error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["name"],
                payload["template"],
                payload["created_at"],
                payload["updated_at"],
                payload["status"],
                payload["pid"],
                payload["port"],
                payload["launch_url"],
                payload["tunnel_url"],
                payload["web_url"],
                payload["log_path"],
                payload["last_error"],
            ),
        )
    conn.commit()
    conn.close()


def _get_app_row(name: str):
    conn = _get_conn()
    row = conn.execute("SELECT * FROM expo_apps WHERE name=?", (_sanitize_name(name),)).fetchone()
    conn.close()
    return dict(row) if row else None


def _read_log_tail(log_path: str, max_chars: int = 24000) -> str:
    if not log_path:
        return ""
    path = Path(log_path)
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[-max_chars:]


def _parse_urls(log_text: str):
    parsed = {"launch_url": "", "tunnel_url": "", "web_url": ""}
    patterns = {
        "launch_url": [
            r"(exp(?:s)?:\/\/[^\s\"']+)",
        ],
        "tunnel_url": [
            r"(https:\/\/[^\s\"']+\.exp\.direct[^\s\"']*)",
            r"(https:\/\/[^\s\"']+expo\.dev[^\s\"']*)",
        ],
        "web_url": [
            r"(https?:\/\/(?:localhost|127\.0\.0\.1):\d+[^\s\"']*)",
        ],
    }
    for key, pattern_list in patterns.items():
        for pattern in pattern_list:
            match = re.search(pattern, log_text, flags=re.IGNORECASE)
            if match:
                parsed[key] = match.group(1)
                break
    return parsed


def _parse_last_error(log_text: str) -> str:
    if not log_text:
        return ""
    lines = [line.strip() for line in log_text.splitlines() if line.strip()]
    low = log_text.lower()
    if "@expo/ngrok" in low and "required to use tunnels" in low:
        return "Tunnel mode requires @expo/ngrok. Falling back to LAN preview."
    for line in reversed(lines):
        if line.startswith("CommandError:"):
            return line
        if line.startswith("Error:"):
            return line
    return ""


def _detect_local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        pass
    try:
        return socket.gethostbyname(socket.gethostname())
    except OSError:
        return ""


def _build_lan_launch_url(port) -> str:
    if not port:
        return ""
    local_ip = _detect_local_ip()
    if not local_ip:
        return ""
    return f"exp://{local_ip}:{port}"


def refresh_app(name: str):
    row = _get_app_row(name)
    if not row:
        return None
    is_alive = _is_process_alive(row.get("pid"))
    log_text = _read_log_tail(row.get("log_path", ""))
    urls = _parse_urls(log_text)
    parsed_error = _parse_last_error(log_text)
    status = row.get("status", "stopped")
    if status == "running" and not is_alive:
        status = "stopped"
    update_fields = {
        "status": status,
        "launch_url": urls["launch_url"] or row.get("launch_url", ""),
        "tunnel_url": urls["tunnel_url"] or row.get("tunnel_url", ""),
        "web_url": urls["web_url"] or row.get("web_url", ""),
        "last_error": "" if (urls["launch_url"] or urls["tunnel_url"]) else (parsed_error or row.get("last_error", "")),
    }
    if not is_alive:
        update_fields["pid"] = None
    _upsert_app(name, **update_fields)
    fresh = _get_app_row(name) or {}
    fresh["is_running"] = fresh.get("status") == "running" and _is_process_alive(fresh.get("pid"))
    fresh["project_dir"] = str(_project_dir(name))
    return fresh


def list_apps():
    conn = _get_conn()
    rows = conn.execute("SELECT name FROM expo_apps ORDER BY updated_at DESC").fetchall()
    conn.close()
    return [refresh_app(row["name"]) for row in rows]


def _default_app_json(name: str) -> str:
    safe_name = _sanitize_name(name)
    data = {
        "expo": {
            "name": safe_name,
            "slug": safe_name,
            "version": "1.0.0",
            "orientation": "portrait",
            "userInterfaceStyle": "automatic",
            "assetBundlePatterns": ["**/*"],
        }
    }
    return json.dumps(data, indent=2)


def _write_project_files(name: str, app_js: str, app_json: str = ""):
    project_dir = _project_dir(name)
    if not project_dir.exists():
        raise RuntimeError(f"Project '{_sanitize_name(name)}' does not exist")

    app_code = (app_js or "").strip()
    if not app_code:
        raise RuntimeError("App.js content is required")

    (project_dir / "App.js").write_text(app_code + "\n", encoding="utf-8")
    tsx_path = project_dir / "App.tsx"
    if tsx_path.exists():
        tsx_path.unlink()

    app_json_text = (app_json or "").strip() or _default_app_json(name)
    try:
        parsed = json.loads(app_json_text)
        app_json_text = json.dumps(parsed, indent=2)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"app_json must be valid JSON: {exc}") from exc
    (project_dir / "app.json").write_text(app_json_text + "\n", encoding="utf-8")


def _missing_web_dependencies(project_dir: Path):
    pkg_path = project_dir / "package.json"
    if not pkg_path.exists():
        return ["react-dom", "react-native-web"]
    try:
        pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
    except Exception:
        return ["react-dom", "react-native-web"]
    deps = pkg.get("dependencies", {})
    missing = []
    for dep in ("react-dom", "react-native-web"):
        if dep not in deps:
            missing.append(dep)
    return missing


def _ensure_web_dependencies(project_dir: Path):
    missing = _missing_web_dependencies(project_dir)
    if not missing:
        return
    cmd = [_npx_command(), "expo", "install", *missing]
    kwargs = {
        "cwd": str(project_dir),
        "capture_output": True,
        "text": True,
        "timeout": 1800,
        "stdin": subprocess.DEVNULL,
    }
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        message = stderr or stdout or f"Failed to install Expo web dependencies: {', '.join(missing)}"
        raise RuntimeError(message[-1200:])


def scaffold_app(name: str, template: str = "blank"):
    safe_name = _sanitize_name(name)
    project_dir = _project_dir(name)
    resolved_template = _resolve_template(template)
    if (project_dir / "package.json").exists():
        _upsert_app(safe_name, template=resolved_template)
        return project_dir

    APPS_DIR.mkdir(parents=True, exist_ok=True)
    cmd = [_npx_command(), "create-expo-app@latest", safe_name, "--template", resolved_template, "--yes"]
    kwargs = {
        "cwd": str(APPS_DIR),
        "capture_output": True,
        "text": True,
        "timeout": 1800,
        "stdin": subprocess.DEVNULL,
    }
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0 or not (project_dir / "package.json").exists():
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        message = stderr or stdout or "create-expo-app failed"
        raise RuntimeError(message[-1200:])

    _upsert_app(safe_name, template=resolved_template, status="stopped", last_error="")
    return project_dir


def start_app(name: str, tunnel: bool = True):
    safe_name = _sanitize_name(name)
    project_dir = _project_dir(safe_name)
    if not (project_dir / "package.json").exists():
        raise RuntimeError(f"Project '{safe_name}' does not exist")

    _ensure_web_dependencies(project_dir)

    current = refresh_app(safe_name)
    if current and current.get("is_running"):
        last_error = (current.get("last_error") or "").lower()
        needs_lan_restart = (
            not tunnel
            and "@expo/ngrok" in last_error
        )
        if needs_lan_restart and current.get("pid") and _is_process_alive(current["pid"]):
            _stop_process(int(current["pid"]))
            _wait_for_process_exit(int(current["pid"]))
            _upsert_app(safe_name, status="stopped", pid=None, launch_url="", tunnel_url="", web_url="")
            current = refresh_app(safe_name)
        elif not (current.get("launch_url") or current.get("tunnel_url")) and current.get("port"):
            lan_url = _build_lan_launch_url(current.get("port"))
            if lan_url:
                _upsert_app(safe_name, launch_url=lan_url)
                current = refresh_app(safe_name)
        if current and current.get("is_running"):
            return current

    port = _find_free_port()
    log_path = LOGS_DIR / f"{safe_name}_{int(time.time())}.log"
    log_handle = open(log_path, "w", encoding="utf-8")

    cmd = [_npx_command(), "expo", "start", "--port", str(port), "--web"]
    cmd.append("--tunnel" if tunnel else "--lan")

    env = os.environ.copy()
    env["EXPO_NO_TELEMETRY"] = "1"
    env.setdefault("BROWSER", "none")

    kwargs = {
        "cwd": str(project_dir),
        "env": env,
        "stdin": subprocess.DEVNULL,
        "stdout": log_handle,
        "stderr": subprocess.STDOUT,
    }
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(
            subprocess, "CREATE_NEW_PROCESS_GROUP", 0
        )
    else:
        kwargs["preexec_fn"] = os.setsid

    proc = subprocess.Popen(cmd, **kwargs)
    log_handle.close()

    _upsert_app(
        safe_name,
        status="running",
        pid=proc.pid,
        port=port,
        log_path=str(log_path),
        last_error="",
    )

    for _ in range(25):
        time.sleep(1)
        refreshed = refresh_app(safe_name)
        if refreshed:
            last_error = (refreshed.get("last_error") or "").lower()
            if tunnel and "@expo/ngrok" in last_error:
                if _is_process_alive(proc.pid):
                    _stop_process(proc.pid)
                    _wait_for_process_exit(proc.pid)
                _upsert_app(safe_name, status="stopped", pid=None, launch_url="", tunnel_url="", web_url="")
                return start_app(safe_name, tunnel=False)
            if refreshed.get("launch_url") or refreshed.get("tunnel_url"):
                _upsert_app(safe_name, last_error="")
                return refreshed
            if not refreshed.get("is_running"):
                return refreshed
        if not _is_process_alive(proc.pid):
            break

    refreshed = refresh_app(safe_name)
    if refreshed and tunnel and "@expo/ngrok" in (refreshed.get("last_error") or "").lower():
        if refreshed.get("pid") and _is_process_alive(refreshed["pid"]):
            _stop_process(int(refreshed["pid"]))
            _wait_for_process_exit(int(refreshed["pid"]))
        _upsert_app(safe_name, status="stopped", pid=None, launch_url="", tunnel_url="", web_url="")
        return start_app(safe_name, tunnel=False)

    if refreshed and refreshed.get("is_running") and not (refreshed.get("launch_url") or refreshed.get("tunnel_url")):
        if not tunnel:
            lan_url = _build_lan_launch_url(port)
            if lan_url:
                _upsert_app(safe_name, launch_url=lan_url, last_error="")
                refreshed = refresh_app(safe_name)
        if refreshed and not (refreshed.get("launch_url") or refreshed.get("tunnel_url")):
            refreshed["last_error"] = "Expo is running but no device launch link was captured yet. Wait a bit longer and refresh status."
            _upsert_app(safe_name, status="running", last_error=refreshed["last_error"])
            refreshed = refresh_app(safe_name)
    return refreshed or {}


def stop_app(name: str):
    safe_name = _sanitize_name(name)
    row = _get_app_row(safe_name)
    if not row:
        raise RuntimeError(f"Project '{safe_name}' not found")
    if row.get("pid"):
        _stop_process(int(row["pid"]))
    _upsert_app(
        safe_name,
        status="stopped",
        pid=None,
        launch_url="",
        tunnel_url="",
        web_url="",
    )
    return refresh_app(safe_name)


def create_app(name: str, app_js: str, app_json: str = "", template: str = "blank", auto_start: bool = True, tunnel: bool = True):
    safe_name = _sanitize_name(name)
    resolved_template = _resolve_template(template)
    scaffold_app(safe_name, template=resolved_template)
    _write_project_files(safe_name, app_js, app_json)
    _upsert_app(safe_name, template=resolved_template, status="stopped", last_error="")
    return start_app(safe_name, tunnel=tunnel) if auto_start else refresh_app(safe_name)


def edit_app(name: str, app_js: str, app_json: str = ""):
    safe_name = _sanitize_name(name)
    _write_project_files(safe_name, app_js, app_json)
    _upsert_app(safe_name, last_error="")
    return refresh_app(safe_name)


def delete_app(name: str):
    safe_name = _sanitize_name(name)
    row = _get_app_row(safe_name)
    if row and row.get("pid"):
        _stop_process(int(row["pid"]))

    project_dir = _project_dir(safe_name)
    if project_dir.exists():
        shutil.rmtree(project_dir)

    conn = _get_conn()
    conn.execute("DELETE FROM expo_apps WHERE name=?", (safe_name,))
    conn.commit()
    conn.close()
    return {"name": safe_name, "deleted": True}


def format_app_summary(app: dict) -> str:
    if not app:
        return "No Expo app data available."
    lines = [f"📱 **{app.get('name', 'expo-app')}**"]
    lines.append(f"Status: {'running' if app.get('is_running') else app.get('status', 'stopped')}")
    primary_link = app.get("launch_url") or app.get("tunnel_url")
    if primary_link:
        lines.append(f"Expo Go link: {primary_link}")
    if app.get("launch_url") and app.get("tunnel_url") and app["launch_url"] != app["tunnel_url"]:
        lines.append(f"Tunnel URL: {app['tunnel_url']}")
    if app.get("web_url"):
        lines.append(f"Web preview: {app['web_url']}")
    if app.get("port"):
        lines.append(f"Port: {app['port']}")
    if app.get("last_error"):
        lines.append(f"Last error: {app['last_error']}")
    return "\n".join(lines)
