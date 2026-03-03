"""
Twilio Voice Call Skill
Calls the owner's phone and speaks a message using Twilio TTS.

Setup — add to .env:
  TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  TWILIO_AUTH_TOKEN=your_auth_token
  TWILIO_FROM=+1415xxxxxxx   (your Twilio number)
  OWNER_PHONE=+91xxxxxxxxxx  (your real number)

Install: pip install twilio
"""

SKILL_INFO = {
    "name":        "twilio_call",
    "version":     "1.0.0",
    "description": "Call the owner's phone via Twilio and speak a message aloud.",
    "author":      "Ninoclaw",
    "requires":    ["twilio"],
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "voice_call",
            "description": (
                "Call the owner's phone via Twilio and speak a message aloud. "
                "Use for urgent alerts or when user says 'call me', 'phone me', "
                "'call and say', 'send a voice note'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The message to speak on the call"
                    }
                },
                "required": ["message"]
            }
        }
    }
]


def execute(tool_name: str, arguments: dict) -> str:
    if tool_name != "voice_call":
        return None

    import os
    message = arguments.get("message", "").strip()
    if not message:
        return "❌ Message is required."

    sid      = os.getenv("TWILIO_ACCOUNT_SID", "")
    token    = os.getenv("TWILIO_AUTH_TOKEN", "")
    from_num = os.getenv("TWILIO_FROM", "")
    to_num   = os.getenv("OWNER_PHONE", "")

    if not all([sid, token, from_num, to_num]):
        return (
            "❌ Twilio not configured. Add to .env:\n"
            "  TWILIO_ACCOUNT_SID=ACxxx...\n"
            "  TWILIO_AUTH_TOKEN=xxx...\n"
            "  TWILIO_FROM=+1415xxxxxxx\n"
            "  OWNER_PHONE=+91xxxxxxxxxx\n\n"
            "Then load this skill: install_skill skills/twilio_call.py"
        )

    try:
        from twilio.rest import Client
    except ImportError:
        return "❌ twilio not installed. Run: pip install twilio"

    try:
        client = Client(sid, token)
        twiml = f'<Response><Say voice="alice">{message}</Say></Response>'
        call = client.calls.create(twiml=twiml, to=to_num, from_=from_num)
        return f"📞 Calling {to_num}...\nMessage: _{message}_\nCall SID: `{call.sid}`"
    except Exception as e:
        return f"❌ Twilio call failed: {e}"
