import os
import requests

SKILL_INFO = {
    "name": "slack",
    "description": "Send messages to Slack",
    "icon": "💬",
    "version": "1.0",
    "requires_key": True,
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "slack_send",
            "description": "Send a message to a Slack channel or webhook",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The message text to send",
                    },
                    "channel": {
                        "type": "string",
                        "description": "Slack channel to send to (e.g. #general). Defaults to configured default channel.",
                    },
                },
                "required": ["message"],
            },
        },
    }
]


def execute(tool_name: str, arguments: dict) -> str:
    if tool_name != "slack_send":
        return f"Unknown tool: {tool_name}"

    message = arguments.get("message", "")
    channel = arguments.get("channel")

    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    bot_token = os.getenv("SLACK_BOT_TOKEN")
    default_channel = os.getenv("SLACK_CHANNEL")

    if webhook_url:
        try:
            resp = requests.post(webhook_url, json={"text": message}, timeout=10)
            resp.raise_for_status()
            return f"Message sent to Slack via webhook."
        except requests.RequestException as e:
            return f"Slack webhook error: {e}"

    if bot_token:
        target_channel = channel or default_channel
        if not target_channel:
            return (
                "No channel specified and SLACK_CHANNEL env var not set. "
                "Provide a channel argument or set SLACK_CHANNEL."
            )
        try:
            resp = requests.post(
                "https://slack.com/api/chat.postMessage",
                headers={"Authorization": f"Bearer {bot_token}"},
                json={"channel": target_channel, "text": message},
                timeout=10,
            )
            data = resp.json()
            if data.get("ok"):
                return f"Message sent to {target_channel}."
            return f"Slack API error: {data.get('error', 'unknown error')}"
        except requests.RequestException as e:
            return f"Slack request error: {e}"

    return (
        "Slack is not configured. To enable, set one of:\n"
        "  SLACK_WEBHOOK_URL — an Incoming Webhook URL, or\n"
        "  SLACK_BOT_TOKEN + SLACK_CHANNEL — a Bot Token and default channel."
    )
