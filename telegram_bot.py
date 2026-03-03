"""
Telegram bot for Ninoclaw
"""
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from ai import chat, list_models, test_connection
from memory import Memory
from tasks import task_manager
from config import SYSTEM_PROMPT
from tools import get_tool_definitions, execute_tool

memory = Memory()

# Onboarding states
ONBOARDING_STEPS = [
    "agent_name",
    "user_name",
    "purpose",
    "timezone"
]

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command with onboarding"""
    user_id = update.effective_user.id
    user_data = memory.get_user_data(user_id)

    # Check if onboarding completed
    if user_data.get("onboarding_complete"):
        # Show welcome with personalized info
        agent_name = user_data.get("agent_name", "Ninoclaw")
        user_name = user_data.get("user_name", "friend")
        purpose = user_data.get("purpose", "be your assistant")

        welcome = f"""🦀 Welcome back, {user_name}!

I'm {agent_name}, {purpose}.

Commands:
/start - Show this message
/chat - Talk to me
/memory - Show conversation memory
/clear - Clear memory
/tasks - List your tasks
/addtask <task> - Add a task
/remind <time> <message> - Set reminder
/cron - Manage recurring tasks
/models - List available AI models
/status - Check system status

Just send any message to chat!"""
        await update.message.reply_text(welcome)
    else:
        # Start onboarding
        memory.set_user_data(user_id, "onboarding_step", 0)
        await update.message.reply_text("""🦀 Welcome! Let me get to know you better.

I need to ask you a few questions:

1️⃣ What would you like to call me? (My name)""")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check system status"""
    ollama_ok = test_connection()
    models = list_models()

    # Count active cron jobs and find next run
    user_id = update.effective_user.id
    cron_jobs = task_manager.list_cron_jobs(user_id)
    active_crons = [j for j in cron_jobs if j.get("is_active", True)]
    next_run_str = "None"

    if active_crons:
        next_runs = [j.get("next_run") for j in active_crons if j.get("next_run")]
        if next_runs:
            next_run = min(next_runs)
            next_run_str = task_manager.format_timestamp(next_run)

    status_msg = f"""🔍 System Status

🤖 Ollama: {'✅ Connected' if ollama_ok else '❌ Disconnected'}
📦 Available models: {', '.join(models[:5]) if models else 'None'}
💾 Memory: Active
📋 Tasks: {len(task_manager.tasks)} total
🔄 Cron Jobs: {len(active_crons)} active (next: {next_run_str})"""

    await update.message.reply_text(status_msg)

async def models_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List available models"""
    models = list_models()
    if models:
        msg = "📦 Available models:\n\n" + "\n".join(f"• {m}" for m in models)
    else:
        msg = "❌ No models found. Make sure Ollama is running."
    await update.message.reply_text(msg)

async def show_memory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show conversation memory"""
    user_id = update.effective_user.id
    conv = memory.get_conversation(user_id, limit=5)

    if conv:
        msg = "💭 Recent messages:\n\n"
        for m in conv:
            emoji = "👤" if m["role"] == "user" else "🤖"
            msg += f"{emoji} {m['content'][:100]}...\n\n"
    else:
        msg = "💭 No messages in memory yet."

    await update.message.reply_text(msg)

async def clear_memory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear memory"""
    user_id = update.effective_user.id
    memory.clear_conversation(user_id)
    await update.message.reply_text("✅ Memory cleared!")

async def set_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set user timezone"""
    user_id = update.effective_user.id

    if not context.args:
        current_tz = memory.get_timezone(user_id) or "Server time (UTC)"
        await update.message.reply_text(
            f"🕐 Current timezone: {current_tz}\n\n"
            f"Usage: /timezone <timezone>\n"
            f"Examples:\n"
            f"  /timezone America/New_York\n"
            f"  /timezone Europe/London\n"
            f"  /timezone UTC\n"
            f"  /timezone default"
        )
        return

    timezone = " ".join(context.args)
    if timezone.lower() == 'default':
        timezone = None

    memory.set_timezone(user_id, timezone)
    display_tz = timezone if timezone else "Server time (UTC)"
    await update.message.reply_text(f"✅ Timezone set to: {display_tz}")

