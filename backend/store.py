"""Reads and writes for saved locations and the alerts raised against them."""

import json
import sqlite3

from backend import db
from backend.alerts.messages import render_all

LOCATION_COLUMNS = (
    "id, label, name, region, country, latitude, longitude, timezone, "
    "units, language, created_at"
)


class DuplicateLocation(Exception):
    pass


class LocationMissing(Exception):
    pass


# --- locations -------------------------------------------------------------


async def list_locations(conn: sqlite3.Connection) -> list[dict]:
    def query(c):
        return db.rows_to_dicts(
            c.execute(f"SELECT {LOCATION_COLUMNS} FROM locations ORDER BY id").fetchall()
        )

    return await db.run(conn, query)


async def get_location(conn: sqlite3.Connection, location_id: int) -> dict:
    def query(c):
        row = c.execute(
            f"SELECT {LOCATION_COLUMNS} FROM locations WHERE id = ?", (location_id,)
        ).fetchone()
        if row is None:
            raise LocationMissing(f"No saved location with id {location_id}")
        return dict(row)

    return await db.run(conn, query)


async def add_location(
    conn: sqlite3.Connection,
    *,
    label: str,
    place: dict,
    units: str = "metric",
    language: str = "en",
) -> dict:
    """`place` is the geocoder's resolved location summary."""

    def insert(c):
        try:
            with c:
                cursor = c.execute(
                    """INSERT INTO locations
                       (label, name, region, country, latitude, longitude,
                        timezone, units, language)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        label,
                        place["name"],
                        place.get("region"),
                        place.get("country"),
                        place["latitude"],
                        place["longitude"],
                        place.get("timezone"),
                        units,
                        language,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise DuplicateLocation(f"{place['name']} is already saved") from exc
        row = c.execute(
            f"SELECT {LOCATION_COLUMNS} FROM locations WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        return dict(row)

    return await db.run(conn, insert)


async def delete_location(conn: sqlite3.Connection, location_id: int) -> None:
    def remove(c):
        with c:
            cursor = c.execute("DELETE FROM locations WHERE id = ?", (location_id,))
        if cursor.rowcount == 0:
            raise LocationMissing(f"No saved location with id {location_id}")

    await db.run(conn, remove)


# --- alerts ----------------------------------------------------------------


async def save_alerts(
    conn: sqlite3.Connection, location_id: int, alerts: list[dict]
) -> int:
    """Insert alerts, skipping any fingerprint already stored. Returns new count."""
    from backend.alerts.rules import fingerprint

    def insert(c):
        added = 0
        with c:
            for alert in alerts:
                cursor = c.execute(
                    """INSERT OR IGNORE INTO alerts
                       (location_id, fingerprint, code, severity, date, params)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        location_id,
                        fingerprint(location_id, alert),
                        alert["code"],
                        alert["severity"],
                        alert["date"],
                        json.dumps(alert, ensure_ascii=False),
                    ),
                )
                added += cursor.rowcount
        return added

    return await db.run(conn, insert)


async def list_alerts(
    conn: sqlite3.Connection,
    *,
    language: str = "en",
    unacknowledged_only: bool = False,
    limit: int = 50,
) -> list[dict]:
    clause = "WHERE a.acknowledged = 0" if unacknowledged_only else ""

    def query(c):
        return c.execute(
            f"""SELECT a.id, a.location_id, a.code, a.severity, a.date,
                       a.params, a.acknowledged, a.created_at, l.label AS location_label
                FROM alerts a
                JOIN locations l ON l.id = a.location_id
                {clause}
                ORDER BY a.date ASC, a.id DESC
                LIMIT ?""",
            (limit,),
        ).fetchall()

    rows = await db.run(conn, query)

    alerts = []
    for row in rows:
        stored = json.loads(row["params"])
        alerts.append(
            {
                **stored,
                "id": row["id"],
                "location_id": row["location_id"],
                "location_label": row["location_label"],
                "acknowledged": bool(row["acknowledged"]),
                "created_at": row["created_at"],
            }
        )
    return render_all(alerts, language)


async def acknowledge_alert(conn: sqlite3.Connection, alert_id: int) -> None:
    def update(c):
        with c:
            cursor = c.execute(
                "UPDATE alerts SET acknowledged = 1 WHERE id = ?", (alert_id,)
            )
        if cursor.rowcount == 0:
            raise LocationMissing(f"No alert with id {alert_id}")

    await db.run(conn, update)
