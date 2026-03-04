"""
Telegram bot for Ninoclaw
"""
import re
import base64
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from ai import chat, list_models, test_connection
from memory import Memory, extract_and_store_facts
from tasks import task_manager
from config import SYSTEM_PROMPT, AGENT_NAME, USER_NAME, BOT_PURPOSE
from tools import get_tool_definitions, execute_tool
from summarizer import extract_urls, is_youtube, get_youtube_transcript, get_url_content, build_summary_prompt

memory = Memory()

# ── File extensions for known code languages ─────────────────────────────────
_CODE_EXTS = {
    "html": "html", "css": "css", "javascript": "js", "js": "js",
    "typescript": "ts", "ts": "ts", "python": "py", "py": "py",
    "bash": "sh", "sh": "sh", "json": "json", "yaml": "yaml",
    "yml": "yml", "sql": "sql", "markdown": "md", "md": "md",
    "xml": "xml", "rust": "rs", "go": "go", "java": "java",
    "cpp": "cpp", "c": "c", "kotlin": "kt", "swift": "swift",
    "php": "php", "ruby": "rb", "r": "r", "toml": "toml",
}

async def send_with_code_files(update: Update, text: str):
    """
    Send a response. If it contains code blocks (```lang\\n...```),
    extract them and send as downloadable files, then send remaining text.
    """
    import io

    # Find all fenced code blocks
    pattern = re.compile(r"```(\w+)?\n([\s\S]*?)```", re.MULTILINE)
    matches = list(pattern.finditer(text))

    # Only extract as files if the code is substantial (>10 lines or >300 chars)
    file_matches = [
        m for m in matches
        if len(m.group(2).strip().splitlines()) > 10 or len(m.group(2).strip()) > 300
    ]

    if not file_matches:
        # No large code blocks — send as plain text
        if len(text) > 4096:
            for i in range(0, len(text), 4096):
                await update.message.reply_text(text[i:i+4096])
        else:
            await update.message.reply_text(text)
        return

    # Send text with code blocks replaced by "[see attached file]"
    summary = text
    sent_files = []
    for m in file_matches:
        lang = (m.group(1) or "txt").lower()
        ext = _CODE_EXTS.get(lang, "txt")
        filename = f"code.{ext}"
        # Use a unique name if multiple files
        i = len(sent_files) + 1
        if len(file_matches) > 1:
            filename = f"file{i}.{ext}"
        sent_files.append((filename, m.group(2).strip()))
        summary = summary.replace(m.group(0), f"📎 `{filename}`")

    # Send summary text
    summary = summary.strip()
    if summary:
        if len(summary) > 4096:
            for i in range(0, len(summary), 4096):
                await update.message.reply_text(summary[i:i+4096])
        else:
            await update.message.reply_text(summary)

    # Send each code block as a file
    for filename, code in sent_files:
        buf = io.BytesIO(code.encode("utf-8"))
        buf.name = filename
        await update.message.reply_document(document=buf, filename=filename)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show welcome message"""
    welcome = f"""🦀 Hey {USER_NAME}!

I'm {AGENT_NAME}, here to {BOT_PURPOSE}.

Commands:
/start - Show this message
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
_AGENT_KEYWORDS = ("research", "find me", "look up and summarize", "compare", "analyze")
_BG_KEYWORDS = ("in background", "background task", "while i sleep")
_COMPLEX_KEYWORDS = ("research", "find all", "look up and summarize", "compare", "analyze and report", "monitor")


def _is_background_request(msg: str) -> bool:
    low = msg.lower()
    return any(low.startswith(kw) or f" {kw}" in low for kw in _BG_KEYWORDS)


