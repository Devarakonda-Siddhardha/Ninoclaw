"""
Tools for Ninoclaw AI Agent
Functions the AI can call to perform actions
"""
from typing import Dict, Any

# Tool definitions that the AI can call
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_timezone",
            "description": "Get the user's configured timezone. Use to check if timezone is set before scheduling.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_timezone",
            "description": "Set the user's timezone for accurate scheduling. Use when user mentions their timezone location (like 'India', 'America/New York', 'Europe/London').",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": "Timezone string (e.g., 'Asia/Kolkata', 'America/New_York', 'Europe/London', 'UTC', 'default'). Use IANA timezone names or 'default' for server time."
                    }
                },
                "required": ["timezone"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_cron",
            "description": "Schedule a recurring task (cron job) that will run automatically. Use when user wants to schedule something regularly like reminders, daily reports, or periodic checks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Schedule timing. Examples: 'every day at 9am', 'hourly', 'every 2 hours', 'daily', 'every monday', 'weekdays at 10am', '9am daily'. Also accepts standard cron like '0 9 * * *' or '*/30 * * * *'."
                    },
                    "command": {
                        "type": "string",
                        "description": "What the task should do or say when it runs."
                    }
                },
                "required": ["expression", "command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_cron_jobs",
            "description": "List all scheduled recurring tasks (cron jobs) for the user",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "remove_cron_job",
            "description": "Remove a scheduled recurring task (cron job) by its ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "The ID of the cron job to remove"
                    }
                },
                "required": ["job_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "toggle_cron_job",
            "description": "Enable or disable a scheduled recurring task (cron job)",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "The ID of the cron job to toggle"
                    }
                },
                "required": ["job_id"]
            }
        }
    }
]

def get_tool_definitions() -> list:
    """Get all tool definitions"""
    return TOOLS


async def execute_tool(tool_name: str, arguments: Dict[str, Any], user_id: int, task_manager) -> str:
    """
    Execute a tool call and return the result

    Args:
        tool_name: Name of the tool to execute
        arguments: Arguments for the tool
        user_id: User ID
        task_manager: TaskManager instance

    Returns:
        Result message string
    """
    from memory import Memory

    memory = Memory()
    user_timezone = memory.get_timezone(user_id)

    if tool_name == "get_timezone":
        tz = user_timezone or "Not set (using server time)"
        return f"🕐 Your timezone: {tz}\n\nUse /timezone command or ask me to set it (e.g., 'set my timezone to Asia/Kolkata')"

    if tool_name == "set_timezone":
        timezone = arguments.get("timezone", "").strip()
        if timezone.lower() in ['default', 'server', 'none', '']:
            timezone = None
        memory.set_timezone(user_id, timezone)
        return f"✅ Timezone set to: {timezone if timezone else 'Server time (UTC)'}"

    if tool_name == "schedule_cron":
        expression = arguments.get("expression")
        command = arguments.get("command")

        job_id, error = task_manager.add_cron_job(user_id, command[:50], expression, command)
        if error:
            return f"Error creating schedule: {error}"

        job = task_manager.get_cron_job(job_id, user_id)
        next_run = task_manager.format_timestamp(job["next_run"]) if job.get("next_run") else "Unknown"
        return f"✅ Scheduled task created!\n\n📝 {command}\n⏰ Schedule: {expression}\n📅 Next run: {next_run}\n🆔 ID: {job_id}"

    elif tool_name == "list_cron_jobs":
        jobs = task_manager.list_cron_jobs(user_id)
        if not jobs:
            return "📋 No scheduled tasks yet."

        msg = "🔄 Your scheduled tasks:\n\n"
        for job in jobs:
            status = "✅" if job.get("is_active", True) else "⏸️"
            next_run = task_manager.format_timestamp(job["next_run"]) if job.get("next_run") else "Unknown"
            msg += f"{status} {job['name']}\n   ⏰ {job['cron_expression']}\n   📅 Next: {next_run}\n   🆔 {job['id']}\n\n"
        return msg

    elif tool_name == "remove_cron_job":
        job_id = arguments.get("job_id")
        if task_manager.remove_cron_job(job_id, user_id):
            return "✅ Scheduled task removed!"
        return "❌ Job not found or you don't have permission"

    elif tool_name == "toggle_cron_job":
        job_id = arguments.get("job_id")
        is_active = task_manager.toggle_cron_job(job_id, user_id)
        if is_active is None:
            return "❌ Job not found or you don't have permission"
        status = "enabled" if is_active else "disabled"
        return f"✅ Scheduled task {status}!"

    return f"Unknown tool: {tool_name}"
