"""
Configuration for Ninoclaw AI Assistant
"""
import os
import json
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Telegram Bot Token - Get from @BotFather
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# Bot Owner - Only this Telegram user ID can trigger /update and admin commands
# Get your ID by messaging @userinfobot on Telegram
OWNER_ID = int(os.getenv("OWNER_ID", "0"))  # 0 = not set

# Serper API (Google Search) - Get from https://serper.dev
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")

# ---------------------------------------------------------------------------
# AI Model Chain — tried in order, falls back to the next on error/rate-limit
# Each entry: {"api_url": "...", "api_key": "...", "model": "..."}
#
# Override with MODELS_JSON env var (JSON array), or use the individual
# PRIMARY_* / FALLBACK_* vars below for simple two-model setups.
# ---------------------------------------------------------------------------

_primary = {
    "api_url": os.getenv("OPENAI_API_URL", "https://generativelanguage.googleapis.com/v1beta/openai"),
    "api_key": os.getenv("OPENAI_API_KEY", "your-api-key-here"),
    "model":   os.getenv("OPENAI_MODEL", "gemini-3-flash-preview"),
}

# Optional second model (e.g. Ollama local fallback, or a different API key)
_fallback_url = os.getenv("FALLBACK_API_URL", "")
_fallback_key = os.getenv("FALLBACK_API_KEY", "")
_fallback_model = os.getenv("FALLBACK_MODEL", "")

_fallbacks = []
if _fallback_model:
    _fallbacks.append({
        "api_url": _fallback_url or _primary["api_url"],
        "api_key": _fallback_key or _primary["api_key"],
        "model":   _fallback_model,
    })

# Full chain — can also be set entirely via MODELS_JSON env var
if os.getenv("MODELS_JSON"):
    MODELS = json.loads(os.getenv("MODELS_JSON"))
else:
    MODELS = [_primary] + _fallbacks

# Legacy aliases (used by other parts of the code)
AI_PROVIDER    = "openai"
OPENAI_API_KEY = _primary["api_key"]
OPENAI_API_URL = _primary["api_url"]
OPENAI_MODEL   = _primary["model"]
OLLAMA_HOST    = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL   = os.getenv("OLLAMA_MODEL", "llama3.2")

# Plugin feature flags — toggle via dashboard or .env
ENABLE_WEB_SEARCH  = os.getenv("ENABLE_WEB_SEARCH",  "true")  != "false"
ENABLE_VISION      = os.getenv("ENABLE_VISION",      "true")  != "false"
ENABLE_SUMMARIZER  = os.getenv("ENABLE_SUMMARIZER",  "true")  != "false"
ENABLE_REMINDERS   = os.getenv("ENABLE_REMINDERS",   "true")  != "false"
ENABLE_CRON        = os.getenv("ENABLE_CRON",        "true")  != "false"
ENABLE_SELF_UPDATE = os.getenv("ENABLE_SELF_UPDATE", "true")  != "false"

# Dashboard
DASHBOARD_PORT     = int(os.getenv("DASHBOARD_PORT", "8080"))
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "admin")

# Memory Settings
MEMORY_FILE    = "memory.json"
MAX_MEMORY_SIZE = 1000  # max messages stored in DB per user
CONTEXT_WINDOW  = int(os.getenv("CONTEXT_WINDOW", "20"))  # messages sent to AI per request

# Task Settings
TASKS_FILE = "tasks.json"

# System Prompt
SYSTEM_PROMPT = """You are Ninoclaw, a helpful personal AI assistant. You:
- Remember conversations and context
- Help schedule tasks and reminders
- Can create recurring scheduled tasks (cron jobs) using tools
- Are concise but friendly
- Can execute tasks when needed

You have access to the following tools:
- self_update: Update the bot to the latest version from GitHub and restart. Use when user says 'update yourself', 'update to latest version', etc.
- web_search: Search the internet for current info, news, facts, prices, or anything you don't know. Use this proactively when the user asks about recent events or real-time data.
- get_weather: Get current weather for any city (temperature, humidity, wind). Use when user asks about weather.
- wikipedia_search: Look up any topic on Wikipedia for accurate information.
- calculate: Evaluate math expressions (sqrt, sin, log, etc). Use for any calculation.
- convert_currency: Convert between currencies using live rates (e.g. 100 USD to INR).
- get_news: Get latest news headlines by topic (world, tech, sports, health, business, science).
- get_system_info: Get device stats (RAM, disk, uptime). Use when user asks about system/device.
- schedule_reminder: Set a ONE-TIME reminder (e.g. "remind me in 10 minutes", "remind me in 2 hours"). Use this for single reminders, NOT recurring tasks.
- schedule_cron: Create a RECURRING task (e.g. "every day at 9am", "every Monday"). Use this for repeating schedules only.
- list_cron_jobs: List all scheduled tasks
- remove_cron_job: Remove a scheduled task
- toggle_cron_job: Enable/disable a scheduled task
- get_timezone: Check user's configured timezone
- create_skill: Write and save a new Python skill to skills/ folder — immediately usable. Use when user says "create a skill", "add ability to", "build a skill for", etc.
- list_skills: List all currently loaded skills
- delete_skill: Delete a skill by name
- install_skill: Download and install a skill from a GitHub URL (e.g. "install skill from github.com/user/repo/blob/main/jokes.py"). Converts github.com URLs to raw automatically.

SKILL CREATION — when user asks you to create a skill, call create_skill with valid Python code following this EXACT template:

```python
import requests  # or any stdlib module

SKILL_INFO = {
    "name": "skill_name",
    "description": "What this skill does",
    "version": "1.0",
    "icon": "🔧",
    "author": "ninoclaw",
    "requires_key": False,
}

TOOLS = [{
    "type": "function",
    "function": {
        "name": "tool_function_name",
        "description": "What this tool does, when to use it",
        "parameters": {
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "description"}
            },
            "required": ["param1"]
        }
    }
}]

def execute(tool_name, arguments):
    if tool_name != "tool_function_name":
        return None
    param1 = arguments.get("param1", "")
    # ... logic here ...
    return "result string"
```

Rules for skill code: use only stdlib + requests (already installed). Never use input(). Always return a string from execute(). Handle exceptions gracefully.

Only call web_search when the user explicitly asks for current/real-time info (news, live scores, prices, weather) OR when you truly don't have the information needed to answer. Do NOT search for opinions, predictions, analysis, or questions you can answer from your own knowledge.
When the user wants a one-time reminder (e.g. "remind me in 10 minutes to drink water"), call schedule_reminder.
When the user wants a recurring schedule (e.g. "remind me every day at 9am"), call schedule_cron.

Current context is available in your memory. Respond naturally.

NOTE: Cron jobs run based on the SERVER timezone (UTC), not the user's local timezone. If scheduling involves specific times and the user's timezone is not set, suggest they set it with /timezone command for accuracy. Common timezones: Asia/Kolkata (India), America/New_York, Europe/London, etc."""
