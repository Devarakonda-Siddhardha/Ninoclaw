"""
Discord integration for Ninoclaw.
Responds when @mentioned in any channel, plus DMs.
"""
import os
import asyncio
import threading

try:
    import discord
    from discord.ext import commands
    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False

from ai import chat, chat_stream
from memory import memory
from tools import execute_tool, get_tool_definitions
from tasks import task_manager

G = "\033[92m"; RST = "\033[0m"


def _get_config():
    from config import AGENT_NAME, USER_NAME, BOT_PURPOSE, SYSTEM_PROMPT
    return AGENT_NAME, USER_NAME, BOT_PURPOSE, SYSTEM_PROMPT


def create_bot(token: str):
    if not DISCORD_AVAILABLE:
        raise ImportError("discord.py not installed. Run: pip install discord.py")

    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix="!", intents=intents)

    @bot.event
    async def on_ready():
        print(f"  {G}✅{RST} Discord bot ready → {bot.user} ({bot.user.id})")
        try:
            await bot.tree.sync()
        except Exception:
            pass

    @bot.event
    async def on_message(message: discord.Message):
        # Ignore own messages
        if message.author == bot.user:
            return

        is_dm = isinstance(message.channel, discord.DMChannel)
        mentioned = bot.user in message.mentions

        # Only respond in DMs or when @mentioned
        if not is_dm and not mentioned:
            return

        # Strip mention from message text
        user_text = message.content
        if mentioned:
            user_text = user_text.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()
        if not user_text:
            user_text = "Hello!"

        AGENT_NAME, USER_NAME, BOT_PURPOSE, SYSTEM_PROMPT = _get_config()
        user_id = f"discord_{message.author.id}"

        system_prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            f"Your name is {AGENT_NAME}. "
            f"You are talking to {message.author.display_name}. "
            f"Your purpose is to {BOT_PURPOSE}."
        )

        conv_history = memory.get_conversation_context(user_id)
        memory.add_message(user_id, "user", user_text)

        async with message.channel.typing():
            # Check for tool calls first (non-streaming)
            response = chat(
                message=user_text,
                system_prompt=system_prompt,
                history=conv_history,
                tools=get_tool_definitions(user_id)
            )

        final_response = response if isinstance(response, str) else response.get("content") or ""
        tool_calls = response.get("tool_calls") if isinstance(response, dict) else None

        # Handle tool calls
        if tool_calls:
            tool_results = []
            for tc in tool_calls:
                tool_name = tc.get("function", {}).get("name")
                raw_args = tc.get("function", {}).get("arguments", "{}")
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
            # Discord has 2000 char limit — split if needed
            await _send_long(message.channel, final_response)
            return

        # No tools — streaming response
        sent = await message.channel.send("⏳")
        accumulated = ""
        last_edit = 0
        EDIT_INTERVAL = 0.8

        async for chunk in chat_stream(
            message=user_text,
            system_prompt=system_prompt,
            history=conv_history,
        ):
            accumulated += chunk
            now = asyncio.get_event_loop().time()
            if now - last_edit >= EDIT_INTERVAL and accumulated.strip():
                try:
                    await sent.edit(content=accumulated[:2000])
                    last_edit = now
                except Exception:
                    pass

        final_response = accumulated or final_response
        if final_response.strip():
            try:
                await sent.edit(content=final_response[:2000])
            except Exception:
                pass
            # If response > 2000 chars, send overflow as follow-ups
            if len(final_response) > 2000:
                for chunk in _split(final_response[2000:]):
                    await message.channel.send(chunk)

        memory.add_message(user_id, "assistant", final_response)

    return bot


async def _send_long(channel, text):
    for chunk in _split(text):
        await channel.send(chunk)


def _split(text, limit=2000):
    """Split text into chunks ≤ limit chars."""
    chunks = []
    while len(text) > limit:
        split_at = text.rfind("\n", 0, limit) or limit
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip()
    if text:
        chunks.append(text)
    return chunks


def run_bot(token: str):
    """Run Discord bot in its own thread."""
    bot = create_bot(token)

    def _run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(bot.start(token))

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return t
