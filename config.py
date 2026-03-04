"""
Configuration for Ninoclaw AI Assistant
"""
import os
import json
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Telegram Bot Token - Get from @BotFather
def _env(key, default=""):
    """Get env var, stripping accidental whitespace/tabs."""
    return os.getenv(key, default).strip()

TELEGRAM_BOT_TOKEN = _env("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
DISCORD_BOT_TOKEN  = _env("DISCORD_BOT_TOKEN", "")

# Bot Owner - Only this Telegram user ID can trigger /update and admin commands
OWNER_ID = int(_env("OWNER_ID", "0"))  # 0 = not set

# Personalization — set via wizard or .env directly
AGENT_NAME  = _env("AGENT_NAME",  "Ninoclaw")
USER_NAME   = _env("USER_NAME",   "friend")
BOT_PURPOSE = _env("BOT_PURPOSE", "be your personal AI assistant")
TIMEZONE    = _env("TIMEZONE",    "UTC")

SERPER_API_KEY = _env("SERPER_API_KEY", "")

# ---------------------------------------------------------------------------
# AI Model Chain — tried in order, falls back to the next on error/rate-limit
# Each entry needs: api_url, api_key, model
# All providers use OpenAI-compatible /chat/completions API.
#
# Set keys in .env:
#   OPENAI_API_KEY      → OpenAI / any primary provider
#   OPENAI_API_URL      → override base URL (default: Google Gemini)
#   OPENAI_MODEL        → override model name
#   GROQ_API_KEY        → Grok / Groq (https://console.groq.com)
#   MISTRAL_API_KEY     → Mistral (https://console.mistral.ai)
#   GLM_API_KEY         → ZhipuAI GLM (https://open.bigmodel.cn)
#   MINIMAX_API_KEY     → MiniMax (https://api.minimax.chat)
#   MINIMAX_GROUP_ID    → MiniMax group ID (required for MiniMax)
#   XAI_API_KEY         → xAI Grok (https://console.x.ai)
#   TOGETHER_API_KEY    → Together AI (https://api.together.xyz)
#   OPENROUTER_API_KEY  → OpenRouter (https://openrouter.ai) — 100+ models
#   OLLAMA_MODEL        → local Ollama model name (e.g. llama3.2)
# ---------------------------------------------------------------------------

def _provider(url, key_env, model, default_model=None):
    key = _env(key_env)
    if not key:
        return None
    return {"api_url": url, "api_key": key, "model": _env(model) or default_model or ""}

_primary = {
    "api_url": _env("OPENAI_API_URL", "https://generativelanguage.googleapis.com/v1beta/openai"),
    "api_key": os.getenv("OPENAI_API_KEY", "your-api-key-here"),
    "model":   os.getenv("OPENAI_MODEL", "gemini-3-flash-preview"),
}

_provider_chain = [
    # Groq — fast inference, free tier (llama, mixtral, gemma)
    _provider("https://api.groq.com/openai/v1",       "GROQ_API_KEY",       "GROQ_MODEL",       "llama-3.3-70b-versatile"),
    # Mistral — mistral-small free, mistral-large paid
    _provider("https://api.mistral.ai/v1",             "MISTRAL_API_KEY",    "MISTRAL_MODEL",    "mistral-small-latest"),
    # xAI Grok
    _provider("https://api.x.ai/v1",                   "XAI_API_KEY",        "XAI_MODEL",        "grok-3-mini"),
    # ZhipuAI GLM
    _provider("https://open.bigmodel.cn/api/paas/v4",  "GLM_API_KEY",        "GLM_MODEL",        "glm-4-flash"),
    # MiniMax
    _provider(
        f"https://api.minimax.chat/v1",
        "MINIMAX_API_KEY", "MINIMAX_MODEL", "MiniMax-Text-01"
    ),
    # Together AI — 100+ open models
    _provider("https://api.together.xyz/v1",           "TOGETHER_API_KEY",   "TOGETHER_MODEL",   "meta-llama/Llama-3-70b-chat-hf"),
    # OpenRouter — universal gateway
    _provider("https://openrouter.ai/api/v1",          "OPENROUTER_API_KEY", "OPENROUTER_MODEL", "openai/gpt-4o-mini"),
    # Ollama — local
    {"api_url": os.getenv("OLLAMA_HOST", "http://localhost:11434") + "/v1",
     "api_key": "ollama",
     "model":   os.getenv("OLLAMA_MODEL", "")} if os.getenv("OLLAMA_MODEL") else None,
]

# Full chain — primary first, then any configured providers, skip unconfigured
if os.getenv("MODELS_JSON"):
    MODELS = json.loads(os.getenv("MODELS_JSON"))
else:
    MODELS = [_primary] + [p for p in _provider_chain if p and p.get("model")]

# Legacy aliases
AI_PROVIDER    = "openai"
OPENAI_API_KEY = _primary["api_key"]
OPENAI_API_URL = _primary["api_url"]
OPENAI_MODEL   = _primary["model"]
OLLAMA_HOST    = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL   = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_THINK   = os.getenv("OLLAMA_THINK", "false").lower() == "true"
# Smart model routing — use fast model for simple tasks, smart model for complex ones
# Set FAST_MODEL to enable routing (uses same URL/key as primary by default)
# Example: FAST_MODEL=anthropic/claude-haiku-4-5  SMART_MODEL=anthropic/claude-opus-4
FAST_MODEL     = _env("FAST_MODEL", "")   # cheap/fast model name
SMART_MODEL    = _env("SMART_MODEL", "")  # big/smart model name (defaults to OPENAI_MODEL)

def _fast_cfg():
    """Config for the fast model (same provider as primary, different model)."""
    if not FAST_MODEL:
        return None
    return {**_primary, "model": FAST_MODEL}

def _smart_cfg():
    """Config for the smart model (same provider as primary, different model)."""
    model = SMART_MODEL or _primary["model"]
    return {**_primary, "model": model}



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
- run_agent: Delegate to a specialized sub-agent ONLY when the task is genuinely complex — requires multiple web searches, multi-step reasoning, writing full code, or deep analysis. Do NOT use for simple questions, single lookups, quick calculations, or anything you can answer directly. Types: researcher (deep research needing 3+ searches), coder (write/debug full programs), analyst (complex data/math breakdowns), planner (multi-step project planning), autonomous (complex open-ended tasks).
- run_command: Run a shell command on the host system (owner-only). Use when user asks to run a command, execute a script, check a service status, etc.
- read_file: Read contents of a file (owner-only). Supports tail=N to read last N lines.
- write_file: Write or append text to a file (owner-only).
- list_dir: List files and folders in a directory (owner-only).

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
