from __future__ import annotations

"""
Calendar capability.

Local store of events and schedule. Chitra references this to understand
what the user has coming up and surface relevant context proactively.

Actions:
    get_upcoming(hours_ahead) — events within the next N hours
    get_today() — all events for today
    create(event) — create a new calendar event
    get_range(start_date, end_date) — events within a date range
"""

import json
import logging
import sqlite3
import uuid
from datetime import datetime, timedelta

from storage.schema import CALENDAR_SCHEMA

logger = logging.getLogger(__name__)


class Calendar:
    """Manages the local calendar store."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Ensure the events table exists."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(CALENDAR_SCHEMA)
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            logger.error("Failed to initialize calendar database: %s", e)

    def _get_conn(self) -> sqlite3.Connection:
        """Return a connection with row factory for dict-like access."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _row_to_dict(self, row: sqlite3.Row) -> dict:
        """Convert a sqlite3.Row to a plain dict."""
        participants = row["participants"]
        # participants is stored as JSON string
        try:
            participants = json.loads(participants)
        except (json.JSONDecodeError, TypeError):
            participants = []

        return {
            "id": row["id"],
            "title": row["title"],
            "date": row["date"],
            "time": row["time"],
            "duration_minutes": row["duration_minutes"],
            "notes": row["notes"],
            "participants": participants,
        }

    async def get_upcoming(self, hours_ahead: int) -> list[dict]:
        """Return events scheduled within the next N hours.

        Compares event date+time against current time through current time + hours_ahead.
        """
        try:
            now = datetime.now()
            cutoff = now + timedelta(hours=hours_ahead)

            now_str = now.strftime("%Y-%m-%d %H:%M")
            cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M")

            conn = self._get_conn()
            rows = conn.execute(
                """SELECT * FROM events
                   WHERE (date || ' ' || time) >= ?
                   AND (date || ' ' || time) <= ?
                   ORDER BY date, time""",
                (now_str, cutoff_str),
            ).fetchall()
            conn.close()

            return [self._row_to_dict(row) for row in rows]

        except sqlite3.Error as e:
            logger.error("Failed to get upcoming events: %s", e)
            return []

    async def get_today(self) -> list[dict]:
        """Return all events for today, ordered by time."""
        try:
            today = datetime.now().date().isoformat()

            conn = self._get_conn()
            rows = conn.execute(
                "SELECT * FROM events WHERE date = ? ORDER BY time",
                (today,),
            ).fetchall()
            conn.close()

            return [self._row_to_dict(row) for row in rows]

        except sqlite3.Error as e:
            logger.error("Failed to get today's events: %s", e)
            return []

    async def create(self, event: dict) -> dict:
        """Create a new calendar event. ID is auto-generated.

        Required fields: title, date, time
        Optional fields: duration_minutes (default 60), notes, participants
        """
        try:
            title = event.get("title")
            date = event.get("date")
            time = event.get("time")

            if not all([title, date, time]):
                return {"error": "Missing required fields: title, date, time"}

            event_id = str(uuid.uuid4())
            duration = event.get("duration_minutes", 60)
            notes = event.get("notes", "")
            participants = json.dumps(event.get("participants", []))

            conn = self._get_conn()
            conn.execute(
                """INSERT INTO events
                   (id, title, date, time, duration_minutes, notes, participants)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (event_id, title, date, time, duration, notes, participants),
            )
            conn.commit()

            row = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
            conn.close()

            result = self._row_to_dict(row)
            logger.info("Created event: %s on %s at %s", title, date, time)
            return result

        except sqlite3.Error as e:
            logger.error("Failed to create event: %s", e)
            return {"error": f"Storage failure: {e}"}

    async def get_range(self, start_date: str, end_date: str) -> list[dict]:
        """Return events within a date range (inclusive), ordered by date and time."""
        try:
            conn = self._get_conn()
            rows = conn.execute(
                """SELECT * FROM events
                   WHERE date >= ? AND date <= ?
                   ORDER BY date, time""",
                (start_date, end_date),
            ).fetchall()
            conn.close()

            return [self._row_to_dict(row) for row in rows]

        except sqlite3.Error as e:
            logger.error("Failed to get events in range: %s", e)
            return []
