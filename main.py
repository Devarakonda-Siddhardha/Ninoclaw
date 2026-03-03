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
    TELEGRAM_BOT_TOKEN, AI_PROVIDER, OLLAMA_HOST, OLLAMA_MODEL,
    OPENAI_MODEL, OPENAI_API_URL
)
import telegram_bot as telegram_module  # Import our local telegram module
from ai import test_connection
from tasks import task_manager

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

    # Check AI connection
    if AI_PROVIDER == "openai":
        print(f"🔗 Checking {OPENAI_API_URL}...")
        if test_connection():
            print(f"✅ API connected (model: {OPENAI_MODEL})")
        else:
            print("❌ API not accessible!")
            print("   Please set OPENAI_API_KEY environment variable")
            return False
    else:
        print(f"🔗 Checking Ollama at {OLLAMA_HOST}...")
        if test_connection():
            print(f"✅ Ollama connected (model: {OLLAMA_MODEL})")
        else:
            print("❌ Ollama not accessible!")
            print("   Make sure Ollama is running:")
            print("   - In Debian proot: ollama serve")
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
    import fcntl
    lock_path = os.path.join(os.path.dirname(__file__), ".ninoclaw.lock")
    lock_file = open(lock_path, "w")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_file.write(str(os.getpid()))
        lock_file.flush()
        return lock_file  # keep reference alive
    except OSError:
        print("❌ Another Ninoclaw instance is already running!")
        print("   Stop it first: pkill -f 'python.*main.py'")
        sys.exit(1)


def main():
    """Main entry point"""
    lock = acquire_lock()  # noqa: F841 — keep lock held

    print_banner()

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

    # Create bot
    app = telegram_module.create_bot(TELEGRAM_BOT_TOKEN)

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
