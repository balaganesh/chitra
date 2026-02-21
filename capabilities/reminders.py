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

logger = logging.getLogger(__name__)


class Reminders:
    """Manages time-based reminders and alarms."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    async def create(self, reminder: dict) -> dict:
        """Create a new reminder. ID is auto-generated."""
        raise NotImplementedError

    async def get_fired(self) -> list[dict]:
        """Return reminders whose trigger_at has passed and status is pending."""
        raise NotImplementedError

    async def dismiss(self, reminder_id: str) -> dict:
        """Mark a reminder as dismissed after it has been surfaced."""
        raise NotImplementedError

    async def list_upcoming(self, hours_ahead: int) -> list[dict]:
        """Return pending reminders due within N hours."""
        raise NotImplementedError

    async def delete(self, reminder_id: str) -> dict:
        """Delete a reminder."""
        raise NotImplementedError
