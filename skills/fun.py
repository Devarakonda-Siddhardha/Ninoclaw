"""
Fun Facts & Jokes skill — lighten the mood with random facts and jokes.
No API keys needed. Uses free public APIs.
"""
import requests

SKILL_INFO = {
    "name": "fun",
    "description": "Get random fun facts, jokes, and riddles",
    "version": "1.0",
    "icon": "😂",
    "author": "ninoclaw",
    "requires_key": False,
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "tell_joke",
            "description": "Tell a random joke. Use when user says 'tell me a joke', 'make me laugh', 'joke', etc.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fun_fact",
            "description": "Share a random fun fact. Use when user says 'tell me a fact', 'fun fact', 'did you know', etc.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


def _tell_joke():
    try:
        r = requests.get("https://official-joke-api.appspot.com/random_joke", timeout=5)
        r.raise_for_status()
        data = r.json()
        setup = data.get("setup", "")
        punchline = data.get("punchline", "")
        return f"😂 {setup}\n\n👉 {punchline}"
    except Exception:
        # Fallback jokes
        import random
        jokes = [
            ("Why do programmers prefer dark mode?", "Because light attracts bugs! 🐛"),
            ("Why did the AI break up with the internet?", "Too many bad connections! 📡"),
            ("What's a robot's favorite type of music?", "Heavy metal! 🤖🎸"),
        ]
        setup, punch = random.choice(jokes)
        return f"😂 {setup}\n\n👉 {punch}"


def _fun_fact():
    try:
        r = requests.get("https://uselessfacts.jsph.pl/api/v2/facts/random?language=en", timeout=5)
        r.raise_for_status()
        data = r.json()
        return f"🤯 **Did you know?**\n\n{data.get('text', 'No fact found.')}"
    except Exception:
        import random
        facts = [
            "A group of flamingos is called a 'flamboyance'. 🦩",
            "Honey never spoils. Archaeologists found 3000-year-old honey in Egyptian tombs! 🍯",
            "Octopuses have three hearts and blue blood. 🐙💙",
        ]
        return f"🤯 **Did you know?**\n\n{random.choice(facts)}"


def execute(tool_name, arguments):
    try:
        if tool_name == "tell_joke":
            return _tell_joke()
        elif tool_name == "fun_fact":
            return _fun_fact()
    except Exception as e:
        return f"❌ Fun error: {e}"
    return None
