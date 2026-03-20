"""
Personal Interests skill — manage preferences and get personalized news.
Learn user's interests over time: sports players, celebrities, topics, etc.
"""
import json
from memory import memory

SKILL_INFO = {
    "name": "personal_interests",
    "description": "Manage personal interests, preferences, and get personalized news/research",
    "version": "1.0",
    "icon": "❤️",
    "author": "ninoclaw",
    "requires_key": False,
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "set_interests",
            "description": "Set or update user's personal interests. Use this when user says things like 'I love cricket', 'I'm a fan of Virat Kohli', 'I like sci-fi movies', 'My favorite actor is Tom Hanks', etc. Save their preferences for future personalization.",
            "parameters": {
                "type": "object",
                "properties": {
                    "interests": {
                        "type": "string",
                        "description": "Comma-separated list of interests, e.g., 'cricket, Virat Kohli, sci-fi movies, Tom Hanks, AI tools, Bollywood'"
                    },
                    "categories": {
                        "type": "string",
                        "description": "Optional categories as JSON object, e.g., '{\"sports\": [\"cricket\"], \"players\": [\"Virat Kohli\"], \"movies\": [\"sci-fi\"], \"actors\": [\"Tom Hanks\"], \"topics\": [\"AI\"]}'"
                    }
                },
                "required": ["interests"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_interests",
            "description": "Get the user's saved personal interests and preferences. Use this when user asks 'what do you know about me', 'my interests', 'what are my favorites', etc.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_personalized_news",
            "description": "Search for news based on user's personal interests. This will fetch news relevant to their favorite sports players, celebrities, topics, etc. Use this when user asks 'news about cricket', 'Virat Kohli news', 'Bollywood news', or wants personalized updates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Optional specific topic to search for. If not provided, will search based on user's saved interests."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_interest",
            "description": "Add a single interest to user's preferences. Use this when user mentions something they like, e.g., 'I love cricket', 'I'm a fan of Virat Kohli', 'I like sci-fi movies'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "interest": {
                        "type": "string",
                        "description": "The interest to add, e.g., 'cricket', 'Virat Kohli', 'sci-fi movies', 'Bollywood movies'"
                    }
                },
                "required": ["interest"]
            }
        }
    },
]

def _get_user_interests(user_id):
    """Get user's interests from memory."""
    try:
        data = memory.get_user_data(user_id)
        interests = data.get("interests", [])
        categories = data.get("interest_categories", {})
        return interests, categories
    except Exception:
        return [], {}

def _set_user_interests(user_id, interests, categories=None):
    """Set user's interests in memory."""
    try:
        memory.set_user_data(user_id, "interests", interests)
        if categories:
            memory.set_user_data(user_id, "interest_categories", categories)
        return True
    except Exception:
        return False

def _search_topic(topic):
    """Search for news on a specific topic using web search."""
    try:
        import requests
        from config import SERPER_API_KEY

        if not SERPER_API_KEY:
            return "❌ Search API key not configured. Please set SERPER_API_KEY in .env"

        url = "https://google.serper.dev/news"
        headers = {
            "X-API-KEY": SERPER_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {"q": topic, "num": 5}
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data.get("news"):
            return f"🔍 No recent news found for: {topic}"

        lines = [f"📰 **News for: {topic}**\n"]
        for item in data["news"][:5]:
            title = item.get("title", "")
            link = item.get("link", "")
            snippet = item.get("snippet", "")
            date = item.get("date", "")
            lines.append(f"• **{title}**")
            if date:
                lines.append(f"  📅 {date}")
            if snippet:
                lines.append(f"  {snippet[:150]}...")
            if link:
                lines.append(f"  🔗 {link}")
            lines.append("")

        return "\n".join(lines)
    except Exception as e:
        return f"❌ Search error: {e}"

def execute(tool_name, arguments, user_id=None):
    # Default user_id to config OWNER_ID if not provided
    if not user_id:
        from config import OWNER_ID
        user_id = str(OWNER_ID)

    try:
        if tool_name == "set_interests":
            interests_str = arguments.get("interests", "")
            categories_str = arguments.get("categories", "{}")

            # Parse interests
            interests = [i.strip() for i in interests_str.split(",") if i.strip()]

            # Parse categories if provided
            try:
                categories = json.loads(categories_str) if categories_str else {}
            except json.JSONDecodeError:
                categories = {}

            # Get existing interests and merge
            existing_interests, existing_categories = _get_user_interests(user_id)
            combined_interests = list(set(existing_interests + interests))
            combined_categories = {**existing_categories, **categories}

            if _set_user_interests(user_id, combined_interests, combined_categories):
                return f"✅ **Preferences saved!**\n\nYour interests: {', '.join(combined_interests)}\n\nI'll remember these and find personalized content for you."
            return "❌ Failed to save interests."

        elif tool_name == "get_interests":
            interests, categories = _get_user_interests(user_id)

            if not interests and not categories:
                return "📝 No interests saved yet. Tell me what you like - sports, celebrities, topics, etc!"

            lines = [f"❤️ **Your Interests:**\n"]
            if interests:
                lines.append(f"**General:** {', '.join(interests)}")

            if categories:
                lines.append("\n**Categories:**")
                for category, items in categories.items():
                    if items:
                        lines.append(f"• {category}: {', '.join(items) if isinstance(items, list) else items}")

            return "\n".join(lines)

        elif tool_name == "search_personalized_news":
            topic = arguments.get("topic", "").strip()

            # If no topic provided, search based on user's interests
            if not topic:
                interests, categories = _get_user_interests(user_id)

                if not interests and not categories:
                    return "📝 No interests saved yet. Tell me what you like first, or provide a topic to search!"

                # Build search query from interests
                search_terms = interests[:3]  # Limit to top 3 interests
                if not search_terms:
                    # Fallback to categories
                    all_items = []
                    for items in categories.values():
                        if isinstance(items, list):
                            all_items.extend(items)
                    search_terms = all_items[:3]

                if not search_terms:
                    return "❌ No interests to search for. Set some interests first!"

                # Search for each term and combine results
                results = []
                for term in search_terms:
                    result = _search_topic(term)
                    results.append(result)

                return "\n\n---\n\n".join(results)
            else:
                # Search for specific topic
                return _search_topic(topic)

        elif tool_name == "add_interest":
            interest = arguments.get("interest", "").strip()
            if not interest:
                return "❌ Please provide an interest to add."

            existing_interests, existing_categories = _get_user_interests(user_id)
            if interest not in existing_interests:
                existing_interests.append(interest)
                if _set_user_interests(user_id, existing_interests, existing_categories):
                    return f"✅ Added '{interest}' to your interests!\n\nYour interests: {', '.join(existing_interests)}"
            else:
                return f"✅ '{interest}' is already in your interests."

    except Exception as e:
        return f"❌ Personal interests error: {e}"

    return None
