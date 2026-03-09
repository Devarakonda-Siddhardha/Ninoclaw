"""
Autonomous Researcher — learns user preferences and automatically sends personalized news/research updates.
"""
import asyncio
from datetime import datetime, timedelta
from memory import memory
from config import OWNER_ID, AGENT_NAME

class AutonomousResearcher:
    def __init__(self, bot):
        self.bot = bot
        self.last_research_time = None
        self.research_interval_hours = 24  # Default: daily research
        self.enabled = True  # Can be toggled on/off

    async def check_and_research(self):
        """Check if it's time for autonomous research and execute if needed."""
        if not self.enabled:
            return  # Skip if disabled
        if self._should_research():
            await self._do_autonomous_research()

    def _should_research(self):
        """Determine if it's time to run autonomous research."""
        if not self.last_research_time:
            return True

        time_since_last = datetime.now() - self.last_research_time
        return time_since_last >= timedelta(hours=self.research_interval_hours)

    async def _do_autonomous_research(self):
        """Perform autonomous research based on user interests."""
        user_id = str(OWNER_ID)

        try:
            # Get user interests
            interests, categories = self._get_user_interests(user_id)

            if not interests and not categories:
                print("🔍 No user interests found for autonomous research")
                return

            print(f"🔍 Starting autonomous research for user {user_id}")
            self.last_research_time = datetime.now()

            # Research each interest
            results = []
            search_terms = interests[:5]  # Limit to top 5 interests

            for term in search_terms:
                try:
                    research_result = await self._research_topic(term)
                    if research_result:
                        results.append(research_result)
                except Exception as e:
                    print(f"❌ Error researching '{term}': {e}")

            if results:
                # Send consolidated update to user
                await self._send_research_update(user_id, results)
            else:
                print("🔍 No new research results found")

        except Exception as e:
            print(f"❌ Error in autonomous research: {e}")

    def _get_user_interests(self, user_id):
        """Get user's interests from memory."""
        try:
            data = memory.get_user_data(user_id)
            interests = data.get("interests", [])
            categories = data.get("interest_categories", {})
            return interests, categories
        except Exception:
            return [], {}

    async def _research_topic(self, topic):
        """Research a specific topic using available skills."""
        try:
            from skills.personal_interests import execute as interests_execute
            result = interests_execute("search_personalized_news", {"topic": topic}, user_id=OWNER_ID)

            if result and not result.startswith("❌") and not result.startswith("🔍 No recent news"):
                return {
                    "topic": topic,
                    "content": result,
                    "timestamp": datetime.now().isoformat()
                }
            return None

        except Exception as e:
            print(f"❌ Error researching topic '{topic}': {e}")
            return None

    async def _send_research_update(self, user_id, results):
        """Send research results to user."""
        try:
            # Format the research update
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            message = f"🤖 **{AGENT_NAME} Auto-Research Update**\n"
            message += f"📅 {timestamp}\n\n"
            message += f"🔍 Found {len(results)} updates based on your interests:\n\n"

            for i, result in enumerate(results, 1):
                message += f"**{i}. {result['topic'].upper()}**\n"
                message += result['content']
                message += "\n\n---\n\n"

            message += f"💡 These are based on your saved interests. "
            message += f"Use 'my interests' to see all saved topics, "
            message += f"or 'news about [topic]' for specific searches."

            # Send to user
            try:
                await self.bot.send_message(chat_id=int(user_id), text=message, parse_mode="Markdown")
                print(f"📤 Sent autonomous research update to user {user_id}")
            except Exception as e:
                print(f"❌ Error sending research update: {e}")

        except Exception as e:
            print(f"❌ Error formatting research update: {e}")

    def set_research_interval(self, hours):
        """Set how often to run autonomous research (in hours)."""
        self.research_interval_hours = hours
        print(f"🔍 Research interval set to {hours} hours")

# Global instance (will be initialized when bot starts)
_researcher = None

def get_researcher():
    """Get the autonomous researcher instance."""
    return _researcher

def init_researcher(bot):
    """Initialize the autonomous researcher with bot instance."""
    global _researcher
    _researcher = AutonomousResearcher(bot)
    return _researcher
