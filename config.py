"""
Configuration for Ninoclaw AI Assistant
"""
import os
import json

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
    "model":   os.getenv("OPENAI_MODEL", "gemini-2.0-flash"),
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

# Memory Settings
MEMORY_FILE    = "memory.json"
MAX_MEMORY_SIZE = 1000

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
- schedule_reminder: Set a ONE-TIME reminder (e.g. "remind me in 10 minutes", "remind me in 2 hours"). Use this for single reminders, NOT recurring tasks.
- schedule_cron: Create a RECURRING task (e.g. "every day at 9am", "every Monday"). Use this for repeating schedules only.
- list_cron_jobs: List all scheduled tasks
- remove_cron_job: Remove a scheduled task
- toggle_cron_job: Enable/disable a scheduled task
- get_timezone: Check user's configured timezone

When the user asks about something current or factual that you're unsure about, ALWAYS call web_search first before answering.
When the user wants a one-time reminder (e.g. "remind me in 10 minutes to drink water"), call schedule_reminder.
When the user wants a recurring schedule (e.g. "remind me every day at 9am"), call schedule_cron.

Current context is available in your memory. Respond naturally.

NOTE: Cron jobs run based on the SERVER timezone (UTC), not the user's local timezone. If scheduling involves specific times and the user's timezone is not set, suggest they set it with /timezone command for accuracy. Common timezones: Asia/Kolkata (India), America/New_York, Europe/London, etc."""
