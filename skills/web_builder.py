"""
Web Builder skill — generate and preview websites from Telegram.

Flow:
  1. User says "build me a portfolio site"
  2. AI generates HTML/CSS/JS and calls web_build(name, html)
  3. Skill saves files to websites/<name>/index.html
  4. Returns a live preview link (served via dashboard Flask)

Preview is accessible from: http://<pc-ip>:8080/builds/<name>
"""
import os
import re
import shutil
from pathlib import Path

SKILL_INFO = {
    "name": "web_builder",
    "description": "Build and preview websites — generate HTML/CSS/JS from a description",
    "version": "1.0",
    "icon": "🌐",
    "author": "ninoclaw",
    "requires_key": False,
}

WEBSITES_DIR = Path(__file__).parent.parent / "websites"

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_build",
            "description": "Create a new website. Generate beautiful, modern HTML with inline CSS and JS. The html parameter must contain a COMPLETE, valid HTML document (<!DOCTYPE html>...) with all styling and logic included inline. Make it visually stunning with gradients, animations, and modern design. If image URLs are provided in context, use them directly in <img src=\"...\">. After creating, the user gets a live preview link.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Short name for the project (lowercase, no spaces, e.g. 'portfolio', 'landing-page', 'todo-app')"
                    },
                    "html": {
                        "type": "string",
                        "description": "Complete HTML document with inline CSS and JS. Must be a full valid page starting with <!DOCTYPE html>."
                    },
                },
                "required": ["name", "html"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_edit",
            "description": "Edit an existing website's HTML. Provide the full updated HTML to replace the current file. Reuse provided image URLs when requested.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Project name to edit (must already exist)"
                    },
                    "html": {
                        "type": "string",
                        "description": "The full updated HTML document to replace the existing one."
                    },
                },
                "required": ["name", "html"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_list",
            "description": "List all built websites with their preview links. Use when user asks 'show my builds', 'list websites', 'my sites', etc.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_delete",
            "description": "Delete a built website project.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Project name to delete"},
                },
                "required": ["name"],
            },
        },
    },
]


def _sanitize_name(name):
    """Clean project name to be filesystem-safe."""
    name = re.sub(r'[^a-z0-9_-]', '-', name.lower().strip())
    return name[:50] or "project"


def _get_preview_url(name):
    """Get the preview URL for a project."""
    port = os.getenv("DASHBOARD_PORT", "8080")
    return f"http://localhost:{port}/builds/{name}/"


def _validate_html(html):
    html = (html or "").strip()
    if not html:
        return False, "HTML is required."
    if "<html" not in html.lower():
        return False, "HTML must include an <html> document."
    return True, ""


def _web_build(name, html):
    ok, err = _validate_html(html)
    if not ok:
        return f"❌ Invalid website content: {err}"

    name = _sanitize_name(name)
    WEBSITES_DIR.mkdir(parents=True, exist_ok=True)
    project_dir = WEBSITES_DIR / name
    project_dir.mkdir(parents=True, exist_ok=True)

    # Write the HTML file
    index_file = project_dir / "index.html"
    index_file.write_text(html, encoding="utf-8")

    url = _get_preview_url(name)
    return (
        f"🌐 **Website created: {name}**\n\n"
        f"🔗 Preview: {url}\n\n"
        f"Open the link to see your website! "
        f"Tell me if you want any changes."
    )


def _web_edit(name, html):
    ok, err = _validate_html(html)
    if not ok:
        return f"❌ Invalid website content: {err}"

    name = _sanitize_name(name)
    project_dir = WEBSITES_DIR / name

    if not project_dir.exists():
        return f"❌ Project '{name}' not found. Use web_build to create it first."

    index_file = project_dir / "index.html"
    index_file.write_text(html, encoding="utf-8")

    url = _get_preview_url(name)
    return (
        f"✏️ **Website updated: {name}**\n\n"
        f"🔗 Preview: {url}\n\n"
        f"Refresh the page to see your changes!"
    )


def _web_list():
    if not WEBSITES_DIR.exists():
        return "📭 No websites built yet. Ask me to build one!"

    projects = [d for d in sorted(WEBSITES_DIR.iterdir()) if d.is_dir() and (d / "index.html").exists()]
    if not projects:
        return "📭 No websites built yet. Ask me to build one!"

    port = os.getenv("DASHBOARD_PORT", "8080")
    lines = [f"🌐 **Your Builds** ({len(projects)} sites):\n"]
    for p in projects:
        size = (p / "index.html").stat().st_size
        size_str = f"{size:,} bytes" if size < 1024 else f"{size/1024:.1f} KB"
        url = f"http://localhost:{port}/builds/{p.name}/"
        lines.append(f"  • **{p.name}** ({size_str}) — {url}")

    return "\n".join(lines)


def _web_delete(name):
    name = _sanitize_name(name)
    project_dir = WEBSITES_DIR / name

    if not project_dir.exists():
        return f"❌ Project '{name}' not found."

    shutil.rmtree(project_dir)
    return f"🗑️ Deleted website: **{name}**"


def execute(tool_name, arguments):
    try:
        if tool_name == "web_build":
            return _web_build(arguments.get("name", "project"), arguments.get("html", ""))
        elif tool_name == "web_edit":
            return _web_edit(arguments.get("name", ""), arguments.get("html", ""))
        elif tool_name == "web_list":
            return _web_list()
        elif tool_name == "web_delete":
            return _web_delete(arguments.get("name", ""))
    except Exception as e:
        return f"❌ Web builder error: {e}"
    return None
