from __future__ import annotations

"""
Contacts capability.

Local store of people the user knows. Chitra references this to understand
who the user is talking about and surface relationship context.

Actions:
    get(name) — find contact by name or partial name
    list() — return all contacts
    create(contact) — create a new contact
    update(id, fields) — update specific fields on a contact
    note_interaction(id) — update last_interaction to now
    get_neglected(days_threshold) — contacts not interacted with recently
"""

import logging

logger = logging.getLogger(__name__)


class Contacts:
    """Manages the local contact store."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    async def get(self, name: str) -> dict | None:
        """Find a contact by name or partial name."""
        raise NotImplementedError

    async def list(self) -> list[dict]:
        """Return all contacts."""
        raise NotImplementedError

    async def create(self, contact: dict) -> dict:
        """Create a new contact. ID is auto-generated."""
        raise NotImplementedError

    async def update(self, contact_id: str, fields: dict) -> dict:
        """Update specific fields on an existing contact."""
        raise NotImplementedError

    async def note_interaction(self, contact_id: str) -> dict:
        """Update last_interaction date to now."""
        raise NotImplementedError

    async def get_neglected(self, days_threshold: int) -> list[dict]:
        """Return contacts whose last_interaction is older than threshold."""
        raise NotImplementedError
