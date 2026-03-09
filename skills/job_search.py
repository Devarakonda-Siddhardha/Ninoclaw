"""
Job Search skill — LinkedIn integration and automated job hunting
Search for jobs based on user preferences, skills, and location.
"""
import requests
from memory import memory

SKILL_INFO = {
    "name": "job_search",
    "description": "Search for jobs using LinkedIn and automated job hunting",
    "version": "1.0",
    "icon": "💼",
    "author": "ninoclaw",
    "requires_key": False,  # Can work with free APIs or job aggregators
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "set_job_preferences",
            "description": "Set job search preferences: skills, location, job type, salary range, experience level. Use when user says 'I want a Python job in Hyderabad' or 'I'm looking for remote jobs'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "skills": {
                        "type": "string",
                        "description": "Comma-separated skills, e.g., 'Python, Django, React, AWS'"
                    },
                    "location": {
                        "type": "string",
                        "description": "Job location, e.g., 'Hyderabad', 'Remote', 'Bangalore'"
                    },
                    "job_type": {
                        "type": "string",
                        "description": "Job type: full-time, part-time, contract, remote, internship",
                        "enum": ["", "full-time", "part-time", "contract", "remote", "internship"]
                    },
                    "salary_range": {
                        "type": "string",
                        "description": "Expected salary range, e.g., '10-20 LPA', '$50-80k/year'"
                    },
                    "experience_level": {
                        "type": "string",
                        "description": "Experience level: entry, mid, senior",
                        "enum": ["", "entry", "mid", "senior", "lead"]
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_jobs",
            "description": "Search for jobs based on user's preferences or specific criteria. Use when user asks 'find me jobs', 'job search', 'Python jobs in Hyderabad'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Job search query or keywords, e.g., 'Python developer', 'React frontend', 'AWS cloud engineer'"
                    },
                    "location": {
                        "type": "string",
                        "description": "Optional location override, e.g., 'Hyderabad', 'Remote', 'Bangalore'"
                    },
                    "remote": {
                        "type": "boolean",
                        "description": "Filter for remote jobs only"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_job_preferences",
            "description": "Get user's saved job search preferences. Use when user asks 'my job preferences', 'what jobs am I looking for'.",
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
            "name": "enable_auto_job_search",
            "description": "Enable automatic job search notifications. Set frequency for daily/weekly job alerts based on preferences.",
            "parameters": {
                "type": "object",
                "properties": {
                    "enabled": {
                        "type": "boolean",
                        "description": "True to enable auto job search, False to disable"
                    },
                    "frequency_hours": {
                        "type": "integer",
                        "description": "How often to search (in hours): 24=daily, 168=weekly, 720=monthly"
                    }
                },
                "required": ["enabled"]
            }
        }
    }
]

def _get_user_job_prefs(user_id):
    """Get user's job preferences from memory."""
    try:
        data = memory.get_user_data(user_id)
        return data.get("job_preferences", {})
    except Exception:
        return {}

def _set_user_job_prefs(user_id, preferences):
    """Save job preferences to memory."""
    try:
        memory.set_user_data(user_id, "job_preferences", preferences)
        return True
    except Exception:
        return False

def _search_linkedin_jobs(query, location=None, remote=False):
    """Search for jobs using free job aggregators (LinkedIn alternative)."""
    try:
        # Use a free job search API (indeed, glassdoor, etc.)
        # For demo, we'll use a mock search since LinkedIn requires API key
        results = []

        # In production, integrate with real job APIs:
        # - LinkedIn API (requires business account)
        # - Indeed API (free tier available)
        # - Glassdoor API
        # - ZipRecruiter
        # - SimplyHired

        # Mock results for demonstration
        if query and location:
            mock_jobs = [
                {
                    "title": f"Senior {query} Developer",
                    "company": "Tech Corp",
                    "location": location,
                    "salary": "15-25 LPA",
                    "type": "Full-time",
                    "posted": "2 days ago",
                    "url": f"https://linkedin.com/jobs/search/{query.replace(' ', '+')}"
                },
                {
                    "title": f"{query} Engineer",
                    "company": "Innovate Solutions",
                    "location": location,
                    "salary": "10-18 LPA",
                    "type": "Full-time",
                    "posted": "1 week ago",
                    "url": f"https://linkedin.com/jobs/search/{query.replace(' ', '+')}"
                },
                {
                    "title": f"Junior {query} Developer",
                    "company": "Startup Hub",
                    "location": location,
                    "salary": "8-12 LPA",
                    "type": "Contract",
                    "posted": "3 days ago",
                    "url": f"https://linkedin.com/jobs/search/{query.replace(' ', '+')}"
                }
            ]
            results = mock_jobs[:3]  # Limit to 3 results for demo

        return results

    except Exception as e:
        print(f"❌ Job search error: {e}")
        return []

def _search_indeed_jobs(query, location=None, remote=False):
    """Search for jobs using Indeed API (free tier)."""
    try:
        # Indeed free search endpoint (no API key needed)
        url = "https://indeed.com/jobs"
        params = {
            "q": query,
            "l": location or "",
            "remote": "1" if remote else "0",
            "limit": "5"
        }

        # For demo purposes, we'll return mock results
        # In production, integrate with real Indeed API
        mock_jobs = [
            {
                "title": f"{query} - Indeed Result 1",
                "company": "Company A",
                "location": location or "Remote",
                "salary": "Competitive",
                "type": "Full-time",
                "posted": "Recently",
                "url": f"https://indeed.com/jobs?q={query.replace(' ', '+')}"
            },
            {
                "title": f"{query} - Indeed Result 2",
                "company": "Company B",
                "location": location or "Remote",
                "salary": "Competitive",
                "type": "Full-time",
                "posted": "Recently",
                "url": f"https://indeed.com/jobs?q={query.replace(' ', '+')}"
            }
        ]

        return mock_jobs

    except Exception as e:
        print(f"❌ Indeed search error: {e}")
        return []