def _is_complex_request(msg: str) -> bool:
    low = msg.lower()
    return any(kw in low for kw in _COMPLEX_KEYWORDS)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular chat messages"""
    import asyncio
    from ai import chat_stream
    user_id = update.effective_user.id
    user_message = update.message.text

    # Save user message to memory
    memory.add_message(user_id, "user", user_message)

    # Check for URLs — auto-summarize
    urls = extract_urls(user_message)
    if urls:
        url = urls[0]
        await update.message.chat.send_action(action="typing")
        if is_youtube(url):
            content, err = get_youtube_transcript(url)
        else:
            content, err = get_url_content(url)

        if err:
            await update.message.reply_text(f"❌ {err}")
            return

        summary_prompt = build_summary_prompt(content, url, is_yt=is_youtube(url))
        response = chat(message=summary_prompt, system_prompt=SYSTEM_PROMPT, history=[])
        final_response = response if isinstance(response, str) else response.get("content") or ""
        memory.add_message(user_id, "assistant", final_response)
        asyncio.create_task(asyncio.to_thread(extract_and_store_facts, user_id, user_message, final_response))
        await update.message.reply_text(f"🔗 Summary of {url}\n\n{final_response}")
        return

    # ── Background job detection ──────────────────────────────────────────────
    if _is_background_request(user_message):
        from bg_agent import bg_runner
        # Strip the background prefix to get the actual goal
        goal = user_message
        for kw in _BG_KEYWORDS:
            goal = re.sub(rf'(?i)^{re.escape(kw)}[,:\s]*', '', goal).strip()
        job_id = bg_runner.queue_job(str(user_id), goal)
        await update.message.reply_text(f"⚙️ Got it! Working on it in the background...\n\n🆔 Job ID: `{job_id}`\nUse /jobs to check status.")
        return

    # Get conversation history for context
    conv_history = memory.get_conversation_context(user_id)
    # Remove the last message (we just added it)
    conv_history = conv_history[:-1]

    facts_ctx = memory.facts_as_context(user_id)
    personalized_prompt = f"""{SYSTEM_PROMPT}

Your name is {AGENT_NAME}. You are talking to {USER_NAME}.
Your purpose is to {BOT_PURPOSE}.
{facts_ctx}
Remember these details and use them in your responses.

