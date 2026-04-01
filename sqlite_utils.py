"""
Shared SQLite helpers for Ninoclaw.
"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_DB_FILE = ROOT_DIR / "ninoclaw.db"
BACKUP_DIR = ROOT_DIR / "backups"


def connect_db(db_path=None):
    path = Path(db_path or DEFAULT_DB_FILE)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def maybe_backup_database(db_path=None, keep=7):
    path = Path(db_path or DEFAULT_DB_FILE)
    if not path.exists():
        return None

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%d")
    backup_path = BACKUP_DIR / f"{path.stem}-{stamp}.sqlite3"
    if backup_path.exists():
        return backup_path

    src = sqlite3.connect(path)
    try:
        dst = sqlite3.connect(backup_path)
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()

    backups = sorted(BACKUP_DIR.glob(f"{path.stem}-*.sqlite3"))
    if len(backups) > keep:
        for old in backups[:-keep]:
            try:
                old.unlink()
            except OSError:
                pass
    return backup_path
