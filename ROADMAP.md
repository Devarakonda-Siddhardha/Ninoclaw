# Ninoclaw Roadmap

Feature gap analysis vs [OpenClaw](https://github.com/openclaw/openclaw), the leading open-source personal AI assistant.
Includes feasibility, priority, and whether Ninoclaw already covers the use case differently.

---

## Top 20 Missing Features

| # | Feature | OpenClaw | Ninoclaw | Feasible? | Needed? |
|---|---------|----------|----------|-----------|---------|
| 1 | **Text-to-Speech (TTS)** | ElevenLabs + local ONNX sherpa | ❌ Missing | ✅ Easy — ElevenLabs/gTTS skill | Yes — huge UX upgrade for voice replies |
| 2 | **Browser Automation** | Full Chrome control via CDP | ❌ Missing (MCP optional) | ✅ Medium — Playwright skill | Yes — very useful for web tasks |
| 3 | **Usage / Cost Tracking** | Built-in token cost monitor | ❌ Missing | ✅ Easy — log tokens per call to DB | Yes — helps manage API spend |
| 4 | **Webhook Triggers** | External webhooks fire agent | ❌ Missing | ✅ Easy — add `/webhook/<token>` Flask route | Yes — enables automation from any app |
| 5 | **PDF Processing** | nano-pdf skill | ❌ Missing | ✅ Easy — pypdf skill | Yes — very common use case |
| 6 | **Thinking Level Config** | off → xhigh per request | ❌ Missing | ✅ Easy — env var + prompt prefix | Yes — useful for hard reasoning tasks |
| 7 | **Note-taking (Obsidian/Notion)** | Obsidian, Notion, Bear, Apple Notes | ❌ Missing | ✅ Easy — REST APIs available | Yes — core productivity |
| 8 | **Smart Home (Hue/MQTT)** | OpenHue smart lights skill | ❌ Missing | ✅ Easy — Hue API skill | Yes, if user has smart home |
| 9 | **Trello / Task Managers** | Trello, Things, Taskflow skills | ❌ Missing | ✅ Easy — Trello REST API | Yes — productivity |
| 10 | **Tailscale / Remote Access** | Tailscale Serve/Funnel built-in | ❌ Missing | ✅ Easy — docs + CLI wrapper | Yes — remote dashboard access is painful |
| 11 | **Group Chat Mention Gating** | `@bot` required in groups, reply tags | Basic group support | ✅ Easy — filter by mention in telegram_bot.py | Yes — prevents noise in group chats |
| 12 | **More Messaging Channels** | 23+ (Signal, Matrix, iMessage, Teams…) | Telegram, Discord, WhatsApp only | ⚠️ Each needs a bridge | Signal and Matrix most useful |
| 13 | **Video Analysis** | video-frames skill | ❌ Missing | ✅ Medium — ffmpeg frames + vision model | Useful |
| 14 | **DM Pairing / Multi-user** | Pairing codes, per-user allowlist | Owner-only model | ⚠️ Medium — needs user DB + pairing flow | Yes — sharing bot with family/team |
| 15 | **Voice Wake Word** | Native macOS/Android detection | ❌ Missing | ⚠️ Hard on Windows; doable on Android companion | Nice to have |
| 16 | **Talk Mode (Continuous Voice)** | Android overlay, always-listening | ❌ Missing | ⚠️ Hard natively; partial via companion mic | Nice to have |
| 17 | **Native Desktop App (macOS)** | Menu bar app, voice wake, push-to-talk | ❌ No native app | ❌ Major effort — different stack | Not needed, dashboard covers it |
| 18 | **Per-user Sandboxing** | Docker isolation per session | ❌ Missing | ❌ Hard — major architecture change | Not needed for single-owner use |
| 19 | **Cross-session Agent Comms** | Agents can message each other | ❌ Missing | ⚠️ Medium — needs session routing | Not needed for single-owner |
| 20 | **Development Channels (beta/dev)** | stable / beta / dev branches | Single main branch | ✅ Easy — branching + version tags | Nice to have |

---

## What We Already Have (Just Different)

These features exist in OpenClaw and are also covered in Ninoclaw — just via a different approach:

| Feature | OpenClaw Approach | Ninoclaw Approach |
|---------|-------------------|-------------------|
| LAN auto-discovery | Bonjour/mDNS | Companion app subnet scanner |
| Skill creation | ClawHub registry + plugin-sdk | `create_skill` tool + dynamic loading |
| Memory | Session-based context compacting | SQLite `conversations` + `facts` tables |
| Web/App builder | Canvas visual workspace | `web_build`, `expo_create_app` tools |
| Browser automation | Chrome CDP plugin | Optional via MCP (Live Chrome Automation) |
| Screenshot | Device-native capture | `take_screenshot` tool on PC |
| Health check | `openclaw doctor` command | `/api/mobile/runtime/health` + `fixenv` |
| Setup wizard | `openclaw onboard` | `ninoclaw setup` interactive wizard |
| Skill hot-reload | Plugin toggle | `reload_runtime` tool |
| Self-update | Implied in setup | `self_update` tool (GitHub pull + restart) |

---

## Where Ninoclaw Leads OpenClaw

Features we have that OpenClaw does not:

- **Website builder** — `web_build`, `web_edit`, `web_list`, `web_delete` with live preview at `/builds/<name>/`
- **Expo mobile app builder** — `expo_create_app`, `expo_edit_app`, `expo_start_app`, `expo_stop_app`, `expo_list_apps`, `expo_delete_app`
- **PC app control** — `open_app`, `close_app`, `list_running_apps`
- **File operations** — `read_file`, `write_file`, `list_dir`, `rename_path` (all owner-gated)
- **Stock & crypto prices** — `crypto_price`, `stock_price`
- **Currency conversion** — `convert_currency` with live rates
- **Claude Code integration** — `claude_code` tool for programming tasks
- **Termux/Android-hosted** — explicitly supported with capability detection
- **Android companion with accessibility service** — screen reading, tap, type, gestures

---

## Phased Roadmap

### Phase 1 — Quick Wins (1–2 weeks)
All of these are standalone skills or small Flask routes.

- [ ] **TTS skill** — ElevenLabs API (fallback: gTTS offline). Send voice replies on Telegram.
- [ ] **PDF skill** — `pypdf` extraction. `read_pdf(path_or_url)` tool.
- [ ] **Webhook trigger** — `POST /webhook/<token>` fires the agent with a payload message.
- [ ] **Usage tracking** — Log `prompt_tokens` + `completion_tokens` per call to SQLite. Add `/usage` dashboard route.
- [ ] **Thinking level** — `THINKING_LEVEL` env var (off/low/medium/high). Prefix system prompt when set.
- [ ] **Group chat mention gating** — In `telegram_bot.py`, ignore group messages that don't mention the bot.

### Phase 2 — Integrations (2–4 weeks)
Popular third-party API skills.

- [ ] **Notion skill** — Read/create pages via Notion API.
- [ ] **Obsidian skill** — Read/write local vault via Obsidian Local REST API plugin.
- [ ] **Trello skill** — List boards/cards, create cards, move cards.
- [ ] **Smart home skill** — Philips Hue lights (on/off/colour/brightness). MQTT optional.
- [ ] **Tailscale docs + helper** — Document how to expose dashboard via `tailscale serve`. Add `ninoclaw tunnel` CLI shortcut.
- [ ] **Signal bridge** — Add Signal as a channel via signal-cli or AsamK bridge.

### Phase 3 — Power Features (1–2 months)
More complex, higher impact.

- [ ] **Browser automation skill** — Playwright headless Chrome. `browse(url)`, `click(selector)`, `fill(selector, text)`, `screenshot()`.
- [ ] **Video analysis** — ffmpeg frame extraction + vision model. `analyze_video(path_or_url)` tool.
- [ ] **DM pairing / multi-user** — Pairing code flow for Telegram. Allowlist DB. Per-user memory isolation.
- [ ] **Voice wake (companion app)** — Hold-to-talk in Android companion. Push audio to `/api/chat/voice`. STT via Whisper API.
- [ ] **Talk mode** — Continuous mic in companion app. Streams audio, plays TTS response back.

### Phase 4 — Polish (ongoing)
- [ ] **Cost dashboard** — `/usage` page with charts by day/model/channel.
- [ ] **Beta branch** — Maintain `main` (stable) and `dev` (bleeding edge). Tag releases.
- [ ] **Matrix channel** — Add Matrix as a channel via matrix-nio.
- [ ] **More pre-built skills** — `install_skill` from a curated list in README (like ClawHub but simpler).

---

## Architecture Notes

**We should NOT do:**
- Per-session Docker sandboxing — overkill for personal use, breaks simplicity
- Cross-session agent comms — single-owner model is our strength
- Native macOS menu bar app — wrong stack, Flask dashboard is better

**We should KEEP:**
- Python-first, single process, `.env` config — easy to self-host anywhere
- `create_skill` dynamic extension — more flexible than a registry
- SQLite for everything — no infrastructure dependencies
- Owner-only model by default — simpler and more secure for personal use

---

*Last updated: 2026-04-07. Based on comparison with [openclaw/openclaw](https://github.com/openclaw/openclaw).*
