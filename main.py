"""
Ninoclaw - Personal AI Assistant
Core bot startup — use cli.py / ninoclaw command for full CLI experience.
"""
import os
import sys

# ── Load .env before importing config ────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from telegram import BotCommand
from telegram.ext import Application
from telegram import __version__ as ptb_version
from config import (
    TELEGRAM_BOT_TOKEN, DISCORD_BOT_TOKEN, AI_PROVIDER, OLLAMA_HOST, OLLAMA_MODEL,
    OPENAI_MODEL, OPENAI_API_URL, OPENAI_API_KEY, AGENT_NAME, USER_NAME, BOT_PURPOSE, TIMEZONE
)
import telegram_bot as telegram_module  # Import our local telegram module
from ai import test_connection
from tasks import task_manager
from bg_agent import bg_runner

def print_banner():
    """Print startup banner"""
    banner = """
    ╔════════════════════════════════════════╗
    ║           🦀 NINOCLAW 🦀               ║
    ║     Personal AI Assistant              ║
    ╠════════════════════════════════════════╣
    ║  Memory | Tasks | Telegram | Ollama    ║
    ╚════════════════════════════════════════╝
    """
    print(banner)

def check_environment():
    """Check if environment is properly configured"""
    print("\n🔍 Checking environment...")

    # Check Telegram token
    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ Telegram bot token not set!")
        print("   Please set TELEGRAM_BOT_TOKEN environment variable")
        print("   Get your token from @BotFather on Telegram")
        return False
    else:
        print(f"✅ Telegram token configured")

    # Check AI connection — detect Ollama by API key or URL
    _is_ollama = OPENAI_API_KEY == "ollama" or "localhost:11434" in OPENAI_API_URL
    if _is_ollama:
        print(f"🔗 Checking Ollama at {OPENAI_API_URL}...")
        if test_connection():
            print(f"✅ Ollama connected (model: {OPENAI_MODEL})")
        else:
            print("❌ Ollama not accessible!")
            print("   Make sure Ollama is running: ollama serve")
            print(f"   And that model is pulled: ollama pull {OPENAI_MODEL}")
            return False
    else:
        print(f"🔗 Checking {OPENAI_API_URL}...")
        if test_connection():
            print(f"✅ API connected (model: {OPENAI_MODEL})")
        else:
            print("❌ API not accessible!")
            print("   Check your OPENAI_API_KEY and OPENAI_API_URL in .env")
            return False

    # Check python-telegram-bot version
    print(f"📦 python-telegram-bot: {ptb_version}")

    return True

def setup_bot_commands(application):
    """Set up bot commands for the menu"""
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("status", "Check system status"),
        BotCommand("models", "List available AI models"),
        BotCommand("memory", "Show conversation memory"),
        BotCommand("clear", "Clear memory"),
        BotCommand("reset", "Reset onboarding"),
        BotCommand("tasks", "List your tasks"),
        BotCommand("addtask", "Add a task"),
        BotCommand("remind", "Set a reminder"),
        BotCommand("cron", "Manage recurring tasks"),
        BotCommand("timezone", "Set your timezone"),
    ]
    # set_my_commands is async, but run_polling will handle it
    # Just set the commands, they will be configured on first poll
    application.bot._commands = commands
    return None

def start_dashboard():
    """Start the web dashboard in a background thread"""
    try:
        from dashboard import app as dash_app
        from dotenv import dotenv_values
        import threading
        env = dotenv_values(os.path.join(os.path.dirname(__file__), ".env"))
        port = int(env.get("DASHBOARD_PORT", "8080"))
        t = threading.Thread(
            target=lambda: dash_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False),
            daemon=True
        )
        t.start()
        print(f"✅ Dashboard started → http://localhost:{port}")
    except Exception as e:
        print(f"⚠️  Dashboard failed to start: {e}")


def acquire_lock():
    """Ensure only one instance runs. Returns lock file path or exits."""
    lock_path = os.path.join(os.path.dirname(__file__), ".ninoclaw.lock")
    lock_file = open(lock_path, "w")
    try:
        if sys.platform == "win32":
            import msvcrt
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_file.write(str(os.getpid()))
        lock_file.flush()
        return lock_file  # keep reference alive
    except OSError:
        print("❌ Another Ninoclaw instance is already running!")
        if sys.platform == "win32":
            print("   Stop it first via Task Manager or close the other terminal.")
        else:
            print("   Stop it first: pkill -f 'python.*main.py'")
        sys.exit(1)


