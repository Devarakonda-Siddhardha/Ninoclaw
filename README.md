# Ninoclaw

Personal AI assistant with Telegram chat, a local dashboard, memory/tasks, tool use, website generation, and React Native Expo app generation.

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)](https://python.org)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4?logo=telegram)](https://telegram.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Termux](https://img.shields.io/badge/Runs%20on-Termux-black?logo=android)](https://termux.dev)

## What It Is

Ninoclaw is no longer just a Telegram bot. The current project includes:

- Telegram bot interface
- local Flask dashboard
- SQLite-backed memory and task scheduling
- model fallback and fast/smart routing
- plugin-style skills
- website builder with live previews
- React Native Expo app builder with Expo Go and web preview links
- owner-gated system and admin tools
- runtime hot reload for skills, plugin flags, and model settings

## Current Highlights

- Live dashboard at `http://localhost:8080` by default
- Model changes from the dashboard apply to new requests without restarting
- Web chat and Telegram both use the tool-capable agent path
- Expo apps can be created, started, listed, stopped, and deleted from chat or dashboard
- Mobile Apps dashboard page shows Expo Go links, web preview links, and QR codes
- Plugin and skill toggles can hot-reload for new requests
- Capability detection auto-hides unsupported tools on constrained or incompatible devices
- Owner-only enforcement exists at both tool-definition time and execution time

## Features

### Core assistant

- persistent conversation memory
- long-term fact extraction
- one-time reminders
- recurring cron jobs
- URL and YouTube summarization
- multimodal image prompts in Telegram

### AI routing

- OpenAI-compatible providers
- fallback model chain via `MODELS_JSON`
- fast/smart model routing via `FAST_MODEL` and `SMART_MODEL`
- optional local Ollama path

### Builders

- `web_build`, `web_edit`, `web_list`, `web_delete`
- `expo_create_app`, `expo_edit_app`, `expo_start_app`, `expo_stop_app`, `expo_list_apps`, `expo_delete_app`

### Dashboard

- overview/system health
- bot config
- plugin and skill toggles
- AI model config
- memory viewer
- chat history
- tasks and cron management
- builds page
- mobile apps page

## Architecture

Main runtime files:

- [main.py](./main.py): startup, scheduler, dashboard thread, startup checks
- [telegram_bot.py](./telegram_bot.py): Telegram handlers, tool loop, multimodal flow
- [chat_runtime.py](./chat_runtime.py): shared tool-aware runner for dashboard/web chat
- [tools.py](./tools.py): built-in tools, skill tool loading, owner gating, runtime reload
- [ai.py](./ai.py): model routing, provider fallback, live model config reads
- [dashboard.py](./dashboard.py): Flask dashboard and operational UI
- [memory.py](./memory.py): conversation/fact persistence
- [tasks.py](./tasks.py): reminders and cron execution
- [expo_manager.py](./expo_manager.py): Expo project/process lifecycle
- [runtime_capabilities.py](./runtime_capabilities.py): local capability detection and compatibility gating
- [security.py](./security.py): owner checks, path/command guards, skill validation

Important skill files:

- [skills/web_builder.py](./skills/web_builder.py)
- [skills/expo_builder.py](./skills/expo_builder.py)
- [skills/image_gen.py](./skills/image_gen.py)

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

You can also run the core process directly:

```bash
python main.py
```

## Wizard and Compatibility Detection

The setup wizard now detects the local runtime profile and writes conservative defaults for incompatible devices.

Examples:

- disable Windows-only skills on Linux/Termux
- disable Expo builder on low-resource or Termux-like environments
- surface detected device/profile in the wizard, startup logs, and dashboard overview

This is local-only detection:

- OS
- device model when locally available
- RAM
- display availability
- required binaries such as `node`, `npx`, `ollama`
- optional bridge env vars

It does not use hardware IDs, MAC addresses, or telemetry.

## Platform Notes

### Works well for the core gateway

- Windows
- Linux
- macOS
- Termux / Android-hosted setups
- Raspberry Pi class devices for the core bot/dashboard flow

### Conditional or limited

- Expo builder needs `node` and `npx`, and is disabled automatically on low-resource or Termux-like environments
- screenshot support depends on display/desktop environment and available libraries
- local Ollama is a hardware question, not just a code-path question

### Windows-only or Windows-biased skills

- app launcher
- some media-key based desktop controls

## Dashboard Routes

- `/overview`
- `/config`
- `/plugins`
- `/models`
- `/memory`
- `/chat`
- `/tasks`
- `/builds`
- `/mobile-apps`

Build previews:

- website preview: `/builds/<name>/`
- website shared assets: `/builds-assets/<filename>`

Expo previews:

- Expo Go link shown in dashboard/mobile-app results
- web preview link shown separately when Expo web starts successfully

## Example Prompts

### General

- `Remind me in 20 minutes to call mom`
- `Every day at 8am send me a checklist`
- `Summarize https://youtube.com/watch?v=...`
- `What is on my calendar tomorrow?`

### Website builder

- `Build me a SaaS landing page for an AI note-taking startup`
- `Edit my portfolio site and add a pricing section`
- `Use this uploaded image in the hero section`

### Expo builder

- `Build me a React Native Expo app called habit-tracker and return the preview link`
- `Create a mobile to-do app in Expo and start it`
- `Update the todos app UI and restart Expo`

## Configuration

Main config lives in `.env`.

Important keys:

```env
TELEGRAM_BOT_TOKEN=
OWNER_ID=

OPENAI_API_KEY=
OPENAI_API_URL=https://generativelanguage.googleapis.com/v1beta/openai
OPENAI_MODEL=gemini-3-flash-preview

FAST_MODEL=
SMART_MODEL=
MODELS_JSON=

SERPER_API_KEY=

ENABLE_WEB_SEARCH=true
ENABLE_VISION=true
ENABLE_SUMMARIZER=true
ENABLE_REMINDERS=true
ENABLE_CRON=true
ENABLE_SELF_UPDATE=true

DASHBOARD_PORT=8080
DASHBOARD_PASSWORD=change_me

AGENT_NAME=Ninoclaw
USER_NAME=friend
BOT_PURPOSE=be your personal AI assistant
TIMEZONE=UTC

DISABLED_SKILLS=
```

Optional image providers:

```env
FAL_KEY=
HF_TOKEN=
GEMINI_API_KEY=
```

Optional music / IR bridges:

```env
MUSIC_BRIDGE_URL=
IR_BRIDGE_URL=
```

## Runtime Reload

Ninoclaw can reload parts of the runtime without a full restart:

- skill toggles
- built-in plugin toggles
- live tool catalog
- model settings used for new requests

The owner-only tool `reload_runtime` is available for explicit reloads.

## Security Model

Current security controls include:

- owner-only filtering in tool definitions
- owner-only enforcement again at tool execution time
- command/path/skill validation in [security.py](./security.py)
- prompt hardening against prompt injection from tool output or fetched content
- unsupported tool auto-hiding via capability detection
- dashboard password generation if missing or weak

Recommended:

- set `OWNER_ID`
- keep `.env` private
- do not paste live API keys or tokens into logs/chat
- rotate any token that was ever exposed

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

## Screenshots

Place screenshot assets under `docs/screenshots/`.

Suggested current captures:

- dashboard overview
- plugins and skills page
- models page
- builds page
- mobile apps page
- Telegram Expo reply
- Telegram image-to-website flow

## Hardware Guidance

### Good fit

- desktop/laptop
- VPS or always-on Linux box for core bot/dashboard
- Raspberry Pi 4 / Pi 5 for core gateway use

### Not a good full-feature target

- Raspberry Pi Zero 2 W for the full toolchain

Reason:

- core bot may run
- heavy dev tooling like Expo and local model workloads are not a good fit

## Contributing

PRs are welcome. If you change runtime behavior, keep the README aligned with:

- dashboard capabilities
- install/setup flow
- platform support
- security behavior
- builder workflows

## License

MIT
