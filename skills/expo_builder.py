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
                    "template": {"type": "string", "enum": ["blank"], "description": "Expo project template. blank defaults to SDK 54."},
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
            "description": "Update an existing mobile Expo app by replacing App.js and optionally app.json.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Existing project name"},
                    "app_js": {"type": "string", "description": "Complete App.js source code"},
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
    except Exception as e:
        return f"❌ Expo builder error: {e}"

    return None