async def reset_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset onboarding to start over"""
    user_id = update.effective_user.id

    # Clear onboarding data
    memory.set_user_data(user_id, "agent_name", None)
    memory.set_user_data(user_id, "user_name", None)
    memory.set_user_data(user_id, "purpose", None)
    memory.set_user_data(user_id, "onboarding_step", 0)
    memory.set_user_data(user_id, "onboarding_complete", False)

    await update.message.reply_text("✅ Onboarding reset! Send /start to begin again.")

async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List user tasks"""
    user_id = update.effective_user.id
    tasks = task_manager.list_tasks(user_id)

    if tasks:
        msg = "📋 Your tasks:\n\n"
        for t in tasks:
            time_str = task_manager.format_timestamp(t["scheduled_time"])
            msg += f"• {t['name']}\n  📅 {time_str}\n\n"
    else:
        msg = "📋 No pending tasks."

    await update.message.reply_text(msg)

async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a task"""
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("Usage: /addtask <task description>")
        return

    task_name = " ".join(context.args)
    # Default: schedule in 1 hour
    ts = task_manager.parse_time("in 60 minutes")
    task_id = task_manager.add_task(user_id, task_name, ts)

    time_str = task_manager.format_timestamp(ts)
    await update.message.reply_text(f"✅ Task added!\n\n📝 {task_name}\n📅 {time_str}")

async def remind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set a reminder"""
    user_id = update.effective_user.id

    if len(context.args) < 2:
        await update.message.reply_text("Usage: /remind <time> <message>\nExample: /remind in 10 minutes check the oven")
        return

    # Parse time (first argument)
    time_str = context.args[0]
    message = " ".join(context.args[1:])

    ts = task_manager.parse_time(time_str)
    task_id = task_manager.add_task(user_id, f"⏰ Reminder: {message}", ts)

    time_str_formatted = task_manager.format_timestamp(ts)
    await update.message.reply_text(f"⏰ Reminder set!\n\n📝 {message}\n📅 {time_str_formatted}")

async def cron_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a cron job"""
    user_id = update.effective_user.id

    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /cron add <expression> <command>\n"
            "Examples:\n"
            "  /cron add every day at 9am Send me a morning greeting\n"
            "  /cron add */30 * * * * Check my tasks\n"
            "  /cron add weekdays at 10am Weekly check-in"
        )
        return

    # Parse: first argument is expression, rest is command
    # Need to handle cron expressions with spaces like "0 9 * * *"
    # Try to detect if it's a standard cron expression (5 parts)
    args = context.args

    # Check if first args form a valid cron expression (5 parts)
    cron_parts = []
    command_parts = []
    i = 0

    # Try to extract cron expression (5 parts)
    if len(args) >= 6 and re.match(r'^[\d*/\-,\s?*]+$', args[0]):
        # Looks like a cron expression
        cron_expr = " ".join(args[:5])
        command = " ".join(args[5:])
    else:
        # Natural language - first arg is expression, rest is command
        expr = args[0]
        command = " ".join(args[1:])
        cron_expr = expr

    # Generate a name for the job
    name = command[:30] + "..." if len(command) > 30 else command

    # Add the cron job
    job_id, error = task_manager.add_cron_job(user_id, name, cron_expr, command)

    if error:
        await update.message.reply_text(f"❌ Error: {error}")
    else:
        job = task_manager.get_cron_job(job_id, user_id)
        next_run = task_manager.format_timestamp(job["next_run"]) if job["next_run"] else "Unknown"
        await update.message.reply_text(
            f"✅ Cron job added!\n\n"
            f"📝 {name}\n"
            f"⏰ Expression: {job['cron_expression']}\n"
            f"📅 Next run: {next_run}\n"
            f"🆔 ID: {job_id}"
        )

async def cron_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List cron jobs"""
    user_id = update.effective_user.id
    jobs = task_manager.list_cron_jobs(user_id)

    if jobs:
        msg = "🔄 Your cron jobs:\n\n"
        for job in jobs:
            status_emoji = "✅" if job.get("is_active", True) else "⏸️"
            next_run = task_manager.format_timestamp(job["next_run"]) if job.get("next_run") else "Unknown"
            last_run = task_manager.format_timestamp(job["last_run"]) if job.get("last_run") else "Never"
            msg += f"{status_emoji} {job['name']}\n"
            msg += f"   ⏰ {job['cron_expression']}\n"
            msg += f"   📅 Next: {next_run}\n"
            msg += f"   🕐 Last: {last_run}\n"
            msg += f"   🆔 {job['id']}\n\n"
    else:
        msg = "🔄 No cron jobs yet.\n\nUse /cron add to create one!"

    await update.message.reply_text(msg)

