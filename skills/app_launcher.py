"""
App Launcher skill — open, close, and manage apps on your PC from Telegram.
Windows-focused. No API keys needed.
"""
import subprocess
import sys
import os

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
    "chrome": "start chrome",
    "google chrome": "start chrome",
    "firefox": "start firefox",
    "edge": "start msedge",
    "microsoft edge": "start msedge",
    "brave": "start brave",
    # Dev tools
    "vscode": "code",
    "vs code": "code",
    "visual studio code": "code",
    "terminal": "start wt",
    "windows terminal": "start wt",
    "cmd": "start cmd",
    "powershell": "start powershell",
    "git bash": "start \"\" \"C:\\Program Files\\Git\\git-bash.exe\"",
    # System
    "notepad": "start notepad",
    "calculator": "start calc",
    "calc": "start calc",
    "file explorer": "start explorer",
    "explorer": "start explorer",
    "task manager": "start taskmgr",
    "settings": "start ms-settings:",
    "control panel": "start control",
    "paint": "start mspaint",
    "snipping tool": "start snippingtool",
    # Media
    "spotify": "start spotify:",
    "vlc": "start vlc",
    # Office
    "word": "start winword",
    "excel": "start excel",
    "powerpoint": "start powerpnt",
    # Communication
    "whatsapp": "start whatsapp:",
    "telegram": "start telegram:",
    "discord": "start discord:",
    "teams": "start msteams:",
    "zoom": "start zoom",
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
    cmd = _WIN_APPS.get(name)

    if not cmd:
        # Try fuzzy match
        match = _fuzzy_match(name, _WIN_APPS)
        if match:
            cmd = _WIN_APPS[match]
            name = match  # Use the matched name for the response

    if not cmd:
        # Last resort: try to launch it directly
        cmd = f"start {name}"

    try:
        subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return f"🚀 Opened **{name.title()}**!"
    except Exception as e:
        return f"❌ Could not open {app_name}: {e}"


def _close_app(app_name):
    if sys.platform != "win32":
        return "❌ App launcher currently supports Windows only."

    name = app_name.lower().strip()
    process = _WIN_PROCESSES.get(name, f"{name}.exe")

    try:
        result = subprocess.run(
            f"taskkill /IM \"{process}\" /F",
            shell=True, capture_output=True, text=True, timeout=10
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
            'powershell -Command "Get-Process | Where-Object {$_.MainWindowTitle -ne \'\'} | Select-Object -Property Name,MainWindowTitle | Format-Table -AutoSize"',
            shell=True, capture_output=True, text=True, timeout=10
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
