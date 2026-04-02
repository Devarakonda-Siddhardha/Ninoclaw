"""
WhatsApp webhook channel integration for Ninoclaw.
"""
import asyncio
import json
import threading
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional

from ai import chat
from memory import Memory
from run_traces import clear_current_run, finish_run, start_run
from tasks import task_manager
from tools import execute_tool, get_tool_definitions
from whatsapp_bridge import bridge_manager

memory = Memory()
_SEEN_MESSAGE_IDS = deque(maxlen=200)
_SEEN_LOCK = threading.Lock()


def _runtime_cfg():
    from config import (
        AGENT_NAME,
        BOT_PURPOSE,
        SYSTEM_PROMPT,
        WHATSAPP_ALLOWED_SENDERS,
        WHATSAPP_WEBHOOK_HOST,
        WHATSAPP_WEBHOOK_PORT,
        WHATSAPP_WEBHOOK_PATH,
        WHATSAPP_WEBHOOK_SECRET,
    )
    return {
        "system_prompt": SYSTEM_PROMPT,
        "agent_name": AGENT_NAME,
        "bot_purpose": BOT_PURPOSE,
        "allowed_senders": WHATSAPP_ALLOWED_SENDERS,
        "webhook_host": WHATSAPP_WEBHOOK_HOST,
        "webhook_port": WHATSAPP_WEBHOOK_PORT,
        "webhook_path": WHATSAPP_WEBHOOK_PATH or "/whatsapp/webhook",
        "webhook_secret": WHATSAPP_WEBHOOK_SECRET,
    }


