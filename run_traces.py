"""
Dashboard-only run tracing for operator observability.
"""
import json
import os
import sqlite3
import uuid
from contextvars import ContextVar
from datetime import datetime

DB_FILE = os.path.join(os.path.dirname(__file__), "ninoclaw.db")
_CURRENT_RUN_ID = ContextVar("current_run_id", default=None)


def _utc_now():
    return datetime.utcnow().isoformat(timespec="seconds")


def _get_conn():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    conn = _get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS runs (
            id            TEXT PRIMARY KEY,
            user_id       TEXT NOT NULL,
            channel       TEXT NOT NULL,
            user_message  TEXT NOT NULL,
            started_at    TEXT NOT NULL,
            finished_at   TEXT,
            status        TEXT NOT NULL DEFAULT 'running',
            final_response TEXT,
            error         TEXT,
            total_ms      INTEGER,
            model_calls   INTEGER NOT NULL DEFAULT 0,
            tool_calls    INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS run_events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id      TEXT NOT NULL,
            seq         INTEGER NOT NULL,
            ts          TEXT NOT NULL,
            event_type  TEXT NOT NULL,
            label       TEXT,
            payload     TEXT,
            FOREIGN KEY(run_id) REFERENCES runs(id)
        );
        CREATE INDEX IF NOT EXISTS idx_runs_started_at ON runs(started_at DESC);
        CREATE INDEX IF NOT EXISTS idx_runs_user_id ON runs(user_id);
        CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
        CREATE INDEX IF NOT EXISTS idx_run_events_run_id_seq ON run_events(run_id, seq);
        """
    )
    conn.commit()
    conn.close()


def _sanitize_text(value, limit=4000):
    if value is None:
        return None
    text = str(value)
    if len(text) > limit:
        return text[:limit] + "..."
    return text


def _safe_payload(payload):
    if payload is None:
        return None
    try:
        if isinstance(payload, str):
            return _sanitize_text(payload, limit=4000)
        return json.dumps(payload, ensure_ascii=False)[:4000]
    except Exception:
        return _sanitize_text(payload, limit=4000)


def set_current_run(run_id):
    _CURRENT_RUN_ID.set(run_id)


def get_current_run_id():
    return _CURRENT_RUN_ID.get()


def clear_current_run():
    _CURRENT_RUN_ID.set(None)


def start_run(user_id, channel, user_message):
    _init_db()
    run_id = uuid.uuid4().hex
    conn = _get_conn()
    conn.execute(
        """
        INSERT INTO runs (id, user_id, channel, user_message, started_at, status)
        VALUES (?, ?, ?, ?, ?, 'running')
        """,
        (run_id, str(user_id), channel, _sanitize_text(user_message, limit=8000) or "", _utc_now()),
    )
    conn.commit()
    conn.close()
    set_current_run(run_id)
    log_event("run_started", payload={"channel": channel})
    return run_id


def _next_seq(conn, run_id):
    row = conn.execute("SELECT COALESCE(MAX(seq), 0) AS seq FROM run_events WHERE run_id=?", (run_id,)).fetchone()
    return int(row["seq"]) + 1 if row else 1


def log_event(event_type, label=None, payload=None, run_id=None):
    run_id = run_id or get_current_run_id()
    if not run_id:
        return
    try:
        conn = _get_conn()
        seq = _next_seq(conn, run_id)
        conn.execute(
            """
            INSERT INTO run_events (run_id, seq, ts, event_type, label, payload)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (run_id, seq, _utc_now(), event_type, _sanitize_text(label, 500), _safe_payload(payload)),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def increment_run_counter(counter_name, amount=1, run_id=None):
    run_id = run_id or get_current_run_id()
    if not run_id or counter_name not in {"model_calls", "tool_calls"}:
        return
    try:
        conn = _get_conn()
        conn.execute(f"UPDATE runs SET {counter_name} = COALESCE({counter_name}, 0) + ? WHERE id=?", (amount, run_id))
        conn.commit()
        conn.close()
    except Exception:
        pass


def finish_run(final_response=None, status="completed", error=None, run_id=None):
    run_id = run_id or get_current_run_id()
    if not run_id:
        return
    try:
        conn = _get_conn()
        row = conn.execute("SELECT started_at FROM runs WHERE id=?", (run_id,)).fetchone()
        total_ms = None
        if row and row["started_at"]:
            try:
                started = datetime.fromisoformat(row["started_at"])
                total_ms = int((datetime.utcnow() - started).total_seconds() * 1000)
            except Exception:
                total_ms = None
        conn.execute(
            """
            UPDATE runs
            SET finished_at=?, status=?, final_response=?, error=?, total_ms=?
            WHERE id=?
            """,
            (
                _utc_now(),
                status,
                _sanitize_text(final_response, limit=12000),
                _sanitize_text(error, limit=4000),
                total_ms,
                run_id,
            ),
        )
        conn.commit()
        conn.close()
        log_event("run_finished", payload={"status": status, "error": error})
    except Exception:
        pass


def list_runs(limit=200, status=None, channel=None, user_id=None):
    _init_db()
    conn = _get_conn()
    where = []
    params = []
    if status:
        where.append("status=?")
        params.append(status)
    if channel:
        where.append("channel=?")
        params.append(channel)
    if user_id:
        where.append("user_id=?")
        params.append(str(user_id))
    sql = "SELECT * FROM runs"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY started_at DESC LIMIT ?"
    params.append(int(limit))
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_run(run_id):
    _init_db()
    conn = _get_conn()
    row = conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_run_events(run_id):
    _init_db()
    conn = _get_conn()
    rows = conn.execute(
        "SELECT seq, ts, event_type, label, payload FROM run_events WHERE run_id=? ORDER BY seq ASC",
        (run_id,),
    ).fetchall()
    conn.close()
    out = []
    for row in rows:
        item = dict(row)
        payload = item.get("payload")
        if payload:
            try:
                item["payload_json"] = json.loads(payload)
            except Exception:
                item["payload_json"] = None
        else:
            item["payload_json"] = None
        out.append(item)
    return out


def summarize_runs(limit=500):
    runs = list_runs(limit=limit)
    summary = {
        "total": len(runs),
        "running": 0,
        "completed": 0,
        "error": 0,
        "avg_ms": 0,
    }
    durations = []
    for run in runs:
        status = run.get("status") or "unknown"
        if status in summary:
            summary[status] += 1
        elif status == "failed":
            summary["error"] += 1
        total_ms = run.get("total_ms")
        if isinstance(total_ms, int):
            durations.append(total_ms)
    if durations:
        summary["avg_ms"] = int(sum(durations) / len(durations))
    return summary


