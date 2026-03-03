"""
News skill — latest headlines via BBC RSS (no API key needed)
"""
import requests
from xml.etree import ElementTree as ET

SKILL_INFO = {
    "name": "news",
    "description": "Get latest news headlines from BBC by topic",
    "version": "1.0",
    "icon": "📰",
    "author": "ninoclaw",
    "requires_key": False,
}

TOOLS = [{
    "type": "function",
    "function": {
        "name": "get_news",
        "description": "Get latest news headlines. Optionally filter by topic: world, technology, science, health, business, sports",
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "News topic. Leave empty for top headlines.",
                    "enum": ["", "world", "technology", "science", "health", "business", "sports"]
                }
            },
            "required": []
        }
    }
}]

_FEEDS = {
    "":           "https://feeds.bbci.co.uk/news/rss.xml",
    "world":      "https://feeds.bbci.co.uk/news/world/rss.xml",
    "technology": "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "science":    "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
    "health":     "https://feeds.bbci.co.uk/news/health/rss.xml",
    "business":   "https://feeds.bbci.co.uk/news/business/rss.xml",
    "sports":     "https://feeds.bbci.co.uk/news/sport/rss.xml",
}

def execute(tool_name, arguments):
    if tool_name != "get_news":
        return None
    topic = arguments.get("topic", "").lower().strip()
    url = _FEEDS.get(topic, _FEEDS[""])
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Ninoclaw/1.0"})
        root = ET.fromstring(resp.content)
        items = root.findall(".//item")[:6]
        lines = []
        for item in items:
            title = item.findtext("title", "").strip()
            desc  = item.findtext("description", "").strip()
            if len(desc) > 120:
                desc = desc[:120] + "…"
            lines.append(f"• **{title}**\n  {desc}")
        label = topic.title() if topic else "Top"
        return f"📰 **{label} Headlines** (BBC)\n\n" + "\n\n".join(lines)
    except Exception as e:
        return f"❌ News error: {e}"
