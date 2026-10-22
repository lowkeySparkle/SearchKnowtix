"""SQLite storage for SearchKnowtix research runs (standard library only).

Provides what app.py imports: init_db(), save_run(run), get_all_runs().
The database file is created next to this file as searchknowtix.db.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "searchknowtix.db"


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _connect() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS runs (
                   id TEXT PRIMARY KEY,
                   topic TEXT NOT NULL,
                   started_at TEXT NOT NULL,
                   duration REAL,
                   status TEXT NOT NULL,
                   state_json TEXT,
                   events_json TEXT,
                   error TEXT
               )"""
        )


def save_run(run):
    started = run.get("started_at")
    if isinstance(started, datetime):
        started = started.isoformat()
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO runs "
            "(id, topic, started_at, duration, status, state_json, events_json, error) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                run["id"],
                run["topic"],
                started,
                run.get("duration"),
                run["status"],
                json.dumps(run.get("state") or {}, default=str),
                json.dumps(run.get("events") or [], default=str),
                run.get("error"),
            ),
        )


def get_all_runs():
    """All saved runs, oldest first, in the same shape app.py creates them."""
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM runs ORDER BY started_at ASC").fetchall()
    runs = []
    for r in rows:
        runs.append(
            {
                "id": r["id"],
                "topic": r["topic"],
                "started_at": datetime.fromisoformat(r["started_at"]),
                "duration": r["duration"] or 0,
                "status": r["status"],
                "state": json.loads(r["state_json"] or "{}"),
                "events": json.loads(r["events_json"] or "[]"),
                "error": r["error"],
            }
        )
    return runs