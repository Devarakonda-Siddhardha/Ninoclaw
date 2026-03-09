"""
Expo app builder skill.
"""
from expo_manager import (
    create_app,
    delete_app,
    edit_app,
    format_app_summary,
    list_apps,
    start_app,
    stop_app,
    install_package,
)


SKILL_INFO = {
    "name": "expo_builder",
    "description": "Create and run React Native Expo SDK 54 apps with Expo Go plus web preview links",
    "version": "1.0",
    "icon": "📱",
    "author": "ninoclaw",
    "requires_key": False,
}


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "expo_create_app",
            "description": "Create a new mobile app with React Native Expo SDK 54, write App.js, start Expo with device and web preview enabled, and return preview links. Use when the user asks for a mobile app, phone app, Android app, iOS app, native app, Expo app, React Native app, or an app to open in Expo Go or the browser.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Project name, lowercase and short"},
                    "app_js": {"type": "string", "description": "Complete App.js source code for the Expo app"},
                    "app_json": {"type": "string", "description": "Optional app.json content as JSON text"},
                    "template": {
                        "type": "string", 
                        "enum": ["blank", "tabs", "blank-typescript", "navigation", "default"], 
                        "description": "Expo project template. 'blank' is default empty SDK 54. 'tabs' includes file-based routing. 'default' is the standard Expo starter."
                    },
                    "auto_start": {"type": "boolean", "description": "Start Expo immediately after creation"},
                    "tunnel": {"type": "boolean", "description": "Start Expo with tunnel mode for easier device access"},
                },
                "required": ["name", "app_js"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "expo_edit_app",
            "description": "WARNING: This REPLACES the entire App.js file. Do not use this to 'add' a small feature, use it only if you intend to rewrite the entire App.js from scratch. If you only want to add a screen or a component, use the `expo_write_component` tool instead to create a new file. IMPORTANT: After editing, you MUST use `expo_get_logs` (and `expo_start_app` if not running) to check for Metro or React Native errors. If errors exist, fix them and check again until clear.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Existing project name"},
                    "app_js": {"type": "string", "description": "The COMPLETE, fully functional App.js source code. Never send partial code here."},
                    "app_json": {"type": "string", "description": "Optional app.json content as JSON text"},
                },
                "required": ["name", "app_js"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "expo_start_app",
            "description": "Start an existing Expo mobile app and return Expo Go and web preview links.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Project name"},
                    "tunnel": {"type": "boolean", "description": "Use tunnel mode for device access"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "expo_stop_app",
            "description": "Stop a running Expo app dev server.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Project name"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "expo_list_apps",
            "description": "List all Expo apps and their current status.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "expo_delete_app",
            "description": "Delete an Expo app project and stop it if it is running.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Project name"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "expo_install_package",
            "description": "Install npm packages into an existing Expo app.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Project name"},
                    "packages": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of package names to install (e.g., ['react-native-reanimated', '@react-navigation/native'])"
                    },
                },
                "required": ["name", "packages"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "expo_write_component",
            "description": "Write or overwrite a specific file (e.g., a component or screen) inside an Expo app project. This creates directories automatically if needed. IMPORTANT: After writing, you MUST use `expo_get_logs` (and `expo_start_app` if not running) to check for Metro or compilation errors. If errors exist, rewrite it to fix them and check again until clear.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Project name"},
                    "file_path": {"type": "string", "description": "Relative path to the file inside the project (e.g., 'components/Button.js' or 'screens/Home.js')"},
                    "content": {"type": "string", "description": "The complete source code or content for the file"},
                },
                "required": ["name", "file_path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "expo_get_logs",
            "description": "Get the most recent 100 lines of console and Metro logs for a running Expo app. Useful for debugging errors without asking the user for screenshots.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Project name"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "expo_screenshot_web",
            "description": "Take a screenshot of the running Expo app's web preview. This saves the image and automatically sends it to the user in Telegram. The app must be running with a web preview available.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Project name"},
                },
                "required": ["name"],
            },
        },
    },
]


def _format_list(apps):
    if not apps:
        return "📱 No Expo apps yet."
    lines = [f"📱 **Expo Apps** ({len(apps)}):", ""]
    for app in apps:
        status = "running" if app.get("is_running") else app.get("status", "stopped")
        launch = app.get("launch_url") or app.get("tunnel_url") or app.get("web_url") or "no link yet"
        lines.append(f"• **{app['name']}** - {status} - {launch}")
    return "\n".join(lines)


