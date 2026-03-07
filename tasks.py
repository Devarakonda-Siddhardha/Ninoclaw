"""
Task management and scheduling for Ninoclaw — SQLite backend
"""
import sqlite3
import json
import schedule
import time
import re
from datetime import datetime
from threading import Thread
from croniter import croniter

DB_FILE = "ninoclaw.db"

def _get_conn():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def _init_db():
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS tasks (
            id             TEXT PRIMARY KEY,
            user_id        TEXT NOT NULL,
            name           TEXT NOT NULL,
            scheduled_time REAL NOT NULL,
            completed      INTEGER DEFAULT 0,
            completed_at   TEXT,
            created_at     TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS cron_jobs (
            id                  TEXT PRIMARY KEY,
            user_id             TEXT NOT NULL,
            name                TEXT NOT NULL,
            cron_expression     TEXT NOT NULL,
            original_expression TEXT,
            command             TEXT NOT NULL,
            is_active           INTEGER DEFAULT 1,
            created_at          TEXT NOT NULL,
            last_run            TEXT,
            next_run            REAL
        );
    """)
    conn.commit()
    conn.close()

_init_db()


class TaskManager:
    def __init__(self):
        self.running = False
        self.thread = None
        self.telegram_app = None

    @property
    def tasks(self):
        conn = _get_conn()
        rows = conn.execute("SELECT * FROM tasks").fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def _row_to_task(self, r):
        d = dict(r)
        d["completed"] = bool(d["completed"])
        return d

    def _row_to_job(self, r):
        d = dict(r)
        d["is_active"] = bool(d["is_active"])
        return d

    def add_task(self, user_id, task_name, schedule_time, callback=None):
        task_id = f"{datetime.now().timestamp()}".replace('.', '')
        conn = _get_conn()
        conn.execute(
            "INSERT INTO tasks (id, user_id, name, scheduled_time, completed, created_at) VALUES (?,?,?,?,0,?)",
            (task_id, str(user_id), task_name, schedule_time, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
        return task_id

    def list_tasks(self, user_id):
        conn = _get_conn()
        rows = conn.execute(
            "SELECT * FROM tasks WHERE user_id=? AND completed=0",
            (str(user_id),)
        ).fetchall()
        conn.close()
        return [self._row_to_task(r) for r in rows]

    def complete_task(self, task_id):
        conn = _get_conn()
        cur = conn.execute(
            "UPDATE tasks SET completed=1, completed_at=? WHERE id=?",
            (datetime.now().isoformat(), task_id)
        )
        conn.commit()
        conn.close()
        return cur.rowcount > 0

    def delete_task(self, task_id):
        conn = _get_conn()
        conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        conn.commit()
        conn.close()

    def parse_time(self, time_str):
        """Parse 'in X minutes/hours/days' into a timestamp"""
        time_str = time_str.lower().strip()

        match = re.search(r'in (\d+)\s*(minute|minutes|min|hour|hours|hr|day|days)', time_str)
        if match:
            amount = int(match.group(1))
            unit = match.group(2)
            if unit in ('hour', 'hours', 'hr'):
                return datetime.now().timestamp() + amount * 3600
            elif unit in ('day', 'days'):
                return datetime.now().timestamp() + amount * 86400
            else:
                return datetime.now().timestamp() + amount * 60

        return datetime.now().timestamp() + 300

    def format_timestamp(self, ts):
        if ts is None:
            return "Unknown"
        dt = datetime.fromtimestamp(ts)
        return dt.strftime("%Y-%m-%d %H:%M")

    def _parse_cron_expression(self, expr):
        expr = expr.lower().strip()

        patterns = [
            (r'every day at (\d{1,2}):?(\d{2})?(am|pm)?', lambda m: self._daily_to_cron(m)),
            (r'every day at (\d{1,2})(am|pm)', lambda m: self._daily_to_cron_simple(m)),
            (r'every (\d{1,2}):?(\d{2})?(am|pm)? daily', lambda m: self._daily_to_cron(m)),
            (r'every (\d+) hours?', lambda m: f"0 */{m.group(1)} * * *"),
            (r'every (\d+) minutes?', lambda m: f"*/{m.group(1)} * * * *"),
            (r'every (monday|tuesday|wednesday|thursday|friday|saturday|sunday)', lambda m: self._weekday_to_cron(m)),
            (r'weekdays at (\d{1,2}):?(\d{2})?(am|pm)?', lambda m: self._weekdays_to_cron(m)),
            (r'weekends at (\d{1,2}):?(\d{2})?(am|pm)?', lambda m: self._weekends_to_cron(m)),
            (r'daily at (\d{1,2}):?(\d{2})?(am|pm)?', lambda m: self._daily_to_cron(m)),
            (r'(\d{1,2}):?(\d{2})?(am|pm)? daily', lambda m: self._daily_to_cron(m)),
            (r'hourly', lambda m: "0 * * * *"),
            (r'daily', lambda m: "0 0 * * *"),
            (r'weekly', lambda m: "0 0 * * 0"),
            (r'monthly', lambda m: "0 0 1 * *"),
        ]

        for pattern, converter in patterns:
            match = re.search(pattern, expr)
            if match:
                cron_expr = converter(match)
                try:
                    cron = croniter(cron_expr, datetime.now())
                    next_run = cron.get_next(datetime)
                    return cron_expr, next_run.timestamp()
                except Exception:
                    pass

        try:
            cron = croniter(expr, datetime.now())
            next_run = cron.get_next(datetime)
            return expr, next_run.timestamp()
        except Exception:
            return None, None

    def _daily_to_cron(self, match):
        hour = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0
        ampm = match.group(3)
        if ampm == 'pm' and hour != 12:
            hour += 12
        elif ampm == 'am' and hour == 12:
            hour = 0
        return f"{minute} {hour} * * *"

    def _daily_to_cron_simple(self, match):
        hour = int(match.group(1))
        ampm = match.group(2)
        if ampm == 'pm' and hour != 12:
            hour += 12
        elif ampm == 'am' and hour == 12:
            hour = 0
        return f"0 {hour} * * *"

    def _weekday_to_cron(self, match):
        day_map = {'monday': 1, 'tuesday': 2, 'wednesday': 3,
                   'thursday': 4, 'friday': 5, 'saturday': 6, 'sunday': 0}
        return f"0 0 * * {day_map[match.group(1)]}"

    def _weekdays_to_cron(self, match):
        hour = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0
        ampm = match.group(3)
        if ampm == 'pm' and hour != 12:
            hour += 12
        elif ampm == 'am' and hour == 12:
            hour = 0
        return f"{minute} {hour} * * 1-5"

    def _weekends_to_cron(self, match):
        hour = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0
        ampm = match.group(3)
        if ampm == 'pm' and hour != 12:
            hour += 12
        elif ampm == 'am' and hour == 12:
            hour = 0
        return f"{minute} {hour} * * 0,6"

    def add_cron_job(self, user_id, name, expression, command):
        print(f"[DEBUG] Parsing expression: '{expression}'")
        cron_expr, next_run = self._parse_cron_expression(expression)
        if not cron_expr:
            return None, f"Invalid cron expression: '{expression}'. Try formats like 'every day at 9am', 'hourly', 'daily', or '*/30 * * * *'"

        task_id = f"{datetime.now().timestamp()}".replace('.', '')
        conn = _get_conn()
        conn.execute(
            "INSERT INTO cron_jobs (id,user_id,name,cron_expression,original_expression,command,is_active,created_at,next_run) VALUES (?,?,?,?,?,?,1,?,?)",
            (task_id, str(user_id), name, cron_expr, expression, command, datetime.now().isoformat(), next_run)
        )
        conn.commit()
        conn.close()
        return task_id, None

    def list_cron_jobs(self, user_id):
        conn = _get_conn()
        rows = conn.execute("SELECT * FROM cron_jobs WHERE user_id=?", (str(user_id),)).fetchall()
        conn.close()
        return [self._row_to_job(r) for r in rows]

    def remove_cron_job(self, job_id, user_id):
        conn = _get_conn()
        cur = conn.execute("DELETE FROM cron_jobs WHERE id=? AND user_id=?", (job_id, str(user_id)))
        conn.commit()
        conn.close()
        return cur.rowcount > 0

    def toggle_cron_job(self, job_id, user_id):
        conn = _get_conn()
        row = conn.execute("SELECT is_active FROM cron_jobs WHERE id=? AND user_id=?", (job_id, str(user_id))).fetchone()
        if not row:
            conn.close()
            return None
        new_state = 0 if row["is_active"] else 1
        conn.execute("UPDATE cron_jobs SET is_active=? WHERE id=?", (new_state, job_id))
        conn.commit()
        conn.close()
        return bool(new_state)

    def get_cron_job(self, job_id, user_id):
        conn = _get_conn()
        row = conn.execute("SELECT * FROM cron_jobs WHERE id=? AND user_id=?", (job_id, str(user_id))).fetchone()
        conn.close()
        return self._row_to_job(row) if row else None

    async def check_due_tasks(self):
        now = datetime.now().timestamp()
        conn = _get_conn()
        rows = conn.execute(
            "SELECT * FROM tasks WHERE completed=0 AND scheduled_time<=?", (now,)
        ).fetchall()

        for row in rows:
            task = self._row_to_task(row)
            conn.execute(
                "UPDATE tasks SET completed=1, completed_at=? WHERE id=?",
                (datetime.now().isoformat(), task["id"])
            )
            if self.telegram_app:
                try:
                    await self.telegram_app.bot.send_message(
                        chat_id=int(task["user_id"]),
                        text=f"⏰ {task['name']}"
                    )
                except Exception as e:
                    print(f"[Reminder] Failed to send: {e}")

        conn.commit()
        conn.close()

    async def execute_cron_job(self, job):
        if not job["is_active"]:
            return

        user_id = int(job["user_id"])
        command = job["command"]

        from ai import chat
        from memory import Memory
        memory = Memory()
        user_data = memory.get_user_data(user_id)
        agent_name = user_data.get("agent_name", "Ninoclaw")
        user_name = user_data.get("user_name", "friend")
        from config import SYSTEM_PROMPT

        personalized_prompt = f"""{SYSTEM_PROMPT}

Your name is {agent_name}. You are talking to {user_name}.
This is an automated task execution. Be helpful and concise."""

        try:
            from tools import get_tool_definitions, execute_tool
            tools = get_tool_definitions(user_id)
            result = chat(message=command, system_prompt=personalized_prompt, history=[], tools=tools)

            # Handle tool calls from the scheduled job
            tool_results = []
            if isinstance(result, dict) and result.get("tool_calls"):
                for tc in result["tool_calls"]:
                    fn = tc.get("function", {})
                    tool_name = fn.get("name", "")
                    args = fn.get("arguments", {})
                    if isinstance(args, str):
                        import json as _json
                        try: args = _json.loads(args)
                        except Exception: args = {}
                    tool_output = await execute_tool(tool_name, args, user_id, self)
                    tool_results.append(f"✅ {tool_name}: {tool_output}")
                response = "\n".join(tool_results) if tool_results else "✅ Done."
            else:
                response = result if isinstance(result, str) else (result or {}).get("content", "✅ Done.")

            if self.telegram_app:
                await self.telegram_app.bot.send_message(
                    chat_id=user_id,
                    text=f"⏰ Scheduled: {job['name']}\n\n{response}"
                )

            conn = _get_conn()
            cron = croniter(job["cron_expression"], datetime.now())
            next_run = cron.get_next(datetime).timestamp()
            conn.execute(
                "UPDATE cron_jobs SET last_run=?, next_run=? WHERE id=?",
                (datetime.now().isoformat(), next_run, job["id"])
            )
            conn.commit()
            conn.close()

        except Exception as e:
            if self.telegram_app:
                try:
                    await self.telegram_app.bot.send_message(
                        chat_id=user_id, text=f"❌ Error in scheduled task: {e}"
                    )
                except Exception:
                    pass

    async def update_cron_schedules(self):
        now = datetime.now().timestamp()
        conn = _get_conn()
        rows = conn.execute(
            "SELECT * FROM cron_jobs WHERE is_active=1 AND next_run<=?", (now,)
        ).fetchall()
        conn.close()
        for row in rows:
            await self.execute_cron_job(self._row_to_job(row))

    def start_scheduler(self):
        if self.running:
            return
        self.running = True

        def run():
            while self.running:
                schedule.run_pending()
                import asyncio
                try:
                    asyncio.run(self.check_due_tasks())
                    asyncio.run(self.update_cron_schedules())
                except Exception:
                    pass
                time.sleep(1)

        self.thread = Thread(target=run, daemon=True)
        self.thread.start()

    def stop_scheduler(self):
        self.running = False
        if self.thread:
            self.thread.join()


# Singleton instance
task_manager = TaskManager()
