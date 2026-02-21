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

import logging

logger = logging.getLogger(__name__)


class Calendar:
    """Manages the local calendar store."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    async def get_upcoming(self, hours_ahead: int) -> list[dict]:
        """Return events scheduled within the next N hours."""
        raise NotImplementedError

    async def get_today(self) -> list[dict]:
        """Return all events for today."""
        raise NotImplementedError

    async def create(self, event: dict) -> dict:
        """Create a new calendar event. ID is auto-generated."""
        raise NotImplementedError

    async def get_range(self, start_date: str, end_date: str) -> list[dict]:
        """Return events within a date range."""
        raise NotImplementedError
