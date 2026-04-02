# Ninoclaw WhatsApp Channel Plan

This document is a handoff-ready implementation plan for adding WhatsApp support to Ninoclaw in a way that fits the current codebase.

Goal:
- Add WhatsApp as a first-class messaging channel alongside Telegram and Discord.
- Reuse Ninoclaw's existing memory, tools, tracing, and AI flow.
- Keep the bridge architecture local and safer than the older Nanobot pattern.

Non-goals for v1:
- Perfect media parity with Telegram on day one
- Group chat support
- Rich interactive WhatsApp UI components
- Multi-device bridge clustering

## Existing Architecture Summary

Ninoclaw already has the right shape for another chat channel:

- [`main.py`](./main.py): starts Telegram, Discord, background jobs, dashboard
- [`telegram_bot.py`](./telegram_bot.py): full-featured channel implementation with memory, tools, run tracing, media
- [`discord_bot.py`](./discord_bot.py): simpler channel implementation with the same core AI flow
- [`config.py`](./config.py): `.env`-based runtime configuration
- [`cli.py`](./cli.py): command entrypoint and integration/config commands
- [`wizard.py`](./wizard.py): guided setup flow for messaging platforms
- [`run_traces.py`](./run_traces.py): dashboard run tracing by channel
- [`memory.py`](./memory.py): conversation context and facts storage
- [`tools.py`](./tools.py): shared tool definitions and tool execution

Interpretation:
- WhatsApp should be implemented as another channel module, not as a separate application model.
- The bridge should only translate WhatsApp events to Ninoclaw's existing AI pipeline.

## Recommended Design

### 1. New Modules

Add these files:

- [`whatsapp_bot.py`](./whatsapp_bot.py)
  Purpose:
  - normalize inbound WhatsApp events
  - create channel-specific `user_id` values like `whatsapp_<phone>`
  - call the same AI/tool flow used by other channels
  - send replies back through the bridge

- [`whatsapp_bridge.py`](./whatsapp_bridge.py)
  Purpose:
  - manage the local WhatsApp bridge process
  - expose health/login/session helpers
  - hide bridge-specific details from the bot logic

Optional later:

- [`whatsapp_media.py`](./whatsapp_media.py)
  Purpose:
  - keep media upload/download helpers separate if `whatsapp_bot.py` grows too much

### 2. Configuration Model

Add these env vars in [`config.py`](./config.py) and surface them in wizard/dashboard later:

- `WHATSAPP_ENABLED=false`
- `WHATSAPP_BRIDGE_URL=http://127.0.0.1:3001`
- `WHATSAPP_BRIDGE_TOKEN=`  
- `WHATSAPP_SESSION_NAME=ninoclaw`
- `WHATSAPP_ALLOWED_SENDERS=`  
- `WHATSAPP_AUTO_START_BRIDGE=true`
- `WHATSAPP_BRIDGE_TYPE=`  

Notes:
- `WHATSAPP_ALLOWED_SENDERS` should be a comma-separated allowlist of phone numbers.
- Default bind must stay local-only.
- Bridge auth token is required for local HTTP/WebSocket calls if the bridge supports it.

### 3. Channel Runtime Flow

Inbound flow:

1. bridge receives WhatsApp message
2. bridge forwards normalized event to `whatsapp_bot.py`
3. `whatsapp_bot.py` validates sender against allowlist
4. build `user_id = "whatsapp_<sender>"`
5. call `start_run(user_id, "whatsapp", user_message)`
6. load memory context
7. call `chat(...)` and tools using existing tool system
8. save assistant response to memory
9. send response back through bridge
10. call `finish_run(...)`

This should mirror the current patterns in [`telegram_bot.py`](./telegram_bot.py) and [`discord_bot.py`](./discord_bot.py).

## Security Requirements

These are mandatory and should not be deferred:

- Bridge must bind to `127.0.0.1`, never `0.0.0.0`
- Bridge communication should require a secret token if supported
- Only explicitly allowed senders should be accepted in v1
- Session files must remain local and never be committed
- Media downloads must be size-limited
- Log and trace payloads must avoid storing raw secrets

Do not copy insecure patterns from older public WhatsApp bridge examples.

## Implementation Phases

## Phase 1: Config and Bridge Skeleton

Goal:
- Create the config surface and a bridge manager without yet completing full chat support

Tasks:
- Add WhatsApp env vars in [`config.py`](./config.py)
- Add bridge/process helpers in [`whatsapp_bridge.py`](./whatsapp_bridge.py)
- Add CLI commands in [`cli.py`](./cli.py):
  - `ninoclaw whatsapp status`
  - `ninoclaw whatsapp start`
  - `ninoclaw whatsapp stop`
  - `ninoclaw whatsapp login`
- Add `.gitignore` entries if the bridge creates session/cache files

Acceptance criteria:
- status command works even when bridge is missing
- start/stop commands fail gracefully with clear messages
- login command explains next steps clearly

## Phase 2: Text-Only Channel Integration

Goal:
- Support one-to-one text conversations on WhatsApp

