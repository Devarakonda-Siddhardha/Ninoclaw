"""
Autonomous Job Searcher — automatically searches for jobs based on user preferences and sends alerts.
Works like an AI job agent that hunts for opportunities 24/7.
"""
from datetime import datetime, timedelta
from memory import memory
from config import OWNER_ID, AGENT_NAME

class AutonomousJobSearcher:
    def __init__(self, bot):
        self.bot = bot
        self.last_search_time = None
        self.search_interval_hours = 24  # Default: daily job search
        self.enabled = True  # Can be toggled on/off

    async def check_and_search(self):
        """Check if it's time for autonomous job search and execute if needed."""
        if not self.enabled:
            return  # Skip if disabled
        if self._should_search():
            await self._do_autonomous_job_search()

    def _should_search(self):
        """Determine if it's time to run autonomous job search."""
        if not self.last_search_time:
            return True

        time_since_last = datetime.now() - self.last_search_time
        return time_since_last >= timedelta(hours=self.search_interval_hours)

    async def _do_autonomous_job_search(self):
        """Perform autonomous job search based on user preferences."""
        user_id = str(OWNER_ID)

        try:
            # Get user job preferences
            prefs = self._get_user_job_prefs(user_id)

            if not prefs or not prefs.get("auto_search_enabled", False):
                print("🔍 Auto job search disabled or no preferences set")
                return

            # Extract search criteria
            query = prefs.get("skills", "")
            location = prefs.get("location", "")
            remote = "remote" in str(location).lower()

            if not query:
                print("🔍 No job search criteria (skills) set for autonomous search")
                return

            print(f"🔍 Starting autonomous job search for user {user_id}")
            self.last_search_time = datetime.now()

            # Search for jobs
            results = await self._search_jobs_with_tools(query, location, remote)

            if results:
                # Send job alert to user
                await self._send_job_alert(user_id, results, query, location)
            else:
                print("🔍 No new jobs found in autonomous search")

        except Exception as e:
            print(f"❌ Error in autonomous job search: {e}")

    def _get_user_job_prefs(self, user_id):
        """Get user's job preferences from memory."""
        try:
            data = memory.get_user_data(user_id)
            return data.get("job_preferences", {})
        except Exception:
            return {}

    async def _search_jobs_with_tools(self, query, location, remote=False):
        """Search for jobs using job_search skill tools."""
        try:
            from skills.job_search import execute as job_execute

            # Call the search_jobs tool
            result = job_execute(
                "search_jobs",
                {"query": query, "location": location, "remote": remote},
                user_id=OWNER_ID
            )

            if result and not result.startswith("❌"):
                return {
                    "query": query,
                    "location": location,
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                }
            return None

        except Exception as e:
            print(f"❌ Error searching jobs: {e}")
            return None

    async def _send_job_alert(self, user_id, results, query, location):
        """Send job search alert to user."""
        try:
            # Format job alert
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            location_text = f" in {location}" if location else " (remote/location flexible)"

            message = f"🤖 **{AGENT_NAME} Auto Job Search Alert**\n"
            message += f"📅 {timestamp}\n\n"
            message += f"🔍 Found jobs matching your preferences{location_text}!\n\n"
            message += f"💼 **Search Query:** {query}\n\n"
            message += results["result"]
            message += "\n\n"
            message += f"💡 These matches are based on your saved job preferences. "
            message += f"Use 'my job preferences' to update, "
            message += f"'find me jobs' for new search, "
            message += f"'disable auto job search' to pause alerts."

            # Send to user
            try:
                await self.bot.send_message(chat_id=int(user_id), text=message, parse_mode="Markdown")
                print(f"📤 Sent job search alert to user {user_id}")
            except Exception as e:
                print(f"❌ Error sending job alert: {e}")

        except Exception as e:
            print(f"❌ Error formatting job alert: {e}")

    def set_search_interval(self, hours):
        """Set how often to run autonomous job search (in hours)."""
        self.search_interval_hours = hours
        print(f"🔍 Job search interval set to {hours} hours")

# Global instance (will be initialized when bot starts)
_job_searcher = None

def get_job_searcher():
    """Get autonomous job searcher instance."""
    return _job_searcher

def init_job_searcher(bot):
    """Initialize autonomous job searcher with bot instance."""
    global _job_searcher
    _job_searcher = AutonomousJobSearcher(bot)
    return _job_searcher
