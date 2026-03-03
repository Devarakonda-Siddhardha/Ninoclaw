"""
Proactive messaging — bot initiates conversations without user prompting.
Daily briefing, goal check-ins, reminders.
"""
import asyncio
from datetime import datetime


async def send_daily_briefing(bot_send_fn, user_id: str):
    """Generate and send a daily briefing to the user."""
    from ai import chat
    from memory import memory
    from config import AGENT_NAME, USER_NAME, BOT_PURPOSE, SYSTEM_PROMPT

    facts_ctx = memory.facts_as_context(user_id)

    # Get pending tasks
    from tasks import task_manager
    pending = task_manager.list_tasks(str(user_id))
    pending_str = ""
    if pending:
        pending_str = "\nPending tasks:\n" + "\n".join(f"- {t['name']}" for t in pending[:5])

    now = datetime.now().strftime("%A, %B %d %Y, %I:%M %p")

    prompt = f"""Generate a warm, concise morning briefing for {USER_NAME}.
Current time: {now}
{facts_ctx}
{pending_str}

Include:
1. A friendly good morning greeting
2. What day/date it is
3. Any pending tasks (if any)
4. A short motivational or useful tip for the day
5. Offer to help with anything

Keep it under 200 words. Be warm and personal."""

    response = chat(
        message=prompt,
        system_prompt=f"{SYSTEM_PROMPT}\nYour name is {AGENT_NAME}.",
    )
    text = response if isinstance(response, str) else (response.get("content") or "Good morning! 🌅 Have a great day!")

    await bot_send_fn(user_id, f"🌅 **Morning Briefing**\n\n{text}")


def setup_daily_briefing(task_manager, bot_send_fn, user_id: str, time_str: str = "08:00"):
    """Register daily briefing cron job."""
    hour, minute = time_str.split(":")
    cron_expr = f"{minute} {hour} * * *"

    async def _briefing_callback():
        await send_daily_briefing(bot_send_fn, user_id)

    task_manager.add_cron_job(
        user_id=str(user_id),
        name="🌅 Daily Briefing",
        expression=f"daily at {time_str}",
        command="__daily_briefing__"
    )
