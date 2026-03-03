# 🦀 Ninoclaw — Personal AI Assistant

A lightweight personal AI assistant with memory, scheduling, web search, image vision, and Telegram integration.

---

## ⚡ Quick Start (Termux)

```bash
# 1. Install dependencies
pkg install python git -y
pip install -r requirements.txt

# 2. Clone
git clone https://github.com/Devarakonda-Siddhardha/Ninoclaw.git
cd Ninoclaw

# 3. Make CLI available globally
chmod +x ninoclaw
ln -s "$(pwd)/ninoclaw" "$PREFIX/bin/ninoclaw"

# 4. Run setup wizard + start bot
ninoclaw setup
ninoclaw start
```

---

## 🖥 CLI Commands

```bash
ninoclaw               # start the bot (auto-setup on first run)
ninoclaw setup         # run setup wizard (API keys, model, etc.)
ninoclaw onboard       # alias for setup
ninoclaw reset         # wipe config and re-configure
ninoclaw status        # show current config, model, DB stats
ninoclaw update        # pull latest from GitHub and restart
ninoclaw memory clear  # clear all conversations
ninoclaw memory stats  # show per-user message counts
ninoclaw version       # show current git version
```

---

## 🤖 Telegram Bot Commands

| Command | Description |
|---|---|
| `/start` | Welcome + onboarding (first time) |
| `/status` | System status |
| `/memory` | Show recent conversation |
| `/clear` | Clear chat history |
| `/tasks` | List pending tasks |
| `/remind in 10 minutes buy milk` | One-time reminder |
| `/cron add every day at 9am Good morning!` | Recurring task |
| `/cron list` | List cron jobs |
| `/timezone Asia/Kolkata` | Set your timezone |
| `/update` | Update bot to latest version (owner only) |

You can also just **chat naturally**:
- *"Remind me in 30 minutes to call mom"*
- *"Search for latest iPhone 16 price"*
- *"Update yourself to the latest version"*
- Send any **photo** — bot will describe/analyze it

---

## 🔑 What You Need

| Thing | Where to get |
|---|---|
| Telegram Bot Token | Message `@BotFather` on Telegram |
| Gemini API Key *(free)* | https://aistudio.google.com/app/apikey |
| Serper API Key *(optional, web search)* | https://serper.dev |
| Your Telegram ID *(optional, owner lock)* | Message `@userinfobot` on Telegram |

---

## 🔄 Run in Background (Termux)

```bash
# Keep running after closing Termux
nohup ninoclaw start > ninoclaw.log 2>&1 &

# With tmux (recommended)
pkg install tmux
tmux new -s ninoclaw
ninoclaw start
# Detach: Ctrl+B then D
# Reattach: tmux attach -t ninoclaw
```

---

## 📁 Project Files

| File | Purpose |
|---|---|
| `cli.py` | CLI entry point |
| `wizard.py` | Interactive setup wizard |
| `main.py` | Bot startup |
| `telegram_bot.py` | Telegram handlers |
| `ai.py` | AI model chain with fallback |
| `memory.py` | SQLite conversation memory |
| `tasks.py` | Task & cron scheduler |
| `tools.py` | AI tool definitions |
| `summarizer.py` | URL & YouTube summarizer |
| `updater.py` | Self-update via git pull |
| `config.py` | Configuration loader |
| `.env` | Your secrets *(never committed)* |
| `ninoclaw.db` | SQLite database *(never committed)* |
