"""Background polling: check every saved location, store anything new.

This is what makes alerts *proactive* rather than something the user has to ask
for. One pass is also exposed directly so the UI can force a refresh during a
demo instead of waiting for the next tick.
"""

import asyncio
import logging
import sqlite3
from datetime import datetime, timezone

import httpx

from backend import config, store
from backend.tools.alerts import check_alerts

log = logging.getLogger("alerts")


class AlertScheduler:
    def __init__(
        self,
        conn: sqlite3.Connection,
        http: httpx.AsyncClient,
        *,
        interval_minutes: int | None = None,
        lookahead_days: int | None = None,
    ):
        self.conn = conn
        self.http = http
        self.interval = (interval_minutes or config.ALERT_POLL_MINUTES) * 60
        self.lookahead = lookahead_days or config.ALERT_LOOKAHEAD_DAYS
        self.last_run_at: str | None = None
        self.last_error: str | None = None
        self._task: asyncio.Task | None = None

    async def run_once(self) -> dict:
        """One pass over every saved location. Never raises."""
        checked, new_alerts, failures = 0, 0, []

        for location in await store.list_locations(self.conn):
            query = f"{location['name']}, {location['country'] or ''}".strip(", ")
            try:
                result = await check_alerts(self.http, query, self.lookahead)
                new_alerts += await store.save_alerts(
                    self.conn, location["id"], result["alerts"]
                )
                checked += 1
            except Exception as exc:  # a bad location must not stop the others
                failures.append({"location": location["label"], "error": str(exc)})
                log.warning("Alert check failed for %s: %s", location["label"], exc)

        self.last_run_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.last_error = failures[0]["error"] if failures else None
        return {
            "locations_checked": checked,
            "new_alerts": new_alerts,
            "failures": failures,
            "ran_at": self.last_run_at,
        }

    async def _loop(self) -> None:
        while True:
            try:
                await self.run_once()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log.exception("Alert poll crashed: %s", exc)
            await asyncio.sleep(self.interval)

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._loop(), name="alert-poll")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    def status(self) -> dict:
        return {
            "running": self._task is not None and not self._task.done(),
            "interval_minutes": self.interval // 60,
            "lookahead_days": self.lookahead,
            "last_run_at": self.last_run_at,
            "last_error": self.last_error,
        }
