"""
App Launcher skill — open, close, and manage apps on your PC from Telegram.
Windows-focused. No API keys needed.
"""
import subprocess
import sys
import os
import re

SKILL_INFO = {
    "name": "app_launcher",
    "description": "Open and close apps on your PC remotely",
    "version": "1.0",
    "icon": "🚀",
    "author": "ninoclaw",
    "requires_key": False,
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": "Open an application on the PC. Examples: 'open Chrome', 'open VS Code', 'open Notepad', 'open File Explorer', 'open Calculator'",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {"type": "string", "description": "Name of the application to open"},
                },
                "required": ["app_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "close_app",
            "description": "Close/kill an application running on the PC. Examples: 'close Chrome', 'close Notepad'",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {"type": "string", "description": "Name of the application to close"},
                },
                "required": ["app_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_running_apps",
            "description": "List currently running applications on the PC",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]

# ── App name → command mapping (Windows) ─────────────────────────────────────

_WIN_APPS = {
    # Browsers
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "firefox": "firefox.exe",
    "edge": "msedge.exe",
    "microsoft edge": "msedge.exe",
    "brave": "brave.exe",
    # Dev tools
    "vscode": "Code.exe",
    "vs code": "Code.exe",
    "visual studio code": "Code.exe",
    "terminal": "wt.exe",
    "windows terminal": "wt.exe",
    "cmd": "cmd.exe",
    "powershell": "powershell.exe",
    "git bash": "C:\\Program Files\\Git\\git-bash.exe",
    # System
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "file explorer": "explorer.exe",
    "explorer": "explorer.exe",
    "task manager": "taskmgr.exe",
    "settings": "ms-settings:",
    "control panel": "control.exe",
    "paint": "mspaint.exe",
    "snipping tool": "snippingtool.exe",
    # Media
    "spotify": "spotify:",
    "vlc": "vlc.exe",
    # Office
    "word": "winword.exe",
    "excel": "excel.exe",
    "powerpoint": "powerpnt.exe",
    # Communication
    "whatsapp": "whatsapp:",
    "telegram": "tg:",
    "discord": "discord:",
    "teams": "msteams:",
    "zoom": "zoom.exe",
}

# Process names for closing apps
_WIN_PROCESSES = {
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "firefox": "firefox.exe",
    "edge": "msedge.exe",
    "microsoft edge": "msedge.exe",
    "brave": "brave.exe",
    "vscode": "Code.exe",
    "vs code": "Code.exe",
    "visual studio code": "Code.exe",
    "notepad": "notepad.exe",
    "vlc": "vlc.exe",
    "spotify": "Spotify.exe",
    "discord": "Discord.exe",
    "telegram": "Telegram.exe",
    "teams": "Teams.exe",
    "zoom": "Zoom.exe",
    "word": "WINWORD.EXE",
    "excel": "EXCEL.EXE",
    "powerpoint": "POWERPNT.EXE",
    "paint": "mspaint.exe",
    "task manager": "Taskmgr.exe",
    "calculator": "Calculator.exe",
}


def _fuzzy_match(name, mapping):
    """Find the best match for a (possibly misspelled) app name."""
    # Exact match
    if name in mapping:
        return name
    # Substring: user input is contained in a known app name, or vice versa
    for key in mapping:
        if name in key or key in name:
            return key
    # Partial overlap: check if 3+ consecutive chars match (handles 'rome' → 'chrome')
    for key in mapping:
        for i in range(len(name) - 2):
            if name[i:i+3] in key:
                return key
    return None


def _open_app(app_name):
    if sys.platform != "win32":
        return "❌ App launcher currently supports Windows only."

    name = app_name.lower().strip()
    target = _WIN_APPS.get(name)

    if not target:
        # Try fuzzy match
        match = _fuzzy_match(name, _WIN_APPS)
        if match:
            target = _WIN_APPS[match]
            name = match  # Use the matched name for the response

    if not target:
        return (
            f"❌ Unknown app: {app_name}. For security, only known apps are allowed. "
            f"Try names like Chrome, VS Code, Notepad, Spotify, etc."
        )

    try:
        os.startfile(target)  # noqa: S606 - starts a fixed local app target/URI
        return f"🚀 Opened **{name.title()}**!"
    except Exception as e:
        return f"❌ Could not open {app_name}: {e}"


def _close_app(app_name):
    if sys.platform != "win32":
        return "❌ App launcher currently supports Windows only."

    name = app_name.lower().strip()
    process = _WIN_PROCESSES.get(name)
    if not process:
        safe = re.sub(r"[^a-z0-9_.-]", "", name)
        if not safe:
            return "❌ Invalid app/process name."
        process = safe if safe.endswith(".exe") else f"{safe}.exe"

    if not re.fullmatch(r"[A-Za-z0-9_.-]+\.exe", process):
        return "❌ Invalid process name."

    try:
        result = subprocess.run(
            ["taskkill", "/IM", process, "/F"],
            shell=False, capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return f"✅ Closed **{app_name}**."
        elif "not found" in result.stderr.lower():
            return f"⚠️ **{app_name}** is not currently running."
        else:
            return f"❌ Could not close {app_name}: {result.stderr.strip()}"
    except Exception as e:
        return f"❌ Error closing {app_name}: {e}"


def _list_running():
    if sys.platform != "win32":
        return "❌ App listing currently supports Windows only."

    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-Process | Where-Object {$_.MainWindowTitle -ne ''} | "
                "Select-Object -Property Name,MainWindowTitle | Format-Table -AutoSize",
            ],
            shell=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        apps = result.stdout.strip()
        if not apps:
            return "📋 No visible applications running."

        # Parse and format nicely
        lines = apps.strip().split("\n")
        if len(lines) <= 2:
            return "📋 No visible applications running."

        formatted = ["📋 **Running Applications:**", ""]
        for line in lines[2:]:  # Skip header
            parts = line.strip().split(None, 1)
            if len(parts) == 2:
                name, title = parts
                formatted.append(f"  • **{name}** — {title}")
            elif parts:
                formatted.append(f"  • {parts[0]}")
        return "\n".join(formatted[:25])  # Limit to 25 apps
    except Exception as e:
        return f"❌ Error listing apps: {e}"


def execute(tool_name, arguments):
    try:
        if tool_name == "open_app":
            return _open_app(arguments.get("app_name", ""))
        elif tool_name == "close_app":
            return _close_app(arguments.get("app_name", ""))
        elif tool_name == "list_running_apps":
            return _list_running()
    except Exception as e:
        return f"❌ App launcher error: {e}"
    return None