Tasks:
- Create [`whatsapp_bot.py`](./whatsapp_bot.py)
- Implement sender normalization and allowlist checking
- Reuse memory/tool/AI flow from existing channels
- Add `run_traces.py` integration with channel name `whatsapp`
- Start WhatsApp listener from [`main.py`](./main.py) when enabled

Acceptance criteria:
- WhatsApp DM text reaches the model
- assistant reply is sent back successfully
- memory is stored under `whatsapp_<sender>`
- dashboard run trace shows channel `whatsapp`

## Phase 3: Wizard and Dashboard Integration

Goal:
- Make WhatsApp discoverable and configurable through existing UX

Tasks:
- Add WhatsApp to messaging platform selection in [`wizard.py`](./wizard.py)
- Add WhatsApp config/status card to [`dashboard.py`](./dashboard.py)
- Show bridge health, session name, allowed senders, and login status

Acceptance criteria:
- users can enable WhatsApp from wizard
- dashboard shows whether session is connected
- users do not need to manually edit `.env` for common setup

## Phase 4: Media Support

Goal:
- Handle common media flows, starting small

v1 media scope:
- receive image messages
- include image/caption in model input
- send text responses back

Optional v1.1:
- receive voice notes as files
- receive documents
- send image/file replies

Acceptance criteria:
- image + caption messages do not crash the channel
- media downloads are temporary and bounded
- model can answer based on image content when supported

## Suggested File-Level Work Breakdown

This section is intended for parallel agents or separate PRs.

### Worker A: Config + CLI

Own these files:
- [`config.py`](./config.py)
- [`cli.py`](./cli.py)
- [`SETUP.md`](./SETUP.md)
- [`README.md`](./README.md)

Deliverables:
- new WhatsApp env vars
- WhatsApp CLI subcommands
- docs for setup and login flow

### Worker B: Bridge Manager

Own these files:
- [`whatsapp_bridge.py`](./whatsapp_bridge.py)
- optionally [`requirements.txt`](./requirements.txt) if a new Python dependency is truly needed

Deliverables:
- local bridge lifecycle management
- health/login/session helper functions
- secure local-only defaults

### Worker C: Bot Channel

Own these files:
- [`whatsapp_bot.py`](./whatsapp_bot.py)
- [`main.py`](./main.py)
- [`run_traces.py`](./run_traces.py) only if channel-specific trace additions are needed

Deliverables:
- inbound/outbound text flow
- memory integration
- tool execution path
- startup hook in main

### Worker D: UX Integration

Own these files:
- [`wizard.py`](./wizard.py)
- [`dashboard.py`](./dashboard.py)

Deliverables:
- wizard support
- dashboard status/config page

## Suggested Technical Approach

Bridge selection:
- Prefer a local bridge with a stable HTTP/WebSocket API and QR login flow
- Wrap all bridge-specific behavior behind `whatsapp_bridge.py`
- Do not scatter bridge API calls throughout the codebase

Message handling:
- Start with plain text only
- Keep message normalization in one function
- Convert WhatsApp sender IDs into a stable internal `user_id`

Tracing:
- use `start_run(..., "whatsapp", ...)`
- log bridge receive/send failures through `log_event(...)`
- ensure `finish_run(...)` always runs even on send failure

Error handling:
- never let a malformed bridge event crash the whole process
- return clear operator-facing error strings in CLI status commands
- print actionable setup instructions when login is incomplete

## Open Decisions

These should be resolved before Phase 2 is finalized:

1. Which bridge to use
- local Node bridge
- HTTP bridge
- another maintained local wrapper

2. Sender policy for v1
- strict allowlist only
- owner-only single number
- multi-user allowlist from env

3. Startup behavior
- auto-start bridge from `main.py`
- or require manual `ninoclaw whatsapp start`

Recommended default:
- auto-start if `WHATSAPP_ENABLED=true`
- still allow manual CLI control

## Testing Checklist

Minimum manual tests:

- bridge not installed -> status/start/login give helpful output
- allowed sender sends text -> gets response
- blocked sender sends text -> ignored or rejected cleanly
- dashboard run trace shows `whatsapp`
- restart Ninoclaw -> WhatsApp session reconnects cleanly
- bridge unavailable during runtime -> process logs error but other channels remain alive

## Definition of Done for V1

V1 is complete when:

- `WHATSAPP_ENABLED=true` starts a WhatsApp channel
- a user can complete QR login
- text chats work end-to-end
- allowlist is enforced
- runs are visible in dashboard tracing
- setup/docs are clear enough for another developer to reproduce

## Recommended First Commit

If time is limited, the first commit should only include:

- [`whatsapp_bridge.py`](./whatsapp_bridge.py) skeleton
- WhatsApp env vars in [`config.py`](./config.py)
- CLI placeholders in [`cli.py`](./cli.py)
- startup placeholder in [`main.py`](./main.py)
- docs note in [`README.md`](./README.md)

That creates a clean foundation for follow-up agents without locking in the full implementation yet.
