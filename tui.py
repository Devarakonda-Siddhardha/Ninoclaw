"""Terminal UI for local Ninoclaw sessions."""

from __future__ import annotations

import threading
import textwrap
from datetime import datetime

from config import AGENT_NAME
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Footer, Header, Input, RichLog, Static


class NinoclawTUI(App):
    CSS = """
    Screen {
        background: #0b1020;
        color: #e5eef8;
    }

    #status {
        height: 3;
        padding: 0 1;
        background: #131c32;
        color: #9db4d0;
        border: round #283655;
        margin: 0 1 1 1;
    }

    #chatlog {
        background: #0f172a;
        border: round #283655;
        margin: 0 1 1 1;
        padding: 0 1;
    }

    #prompt {
        margin: 0 1 1 1;
    }
    """

    BINDINGS = [
        ("ctrl+l", "clear_log", "Clear"),
        ("ctrl+c", "quit", "Quit"),
    ]

    def __init__(self, user_id: str) -> None:
        super().__init__()
        self.user_id = user_id
        self.busy = False
        self._spinner_index = 0
        self._spinner_timer = None
        self._pending_marker = ""

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical():
            yield Static("", id="status")
            yield RichLog(id="chatlog", wrap=True, markup=False, highlight=False)
            yield Input(placeholder="Type a message and press Enter...", id="prompt")
        yield Footer()

    def on_mount(self) -> None:
        self._set_status("Ready. Telegram and dashboard stay live while you chat here.")
        self._log("system", f"{AGENT_NAME} terminal UI is ready.")
        self._log("system", "Shortcuts: Ctrl+L clear, Ctrl+C quit.")
        self.query_one(Input).focus()

    def action_clear_log(self) -> None:
        self.query_one(RichLog).clear()
        self._set_status("Transcript cleared.")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        message = event.value.strip()
        event.input.value = ""
        if not message:
            return
        if self.busy:
            self._set_status("Busy. Wait for the current reply to finish.")
            return

        self.busy = True
        event.input.disabled = True
        self._log("you", message)
        self._pending_marker = f"pending-{datetime.now().timestamp()}"
        self._log("system", f"[{self._pending_marker}] {AGENT_NAME} is thinking...")
        self._start_spinner()

        worker = threading.Thread(target=self._generate_reply, args=(message,), daemon=True)
        worker.start()

    def _generate_reply(self, message: str) -> None:
        from chat_runtime import generate_reply_sync

        try:
            reply = generate_reply_sync(self.user_id, message)
        except Exception as exc:
            self.call_from_thread(self._finish_reply, f"Error: {exc}", True)
            return
        self.call_from_thread(self._finish_reply, reply or "No response.", False)

    def _finish_reply(self, reply: str, failed: bool) -> None:
        self._stop_spinner()
        self._remove_pending_line()
        self._log("error" if failed else AGENT_NAME, reply)
        self.busy = False
        prompt = self.query_one(Input)
        prompt.disabled = False
        prompt.focus()
        self._set_status("Ready." if not failed else "Last request failed.")

    def _set_status(self, message: str) -> None:
        status = self.query_one("#status", Static)
        now = datetime.now().strftime("%H:%M:%S")
        status.update(f"[{now}] {message}")

    def _log(self, speaker: str, text: str) -> None:
        timestamp = datetime.now().strftime("%H:%M")
        wrapped = []
        for line in str(text).splitlines() or [""]:
            wrapped.append(textwrap.fill(line, width=100, replace_whitespace=False))
        body = "\n".join(wrapped)
        self.query_one(RichLog).write(f"[{timestamp}] {speaker}> {body}")

    def _start_spinner(self) -> None:
        self._spinner_index = 0
        self._tick_spinner()

    def _tick_spinner(self) -> None:
        if not self.busy:
            return
        frames = ["-", "\\", "|", "/"]
        frame = frames[self._spinner_index % len(frames)]
        self._spinner_index += 1
        self._set_status(f"{frame} Thinking...")
        self._spinner_timer = self.set_timer(0.2, self._tick_spinner)

    def _stop_spinner(self) -> None:
        if self._spinner_timer is not None:
            self._spinner_timer.stop()
            self._spinner_timer = None

    def _remove_pending_line(self) -> None:
        if not self._pending_marker:
            return
        log = self.query_one(RichLog)
        lines = [line for line in log.lines if self._pending_marker not in str(line)]
        log.clear()
        for line in lines:
            log.write(line)
        self._pending_marker = ""


def run_tui(user_id: str) -> None:
    NinoclawTUI(user_id).run()
