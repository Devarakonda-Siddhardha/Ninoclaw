"""
Memory management for Ninoclaw — SQLite backend
"""
import sqlite3
import json
from datetime import datetime
from config import MAX_MEMORY_SIZE

DB_FILE = "ninoclaw.db"

def _get_conn():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def _init_db():
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS conversations (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id  TEXT NOT NULL,
            role     TEXT NOT NULL,
            content  TEXT NOT NULL,
            ts       TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS user_data (
            user_id  TEXT NOT NULL,
            key      TEXT NOT NULL,
            value    TEXT,
            PRIMARY KEY (user_id, key)
        );
    """)
    conn.commit()
    conn.close()

_init_db()

class Memory:
    def get_conversation(self, user_id, limit=MAX_MEMORY_SIZE):
        conn = _get_conn()
        rows = conn.execute(
            "SELECT role, content, ts FROM conversations WHERE user_id=? ORDER BY id DESC LIMIT ?",
            (str(user_id), limit)
        ).fetchall()
        conn.close()
        return [{"role": r["role"], "content": r["content"], "timestamp": r["ts"]} for r in reversed(rows)]

    def add_message(self, user_id, role, content):
        conn = _get_conn()
        conn.execute(
            "INSERT INTO conversations (user_id, role, content, ts) VALUES (?,?,?,?)",
            (str(user_id), role, content, datetime.now().isoformat())
        )
        # Trim old messages beyond MAX_MEMORY_SIZE
        conn.execute("""
            DELETE FROM conversations WHERE user_id=? AND id NOT IN (
                SELECT id FROM conversations WHERE user_id=? ORDER BY id DESC LIMIT ?
            )
        """, (str(user_id), str(user_id), MAX_MEMORY_SIZE))
        conn.commit()
        conn.close()

    def get_user_data(self, user_id):
        conn = _get_conn()
        rows = conn.execute("SELECT key, value FROM user_data WHERE user_id=?", (str(user_id),)).fetchall()
        conn.close()
        result = {}
        for r in rows:
            try:
                result[r["key"]] = json.loads(r["value"])
            except (json.JSONDecodeError, TypeError):
                result[r["key"]] = r["value"]
        return result

    def set_user_data(self, user_id, key, value):
        conn = _get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO user_data (user_id, key, value) VALUES (?,?,?)",
            (str(user_id), key, json.dumps(value))
        )
        conn.commit()
        conn.close()

    def get_conversation_context(self, user_id):
        conv = self.get_conversation(user_id)
        return [{"role": m["role"], "content": m["content"]} for m in conv]

    def get_timezone(self, user_id):
        return self.get_user_data(user_id).get("timezone")

    def set_timezone(self, user_id, timezone):
        self.set_user_data(user_id, "timezone", timezone)

    def clear_conversation(self, user_id):
        conn = _get_conn()
        conn.execute("DELETE FROM conversations WHERE user_id=?", (str(user_id),))
        conn.commit()
        conn.close()
