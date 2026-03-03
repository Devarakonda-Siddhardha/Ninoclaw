"""
security.py — Central security module for Ninoclaw
All sensitive operations must go through these helpers.
"""
import os
import re
import ast
import time
from functools import wraps
from typing import Optional

# ── Owner check ───────────────────────────────────────────────────────────────

def require_owner(user_id: int) -> Optional[str]:
    """
    Returns None if user is the owner, else an error string.
    FAILS CLOSED: if OWNER_ID is not configured, ALL users are blocked.
    """
    from config import OWNER_ID
    if not OWNER_ID:
        return "❌ OWNER_ID is not set in .env — system tools are disabled until you configure it."
    if int(user_id) != int(OWNER_ID):
        return "❌ This action is restricted to the bot owner."
    return None


# ── Path safety ───────────────────────────────────────────────────────────────

# Absolute paths that are always blocked
_BLOCKED_PATHS = [
    ".env", "/.env",
    "id_rsa", "id_ed25519", "id_ecdsa", "id_dsa",
    ".ssh",
    "shadow", "/etc/shadow",
    "passwd", "/etc/passwd",
    ".bashrc", ".bash_history", ".zsh_history",
    "authorized_keys",
    "known_hosts",
]

def safe_path(path: str) -> Optional[str]:
    """
    Returns None if path is safe, else an error string.
    Blocks traversal and sensitive files.
    """
    expanded = os.path.abspath(os.path.expanduser(path))

    # Block path traversal attempts
    if ".." in path:
        return f"❌ Path traversal blocked: `{path}`"

    # Block sensitive files/dirs
    lower = expanded.lower()
    for blocked in _BLOCKED_PATHS:
        if blocked.lower() in lower:
            return f"❌ Access to `{blocked}` is blocked for security."

    return None


# ── Command safety ────────────────────────────────────────────────────────────

_BLOCKED_COMMANDS = [
    # Destructive
    "rm -rf /", "rm -rf ~", "rm -rf /*",
    "mkfs", "fdisk", "parted", "wipefs",
    "dd if=/dev/zero", "dd if=/dev/urandom",
    "shred",
    # Fork bomb
    ":(){:|:&};:",
    # Privilege escalation
    "chmod 777 /", "chmod -R 777 /",
    "chown -R root",
    # Exfiltration / backdoors
    "curl | bash", "wget | bash", "curl | sh", "wget | sh",
    "bash <(curl", "bash <(wget",
    # Erase bot config
    "rm .env", "rm -f .env", "truncate .env",
    # Shutdown
    "shutdown", "reboot", "halt", "poweroff",
    # Write to crontab as root
    "crontab -r",
]

def safe_command(command: str) -> Optional[str]:
    """
    Returns None if command is safe, else an error string.
    """
    lower = command.lower().strip()
    for blocked in _BLOCKED_COMMANDS:
        if blocked.lower() in lower:
            return f"❌ Blocked command pattern: `{blocked}`"

    # Block commands that pipe to shell interpreters from internet
    if re.search(r'(curl|wget)\s+.*\|\s*(bash|sh|python|python3|perl|ruby)', lower):
        return "❌ Piping remote content to a shell interpreter is blocked."

    return None


# ── Skill code validation ─────────────────────────────────────────────────────

_BLOCKED_IMPORTS = {
    "subprocess", "os.system", "pty", "socket",
    "pickle", "marshal", "ctypes", "cffi",
    "__import__", "importlib.util.spec_from_file_location",
}

def validate_skill_code(code: str) -> Optional[str]:
    """
    Validates skill code with AST parsing.
    Returns None if safe, else an error string.
    """
    # Must have required structure
    for required in ("SKILL_INFO", "TOOLS", "def execute"):
        if required not in code:
            return f"❌ Skill code missing required: `{required}`"

    # Parse AST — catches syntax errors
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return f"❌ Syntax error in skill code: {e}"

    # Walk AST for dangerous patterns
    for node in ast.walk(tree):
        # Block dangerous imports
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                if name in _BLOCKED_IMPORTS:
                    return f"❌ Skill cannot import `{name}` (blocked for security)."

        # Block exec() and eval() calls
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in ("exec", "eval", "compile", "__import__"):
                return f"❌ Skill cannot use `{func.id}()` (blocked)."

        # Block open() for writing (skills should not write arbitrary files)
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "open":
                for kw in node.keywords:
                    if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                        if "w" in str(kw.value.value) or "a" in str(kw.value.value):
                            return "❌ Skill cannot open files for writing."
                # Also check positional mode arg
                if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
                    mode = str(node.args[1].value)
                    if "w" in mode or "a" in mode:
                        return "❌ Skill cannot open files for writing."

    return None


# ── Dashboard brute-force protection ─────────────────────────────────────────

_login_attempts: dict = {}  # ip -> [timestamps]
_LOGIN_WINDOW = 300   # 5 minutes
_LOGIN_MAX = 5        # max attempts per window

def check_login_rate(ip: str) -> Optional[str]:
    """
    Returns None if login is allowed, else an error string.
    Limits to _LOGIN_MAX attempts per _LOGIN_WINDOW seconds per IP.
    """
    now = time.time()
    attempts = _login_attempts.get(ip, [])
    # Prune old attempts
    attempts = [t for t in attempts if now - t < _LOGIN_WINDOW]
    if len(attempts) >= _LOGIN_MAX:
        wait = int(_LOGIN_WINDOW - (now - attempts[0]))
        return f"Too many login attempts. Try again in {wait}s."
    attempts.append(now)
    _login_attempts[ip] = attempts
    return None

def reset_login_rate(ip: str):
    """Clear rate limit on successful login."""
    _login_attempts.pop(ip, None)
