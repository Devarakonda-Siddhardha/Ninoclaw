"""
Wikipedia skill — uses the free Wikipedia REST API, no key needed
"""
import requests

SKILL_INFO = {
    "name": "wikipedia",
    "description": "Search and summarize any Wikipedia article",
    "version": "1.0",
    "icon": "📖",
    "author": "ninoclaw",
    "requires_key": False,
}

TOOLS = [{
    "type": "function",
    "function": {
        "name": "wikipedia_search",
        "description": "Search Wikipedia and get a concise summary of the topic",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Topic or person to look up"}
            },
            "required": ["query"]
        }
    }
}]

def execute(tool_name, arguments):
    if tool_name != "wikipedia_search":
        return None
    query = arguments.get("query", "").strip()
    try:
        # Search for best match
        search = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={"action": "query", "list": "search", "srsearch": query,
                    "srlimit": 1, "format": "json"},
            timeout=10
        ).json()
        results = search.get("query", {}).get("search", [])
        if not results:
            return f"❌ No Wikipedia results for: {query}"
        title = results[0]["title"]

        # Get summary
        data = requests.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{title.replace(' ', '_')}",
            timeout=10
        ).json()
        extract = data.get("extract", "No summary available.")
        url = data.get("content_urls", {}).get("desktop", {}).get("page", "")
        if len(extract) > 1200:
            extract = extract[:1200] + "…"
        return f"📖 **{title}**\n\n{extract}\n\n🔗 {url}"
    except Exception as e:
        return f"❌ Wikipedia error: {e}"
