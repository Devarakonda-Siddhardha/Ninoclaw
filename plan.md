# Ninoclaw Future Roadmap: Plan.md

This document outlines the design and implementation strategy for the remaining 3 "Phase 2" enhancements for the Ninoclaw pure agent.

---

## 3. "Human-in-the-Loop" for Destructive Skills
**Goal:** Pause execution on risky actions and wait for Telegram button approval.

### Implementation Logic:
- **Flagging:** Add `requires_confirmation = True` to `SKILL_INFO` for skills like `run_command`, `expo_delete_app`, or `create_integration`.
- **Interception:** Modify `tools.py` to check this flag. If `True`, return a special JSON payload or signal.
- **Bot Response:** In `telegram_bot.py`, catch this signal and send an `InlineKeyboardMarkup` with `[Confirm]` and `[Cancel]` buttons.
- **State Management:** Temporarily store the pending tool call in `ninoclaw.db` or a dictionary.
- **Callback:** On button click, either execute the stored tool call or discard it.

---

## 4. Local Tool Sandboxing
**Goal:** Isolate `npx` and shell executions from the core engine files.

### Implementation Logic:
- **Sandbox Wrapper:** Create `security.py` utilities to spawn processes with limited environment variables.
- **Directory Isolation:** Force all `expo_builder` and `web_builder` work into a strictly controlled `builds/` directory relative to the user's home, never the Ninoclaw root.
- **Permission Limiting (Optional):** If on Linux, attempt to use `setuid/setgid` or simple `chroot` for execution if permissions allow.

---

## 5. Token & Cost Circuit Breakers
**Goal:** Prevent runaway API costs.

### Implementation Logic:
- **DB Table:** Create `usage_metrics` in `ninoclaw.db` to track daily token counts and estimated USD cost.
- **Middleware:** In `ai.py`, after every successful `chat()` completion, calculate cost based on model-specific rates and update the DB.
- **Governor:** Add a check at the start of `ai.chat()`. If `current_daily_cost > MAX_DAILY_BUDGET`, raise a `BudgetExceeded` error or force `fallback_to_ollama = True`.

---

## Status Update
- **[DONE]** Feature 1: Automated Self-Healing (Global skill protection).
- **[DONE]** Feature 2: Nightly Memory Compression (Summarization cron job).
