"""
Currency converter skill — uses frankfurter.app (free, no API key)
"""
import requests

SKILL_INFO = {
    "name": "currency",
    "description": "Convert between currencies using live exchange rates",
    "version": "1.0",
    "icon": "💱",
    "author": "ninoclaw",
    "requires_key": False,
}

TOOLS = [{
    "type": "function",
    "function": {
        "name": "convert_currency",
        "description": "Convert an amount from one currency to another using live rates. E.g. 100 USD to INR",
        "parameters": {
            "type": "object",
            "properties": {
                "amount":        {"type": "number", "description": "Amount to convert"},
                "from_currency": {"type": "string", "description": "Source currency code, e.g. USD"},
                "to_currency":   {"type": "string", "description": "Target currency code, e.g. INR"}
            },
            "required": ["amount", "from_currency", "to_currency"]
        }
    }
}]

def execute(tool_name, arguments):
    if tool_name != "convert_currency":
        return None
    amount   = float(arguments.get("amount", 1))
    from_c   = arguments.get("from_currency", "USD").upper().strip()
    to_c     = arguments.get("to_currency", "INR").upper().strip()
    try:
        resp = requests.get(
            "https://api.frankfurter.app/latest",
            params={"from": from_c, "to": to_c},
            timeout=10
        ).json()
        if "rates" not in resp:
            return f"❌ Could not get rate for {from_c} → {to_c}"
        rate = resp["rates"][to_c]
        converted = round(amount * rate, 2)
        return (f"💱 **{amount:,g} {from_c}** = **{converted:,g} {to_c}**\n"
                f"Rate: 1 {from_c} = {rate} {to_c}")
    except Exception as e:
        return f"❌ Currency error: {e}"
