"""
Configuration for Ninoclaw AI Assistant
"""
import os

# Telegram Bot Token - Get from @BotFather
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# AI Provider: "openai" or "ollama"
AI_PROVIDER = os.getenv("AI_PROVIDER", "openai")

# OpenAI API Settings (for GPT-4, Claude-compatible, Gemini, etc.)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-api-key-here")
OPENAI_API_URL = os.getenv("OPENAI_API_URL", "https://generativelanguage.googleapis.com/v1beta/openai")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gemini-3-flash-preview")  # or gpt-4o, claude-3-5-sonnet, etc.

# Ollama Settings (local, alternative to API)
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

# Memory Settings
MEMORY_FILE = "memory.json"
MAX_MEMORY_SIZE = 1000  # max messages in memory

# Task Settings
TASKS_FILE = "tasks.json"

# System Prompt
SYSTEM_PROMPT = """You are Ninoclaw, a helpful personal AI assistant. You:
- Remember conversations and context
- Help schedule tasks and reminders
- Can create recurring scheduled tasks (cron jobs) using tools
- Are concise but friendly
- Can execute tasks when needed

You have access to tools for managing scheduled tasks:
- schedule_cron: Create a recurring task
- list_cron_jobs: List all scheduled tasks
- remove_cron_job: Remove a scheduled task
- toggle_cron_job: Enable/disable a scheduled task
- get_timezone: Check user's configured timezone

When the user wants to schedule something naturally (like "remind me every day at 9am"), call the schedule_cron tool with the appropriate parameters.

Current context is available in your memory. Respond naturally.

NOTE: Cron jobs run based on the SERVER timezone (UTC), not the user's local timezone. If scheduling involves specific times and the user's timezone is not set, suggest they set it with /timezone command for accuracy. Common timezones: Asia/Kolkata (India), America/New_York, Europe/London, etc."""