async def cron_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a cron job"""
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("Usage: /cron remove <id>\nUse /cron list to see job IDs")
        return

    job_id = context.args[0]
    if task_manager.remove_cron_job(job_id, user_id):
        await update.message.reply_text("✅ Cron job removed!")
    else:
        await update.message.reply_text("❌ Job not found or you don't have permission")

async def cron_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle a cron job on/off"""
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("Usage: /cron toggle <id>\nUse /cron list to see job IDs")
        return

    job_id = context.args[0]
    is_active = task_manager.toggle_cron_job(job_id, user_id)

    if is_active is None:
        await update.message.reply_text("❌ Job not found or you don't have permission")
    else:
        status = "enabled" if is_active else "disabled"
        await update.message.reply_text(f"✅ Cron job {status}!")

async def cron_show(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show details of a specific cron job"""
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("Usage: /cron show <id>\nUse /cron list to see job IDs")
        return

    job_id = context.args[0]
    job = task_manager.get_cron_job(job_id, user_id)

    if not job:
        await update.message.reply_text("❌ Job not found or you don't have permission")
        return

    status = "✅ Active" if job.get("is_active", True) else "⏸️ Paused"
    next_run = task_manager.format_timestamp(job["next_run"]) if job.get("next_run") else "Unknown"
    last_run = task_manager.format_timestamp(job["last_run"]) if job.get("last_run") else "Never"

    msg = f"""🔄 Cron Job Details

📝 Name: {job['name']}
{status}
⏰ Expression: {job['cron_expression']}
🆔 ID: {job['id']}
📅 Created: {job.get('created_at', 'Unknown')}
📅 Next run: {next_run}
🕐 Last run: {last_run}

💬 Command: {job['command']}"""

    await update.message.reply_text(msg)

async def cron_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /cron command - shows usage or routes to subcommands"""
    if not context.args:
        await update.message.reply_text(
            "🔄 Cron Job Commands\n\n"
            "Usage: /cron <action> [args]\n\n"
            "Actions:\n"
            "  • /cron add <expr> <cmd> - Add a new cron job\n"
            "  • /cron list - List all cron jobs\n"
            "  • /cron show <id> - Show job details\n"
            "  • /cron toggle <id> - Enable/disable a job\n"
            "  • /cron remove <id> - Remove a job\n\n"
            "Examples:\n"
            "  /cron add every day at 9am Send me a greeting\n"
            "  /cron add */30 * * * * Check my tasks\n"
            "  /cron list\n"
            "  /cron toggle 123456"
        )
        return

    action = context.args[0].lower()

    # Route to appropriate handler
    if action == "add":
        # Pass remaining args (skip 'add')
        context.args = context.args[1:]
        await cron_add(update, context)
    elif action == "list":
        await cron_list(update, context)
    elif action == "remove":
        context.args = context.args[1:]
        await cron_remove(update, context)
    elif action == "toggle":
        context.args = context.args[1:]
        await cron_toggle(update, context)
    elif action == "show":
        context.args = context.args[1:]
        await cron_show(update, context)
    else:
        await update.message.reply_text(f"❌ Unknown action: {action}\nUse /cron for help")

# Message handler for chat
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular chat messages and onboarding"""
    user_id = update.effective_user.id
    user_message = update.message.text
    user_data = memory.get_user_data(user_id)

    # Check if in onboarding
    if not user_data.get("onboarding_complete"):
        await handle_onboarding(update, user_id, user_message, user_data)
        return

    # Normal chat - Save user message to memory
    memory.add_message(user_id, "user", user_message)

    # Get conversation history for context
    conv_history = memory.get_conversation_context(user_id)
    # Remove the last message (we just added it)
    conv_history = conv_history[:-1]

    # Build personalized system prompt
    agent_name = user_data.get("agent_name", "Ninoclaw")
    user_name = user_data.get("user_name", "friend")
    purpose = user_data.get("purpose", "be your assistant")

    personalized_prompt = f"""{SYSTEM_PROMPT}

Your name is {agent_name}. You are talking to {user_name}.
Your purpose is to {purpose}.
Remember these details and use them in your responses.

You have access to tools to schedule and manage recurring tasks. When the user wants to schedule something (like "remind me every day at 9am"), use the schedule_cron tool."""

    # Get AI response - show typing indicator
    await update.message.chat.send_action(action="typing")

    response = chat(
        message=user_message,
        system_prompt=personalized_prompt,
        history=conv_history,
        tools=get_tool_definitions()
    )

    # Handle response (can be string or dict with tool_calls)
    final_response = response if isinstance(response, str) else response.get("content", "")
    tool_calls = response.get("tool_calls") if isinstance(response, dict) else None

    # Execute tool calls if any
    tool_results = []
    if tool_calls:
        for tool_call in tool_calls:
            tool_name = tool_call.get("function", {}).get("name")
            # Arguments can be JSON string or dict
            raw_args = tool_call.get("function", {}).get("arguments", "{}")
            if isinstance(raw_args, str):
                import json
                tool_args = json.loads(raw_args)
            else:
                tool_args = raw_args
            if tool_name:
                result = await execute_tool(tool_name, tool_args, user_id, task_manager)
                tool_results.append(result)

        # Combine AI response with tool results
        if tool_results:
            if final_response:
                final_response += "\n\n"
            final_response += "\n\n".join(tool_results)

    # Save AI response to memory
    memory.add_message(user_id, "assistant", final_response)

    await update.message.reply_text(final_response)

async def handle_onboarding(update: Update, user_id, message, user_data):
    """Handle onboarding flow"""
    step = user_data.get("onboarding_step", 0)

    if step == 0:
        # Agent name
        agent_name = message.strip()
        memory.set_user_data(user_id, "agent_name", agent_name)
        memory.set_user_data(user_id, "onboarding_step", 1)
        await update.message.reply_text(f"Got it! I'll be called {agent_name}. 🎉\n\n2️⃣ What's your name?")

    elif step == 1:
        # User name
        user_name = message.strip()
        memory.set_user_data(user_id, "user_name", user_name)
        memory.set_user_data(user_id, "onboarding_step", 2)
        await update.message.reply_text(f"Nice to meet you, {user_name}! 👋\n\n3️⃣ What's my purpose? What should I help you with?")

    elif step == 2:
        # Purpose
        purpose = message.strip()
        memory.set_user_data(user_id, "purpose", purpose)
        memory.set_user_data(user_id, "onboarding_step", 3)
        await update.message.reply_text(f"Got it! I'll {purpose}. 🤖\n\n4️⃣ What's your timezone? (e.g., 'UTC', 'America/New_York', 'Europe/London', or just say 'default' to use server time)")

    elif step == 3:
        # Timezone
        timezone_input = message.strip().lower()

        if timezone_input in ['default', 'server', 'none']:
            # Keep default (None = server time)
            timezone = None
        else:
            # Try to use the provided timezone
            timezone = message.strip()

        memory.set_timezone(user_id, timezone)
        memory.set_user_data(user_id, "onboarding_complete", True)

        agent_name = user_data.get("agent_name", "Ninoclaw")
        user_name = user_data.get("user_name", "friend")
        purpose = user_data.get("purpose", "be your assistant")

        # Complete onboarding
        await update.message.reply_text(
            f"""Perfect! 🎉

I'm {agent_name} and I'm here to {purpose}!

I'll remember:
- My name: {agent_name}
- Your name: {user_name}
- My purpose: {purpose}
- Your timezone: {timezone if timezone else 'Server time (UTC)'}

Ready to chat! Send me any message to get started.

You can ask me to schedule recurring tasks naturally, like:
"Send me a summary every day at 9am"
"Check my tasks every hour"
"Remind me on weekdays at 10am"

Commands:
/start - Show this message
/memory - Show conversation memory
/clear - Clear memory
/tasks - List your tasks
/addtask <task> - Add a task
/remind <time> <message> - Set reminder
/cron - Manage recurring tasks
/models - List available AI models
/status - Check system status"""
        )

def create_bot(token):
    """Create and configure the Telegram bot"""
    app = Application.builder().token(token).build()

    # Add command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("models", models_command))
    app.add_handler(CommandHandler("memory", show_memory))
    app.add_handler(CommandHandler("clear", clear_memory))
    app.add_handler(CommandHandler("reset", reset_onboarding))
    app.add_handler(CommandHandler("tasks", list_tasks))
    app.add_handler(CommandHandler("addtask", add_task))
    app.add_handler(CommandHandler("remind", remind))
    app.add_handler(CommandHandler("cron", cron_command))
    app.add_handler(CommandHandler("timezone", set_timezone))

    # Add message handler for chat
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Set telegram app reference for cron job execution
    task_manager.telegram_app = app

    return app
