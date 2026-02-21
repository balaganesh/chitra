from __future__ import annotations

"""
Reminders & Alarms capability.

Time-based triggers. When a reminder fires, the proactive loop picks it up
and surfaces it conversationally.

Actions:
    create(reminder) — create a new reminder
    get_fired() — reminders whose trigger_at has passed and status is pending
    dismiss(id) — mark a reminder as dismissed
    list_upcoming(hours_ahead) — pending reminders due within N hours
    delete(id) — delete a reminder
"""

import logging
import sqlite3
import uuid
from datetime import datetime, timedelta

from storage.schema import REMINDERS_SCHEMA

logger = logging.getLogger(__name__)


class Reminders:
    """Manages time-based reminders and alarms."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Ensure the reminders table exists."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(REMINDERS_SCHEMA)
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            logger.error("Failed to initialize reminders database: %s", e)

    def _get_conn(self) -> sqlite3.Connection:
        """Return a connection with row factory for dict-like access."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _row_to_dict(self, row: sqlite3.Row) -> dict:
        """Convert a sqlite3.Row to a plain dict."""
        return {
            "id": row["id"],
            "text": row["text"],
            "trigger_at": row["trigger_at"],
            "repeat": row["repeat"],
            "status": row["status"],
            "contact_id": row["contact_id"],
        }

    async def create(self, reminder: dict) -> dict:
        """Create a new reminder. ID is auto-generated.

        Required fields: text, trigger_at (ISO datetime string)
        Optional fields: repeat, contact_id
        """
        try:
            text = reminder.get("text")
            trigger_at = reminder.get("trigger_at")

            if not all([text, trigger_at]):
                return {"error": "Missing required fields: text, trigger_at"}

            reminder_id = str(uuid.uuid4())

            conn = self._get_conn()
            conn.execute(
                """INSERT INTO reminders
                   (id, text, trigger_at, repeat, status, contact_id)
                   VALUES (?, ?, ?, ?, 'pending', ?)""",
                (
                    reminder_id,
                    text,
                    trigger_at,
                    reminder.get("repeat"),
                    reminder.get("contact_id"),
                ),
            )
            conn.commit()

            row = conn.execute("SELECT * FROM reminders WHERE id = ?", (reminder_id,)).fetchone()
            conn.close()

            result = self._row_to_dict(row)
            logger.info("Created reminder: %s at %s", text, trigger_at)
            return result

        except sqlite3.Error as e:
            logger.error("Failed to create reminder: %s", e)
            return {"error": f"Storage failure: {e}"}

    async def get_fired(self) -> list[dict]:
        """Return reminders whose trigger_at has passed and status is pending.

        Called by the proactive loop on every tick.
        """
        try:
            now = datetime.now().isoformat()

            conn = self._get_conn()
            rows = conn.execute(
                """SELECT * FROM reminders
                   WHERE status = 'pending'
                   AND trigger_at <= ?
                   ORDER BY trigger_at ASC""",
                (now,),
            ).fetchall()
            conn.close()

            results = [self._row_to_dict(row) for row in rows]
            if results:
                logger.info("Fired reminders: %d", len(results))
            return results

        except sqlite3.Error as e:
            logger.error("Failed to get fired reminders: %s", e)
            return []

    async def dismiss(self, reminder_id: str) -> dict:
        """Mark a reminder as dismissed after it has been surfaced to the user."""
        try:
            conn = self._get_conn()

            row = conn.execute("SELECT * FROM reminders WHERE id = ?", (reminder_id,)).fetchone()
            if row is None:
                conn.close()
                return {"error": f"Reminder not found: {reminder_id}"}

            conn.execute(
                "UPDATE reminders SET status = 'dismissed' WHERE id = ?",
                (reminder_id,),
            )
            conn.commit()

            row = conn.execute("SELECT * FROM reminders WHERE id = ?", (reminder_id,)).fetchone()
            conn.close()

            result = self._row_to_dict(row)
            logger.info("Dismissed reminder: %s", reminder_id)
            return result

        except sqlite3.Error as e:
            logger.error("Failed to dismiss reminder %s: %s", reminder_id, e)
            return {"error": f"Dismiss failure: {e}"}

    async def list_upcoming(self, hours_ahead: int) -> list[dict]:
        """Return pending reminders due within N hours."""
        try:
            now = datetime.now()
            cutoff = (now + timedelta(hours=hours_ahead)).isoformat()

            conn = self._get_conn()
            rows = conn.execute(
                """SELECT * FROM reminders
                   WHERE status = 'pending'
                   AND trigger_at >= ?
                   AND trigger_at <= ?
                   ORDER BY trigger_at ASC""",
                (now.isoformat(), cutoff),
            ).fetchall()
            conn.close()

            return [self._row_to_dict(row) for row in rows]

        except sqlite3.Error as e:
            logger.error("Failed to list upcoming reminders: %s", e)
            return []

    async def delete(self, reminder_id: str) -> dict:
        """Delete a reminder permanently."""
        try:
            conn = self._get_conn()

            row = conn.execute("SELECT * FROM reminders WHERE id = ?", (reminder_id,)).fetchone()
            if row is None:
                conn.close()
                return {"error": f"Reminder not found: {reminder_id}"}

            conn.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
            conn.commit()
            conn.close()

            logger.info("Deleted reminder: %s", reminder_id)
            return {"status": "deleted"}

        except sqlite3.Error as e:
            logger.error("Failed to delete reminder %s: %s", reminder_id, e)
            return {"error": f"Delete failure: {e}"}
