"""SQLite persistence.

sqlite3 is blocking, so every call runs in a worker thread via asyncio.to_thread.
That keeps the dependency list at zero extra packages and is more than fast
enough for a handful of saved locations.
"""

import asyncio
import sqlite3
from pathlib import Path
from typing import Any, Callable

from backend import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS locations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    label       TEXT    NOT NULL,
    name        TEXT    NOT NULL,
    region      TEXT,
    country     TEXT,
    latitude    REAL    NOT NULL,
    longitude   REAL    NOT NULL,
    timezone    TEXT,
    units       TEXT    NOT NULL DEFAULT 'metric',
    language    TEXT    NOT NULL DEFAULT 'en',
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE (latitude, longitude)
);

CREATE TABLE IF NOT EXISTS alerts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    location_id  INTEGER NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
    fingerprint  TEXT    NOT NULL UNIQUE,
    code         TEXT    NOT NULL,
    severity     TEXT    NOT NULL,
    date         TEXT    NOT NULL,
    params       TEXT    NOT NULL,
    acknowledged INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_alerts_location ON alerts(location_id);
CREATE INDEX IF NOT EXISTS idx_alerts_date ON alerts(date);
"""


def connect(path: str | None = None) -> sqlite3.Connection:
    db_path = path or config.DATABASE_PATH
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init(conn: sqlite3.Connection) -> None:
    with conn:
        conn.executescript(SCHEMA)


async def run(conn: sqlite3.Connection, fn: Callable[[sqlite3.Connection], Any]) -> Any:
    """Run a blocking sqlite function off the event loop."""
    return await asyncio.to_thread(fn, conn)


def rows_to_dicts(rows) -> list[dict]:
    return [dict(row) for row in rows]
