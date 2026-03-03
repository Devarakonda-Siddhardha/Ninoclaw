"""
Task management and scheduling for Ninoclaw
"""
import json
import schedule
import time
import re
from datetime import datetime
from threading import Thread
from config import TASKS_FILE
from croniter import croniter

class TaskManager:
    def __init__(self):
        self.tasks_file = TASKS_FILE
        self.tasks = self._load()
        self.cron_jobs_file = "cron_jobs.json"
        self.cron_jobs = self._load_cron()
        self.running = False
        self.thread = None
        self.telegram_app = None  # Reference to send messages

    def _load(self):
        """Load tasks from file"""
        try:
            with open(self.tasks_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return []

    def _save(self):
        """Save tasks to file"""
        with open(self.tasks_file, 'w') as f:
            json.dump(self.tasks, f, indent=2)

    def _load_cron(self):
        """Load cron jobs from file"""
        try:
            with open(self.cron_jobs_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return []

    def _save_cron(self):
        """Save cron jobs to file"""
        with open(self.cron_jobs_file, 'w') as f:
            json.dump(self.cron_jobs, f, indent=2)

    def add_task(self, user_id, task_name, schedule_time, callback=None):
        """Add a scheduled task"""
        task_id = f"{datetime.now().timestamp()}"
        task = {
            "id": task_id,
            "user_id": str(user_id),
            "name": task_name,
            "scheduled_time": schedule_time,
            "completed": False,
            "created_at": datetime.now().isoformat()
        }
        self.tasks.append(task)
        self._save()
        return task_id

    def list_tasks(self, user_id):
        """List tasks for a user"""
        user_id = str(user_id)
        return [
            t for t in self.tasks
            if t["user_id"] == user_id and not t["completed"]
        ]

    def complete_task(self, task_id):
        """Mark a task as completed"""
        for task in self.tasks:
            if task["id"] == task_id:
                task["completed"] = True
                task["completed_at"] = datetime.now().isoformat()
                self._save()
                return True
        return False

    def delete_task(self, task_id):
        """Delete a task"""
        self.tasks = [t for t in self.tasks if t["id"] != task_id]
        self._save()

    def parse_time(self, time_str):
        """
        Parse time string like:
        - "in 5 minutes"
        - "at 3:00 PM"
        - "tomorrow at 9:00 AM"
        """
        # Simple implementation - expand as needed
        time_str = time_str.lower().strip()

        # "in X minutes"
        if time_str.startswith("in "):
            try:
                minutes = int(time_str.split()[1])
                return datetime.now().timestamp() + (minutes * 60)
            except:
                pass

        # For now, return current time + 5 minutes as default
        return datetime.now().timestamp() + 300

    def format_timestamp(self, ts):
        """Format timestamp for display"""
        dt = datetime.fromtimestamp(ts)
        return dt.strftime("%Y-%m-%d %H:%M")

    def _parse_cron_expression(self, expr):
        """
        Parse natural language to cron expression
        Returns: (cron_expression, next_run_timestamp)
        """
        expr = expr.lower().strip()

        # Patterns for natural language
        patterns = [
            # "every day at 9am" or "every day at 9:00am"
            (r'every day at (\d{1,2}):?(\d{2})?(am|pm)?', lambda m: self._daily_to_cron(m)),
            # "every day at 9am"
            (r'every day at (\d{1,2})(am|pm)', lambda m: self._daily_to_cron_simple(m)),
            # "every X hours"
            (r'every (\d+) hours?', lambda m: f"0 */{m.group(1)} * * *"),
            # "every X minutes"
            (r'every (\d+) minutes?', lambda m: f"*/{m.group(1)} * * * *"),
            # "every monday" or "every tuesday", etc.
            (r'every (monday|tuesday|wednesday|thursday|friday|saturday|sunday)', lambda m: self._weekday_to_cron(m)),
            # "weekdays at 10am"
            (r'weekdays at (\d{1,2}):?(\d{2})?(am|pm)?', lambda m: self._weekdays_to_cron(m)),
            # "weekends at 10am"
            (r'weekends at (\d{1,2}):?(\d{2})?(am|pm)?', lambda m: self._weekends_to_cron(m)),
            # "daily at 9am"
            (r'daily at (\d{1,2}):?(\d{2})?(am|pm)?', lambda m: self._daily_to_cron(m)),
            # "hourly"
            (r'hourly', lambda m: "0 * * * *"),
            # "daily"
            (r'daily', lambda m: "0 0 * * *"),
        ]

        for pattern, converter in patterns:
            match = re.match(pattern, expr)
            if match:
                cron_expr = converter(match)
                # Calculate next run time
                try:
                    cron = croniter(cron_expr, datetime.now())
                    next_run = cron.get_next(datetime)
                    return cron_expr, next_run.timestamp()
                except Exception:
                    return None, None

        # Try as standard cron expression
        try:
            cron = croniter(expr, datetime.now())
            next_run = cron.get_next(datetime)
            return expr, next_run.timestamp()
        except Exception:
            return None, None

    def _daily_to_cron(self, match):
        """Convert "every day at 9:30am" to cron"""
        hour = int(match.group(1))
        minute = match.group(2)
        ampm = match.group(3)

        if minute:
            minute = int(minute)
        else:
            minute = 0

        # Handle AM/PM
        if ampm == 'pm' and hour != 12:
            hour += 12
        elif ampm == 'am' and hour == 12:
            hour = 0

        return f"{minute} {hour} * * *"

    def _daily_to_cron_simple(self, match):
        """Convert "every day at 9am" to cron"""
        hour = int(match.group(1))
        ampm = match.group(2)

        if ampm == 'pm' and hour != 12:
            hour += 12
        elif ampm == 'am' and hour == 12:
            hour = 0

        return f"0 {hour} * * *"

    def _weekday_to_cron(self, match):
        """Convert "every monday" to cron (midnight)"""
        day_map = {
            'monday': 1, 'tuesday': 2, 'wednesday': 3,
            'thursday': 4, 'friday': 5, 'saturday': 6, 'sunday': 0
        }
        day = day_map[match.group(1)]
        return f"0 0 * * {day}"

    def _weekdays_to_cron(self, match):
        """Convert "weekdays at 10am" to cron"""
        hour = int(match.group(1))
        minute = match.group(2)
        ampm = match.group(3)

        if minute:
            minute = int(minute)
        else:
            minute = 0

        if ampm == 'pm' and hour != 12:
            hour += 12
        elif ampm == 'am' and hour == 12:
            hour = 0

        return f"{minute} {hour} * * 1-5"

    def _weekends_to_cron(self, match):
        """Convert "weekends at 10am" to cron"""
        hour = int(match.group(1))
        minute = match.group(2)
        ampm = match.group(3)

        if minute:
            minute = int(minute)
        else:
            minute = 0

        if ampm == 'pm' and hour != 12:
            hour += 12
        elif ampm == 'am' and hour == 12:
            hour = 0

        return f"{minute} {hour} * * 0,6"

    def add_cron_job(self, user_id, name, expression, command):
        """Add a cron job"""
        # Parse expression (natural language or cron syntax)
        cron_expr, next_run = self._parse_cron_expression(expression)
        if not cron_expr:
            return None, "Invalid cron expression or natural language"

        task_id = f"{datetime.now().timestamp()}".replace('.', '')
        job = {
            "id": task_id,
            "user_id": str(user_id),
            "name": name,
            "cron_expression": cron_expr,
            "original_expression": expression,
            "command": command,
            "is_active": True,
            "created_at": datetime.now().isoformat(),
            "last_run": None,
            "next_run": next_run
        }

        self.cron_jobs.append(job)
        self._save_cron()
        return task_id, None

    def list_cron_jobs(self, user_id):
        """List cron jobs for a user"""
        user_id = str(user_id)
        return [job for job in self.cron_jobs if job["user_id"] == user_id]

    def remove_cron_job(self, job_id, user_id):
        """Remove a cron job"""
        user_id = str(user_id)
        original_count = len(self.cron_jobs)
        self.cron_jobs = [j for j in self.cron_jobs if j["id"] != job_id]
        if len(self.cron_jobs) < original_count:
            self._save_cron()
            return True
        return False

    def toggle_cron_job(self, job_id, user_id):
        """Enable/disable a cron job"""
        user_id = str(user_id)
        for job in self.cron_jobs:
            if job["id"] == job_id and job["user_id"] == user_id:
                job["is_active"] = not job["is_active"]
                self._save_cron()
                return job["is_active"]
        return None

    def get_cron_job(self, job_id, user_id):
        """Get a specific cron job"""
        user_id = str(user_id)
        for job in self.cron_jobs:
            if job["id"] == job_id and job["user_id"] == user_id:
                return job
        return None

    async def execute_cron_job(self, job):
        """Execute a cron job's AI task"""
        if not job["is_active"]:
            return

        user_id = int(job["user_id"])
        command = job["command"]

        # Import here to avoid circular imports
        from ai import chat
        from memory import Memory

        memory = Memory()
        user_data = memory.get_user_data(user_id)

        # Build personalized system prompt
        agent_name = user_data.get("agent_name", "Ninoclaw")
        user_name = user_data.get("user_name", "friend")
        from config import SYSTEM_PROMPT

        personalized_prompt = f"""{SYSTEM_PROMPT}

Your name is {agent_name}. You are talking to {user_name}.
This is an automated task execution. Be helpful and concise."""

        # Get AI response
        try:
            response = chat(
                message=command,
                system_prompt=personalized_prompt,
                history=[]
            )

            # Send message via Telegram
            if self.telegram_app:
                await self.telegram_app.bot.send_message(
                    chat_id=user_id,
                    text=f"🔄 Scheduled task: {job['name']}\n\n{response}"
                )

            # Update job
            job["last_run"] = datetime.now().isoformat()
            # Calculate next run
            cron = croniter(job["cron_expression"], datetime.now())
            job["next_run"] = cron.get_next(datetime).timestamp()
            self._save_cron()

        except Exception as e:
            error_msg = f"Failed to execute cron job: {e}"
            if self.telegram_app:
                await self.telegram_app.bot.send_message(
                    chat_id=user_id,
                    text=f"❌ Error in scheduled task: {error_msg}"
                )

    async def update_cron_schedules(self):
        """Check and run due cron jobs"""
        now = datetime.now().timestamp()

        for job in self.cron_jobs:
            if not job["is_active"]:
                continue

            if job["next_run"] and now >= job["next_run"]:
                await self.execute_cron_job(job)

    def detect_schedule_request(self, message, user_timezone=None):
        """
        Detect if user wants to schedule a recurring task
        Returns: (is_schedule, expression, command) or None
        """
        message = message.lower().strip()

        # Simpler pattern matching
        if "every" in message and ("schedule" in message or "remind" in message or "send" in message or "daily" in message or "hourly" in message):
            # This looks like a schedule request
            # Try to extract the schedule expression and command
            # For now, just let the user use /cron add command
            return None

        return None

    async def handle_schedule_request(self, user_id, expression, command, user_timezone=None):
        """
        Handle a schedule request from natural language
        Returns: (success, message)
        """
        # Parse expression
        cron_expr, next_run = self._parse_cron_expression(expression)
        if not cron_expr:
            return (False, f"Sorry, I couldn't understand the schedule: '{expression}'. Try saying 'every day at 9am' or 'hourly'.")

        # Generate a name
        name = command[:30] + "..." if len(command) > 30 else command

        # Add the cron job
        job_id, error = self.add_cron_job(user_id, name, expression, command)

        if error:
            return (False, f"Error creating cron job: {error}")

        job = self.get_cron_job(job_id, user_id)
        next_run_str = self.format_timestamp(job["next_run"]) if job.get("next_run") else "Unknown"

        msg = (
            f"✅ Scheduled task created!\n\n"
            f"📝 {command}\n"
            f"⏰ Schedule: {expression} (cron: {job['cron_expression']})\n"
            f"📅 Next run: {next_run_str}\n"
            f"🆔 ID: {job_id}"
        )

        return (True, msg)

    def start_scheduler(self):
        """Start the scheduler in background thread"""
        if self.running:
            return

        self.running = True

        async def run_async():
            while self.running:
                schedule.run_pending()
                await self.update_cron_schedules()
                time.sleep(1)

        def run():
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(run_async())

        self.thread = Thread(target=run, daemon=True)
        self.thread.start()

    def stop_scheduler(self):
        """Stop the scheduler"""
        self.running = False
        if self.thread:
            self.thread.join()

# Singleton instance
task_manager = TaskManager()