def execute(tool_name, arguments):
    try:
        if tool_name == "expo_create_app":
            app = create_app(
                name=arguments.get("name", "expo-app"),
                app_js=arguments.get("app_js", ""),
                app_json=arguments.get("app_json", ""),
                template=arguments.get("template", "blank") or "blank",
                auto_start=bool(arguments.get("auto_start", True)),
                tunnel=bool(arguments.get("tunnel", True)),
            )
            return "✅ Expo app created.\n\n" + format_app_summary(app)

        if tool_name == "expo_edit_app":
            app = edit_app(
                name=arguments.get("name", ""),
                app_js=arguments.get("app_js", ""),
                app_json=arguments.get("app_json", ""),
            )
            return "✏️ Expo app updated.\n\n" + format_app_summary(app)

        if tool_name == "expo_start_app":
            app = start_app(
                name=arguments.get("name", ""),
                tunnel=bool(arguments.get("tunnel", True)),
            )
            return "🚀 Expo app started.\n\n" + format_app_summary(app)

        if tool_name == "expo_stop_app":
            app = stop_app(arguments.get("name", ""))
            return "⏹️ Expo app stopped.\n\n" + format_app_summary(app)

        if tool_name == "expo_list_apps":
            return _format_list(list_apps())

        if tool_name == "expo_delete_app":
            result = delete_app(arguments.get("name", ""))
            return f"🗑️ Deleted Expo app: **{result['name']}**"

        if tool_name == "expo_install_package":
            packages = arguments.get("packages", [])
            if not isinstance(packages, list) or not packages:
                return "❌ Error: 'packages' must be a non-empty list of strings."
            result = install_package(arguments.get("name", ""), packages)
            return f"📦 {result}"

        if tool_name == "expo_write_component":
            from expo_manager import _project_dir, _sanitize_name
            import os
            
            safe_name = _sanitize_name(arguments.get("name", ""))
            file_path = arguments.get("file_path", "").strip()
            content = arguments.get("content", "")
            
            if not file_path:
                return "❌ Error: file_path is required."
            
            project_dir = _project_dir(safe_name)
            if not (project_dir / "package.json").exists():
                return f"❌ Error: Project '{safe_name}' does not exist."
            
            # Prevent path traversal
            if ".." in file_path or file_path.startswith("/") or file_path.startswith("\\"):
                return "❌ Error: Invalid file_path. Must be relative without '..'"
                
            full_path = project_dir / file_path
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
                
            return f"📝 Wrote file successfully: `{file_path}`"

        if tool_name == "expo_get_logs":
            from expo_manager import _get_app_row, _read_log_tail, _sanitize_name
            safe_name = _sanitize_name(arguments.get("name", ""))
            row = _get_app_row(safe_name)
            
            if not row:
                return f"❌ Error: Project '{safe_name}' not found."
            
            log_path = row.get("log_path", "")
            if not log_path:
                return "❌ No logs available for this app. It might not have been started yet."
                
            logs = _read_log_tail(log_path, max_chars=8000)
            if not logs.strip():
                return "(Logs are empty)"
                
            # Grab just the last ~100 lines to avoid overwhelming context
            lines = logs.splitlines()
            last_lines = lines[-100:] if len(lines) > 100 else lines
            return "📃 **Recent Expo Logs:**\n```\n" + "\n".join(last_lines) + "\n```"

        if tool_name == "expo_screenshot_web":
            from expo_manager import _get_app_row, _sanitize_name
            import tempfile, time, subprocess, sys, os
            
            safe_name = _sanitize_name(arguments.get("name", ""))
            row = _get_app_row(safe_name)
            if not row:
                return f"❌ Error: Project '{safe_name}' not found."
            
            web_url = row.get("web_url", "")
            if not web_url or not row.get("pid"):
                return "❌ Error: The app is not running or does not have a web preview active."
            
            tmp_dir = tempfile.gettempdir()
            path = os.path.join(tmp_dir, f"expo_web_ss_{int(time.time())}.png")
            
            if sys.platform == "win32":
                # Try Edge
                ps_script = f'Start-Process "msedge.exe" -ArgumentList "--headless --disable-gpu --window-size=400,800 --screenshot={path} {web_url}" -Wait -NoNewWindow'
                subprocess.run(["powershell", "-Command", ps_script], capture_output=True, timeout=15)
                
            if os.path.exists(path):
                return f"[IMAGE:{path}]\n📸 Screenshot of the {safe_name} web preview captured!"
            else:
                return "❌ Failed to capture a screenshot of the web preview."
            
    except Exception as e:
        return f"❌ Expo builder error: {e}"

    return None
