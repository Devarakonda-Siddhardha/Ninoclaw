"""
Security audit — runs every 30 minutes, sends Telegram alert only if issues found.
Checks: .env permissions, exposed secrets in skills, disk space, open ports, pip vulnerabilities.
"""
import os
import re
import stat
import shutil
import asyncio
import subprocess
import threading
from datetime import datetime

_BASE = os.path.dirname(__file__)

# ── Individual checks ──────────────────────────────────────────────────────────

def check_env_permissions():
    """Warn if .env is readable by group/others. Skip on Windows due to stat mode handling."""
    issues = []
    import sys
    if sys.platform == "win32":
        return issues
        
    env_path = os.path.join(_BASE, ".env")
    if os.path.exists(env_path):
        mode = os.stat(env_path).st_mode
        if mode & (stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH):
            issues.append(f"⚠️ `.env` has loose permissions ({oct(mode)[-3:]}). Run: `chmod 600 .env`")
    return issues


def check_exposed_secrets():
    """Scan skill files and project root for hardcoded secrets."""
    issues = []
    secret_pattern = re.compile(
        r'(?i)(api[_-]?key|secret|password|token|bearer)\s*[=:]\s*["\']([A-Za-z0-9\-_\.]{16,})["\']'
    )
    skip_files = {".env", "memory.json", "ninoclaw.db"}
    scan_dirs = [
        os.path.join(_BASE, "skills"),
        _BASE,
    ]
    scanned = set()
    for d in scan_dirs:
        if not os.path.isdir(d):
            continue
        for fname in os.listdir(d):
            if fname in skip_files or not fname.endswith(".py"):
                continue
            fpath = os.path.join(d, fname)
            if fpath in scanned:
                continue
            scanned.add(fpath)
            try:
                content = open(fpath).read()
                matches = secret_pattern.findall(content)
                for key_type, val in matches:
                    # Ignore obvious placeholders
                    if val.lower() in ("your_key_here", "xxx", "changeme", "placeholder"):
                        continue
                    issues.append(f"🔑 Possible hardcoded secret in `{fname}`: `{key_type}=...{val[-4:]}`")
            except Exception:
                pass
    return issues


def check_disk_space():
    """Warn if disk usage > 85%."""
    issues = []
    try:
        usage = shutil.disk_usage(_BASE)
        pct = usage.used / usage.total * 100
        free_mb = usage.free // (1024 * 1024)
        if pct > 90:
            issues.append(f"🚨 Disk critically full: {pct:.0f}% used, only {free_mb}MB free!")
        elif pct > 85:
            issues.append(f"⚠️ Disk space low: {pct:.0f}% used, {free_mb}MB free")
    except Exception:
        pass
    return issues


def check_open_ports():
    """Warn about unexpected listening ports (anything beyond 8080 and Telegram)."""
    issues = []
    try:
        result = subprocess.run(
            ["ss", "-tlnp"], capture_output=True, text=True, timeout=5
        )
        expected = {"8080", "443", "80"}
        for line in result.stdout.splitlines()[1:]:
            parts = line.split()
            if len(parts) < 4:
                continue
            addr = parts[3]
            port = addr.rsplit(":", 1)[-1]
            if port not in expected and port.isdigit() and int(port) > 1024:
                issues.append(f"🔓 Unexpected open port: `{port}` — verify this is intentional")
    except Exception:
        pass
    return issues


def check_pip_vulnerabilities():
    """Run pip-audit if available; report any known CVEs."""
    issues = []
    try:
        result = subprocess.run(
            ["pip-audit", "--format", "columns", "-q"],
            capture_output=True, text=True, timeout=30
        )
        lines = [l for l in result.stdout.splitlines() if l.strip() and "No known" not in l]
        if lines:
            count = len(lines)
            issues.append(f"📦 {count} package(s) with known vulnerabilities (run `pip-audit` to see details)")
    except FileNotFoundError:
        pass  # pip-audit not installed — skip silently
    except Exception:
        pass
    return issues


def check_memory_db():
    """Warn if ninoclaw.db is unexpectedly large (>50MB)."""
    issues = []
    db = os.path.join(_BASE, "ninoclaw.db")
    if os.path.exists(db):
        size_mb = os.path.getsize(db) / (1024 * 1024)
        if size_mb > 50:
            issues.append(f"💾 Database large: `ninoclaw.db` is {size_mb:.1f}MB — consider cleanup")
    return issues


# ── Main audit runner ──────────────────────────────────────────────────────────

def run_audit():
    """Run all checks, return list of issues (empty = all clear)."""
    issues = []
    issues += check_env_permissions()
    issues += check_exposed_secrets()
    issues += check_disk_space()
    issues += check_open_ports()
    issues += check_pip_vulnerabilities()
    issues += check_memory_db()
    return issues


def format_report(issues):
    now = datetime.now().strftime("%H:%M, %d %b")
    if not issues:
        return None  # silent when clean
    header = f"🛡️ **Security Audit** ({now})\n{'─'*30}\n"
    body = "\n".join(f"• {i}" for i in issues)
    # AI-written advisory using fast/cheap model
    try:
        from ai import chat
        advice = chat(
            message=f"Security audit found these issues:\n{body}\n\nGive a 1-2 sentence plain-English summary and the single most important fix. Be brief.",
            system_prompt="You are a concise security advisor. No markdown headers. Plain text only.",
            force_fast=True,
        )
        if isinstance(advice, dict):
            advice = advice.get("content", "")
        if advice:
            body += f"\n\n💡 {advice.strip()}"
    except Exception:
        pass
    footer = "\n\nRun `ninoclaw audit` for details."
    return header + body + footer


# ── Background loop ────────────────────────────────────────────────────────────

class SecurityAuditor:
    def __init__(self):
        self.notify_fn = None   # async callable(user_id, msg)
        self.owner_id  = None   # str
        self._thread   = None
        self.interval  = 1800   # 30 minutes

    def start(self, notify_fn, owner_id):
        self.notify_fn = notify_fn
        self.owner_id  = str(owner_id)
        self._thread   = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._loop())

    async def _loop(self):
        # First audit after 5 minutes (let bot fully start)
        await asyncio.sleep(300)
        while True:
            await self._do_audit()
            await asyncio.sleep(self.interval)

    async def _do_audit(self):
        try:
            issues = run_audit()
            report = format_report(issues)
            if report and self.notify_fn and self.owner_id:
                await self.notify_fn(self.owner_id, report)
        except Exception as e:
            print(f"[Security Audit] Error: {e}")

    def run_now(self):
        """Return report string immediately (for CLI use)."""
        issues = run_audit()
        now = datetime.now().strftime("%H:%M, %d %b")
        if not issues:
            return f"🛡️ Security Audit ({now})\n✅ All clear — no issues found."
        header = f"🛡️ Security Audit ({now})\n{'─'*30}\n"
        return header + "\n".join(f"• {i}" for i in issues)


security_auditor = SecurityAuditor()
