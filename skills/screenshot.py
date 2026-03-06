"""
Screenshot skill — capture your PC screen and send it to Telegram.
No API keys needed. Works on Windows, macOS, and Linux.
"""
import os
import sys
import tempfile
import time

SKILL_INFO = {
    "name": "screenshot",
    "description": "Capture your PC screen and send it as a photo",
    "version": "1.0",
    "icon": "📸",
    "author": "ninoclaw",
    "requires_key": False,
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "take_screenshot",
            "description": "Take a screenshot of the PC screen and send it. Use when user says 'take a screenshot', 'show my screen', 'capture screen', 'screenshot', etc.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


def _capture():
    """Capture the screen and return the file path."""
    tmp_dir = tempfile.gettempdir()
    path = os.path.join(tmp_dir, f"ninoclaw_screenshot_{int(time.time())}.png")

    # Try mss first (fast, cross-platform)
    try:
        import mss
        with mss.mss() as sct:
            sct.shot(output=path)
        return path, None
    except ImportError:
        pass

    # Try PIL/Pillow
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        img.save(path)
        return path, None
    except ImportError:
        pass

    # Windows fallback: use PowerShell
    if sys.platform == "win32":
        import subprocess
        ps_script = f"""
        Add-Type -AssemblyName System.Windows.Forms
        $bmp = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
        $bitmap = New-Object System.Drawing.Bitmap($bmp.Width, $bmp.Height)
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        $graphics.CopyFromScreen($bmp.Location, [System.Drawing.Point]::Empty, $bmp.Size)
        $bitmap.Save('{path}')
        """
        subprocess.run(["powershell", "-Command", ps_script],
                       capture_output=True, timeout=10)
        if os.path.exists(path):
            return path, None

    return None, "❌ Screenshot failed. Install Pillow: `pip install Pillow`"


def execute(tool_name, arguments):
    if tool_name != "take_screenshot":
        return None
    try:
        path, err = _capture()
        if err:
            return err
        return f"[IMAGE:{path}]\n📸 Screenshot captured!"
    except Exception as e:
        return f"❌ Screenshot error: {e}"
