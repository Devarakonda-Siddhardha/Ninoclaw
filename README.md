<div align="center">

# 🐾 Ninoclaw

**Your personal AI assistant — running 24/7 on your phone via Telegram**

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)](https://python.org)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4?logo=telegram)](https://telegram.org)
[![Gemini](https://img.shields.io/badge/Google-Gemini-4285F4?logo=google)](https://ai.google.dev)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Termux](https://img.shields.io/badge/Runs%20on-Termux-black?logo=android)](https://termux.dev)

> A fully offline-capable, self-hosted Telegram AI assistant that lives on your Android phone. No servers. No monthly bills. Just you, your bot, and pure AI power.

</div>

---

## ✨ What is Ninoclaw?

Ninoclaw is a **personal AI assistant Telegram bot** you host yourself — on your own Android phone using Termux. It uses Google Gemini (or any OpenAI-compatible API) as its brain and gives you a smart, memory-aware assistant that:

- **Remembers your conversations** across sessions (SQLite-backed memory)
- **Searches the web** for real-time information (Google Serper)
- **Sees images** you send it (vision/multimodal support)
- **Sets reminders** and **schedules recurring tasks** with cron
- **Summarizes YouTube videos and web pages** automatically
- **Falls back across multiple AI models** so it never goes down
- **Updates itself** from GitHub with a single command

---

## 🚀 Features

| Feature | Description |
|---|---|
| 🧠 **Persistent Memory** | Remembers your chats using SQLite. Configurable context window (default: last 20 messages) |
| 🔍 **Web Search** | Searches Google via Serper API for live news, scores, prices, weather |
| 👁️ **Image Vision** | Send any photo and the AI will analyze, describe, or answer questions about it |
| ⏰ **Smart Reminders** | Say "remind me in 30 mins" — one-time reminders that fire at the right time |
| 🔄 **Cron Scheduling** | "Every day at 9am remind me to drink water" — full recurring cron support |
| 📺 **URL Summarizer** | Paste any YouTube link or webpage URL and get an instant summary |
| 🔁 **Model Fallback Chain** | Define multiple AI models — auto-falls back if one is rate-limited or down |
| 🔐 **Owner Lock** | Sensitive commands (update, admin) locked to your Telegram user ID |
| ♻️ **Self Update** | Tell the bot "update yourself" — it pulls from GitHub and restarts |
| 🌍 **Timezone Aware** | Set your timezone once, reminders and crons use it correctly |

---

## 📱 Architecture

```
Your Phone (Termux)
│
├── ninoclaw (CLI entry point)
│   ├── ninoclaw setup     → Interactive setup wizard
│   ├── ninoclaw start     → Start the bot
│   ├── ninoclaw status    → Check if bot is running
│   ├── ninoclaw reset     → Wipe config and start fresh
│   ├── ninoclaw update    → Pull latest from GitHub
│   └── ninoclaw memory    → View / clear conversation memory
│
├── main.py               → App entry point, starts bot + scheduler
├── telegram_bot.py       → Handles all Telegram messages & commands
├── ai.py                 → Multi-model AI engine with fallback chain
├── tools.py              → AI tool definitions (search, reminders, cron)
├── memory.py             → SQLite conversation + user data storage
├── tasks.py              → SQLite task + cron job storage & scheduler
├── summarizer.py         → YouTube transcript + webpage extractor
├── updater.py            → Git pull + pip install + auto-restart
├── wizard.py             → Arrow-key interactive setup wizard
├── config.py             → All configuration, loaded from .env
└── ninoclaw.db           → SQLite database (auto-created, not committed)
```

---

## 🛠️ Setup (Termux)

### 1. Install dependencies

```bash
pkg update && pkg install python git
pip install python-telegram-bot google-generativeai python-dotenv requests
```

### 2. Clone the repo

```bash
git clone https://github.com/Devarakonda-Siddhardha/Ninoclaw.git ~/ninoclaw
cd ~/ninoclaw
pip install -r requirements.txt
```

### 3. Make the CLI available

```bash
chmod +x ninoclaw
ln -s "$(pwd)/ninoclaw" "$PREFIX/bin/ninoclaw"
```

### 4. Run setup wizard

```bash
ninoclaw setup
```

The interactive wizard will walk you through:
- 🤖 Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- 🔑 AI API Key (Gemini, OpenAI, or any compatible provider)
- 🧠 Model selection (Gemini Flash, GPT-4, etc.)
- 🔍 Serper API Key (optional, for web search)
- 👤 Your Telegram User ID (for owner-only commands)
- 🌍 Your timezone

### 5. Start the bot

```bash
ninoclaw start
```

---

## 🤖 Talking to Your Bot

Once running, open Telegram and chat with your bot:

| What you say | What happens |
|---|---|
| `Hey, what's the weather in Hyderabad?` | Searches Google for live weather |
| `Remind me in 20 minutes to call mom` | Sets a one-time reminder |
| `Every day at 8am say good morning` | Creates a recurring cron job |
| `[Send a photo]` | AI analyzes the image |
| `https://youtube.com/watch?v=...` | Summarizes the video |
| `Update yourself to the latest version` | Pulls from GitHub and restarts |
| `What tasks do I have scheduled?` | Lists all your reminders and cron jobs |

---

## ⚙️ Configuration

All config lives in `.env` (created by the setup wizard, never committed):

```env
TELEGRAM_BOT_TOKEN=your_bot_token
OPENAI_API_KEY=your_gemini_or_openai_key
OPENAI_API_URL=https://generativelanguage.googleapis.com/v1beta/openai/
MODEL=gemini-2.0-flash-exp
SERPER_API_KEY=your_serper_key        # optional, enables web search
OWNER_ID=your_telegram_user_id        # optional, locks admin commands
CONTEXT_WINDOW=20                     # messages sent to AI per request
FALLBACK_MODEL=gemini-1.5-flash       # optional fallback model
```

### Multi-model fallback chain

For maximum uptime, define a full fallback chain in `.env`:

```env
MODELS_JSON=[
  {"api_url": "https://...gemini...", "api_key": "key1", "model": "gemini-2.0-flash-exp"},
  {"api_url": "https://api.openai.com/v1", "api_key": "key2", "model": "gpt-4o-mini"},
  {"api_url": "http://localhost:11434/v1", "api_key": "ollama", "model": "llama3"}
]
```

The bot will automatically try each model in order if one fails or is rate-limited.

---

## 💬 CLI Commands

```
ninoclaw setup       Run the interactive setup wizard
ninoclaw start       Start the Telegram bot
ninoclaw status      Check if the bot is currently running
ninoclaw stop        Stop the running bot
ninoclaw restart     Restart the bot
ninoclaw update      Pull latest code from GitHub
ninoclaw reset       Wipe all config and start fresh
ninoclaw memory      Show memory stats
ninoclaw memory clear  Clear all conversation history
ninoclaw version     Show current version
```

---

## 📦 Requirements

- **Android phone** running [Termux](https://termux.dev)
- **Python 3.10+**
- **Telegram Bot Token** — free from [@BotFather](https://t.me/BotFather)
- **AI API Key** — [Google AI Studio](https://aistudio.google.com) (free tier available)
- **Serper API Key** — optional, [serper.dev](https://serper.dev) (free tier: 2500 searches/month)

---

## 🔒 Privacy

- All data stays **on your device** — no third-party servers involved
- Conversation history stored in local SQLite DB (`ninoclaw.db`)
- `.env` and database files are git-ignored and never uploaded
- Only you (via `OWNER_ID`) can trigger admin operations

---

## 🗺️ Roadmap

- [ ] Inline keyboard buttons for tasks
- [ ] Export chat history (`/export`)
- [ ] Voice message transcription
- [ ] Multi-user support
- [ ] Web dashboard

---

## 🤝 Contributing

Pull requests are welcome! For major changes, open an issue first.

---

<div align="center">

Made with ❤️ by [Siddhardha](https://github.com/Devarakonda-Siddhardha) • Running on Termux • Powered by Gemini

</div>
