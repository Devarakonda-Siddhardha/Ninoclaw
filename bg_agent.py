"""
Background agent runner — queues and executes multi-step tasks async.
User says "in background, research X" → job queued → result sent via Telegram/Discord when done.
"""
import sqlite3
import asyncio
import threading
import uuid
from datetime import datetime

DB_FILE = "ninoclaw.db"

def _get_conn():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def _init_db():
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS agent_jobs (
            id         TEXT PRIMARY KEY,
            user_id    TEXT NOT NULL,
            goal       TEXT NOT NULL,
            status     TEXT DEFAULT 'queued',
            result     TEXT,
            created_at TEXT NOT NULL,
            started_at TEXT,
            done_at    TEXT
        );
    """)
    conn.commit()
    conn.close()

_init_db()


class BackgroundAgentRunner:
    def __init__(self):
        self.notify_fn = None  # set to async callable(user_id, msg) after bot starts
        self.notify_loop = None
        self.task_manager = None
        self._loop = None
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._worker())

    async def _worker(self):
        while True:
            conn = _get_conn()
            job = conn.execute(
                "SELECT * FROM agent_jobs WHERE status='queued' ORDER BY created_at LIMIT 1"
            ).fetchone()
            conn.close()

            if job:
                await self._run_job(dict(job))
            else:
                await asyncio.sleep(5)

    async def _notify(self, user_id, msg):
        if not self.notify_fn:
            return
        try:
            target_loop = self.notify_loop
            current_loop = asyncio.get_running_loop()
            if target_loop and target_loop is not current_loop:
                fut = asyncio.run_coroutine_threadsafe(self.notify_fn(user_id, msg), target_loop)
                await asyncio.wrap_future(fut)
            else:
                await self.notify_fn(user_id, msg)
        except Exception as e:
            print(f"[BG Agent] Notify error: {e}")

    async def _run_job(self, job):
        conn = _get_conn()
        conn.execute(
            "UPDATE agent_jobs SET status='running', started_at=? WHERE id=?",
            (datetime.now().isoformat(), job["id"])
        )
        conn.commit()
        conn.close()

        user_id = job["user_id"]
        goal = job["goal"]

        async def progress(msg):
            await self._notify(user_id, f"⚙️ [{goal[:30]}...]\n{msg}")

        try:
            from agent import run_agent
            result = await run_agent(goal, user_id, self.task_manager, notify_fn=None)
            status = "done"
        except Exception as e:
            result = f"❌ Agent failed: {e}"
            status = "failed"

        conn = _get_conn()
        conn.execute(
            "UPDATE agent_jobs SET status=?, result=?, done_at=? WHERE id=?",
            (status, result, datetime.now().isoformat(), job["id"])
        )
        conn.commit()
        conn.close()

        # Notify user
        msg = f"✅ Background task done!\n\n**Goal:** {goal}\n\n{result}"
        await self._notify(user_id, msg)

    def queue_job(self, user_id: str, goal: str) -> str:
        job_id = str(uuid.uuid4())[:8]
        conn = _get_conn()
        conn.execute(
            "INSERT INTO agent_jobs (id, user_id, goal, status, created_at) VALUES (?,?,?,?,?)",
            (job_id, str(user_id), goal, "queued", datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
        return job_id

    def list_jobs(self, user_id: str):
        conn = _get_conn()
        rows = conn.execute(
            "SELECT * FROM agent_jobs WHERE user_id=? ORDER BY created_at DESC LIMIT 20",
            (str(user_id),)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_job(self, job_id: str):
        conn = _get_conn()
        row = conn.execute("SELECT * FROM agent_jobs WHERE id=?", (job_id,)).fetchone()
        conn.close()
        return dict(row) if row else None


bg_runner = BackgroundAgentRunner()