You have access to tools to schedule and manage recurring tasks. When the user wants to schedule something (like "remind me every day at 9am"), use the schedule_cron tool."""

    # ── Agent mode for complex multi-step requests ────────────────────────────
    if _is_complex_request(user_message):
        from agent import run_agent
        await update.message.chat.send_action(action="typing")
        status_msg = await update.message.reply_text("🤔 Working on it step by step...")

        async def _progress(msg):
            try:
                await status_msg.edit_text(msg)
            except Exception:
                pass

        result = await run_agent(user_message, str(user_id), task_manager, notify_fn=_progress)
        memory.add_message(user_id, "assistant", result)
        asyncio.create_task(asyncio.to_thread(extract_and_store_facts, user_id, user_message, result))
        try:
            await status_msg.delete()
        except Exception:
            pass
        await send_with_code_files(update, result)
        return

    # Get AI response — use streaming for plain messages, non-streaming when tools needed
    await update.message.chat.send_action(action="typing")

    # First check if tools are needed (non-streaming path)
    response = chat(
        message=user_message,
        system_prompt=personalized_prompt,
        history=conv_history,
        tools=get_tool_definitions()
    )

    final_response = response if isinstance(response, str) else response.get("content") or ""
    tool_calls = response.get("tool_calls") if isinstance(response, dict) else None

    # Execute tool calls if any
    tool_results = []
    if tool_calls:
        for tool_call in tool_calls:
            tool_name = tool_call.get("function", {}).get("name")
            raw_args = tool_call.get("function", {}).get("arguments", "{}")
            if isinstance(raw_args, str):
                import json
                tool_args = json.loads(raw_args)
            else:
                tool_args = raw_args
            if tool_name:
                result = await execute_tool(tool_name, tool_args, user_id, task_manager)
                tool_results.append(result)

        if tool_results:
            if final_response:
                final_response += "\n\n"
            final_response += "\n\n".join(tool_results)

        memory.add_message(user_id, "assistant", final_response)
        asyncio.create_task(asyncio.to_thread(extract_and_store_facts, user_id, user_message, final_response))
        await send_with_code_files(update, final_response)
        return

    # No tool calls — stream response, editing message as chunks arrive
    accumulated = ""
    sent_msg = None
    last_edit = 0
    EDIT_INTERVAL = 0.7

    try:
        async for chunk in chat_stream(
            message=user_message,
            system_prompt=personalized_prompt,
            history=conv_history,
        ):
            accumulated += chunk
            now = asyncio.get_event_loop().time()
            if not sent_msg and accumulated.strip():
                # Send first message as soon as we have content — no placeholder
                sent_msg = await update.message.reply_text(accumulated[:4096])
                last_edit = now
            elif sent_msg and now - last_edit >= EDIT_INTERVAL:
                try:
                    await sent_msg.edit_text(accumulated[:4096])
                    last_edit = now
                except Exception:
                    pass
    except Exception:
        pass

    final_response = accumulated.strip() or final_response or "⚠️ No response."

    # Final update — handle code files or long responses
    has_code = bool(__import__('re').search(r'```\w*\n[\s\S]{300,}```', final_response))
    if has_code:
        # Delete streamed message and resend with file attachments
        if sent_msg:
            try:
                await sent_msg.delete()
            except Exception:
                pass
        await send_with_code_files(update, final_response)
    elif sent_msg:
        # Just do a final clean edit
        try:
            await sent_msg.edit_text(final_response[:4096])
        except Exception:
            pass
        # Send overflow if > 4096
        if len(final_response) > 4096:
            for i in range(4096, len(final_response), 4096):
                await update.message.reply_text(final_response[i:i+4096])
    else:
        await update.message.reply_text(final_response[:4096])

    memory.add_message(user_id, "assistant", final_response)
    asyncio.create_task(asyncio.to_thread(extract_and_store_facts, user_id, user_message, final_response))

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

async def handle_onboarding(update, user_id, message, user_data):
    pass  # Onboarding moved to CLI wizard — this stub kept for safety

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo messages - send image to vision model"""
    user_id = update.effective_user.id

    # Get caption as the user's question (optional)
    caption = update.message.caption or "Describe this image in detail."

    # Download the highest-res photo
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    photo_bytes = await file.download_as_bytearray()
    image_b64 = base64.b64encode(photo_bytes).decode("utf-8")

    personalized_prompt = f"""{SYSTEM_PROMPT}

Your name is {AGENT_NAME}. You are talking to {USER_NAME}.
Your purpose is to {BOT_PURPOSE}."""

    await update.message.chat.send_action(action="typing")

    conv_history = memory.get_conversation_context(user_id)

    response = chat(
        message=caption,
        system_prompt=personalized_prompt,
        history=conv_history,
        tools=get_tool_definitions(),
        image_b64=image_b64
    )

    final_response = response if isinstance(response, str) else response.get("content") or ""

    memory.add_message(user_id, "user", f"[Image] {caption}")
    memory.add_message(user_id, "assistant", final_response)

    await update.message.reply_text(final_response)


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle document uploads — PDF, DOCX, TXT, CSV, code files"""
    import os, io, tempfile
    user_id = update.effective_user.id

    doc = update.message.document
    filename = doc.file_name or "file"
    ext = os.path.splitext(filename)[1].lower()
    caption = update.message.caption or ""

    await update.message.chat.send_action(action="typing")

    # Download file bytes
    file = await context.bot.get_file(doc.file_id)
    file_bytes = await file.download_as_bytearray()

    # Extract text based on file type
    text = ""
    try:
        if ext == ".pdf":
            pdf_data = bytes(file_bytes)
            # Try pdfminer first (handles more encodings)
            try:
                from pdfminer.high_level import extract_text as pdfminer_extract
                text = pdfminer_extract(io.BytesIO(pdf_data)) or ""
            except ImportError:
                text = ""
            # Fallback to pypdf
            if not text.strip():
                try:
                    import pypdf
                    reader = pypdf.PdfReader(io.BytesIO(pdf_data))
                    text = "\n".join(p.extract_text() or "" for p in reader.pages)
                except ImportError:
                    await update.message.reply_text("❌ Install a PDF library: `pip install pdfminer.six`")
                    return
                except Exception as e:
                    await update.message.reply_text(f"❌ Failed to read PDF: {e}")
                    return
            if not text.strip():
                await update.message.reply_text(
                    "⚠️ Could not extract text from this PDF.\n\n"
                    "Try: `pip install pdfminer.six` for better PDF support, "
                    "or send the text content directly."
                )
                return

        elif ext in (".docx",):
            try:
                import docx
                doc_obj = docx.Document(io.BytesIO(file_bytes))
                text = "\n".join(p.text for p in doc_obj.paragraphs)
            except ImportError:
                await update.message.reply_text("❌ python-docx not installed. Run: `pip install python-docx`")
                return

        elif ext in (".txt", ".md", ".py", ".js", ".ts", ".json", ".yaml", ".yml",
                     ".csv", ".html", ".css", ".sh", ".env", ".log", ".xml"):
            text = file_bytes.decode("utf-8", errors="replace")

        else:
            await update.message.reply_text(
                f"❌ Unsupported file type: `{ext}`\n"
                "Supported: PDF, DOCX, TXT, MD, CSV, JSON, YAML, code files, logs"
            )
            return
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to read file: {e}")
        return

    if not text.strip():
        await update.message.reply_text("⚠️ File appears to be empty or unreadable.")
        return

    # Truncate if very large
    MAX_CHARS = 12000
    truncated = len(text) > MAX_CHARS
    if truncated:
        text = text[:MAX_CHARS]

    # Build prompt
    question = caption or "Summarize this file and highlight the key points."
    file_prompt = (
        f"The user sent a file: `{filename}`\n"
        f"{'(truncated to first 12,000 chars) ' if truncated else ''}\n\n"
        f"File contents:\n```\n{text}\n```\n\n"
        f"User's question/request: {question}"
    )

    personalized_prompt = (
        f"{SYSTEM_PROMPT}\n\nYour name is {AGENT_NAME}. "
        f"You are talking to {USER_NAME}. Your purpose is to {BOT_PURPOSE}."
    )

    conv_history = memory.get_conversation_context(user_id)

    response = chat(
        message=file_prompt,
        system_prompt=personalized_prompt,
        history=conv_history,
        tools=get_tool_definitions(),
    )

    final_response = response if isinstance(response, str) else response.get("content") or ""

    memory.add_message(user_id, "user", f"[File: {filename}] {question}")
    memory.add_message(user_id, "assistant", final_response)

    prefix = f"📄 **{filename}**{'  _(truncated)_' if truncated else ''}\n\n"
    await update.message.reply_text(prefix + final_response)


async def show_facts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show stored long-term facts about the user."""
    user_id = update.effective_user.id
    facts = memory.get_facts(user_id)
    if facts:
        lines = "\n".join(f"• {f['key']}: {f['value']}" for f in facts)
        await update.message.reply_text(f"🧠 Known facts about you:\n\n{lines}")
    else:
        await update.message.reply_text("🧠 No facts stored yet. I'll learn about you as we chat!")


