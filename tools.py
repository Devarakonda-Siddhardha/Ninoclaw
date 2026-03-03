"""
Tools for Ninoclaw AI Agent
Functions the AI can call to perform actions
"""
import requests as _requests
from typing import Dict, Any

# Load skills and merge their tools
try:
    import skill_manager as _sm
    _SKILL_TOOLS = _sm.get_tools()
except Exception:
    _SKILL_TOOLS = []

# Tool definitions that the AI can call
_BUILTIN_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "self_update",
            "description": "Update the bot to the latest version from GitHub. Use when user says 'update yourself', 'pull latest version', 'update to latest', etc.",
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
            "name": "web_search",
            "description": "Search the internet for current information, news, facts, prices, or anything you don't know. Use this when the user asks about recent events or things that require up-to-date info.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to look up on Google"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_reminder",
            "description": "Schedule a one-time reminder or task that fires once at a specific time. Use this when the user says things like 'remind me in 10 minutes', 'remind me at 3pm', 'remind me tomorrow'. NOT for recurring tasks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "What to remind the user about"
                    },
                    "when": {
                        "type": "string",
                        "description": "When to send the reminder. Examples: 'in 10 minutes', 'in 2 hours', 'in 1 day'. Use 'in X minutes/hours/days' format."
                    }
                },
                "required": ["message", "when"]
            }
        }
    },
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
    },
    {
        "type": "function",
        "function": {
            "name": "create_skill",
            "description": "Create a brand new skill and save it to the skills/ folder. The skill is immediately loaded and usable. Use when user asks you to create/add/build a new skill or capability.",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "Filename for the skill (lowercase, underscores, no .py), e.g. 'jokes' or 'ip_checker'"
                    },
                    "code": {
                        "type": "string",
                        "description": "Complete Python code for the skill file. Must include SKILL_INFO dict, TOOLS list, and execute(tool_name, arguments) function."
                    }
                },
                "required": ["skill_name", "code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_skills",
            "description": "List all currently loaded skills and their capabilities",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_skill",
            "description": "Delete a custom skill by name",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_name": {"type": "string", "description": "Name of the skill to delete"}
                },
                "required": ["skill_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "install_skill",
            "description": "Download and install a Python skill from a GitHub URL or raw URL. Use when user says 'install skill from github.com/...', 'download skill from ...', etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "GitHub URL or raw URL of the skill .py file. Supports github.com/user/repo/blob/main/skill.py or raw.githubusercontent.com URLs."
                    }
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_agent",
            "description": (
                "Spawn a specialized sub-agent ONLY for genuinely complex tasks that require "
                "multiple searches, multi-step reasoning, full code programs, or deep analysis. "
                "Do NOT use for simple questions, quick facts, single lookups, or short answers — "
                "handle those directly yourself. "
                "Agent types: 'researcher' (needs 3+ web searches), 'coder' (write full programs), "
                "'analyst' (complex data/math), 'planner' (multi-step project plans), "
                "'autonomous' (complex open-ended tasks)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_type": {
                        "type": "string",
                        "enum": ["researcher", "coder", "analyst", "planner", "autonomous"],
                        "description": "Type of sub-agent to use"
                    },
                    "task": {
                        "type": "string",
                        "description": "Detailed task description for the sub-agent"
                    }
                },
                "required": ["agent_type", "task"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run a shell command on the host system. Owner-only. Use when user asks to run a command, execute a script, check a service, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to execute"},
                    "timeout": {"type": "integer", "description": "Timeout in seconds (default 30)"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read contents of a file on the host system. Owner-only.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute or relative file path"},
                    "tail": {"type": "integer", "description": "Only read last N lines (optional)"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write or append text to a file on the host system. Owner-only.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to write to"},
                    "content": {"type": "string", "description": "Text content to write"},
                    "mode": {"type": "string", "enum": ["overwrite", "append"], "description": "Write mode (default: overwrite)"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List files and directories at a path. Owner-only.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path (default: current directory)"}
                },
                "required": []
            }
        }
    },
]

# Combined tools list — built-ins + all loaded skills
TOOLS = _BUILTIN_TOOLS + _SKILL_TOOLS