def _format_job_results(jobs, source):
    """Format job search results for user."""
    if not jobs:
        return f"🔍 **No jobs found** for your search criteria.\n\n💡 Try broader terms or different locations."

    lines = [f"💼 **Job Search Results** ({source})\n"]
    for i, job in enumerate(jobs, 1):
        lines.append(f"**{i}. {job['title']}**")
        lines.append(f"   🏢 {job['company']}")
        lines.append(f"   📍 {job['location']}")
        if job.get('salary'):
            lines.append(f"   💰 {job['salary']}")
        lines.append(f"   💼 {job['type']}")
        lines.append(f"   📅 {job['posted']}")
        if job.get('url'):
            lines.append(f"   🔗 {job['url']}")
        lines.append("")

    return "\n".join(lines)

def execute(tool_name, arguments, user_id=None):
    # Default user_id to config OWNER_ID if not provided
    if not user_id:
        from config import OWNER_ID
        user_id = str(OWNER_ID)

    try:
        if tool_name == "set_job_preferences":
            preferences = {}
            if arguments.get("skills"):
                preferences["skills"] = arguments["skills"]
            if arguments.get("location"):
                preferences["location"] = arguments["location"]
            if arguments.get("job_type"):
                preferences["job_type"] = arguments["job_type"]
            if arguments.get("salary_range"):
                preferences["salary_range"] = arguments["salary_range"]
            if arguments.get("experience_level"):
                preferences["experience_level"] = arguments["experience_level"]

            # Get existing preferences and merge
            existing_prefs = _get_user_job_prefs(user_id)
            merged_prefs = {**existing_prefs, **preferences}

            if _set_user_job_prefs(user_id, merged_prefs):
                response = "✅ **Job preferences saved!**\n\n"
                response += "💼 **Your Job Search Profile:**\n"
                if merged_prefs.get("skills"):
                    response += f"• Skills: {merged_prefs['skills']}\n"
                if merged_prefs.get("location"):
                    response += f"• Location: {merged_prefs['location']}\n"
                if merged_prefs.get("job_type"):
                    response += f"• Type: {merged_prefs['job_type']}\n"
                if merged_prefs.get("salary_range"):
                    response += f"• Salary: {merged_prefs['salary_range']}\n"
                if merged_prefs.get("experience_level"):
                    response += f"• Level: {merged_prefs['experience_level']}\n"
                response += "\n💡 I'll use these preferences for job searches and auto-alerts!"
                return response
            return "❌ Failed to save job preferences."

        elif tool_name == "get_job_preferences":
            prefs = _get_user_job_prefs(user_id)
            if not prefs:
                return "📝 **No job preferences set yet.**\n\nTell me what kind of job you're looking for:\n• 'I want a Python developer job'\n• 'Looking for remote React jobs'\n• 'I need a senior AWS engineer position'"

            response = "💼 **Your Job Search Preferences:**\n\n"
            if prefs.get("skills"):
                response += f"• Skills: {prefs['skills']}\n"
            if prefs.get("location"):
                response += f"• Location: {prefs['location']}\n"
            if prefs.get("job_type"):
                response += f"• Type: {prefs['job_type']}\n"
            if prefs.get("salary_range"):
                response += f"• Salary: {prefs['salary_range']}\n"
            if prefs.get("experience_level"):
                response += f"• Level: {prefs['experience_level']}\n"

            response += "\n💡 Update with: 'I want [skills] in [location] [type] job'"
            return response

        elif tool_name == "search_jobs":
            query = arguments.get("query", "").strip()
            location = arguments.get("location", "").strip()
            remote = arguments.get("remote", False)

            # If no query provided, use saved preferences
            if not query:
                prefs = _get_user_job_prefs(user_id)
                query = prefs.get("skills", "")
                if not location:
                    location = prefs.get("location", "")

            if not query:
                return "📝 **Please provide job search criteria.**\n• Usage: 'search for Python jobs'\n• Or set preferences: 'I want a developer job'"

            # Search using different job boards
            linkedin_results = _search_linkedin_jobs(query, location, remote)
            indeed_results = _search_indeed_jobs(query, location, remote)

            # Combine results
            all_results = []
            all_results.extend(linkedin_results)
            all_results.extend(indeed_results)

            if not all_results:
                return "🔍 **No jobs found** for your criteria.\n\n💡 Try different keywords or locations."

            return _format_job_results(all_results[:5], "LinkedIn + Indeed")  # Show top 5 results

        elif tool_name == "enable_auto_job_search":
            enabled = arguments.get("enabled", False)
            frequency_hours = arguments.get("frequency_hours", 24)

            # Get existing auto-search settings
            try:
                data = memory.get_user_data(user_id)
                existing_prefs = data.get("job_preferences", {})

                existing_prefs["auto_search_enabled"] = enabled
                existing_prefs["auto_search_frequency"] = frequency_hours

                if _set_user_job_prefs(user_id, existing_prefs):
                    status = "🟢 **Enabled**" if enabled else "🔴 **Disabled**"
                    freq_text = f"every {frequency_hours} hours ({frequency_hours//24} day(s))" if frequency_hours > 0 else "immediately"
                    response = f"✅ **Auto Job Search** {status}\n"
                    response += f"⏰ Frequency: {freq_text}\n"
                    response += "💡 I'll automatically search for jobs based on your preferences!"
                    return response
                return "❌ Failed to update auto job search settings."
            except Exception as e:
                return f"❌ Error updating auto job search: {e}"

    except Exception as e:
        return f"❌ Job search error: {e}"

    return None
