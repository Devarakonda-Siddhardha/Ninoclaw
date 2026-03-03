"""
Ninoclaw - Personal AI Assistant
A lightweight AI assistant with memory, tasks, and Telegram integration.
"""
import os
import sys
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

def main():
    """Main entry point"""
    print_banner()

    # Check environment
    if not check_environment():
        print("\n❌ Environment check failed. Please fix issues above.")
        sys.exit(1)

    print("\n🚀 Starting Ninoclaw...")

    # Start task scheduler
    task_manager.start_scheduler()
    print("✅ Task scheduler started")

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