async def remember_fact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manually store a fact: /remember <key>=<value> or /remember <key> <value>"""
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Usage: /remember <key> <value>\nExample: /remember timezone IST")
        return
    if "=" in context.args[0]:
        key, _, value = context.args[0].partition("=")
        value = value + (" " + " ".join(context.args[1:]) if len(context.args) > 1 else "")
    else:
        key = context.args[0]
        value = " ".join(context.args[1:])
    if not value.strip():
        await update.message.reply_text("Usage: /remember <key> <value>")
        return
    memory.store_fact(user_id, key.strip(), value.strip())
    await update.message.reply_text(f"✅ Remembered: {key.strip()} = {value.strip()}")


async def forget_fact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a stored fact: /forget <key>"""
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Usage: /forget <key>")
        return
    key = " ".join(context.args)
    memory.delete_fact(user_id, key.strip())
    await update.message.reply_text(f"✅ Forgot: {key.strip()}")


async def show_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show background agent jobs."""
    from bg_agent import bg_runner
    user_id = update.effective_user.id
    jobs = bg_runner.list_jobs(str(user_id))
    if not jobs:
        await update.message.reply_text("⚙️ No background jobs yet.")
        return
    lines = []
    for j in jobs:
        emoji = {"queued": "⏳", "running": "⚙️", "done": "✅", "failed": "❌"}.get(j["status"], "❓")
        lines.append(f"{emoji} [{j['id']}] {j['goal'][:40]}\n   Status: {j['status']}")
    await update.message.reply_text("⚙️ Background jobs:\n\n" + "\n\n".join(lines))


async def update_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pull latest code from GitHub and restart — owner only"""
    from updater import check_for_updates, do_update, get_current_version, restart
    from config import OWNER_ID
    import asyncio

    if OWNER_ID and update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⛔ Only the bot owner can trigger updates.")
        return

    await update.message.reply_text(f"🔍 Checking for updates... (current: {get_current_version()})")

    has_updates, commits = check_for_updates()
    if not has_updates:
        await update.message.reply_text("✅ Already on the latest version!")
        return

    await update.message.reply_text(f"📦 New changes found:\n{commits}\n\nUpdating...")
    success, msg = do_update()
    if not success:
        await update.message.reply_text(f"❌ Update failed:\n{msg}")
        return

    await update.message.reply_text("✅ Update complete! Restarting in 2 seconds... 🔄")
    asyncio.get_event_loop().call_later(2, restart)


def create_bot(token):
    """Create and configure the Telegram bot"""
    app = Application.builder().token(token).build()

    # Add command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("models", models_command))
    app.add_handler(CommandHandler("memory", show_memory))
    app.add_handler(CommandHandler("clear", clear_memory))
    app.add_handler(CommandHandler("tasks", list_tasks))
    app.add_handler(CommandHandler("addtask", add_task))
    app.add_handler(CommandHandler("remind", remind))
    app.add_handler(CommandHandler("cron", cron_command))
    app.add_handler(CommandHandler("timezone", set_timezone))
    app.add_handler(CommandHandler("update", update_bot))
    app.add_handler(CommandHandler("facts", show_facts))
    app.add_handler(CommandHandler("remember", remember_fact))
    app.add_handler(CommandHandler("forget", forget_fact))
    app.add_handler(CommandHandler("jobs", show_jobs))

    # Add message handler for chat
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    # Set telegram app reference for cron job execution
    task_manager.telegram_app = app

    return app