def get_tool_definitions() -> list:
    """Get all tool definitions (built-ins + skills)"""
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
    from config import SERPER_API_KEY
    from security import require_owner, safe_path, safe_command, validate_skill_code

    memory = Memory()
    user_timezone = memory.get_timezone(user_id)

    if tool_name == "self_update":
        from updater import check_for_updates, do_update, get_current_version, restart
        import asyncio
        err = require_owner(user_id)
        if err:
            return err
        has_updates, commits = check_for_updates()
        if not has_updates:
            return f"✅ Already on the latest version! (commit: {get_current_version()})"
        success, msg = do_update()
        if not success:
            return f"❌ Update failed:\n{msg}"
        # Schedule restart after reply is sent
        asyncio.get_event_loop().call_later(2, restart)
        return f"✅ Updated successfully!\n\nChanges:\n{commits}\n\n🔄 Restarting now..."

    if tool_name == "web_search":
        query = arguments.get("query", "")
        if not SERPER_API_KEY:
            return "❌ Web search is not configured. Set SERPER_API_KEY in your environment."
        try:
            resp = _requests.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
                json={"q": query, "num": 5},
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            results = []
            for item in data.get("organic", [])[:5]:
                results.append(f"**{item.get('title')}**\n{item.get('snippet', '')}\n{item.get('link', '')}")
            if not results:
                return f"No results found for: {query}"
            return f"🔍 Search results for \"{query}\":\n\n" + "\n\n".join(results)
        except Exception as e:
            return f"❌ Search failed: {e}"

    if tool_name == "schedule_reminder":
        message = arguments.get("message", "Reminder!")
        when = arguments.get("when", "in 5 minutes")
        ts = task_manager.parse_time(when)
        task_manager.add_task(user_id, f"⏰ {message}", ts)
        time_str = task_manager.format_timestamp(ts)
        return f"⏰ Reminder set!\n\n📝 {message}\n📅 {time_str}"

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

    # ── Skill management ────────────────────────────────────────────────────
    if tool_name == "list_skills":
        try:
            import skill_manager as sm
            skills = sm.list_skills()
            if not skills:
                return "No skills loaded yet."
            lines = ["🧩 **Loaded Skills:**\n"]
            for key, info in skills.items():
                lines.append(f"{info.get('icon','🔧')} **{info['name']}** v{info.get('version','1.0')}\n   {info.get('description','')}")
            return "\n".join(lines)
        except Exception as e:
            return f"❌ {e}"

    if tool_name == "delete_skill":
        err = require_owner(user_id)
        if err: return err
        skill_name = arguments.get("skill_name", "").strip().lower().replace(" ", "_")
        import os, re
        if not re.match(r'^[a-z][a-z0-9_]*$', skill_name):
            return "❌ Invalid skill name."
        skill_path = os.path.join(os.path.dirname(__file__), "skills", f"{skill_name}.py")
        if not os.path.exists(skill_path):
            return f"❌ Skill '{skill_name}' not found."
        os.remove(skill_path)
        try:
            import skill_manager as sm
            sm.load_skills()
        except Exception:
            pass
        return f"🗑️ Skill '{skill_name}' deleted."

    if tool_name == "install_skill":
        err = require_owner(user_id)
        if err: return err
        import os, re
        url = arguments.get("url", "").strip()
        if not url:
            return "❌ URL is required."
        # Only allow github.com and raw.githubusercontent.com
        if not re.match(r'https://(raw\.githubusercontent\.com|github\.com)/', url):
            return "❌ Only GitHub URLs are allowed for skill installation."
        # Convert github.com blob URL → raw URL
        raw_url = url
        if "github.com" in url and "/blob/" in url:
            raw_url = url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
        skill_name = os.path.splitext(raw_url.rstrip("/").split("/")[-1])[0]
        skill_name = re.sub(r'[^a-z0-9_]', '_', skill_name.lower())
        if not re.match(r'^[a-z][a-z0-9_]*$', skill_name):
            skill_name = "remote_skill"
        try:
            resp = _requests.get(raw_url, timeout=15)
            resp.raise_for_status()
            code = resp.text
        except Exception as e:
            return f"❌ Failed to download skill: {e}"
        # Full AST validation
        err = validate_skill_code(code)
        if err: return err
        skills_dir = os.path.join(os.path.dirname(__file__), "skills")
        os.makedirs(skills_dir, exist_ok=True)
        skill_path = os.path.join(skills_dir, f"{skill_name}.py")
        with open(skill_path, "w") as f:
            f.write(code)
        try:
            import skill_manager as sm
            sm.load_skills()
            import tools as _t
            _t.TOOLS = _t._BUILTIN_TOOLS + sm.get_tools()
            return f"✅ Skill **{skill_name}** installed from:\n`{url}`\n\nReady to use — just ask me!"
        except Exception as e:
            return f"⚠️ Skill saved as skills/{skill_name}.py but reload failed: {e}\nRestart bot to activate."

    if tool_name == "create_skill":
        err = require_owner(user_id)
        if err: return err
        import os, re
        skill_name = arguments.get("skill_name", "").strip().lower().replace(" ", "_").replace("-", "_")
        code = arguments.get("code", "").strip()
        if not skill_name or not code:
            return "❌ Need both skill_name and code."
        if not re.match(r'^[a-z][a-z0-9_]*$', skill_name):
            return "❌ Skill name must be lowercase letters/numbers/underscores."
        # Full AST validation
        err = validate_skill_code(code)
        if err: return err
        skills_dir = os.path.join(os.path.dirname(__file__), "skills")
        os.makedirs(skills_dir, exist_ok=True)
        skill_path = os.path.join(skills_dir, f"{skill_name}.py")
        with open(skill_path, "w") as f:
            f.write(code)
        try:
            import skill_manager as sm
            sm.load_skills()
            import tools as _t
            _t.TOOLS = _t._BUILTIN_TOOLS + sm.get_tools()
            return (f"✅ Skill **{skill_name}** created and loaded!\n"
                    f"You can now use it — just ask me to use it.")
        except Exception as e:
            return f"⚠️ Skill saved to skills/{skill_name}.py but reload failed: {e}\nRestart bot to activate."

    if tool_name == "run_agent":
        agent_type = arguments.get("agent_type", "autonomous")
        task = arguments.get("task", "")
        if not task:
            return "❌ Task description is required."
        try:
            from subagent import run_subagent
            result = await run_subagent(agent_type, task, user_id, task_manager)
            return f"🤖 **{agent_type.capitalize()} Agent Result:**\n\n{result}"
        except Exception as e:
            return f"❌ Sub-agent failed: {e}"

    # ── System tools (owner-only, hardened) ──────────────────────────────────
    _SYS_TOOLS = {"run_command", "read_file", "write_file", "list_dir"}
    if tool_name in _SYS_TOOLS:
        err = require_owner(user_id)
        if err: return err

    if tool_name == "run_command":
        import subprocess
        command = arguments.get("command", "").strip()
        timeout = int(arguments.get("timeout", 30))
        if not command:
            return "❌ No command provided."
        err = safe_command(command)
        if err: return err
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=timeout, env={**__import__('os').environ, "HOME": __import__('os').path.expanduser("~")}
            )
            out = result.stdout.strip()
            err_out = result.stderr.strip()
            parts = [f"$ {command}"]
            if out:
                parts.append(f"```\n{out[:3000]}\n```")
            if err_out:
                parts.append(f"⚠️ stderr:\n```\n{err_out[:500]}\n```")
            if not out and not err_out:
                parts.append("_(no output)_")
            if result.returncode != 0:
                parts.append(f"↩️ Exit: {result.returncode}")
            return "\n".join(parts)
        except subprocess.TimeoutExpired:
            return f"❌ Command timed out after {timeout}s"
        except Exception as e:
            return f"❌ {e}"

    if tool_name == "read_file":
        import os
        path = arguments.get("path", "")
        tail = arguments.get("tail")
        err = safe_path(path)
        if err: return err
        expanded = os.path.expanduser(path)
        if not os.path.exists(expanded):
            return f"❌ File not found: {path}"
        if os.path.isdir(expanded):
            return "❌ That's a directory. Use list_dir instead."
        try:
            with open(expanded, "r", errors="replace") as f:
                lines = f.readlines()
            if tail:
                lines = lines[-int(tail):]
            content = "".join(lines)
            if len(content) > 3500:
                content = content[:3500] + "\n…(truncated)"
            return f"📄 `{path}`:\n```\n{content}\n```"
        except Exception as e:
            return f"❌ {e}"

    if tool_name == "write_file":
        import os
        path = arguments.get("path", "")
        content = arguments.get("content", "")
        err = safe_path(path)
        if err: return err
        mode = "a" if arguments.get("mode") == "append" else "w"
        expanded = os.path.expanduser(path)
        try:
            os.makedirs(os.path.dirname(os.path.abspath(expanded)), exist_ok=True)
            with open(expanded, mode) as f:
                f.write(content)
            action = "appended to" if mode == "a" else "written to"
            return f"✅ {len(content)} chars {action} `{path}`"
        except Exception as e:
            return f"❌ {e}"

    if tool_name == "list_dir":
        import os
        path = os.path.expanduser(arguments.get("path", "."))
        if not os.path.exists(path):
            return f"❌ Path not found: {path}"
        try:
            entries = sorted(os.scandir(path), key=lambda e: (not e.is_dir(), e.name.lower()))
            lines = [f"📁 `{os.path.abspath(path)}`:\n"]
            for e in entries[:100]:
                icon = "📁" if e.is_dir() else "📄"
                size = f"  {e.stat().st_size:,}B" if e.is_file() else ""
                lines.append(f"{icon} {e.name}{size}")
            if len(entries) > 100:
                lines.append(f"…and {len(entries)-100} more")
            return "\n".join(lines)
        except Exception as e:
            return f"❌ {e}"

    # Try skill tools
    try:
        import skill_manager as _sm
        result = _sm.execute(tool_name, arguments)
        if result is not None:
            return result
    except Exception as e:
        pass

    return f"Unknown tool: {tool_name}"