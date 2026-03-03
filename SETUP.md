# Ninoclaw - Personal AI Assistant

A lightweight Python AI assistant with memory, tasks, and Telegram integration.

## Features

- 🤖 **AI Options** - OpenAI API or local Ollama
- 💾 **Memory** - Remembers conversations across sessions
- 📋 **Tasks** - Schedule tasks and reminders
- 📱 **Telegram** - Chat with your assistant via Telegram
- 🔒 **Private** - Choose local or cloud based on your needs

## Setup

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Get Telegram Bot Token

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` and follow instructions
3. Copy your bot token (looks like `123456:ABC-defGHI...`)

### 3. Choose AI Provider

**Option A: OpenAI API (Recommended - easier setup)**

```bash
export AI_PROVIDER="openai"
export OPENAI_API_KEY="your-api-key-here"
export OPENAI_MODEL="gpt-4o-mini"  # or gpt-4o, claude-3-5-sonnet, etc.
```

Get API key from:
- OpenAI: https://platform.openai.com/api-keys
- Anthropic Claude: https://console.anthropic.com/keys

**Option B: Local Ollama**

```bash
export AI_PROVIDER="ollama"
export OLLAMA_HOST="http://localhost:11434"
export OLLAMA_MODEL="llama3.2"
```

### 4. Set Telegram Token

```bash
export TELEGRAM_BOT_TOKEN="your_bot_token_here"
```

### 5. Run Ninoclaw

**For OpenAI API:**
```bash
python main.py
```

**For Ollama (start it first in another terminal):**
```bash
# In your Debian proot:
ollama serve

# In Termux:
python main.py
```

## Commands

- `/start` - Start bot (first time: onboarding flow)
- `/status` - Check system status
- `/models` - List available AI models
- `/memory` - Show conversation memory
- `/clear` - Clear memory
- `/reset` - Reset onboarding (start over)
- `/tasks` - List your tasks
- `/addtask <task>` - Add a task
- `/remind <time> <message>` - Set a reminder

## First-Time Setup (Onboarding)

When you first run `/start`, the bot will ask you:

1. **What would you like to call me?** - Agent's name
2. **What's your name?** - Your name
3. **What's my purpose?** - What bot should help you with

This information is saved and used in all future conversations.

## Usage Examples

```
/remind in 10 minutes check the oven
/addtask call mom at 5pm
Remember my birthday is July 15th
What's on my calendar today?
```

## Files

- `config.py` - Configuration settings
- `ai.py` - AI integration (OpenAI API + Ollama)
- `memory.py` - Conversation memory
- `tasks.py` - Task scheduling
- `telegram_bot.py` - Telegram bot
- `main.py` - Entry point

## Running in Background

```bash
# Using nohup
nohup python main.py > ninoclaw.log 2>&1 &

# Using tmux
tmux new -s ninoclaw
python main.py
# Press Ctrl+B then D to detach
```
