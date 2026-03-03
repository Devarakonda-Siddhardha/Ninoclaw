"""
Resend Email Skill
Send emails via Resend (https://resend.com) — free tier: 100 emails/day.

Setup — add to .env:
  RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxx
  RESEND_FROM=you@yourdomain.com   (verified sender in Resend dashboard)
  OWNER_EMAIL=you@gmail.com        (your inbox — default recipient)

Install: pip install resend
"""

SKILL_INFO = {
    "name":        "resend_email",
    "version":     "1.0.0",
    "description": "Send emails via Resend. Supports plain text and HTML.",
    "author":      "Ninoclaw",
    "requires":    ["resend"],
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": (
                "Send an email via Resend. Use when user says 'email me', "
                "'send me a mail', 'mail this summary', 'send report to my email', etc. "
                "Defaults to owner's email if no recipient given."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "subject": {
                        "type": "string",
                        "description": "Email subject line"
                    },
                    "body": {
                        "type": "string",
                        "description": "Email body — plain text or HTML"
                    },
                    "to": {
                        "type": "string",
                        "description": "Recipient email address. Defaults to OWNER_EMAIL if omitted."
                    },
                    "html": {
                        "type": "boolean",
                        "description": "If true, body is treated as HTML. Default false."
                    }
                },
                "required": ["subject", "body"]
            }
        }
    }
]


def execute(tool_name: str, arguments: dict) -> str:
    if tool_name != "send_email":
        return None

    import os
    api_key    = os.getenv("RESEND_API_KEY", "")
    from_addr  = os.getenv("RESEND_FROM", "")
    owner_mail = os.getenv("OWNER_EMAIL", "")

    if not api_key or not from_addr:
        return (
            "❌ Resend not configured. Add to .env:\n"
            "  RESEND_API_KEY=re_xxxx...\n"
            "  RESEND_FROM=you@yourdomain.com\n"
            "  OWNER_EMAIL=you@gmail.com\n\n"
            "Get a free API key at https://resend.com"
        )

    subject = arguments.get("subject", "").strip()
    body    = arguments.get("body", "").strip()
    to      = arguments.get("to", "").strip() or owner_mail
    is_html = arguments.get("html", False)

    if not subject or not body:
        return "❌ subject and body are required."
    if not to:
        return "❌ No recipient — set OWNER_EMAIL in .env or provide 'to'."

    try:
        import resend
    except ImportError:
        return "❌ resend not installed. Run: pip install resend"

    try:
        resend.api_key = api_key
        params = {
            "from":    from_addr,
            "to":      [to],
            "subject": subject,
        }
        if is_html:
            params["html"] = body
        else:
            params["text"] = body

        email = resend.Emails.send(params)
        return f"📧 Email sent!\nTo: {to}\nSubject: {subject}\nID: `{email['id']}`"
    except Exception as e:
        return f"❌ Failed to send email: {e}"