def ask_personalization():
    """Interactive first-run: ask bot name, user name, purpose, timezone."""
    env_path = os.path.join(os.path.dirname(__file__), ".env")

    # Read existing .env lines
    lines = []
    if os.path.exists(env_path):
        with open(env_path) as f:
            lines = f.readlines()

    def _set(key, value):
        """Update or append a key in .env"""
        found = False
        for i, line in enumerate(lines):
            if line.startswith(f"{key}="):
                lines[i] = f"{key}={value}\n"
                found = True
                break
        if not found:
            lines.append(f"{key}={value}\n")
        with open(env_path, "w") as f:
            f.writelines(lines)
        # Also update os.environ so config picks it up immediately
        os.environ[key] = value

    C = "\033[96m"; G = "\033[92m"; Y = "\033[93m"; RST = "\033[0m"; B = "\033[1m"

    print(f"\n{C}{B}👋 Quick setup — let me get to know you!{RST}")
    print(f"{Y}  (Press Enter to keep the default shown in brackets){RST}\n")

    try:
        name = input(f"  {C}>{RST} What would you like to call me? [{AGENT_NAME}]: ").strip()
        if not name:
            name = AGENT_NAME
        _set("AGENT_NAME", name)
        print(f"  {G}✓{RST} Got it, I'll be {name}!\n")

        you = input(f"  {C}>{RST} What's your name? [{USER_NAME}]: ").strip()
        if not you:
            you = USER_NAME
        _set("USER_NAME", you)
        print(f"  {G}✓{RST} Nice to meet you, {you}!\n")

        purpose = input(f"  {C}>{RST} What should I help you with? [{BOT_PURPOSE}]: ").strip()
        if not purpose:
            purpose = BOT_PURPOSE
        _set("BOT_PURPOSE", purpose)
        print(f"  {G}✓{RST} I'll {purpose}.\n")

        tz = input(f"  {C}>{RST} Your timezone (e.g. Asia/Kolkata, UTC) [{TIMEZONE}]: ").strip()
        if not tz:
            tz = TIMEZONE
        _set("TIMEZONE", tz)
        print(f"  {G}✓{RST} Timezone: {tz}\n")

        print(f"  {G}✅ All set! Starting {name}...{RST}\n")

        # Reload config values in telegram_bot so it picks up new names
        import importlib, config as cfg
        cfg.AGENT_NAME  = os.environ.get("AGENT_NAME",  name)
        cfg.USER_NAME   = os.environ.get("USER_NAME",   you)
        cfg.BOT_PURPOSE = os.environ.get("BOT_PURPOSE", purpose)
        cfg.TIMEZONE    = os.environ.get("TIMEZONE",    tz)
        import telegram_bot as tb
        tb.AGENT_NAME  = cfg.AGENT_NAME
        tb.USER_NAME   = cfg.USER_NAME
        tb.BOT_PURPOSE = cfg.BOT_PURPOSE

    except (KeyboardInterrupt, EOFError):
        print(f"\n  {Y}Skipped — using defaults.{RST}\n")


def main():
    """Main entry point"""
    lock = acquire_lock()  # noqa: F841 — keep lock held

    print_banner()

    # If personalization not set, ask interactively
    if USER_NAME == "friend" or AGENT_NAME == "Ninoclaw":
        ask_personalization()

    # Check environment
    if not check_environment():
        print("\n❌ Environment check failed. Please fix issues above.")
        sys.exit(1)

    print("\n🚀 Starting Ninoclaw...")

    # Start task scheduler
    task_manager.start_scheduler()
    print("✅ Task scheduler started")

    # Start dashboard
    start_dashboard()

    # Create and start Telegram bot
    app = telegram_module.create_bot(TELEGRAM_BOT_TOKEN)

    # Wire background agent runner
    bg_runner.task_manager = task_manager

    async def _tg_notify(user_id, msg):
        try:
            await app.bot.send_message(chat_id=int(user_id), text=msg)
        except Exception as e:
            print(f"[BG Agent] Notify error: {e}")

    bg_runner.notify_fn = _tg_notify
    bg_runner.start()
    print("✅ Background agent runner started")

    # Start Discord bot if configured
    if DISCORD_BOT_TOKEN:
        try:
            import discord_bot as discord_module
            discord_module.run_bot(DISCORD_BOT_TOKEN)
            print("✅ Discord bot started")
        except ImportError:
            print("⚠️  Discord token set but discord.py not installed — run: pip install discord.py")
        except Exception as e:
            print(f"⚠️  Discord bot failed to start: {e}")

    # Start bot
    print("\n🦀 Ninoclaw is running!")
    print("💬 Open Telegram and talk to your bot\n")

    # Run bot
    app.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down Ninoclaw...")
        task_manager.stop_scheduler()
        print("✅ Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