def _normalize_sender(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        return ""
    text = text.replace(" ", "").replace("-", "")
    if text.startswith("+"):
        text = text[1:]
    if text.endswith("@s.whatsapp.net"):
        text = text[:-15] + "@c.us"
    elif text.isdigit():
        text = text + "@c.us"
    return text


def _sender_allowed(sender: str) -> bool:
    allowed_raw = _runtime_cfg()["allowed_senders"]
    if not allowed_raw.strip():
        return True
    allowed = {_normalize_sender(item) for item in allowed_raw.split(",") if item.strip()}
    return _normalize_sender(sender) in allowed


def _extract_sender(event: Dict[str, Any]) -> str:
    payload = event.get("payload") or {}
    return _normalize_sender(
        payload.get("from")
        or payload.get("author")
        or payload.get("chatId")
        or event.get("from")
        or ""
    )


def _extract_text(event: Dict[str, Any]) -> str:
    payload = event.get("payload") or {}
    body = payload.get("body") or payload.get("text") or payload.get("caption") or ""
    if isinstance(body, dict):
        body = body.get("body") or ""
    return str(body or "").strip()


def _extract_message_id(event: Dict[str, Any]) -> str:
    payload = event.get("payload") or {}
    mid = payload.get("id") or event.get("id") or ""
    if isinstance(mid, dict):
        return str(mid.get("_serialized") or mid.get("id") or "")
    return str(mid or "")


def _is_user_message(event: Dict[str, Any]) -> bool:
    evt = str(event.get("event") or event.get("eventType") or "").strip().lower()
    if evt and evt != "message":
        return False
    payload = event.get("payload") or {}
    if payload.get("fromMe"):
        return False
    body = _extract_text(event)
    sender = _extract_sender(event)
    return bool(body and sender)


def _remember_message(mid: str) -> bool:
    if not mid:
        return True
    with _SEEN_LOCK:
        if mid in _SEEN_MESSAGE_IDS:
            return False
        _SEEN_MESSAGE_IDS.append(mid)
        return True


async def _handle_tool_calls(tool_calls, user_id: str) -> str:
    tool_results = []
    for tc in tool_calls or []:
        tool_name = tc.get("function", {}).get("name")
        raw_args = tc.get("function", {}).get("arguments", "{}")
        if isinstance(raw_args, str):
            try:
                tool_args = json.loads(raw_args)
            except Exception:
                tool_args = {}
        else:
            tool_args = raw_args or {}
        if tool_name:
            result = await execute_tool(tool_name, tool_args, user_id, task_manager)
            if result:
                tool_results.append(str(result))
    return "\n\n".join(tool_results)


async def handle_incoming_event(event: Dict[str, Any]) -> Dict[str, Any]:
    if not _is_user_message(event):
        return {"ok": False, "message": "Ignored non-user WhatsApp event."}

    sender = _extract_sender(event)
    text = _extract_text(event)
    message_id = _extract_message_id(event)

    if not _remember_message(message_id):
        return {"ok": True, "message": "Ignored duplicate WhatsApp message."}
    if not _sender_allowed(sender):
        return {"ok": False, "message": f"Blocked WhatsApp sender: {sender}"}

    cfg = _runtime_cfg()
    user_id = f"whatsapp_{sender.replace('@c.us', '').replace('@s.whatsapp.net', '')}"
    run_id = start_run(user_id, "whatsapp", text)

    try:
        conv_history = memory.get_conversation_context(user_id)
        memory.add_message(user_id, "user", text)

        system_prompt = (
            f"{cfg['system_prompt']}\n\n"
            f"Your name is {cfg['agent_name']}. "
            f"You are talking to WhatsApp user {sender}. "
            f"Your purpose is to {cfg['bot_purpose']}."
        )

        response = chat(
            message=text,
            system_prompt=system_prompt,
            history=conv_history,
            tools=get_tool_definitions(user_id),
        )

        final_response = response if isinstance(response, str) else response.get("content") or ""
        tool_calls = response.get("tool_calls") if isinstance(response, dict) else None
        if tool_calls:
            tool_text = await _handle_tool_calls(tool_calls, user_id)
            if tool_text:
                final_response = (final_response + "\n\n" + tool_text).strip() if final_response else tool_text

        final_response = (final_response or "Done.").strip()
        memory.add_message(user_id, "assistant", final_response)

        send_result = bridge_manager.send_text(sender, final_response)
        if not send_result.get("ok"):
            finish_run(final_response=final_response, status="failed", error=send_result.get("message"), run_id=run_id)
            return {"ok": False, "message": send_result.get("message"), "reply": final_response}

        finish_run(final_response=final_response, status="completed", run_id=run_id)
        return {"ok": True, "message": "WhatsApp message handled.", "reply": final_response}
    except Exception as exc:
        finish_run(status="failed", error=str(exc), run_id=run_id)
        return {"ok": False, "message": f"WhatsApp handler failed: {exc}"}
    finally:
        clear_current_run()


def handle_event_sync(event: Dict[str, Any]) -> Dict[str, Any]:
    return asyncio.run(handle_incoming_event(event))


def _secret_ok(handler: BaseHTTPRequestHandler) -> bool:
    expected = _runtime_cfg()["webhook_secret"]
    if not expected:
        return True
    actual = handler.headers.get("X-Ninoclaw-Secret", "")
    return actual == expected


class _WebhookHandler(BaseHTTPRequestHandler):
    server_version = "NinoclawWhatsApp/0.1"

    def do_POST(self):
        cfg = _runtime_cfg()
        if self.path != cfg["webhook_path"]:
            self.send_response(404)
            self.end_headers()
            return

        if not _secret_ok(self):
            self.send_response(403)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            self.send_response(400)
            self.end_headers()
            return

        try:
            handle_event_sync(payload if isinstance(payload, dict) else {})
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
        except Exception:
            self.send_response(500)
            self.end_headers()

    def log_message(self, format, *args):
        return


def run_bot() -> threading.Thread:
    cfg = _runtime_cfg()
    server = ThreadingHTTPServer((cfg["webhook_host"], int(cfg["webhook_port"])), _WebhookHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True, name="whatsapp-webhook")
    thread.start()
    return thread
