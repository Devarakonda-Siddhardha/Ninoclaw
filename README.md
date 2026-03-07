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

## What It Does

Ninoclaw is a memory-aware AI assistant with tools:

- Persistent chat memory (SQLite)
- Web search and URL/YouTube summarization
- One-time reminders and recurring cron schedules
- Multi-model fallback and optional fast/smart routing
- Telegram photo understanding (multimodal)
- Image generation (fal.ai / HuggingFace / Gemini fallback)
- Web builder skill with live previews
- Web dashboard for config, history, tasks, models, plugins, and builds

## Major Features

- Web dashboard is live (default: `http://localhost:8080`)
- Builds tab lists generated websites
- Generated websites are previewed at `/builds/<name>/`
- Shared image assets are served at `/builds-assets/<filename>`
- Telegram image -> website flow:
  - Send an image with caption like `build a landing page using this image`
  - Bot saves image and can embed it in generated HTML
- Tool execution supports multi-step flow
  - Default mode: shorter rounds for speed
  - Deep mode: more rounds for complex requests or prompts like `think harder`

## Screenshots

Place image files in `docs/screenshots/` with the names below.

### Dashboard

![Dashboard Overview](docs/screenshots/dashboard-overview.png)
![Plugins and Skills](docs/screenshots/dashboard-plugins-skills.png)
![Builds Tab](docs/screenshots/dashboard-builds-tab.png)

### Telegram Flows

![Image to Website Prompt](docs/screenshots/telegram-image-to-website-prompt.jpg)
![Generated Build Reply](docs/screenshots/telegram-generated-build-reply.jpg)
![Think Harder Deep Mode](docs/screenshots/telegram-think-harder-deep-mode.jpg)

### Build Preview

![Generated Website Preview](docs/screenshots/build-preview-website.png)

## Architecture

Core files:

- `main.py`: startup, scheduler, dashboard thread, bot runtime
- `telegram_bot.py`: Telegram handlers, tool loops, multimodal image flow
- `tools.py`: tool definitions and execution dispatch
- `dashboard.py`: Flask dashboard and build/static serving routes
- `skills/web_builder.py`: `web_build`, `web_edit`, `web_list`, `web_delete`
- `skills/image_gen.py`: `generate_image` with website asset persistence
- `memory.py`, `tasks.py`: SQLite-backed memory and scheduling
- `security.py`: owner checks and safety guards

## Quick Start

### Windows

```powershell
git clone https://github.com/Devarakonda-Siddhardha/Ninoclaw.git
cd Ninoclaw
pip install -r requirements.txt
.\ninoclaw setup
.\ninoclaw start
```

### Linux / macOS / Termux

```bash
git clone https://github.com/Devarakonda-Siddhardha/Ninoclaw.git
cd Ninoclaw
pip install -r requirements.txt
./ninoclaw setup
./ninoclaw start
```

## Telegram Usage Examples

- `Remind me in 20 minutes to call mom`
- `Every day at 8am send me a checklist`
- `Summarize https://youtube.com/watch?v=...`
- Send photo with caption: `make a website like this`
- `Generate an image of a modern SaaS hero section`
- `Use that generated image in my website`
- `Think harder and keep iterating until the page is polished`

## Web Builder and Builds

Tools:

- `web_build`: create website from full HTML
- `web_edit`: replace website HTML
- `web_list`: list built websites
- `web_delete`: delete a build

Preview routes:

- Build preview: `http://localhost:8080/builds/<name>/`
- Shared assets: `http://localhost:8080/builds-assets/<filename>`

Dashboard route:

- `http://localhost:8080/builds`

## Configuration

Main config is in `.env`:

```env
TELEGRAM_BOT_TOKEN=...
OWNER_ID=123456789

OPENAI_API_KEY=...
OPENAI_API_URL=https://generativelanguage.googleapis.com/v1beta/openai
OPENAI_MODEL=gemini-3-flash-preview

SERPER_API_KEY=...

ENABLE_WEB_SEARCH=true
ENABLE_VISION=true
ENABLE_SUMMARIZER=true
ENABLE_REMINDERS=true
ENABLE_CRON=true

DASHBOARD_PORT=8080
DASHBOARD_PASSWORD=change_me

CONTEXT_WINDOW=20

# Optional image providers
FAL_KEY=
HF_TOKEN=
GEMINI_API_KEY=
```

Optional multi-model chain:

```env
MODELS_JSON=[
  {"api_url":"https://generativelanguage.googleapis.com/v1beta/openai","api_key":"...","model":"gemini-3-flash-preview"},
  {"api_url":"https://api.openai.com/v1","api_key":"...","model":"gpt-4o-mini"}
]
```

## CLI Commands

```text
ninoclaw start
ninoclaw setup
ninoclaw status
ninoclaw dashboard
ninoclaw update
ninoclaw reset
ninoclaw memory stats
ninoclaw memory clear
ninoclaw model
ninoclaw route
ninoclaw imagegen
ninoclaw version
```

## Security Notes

- Set `OWNER_ID` to restrict dangerous/admin tools.
- Dashboard now enforces non-default password generation if missing/weak.
- Sensitive tools are owner-gated in tool execution.
- Keep `.env` private and never commit real tokens.

## Roadmap

- Export chat history
- Better mobile-first dashboard UX
- Voice message transcription workflow
- Multi-user policy controls

## Contributing

PRs are welcome. For major changes, open an issue first.

## License

MIT
