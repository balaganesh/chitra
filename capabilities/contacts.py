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
import sqlite3
import uuid
from datetime import datetime, timedelta

from storage.schema import CONTACTS_SCHEMA

logger = logging.getLogger(__name__)

# Fields that can be set on a contact
VALID_FIELDS = {
    "name", "relationship", "phone", "email",
    "notes", "last_interaction", "communication_preference",
}


class Contacts:
    """Manages the local contact store."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Ensure the contacts table exists."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(CONTACTS_SCHEMA)
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            logger.error("Failed to initialize contacts database: %s", e)

    def _get_conn(self) -> sqlite3.Connection:
        """Return a connection with row factory for dict-like access."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _row_to_dict(self, row: sqlite3.Row) -> dict:
        """Convert a sqlite3.Row to a plain dict."""
        return {
            "id": row["id"],
            "name": row["name"],
            "relationship": row["relationship"],
            "phone": row["phone"],
            "email": row["email"],
            "notes": row["notes"],
            "last_interaction": row["last_interaction"],
            "communication_preference": row["communication_preference"],
        }

    async def get(self, name: str) -> dict | None:
        """Find a contact by name or partial name (case-insensitive).

        Returns the first matching contact, or None if not found.
        """
        try:
            conn = self._get_conn()
            row = conn.execute(
                "SELECT * FROM contacts WHERE name LIKE ? COLLATE NOCASE",
                (f"%{name}%",),
            ).fetchone()
            conn.close()

            if row is None:
                return None
            return self._row_to_dict(row)

        except sqlite3.Error as e:
            logger.error("Failed to get contact '%s': %s", name, e)
            return None

    async def list(self) -> list[dict]:
        """Return all contacts, ordered by name."""
        try:
            conn = self._get_conn()
            rows = conn.execute("SELECT * FROM contacts ORDER BY name").fetchall()
            conn.close()
            return [self._row_to_dict(row) for row in rows]

        except sqlite3.Error as e:
            logger.error("Failed to list contacts: %s", e)
            return []

    async def create(self, contact: dict) -> dict:
        """Create a new contact. ID is auto-generated.

        Required fields: name
        Optional fields: relationship, phone, email, notes, communication_preference
        """
        try:
            name = contact.get("name")
            if not name:
                return {"error": "Missing required field: name"}

            contact_id = str(uuid.uuid4())
            now = datetime.now().date().isoformat()

            conn = self._get_conn()
            conn.execute(
                """INSERT INTO contacts
                   (id, name, relationship, phone, email, notes, last_interaction, communication_preference)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    contact_id,
                    name,
                    contact.get("relationship"),
                    contact.get("phone"),
                    contact.get("email"),
                    contact.get("notes", ""),
                    now,
                    contact.get("communication_preference", ""),
                ),
            )
            conn.commit()

            row = conn.execute("SELECT * FROM contacts WHERE id = ?", (contact_id,)).fetchone()
            conn.close()

            result = self._row_to_dict(row)
            logger.info("Created contact: %s", name)
            return result

        except sqlite3.Error as e:
            logger.error("Failed to create contact: %s", e)
            return {"error": f"Storage failure: {e}"}

    async def update(self, contact_id: str, fields: dict) -> dict:
        """Update specific fields on an existing contact.

        Only fields in VALID_FIELDS are accepted.
        """
        try:
            # Filter to valid fields only
            updates = {k: v for k, v in fields.items() if k in VALID_FIELDS}
            if not updates:
                return {"error": "No valid fields to update"}

            conn = self._get_conn()

            # Check contact exists
            row = conn.execute("SELECT * FROM contacts WHERE id = ?", (contact_id,)).fetchone()
            if row is None:
                conn.close()
                return {"error": f"Contact not found: {contact_id}"}

            # Build dynamic UPDATE
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            values = [*list(updates.values()), contact_id]
            conn.execute(f"UPDATE contacts SET {set_clause} WHERE id = ?", values)
            conn.commit()

            row = conn.execute("SELECT * FROM contacts WHERE id = ?", (contact_id,)).fetchone()
            conn.close()

            result = self._row_to_dict(row)
            logger.info("Updated contact: %s", contact_id)
            return result

        except sqlite3.Error as e:
            logger.error("Failed to update contact %s: %s", contact_id, e)
            return {"error": f"Update failure: {e}"}

    async def note_interaction(self, contact_id: str) -> dict:
        """Update last_interaction date to now."""
        try:
            conn = self._get_conn()
            now = datetime.now().date().isoformat()

            row = conn.execute("SELECT * FROM contacts WHERE id = ?", (contact_id,)).fetchone()
            if row is None:
                conn.close()
                return {"error": f"Contact not found: {contact_id}"}

            conn.execute(
                "UPDATE contacts SET last_interaction = ? WHERE id = ?",
                (now, contact_id),
            )
            conn.commit()

            row = conn.execute("SELECT * FROM contacts WHERE id = ?", (contact_id,)).fetchone()
            conn.close()

            result = self._row_to_dict(row)
            logger.info("Noted interaction with: %s", result["name"])
            return result

        except sqlite3.Error as e:
            logger.error("Failed to note interaction for %s: %s", contact_id, e)
            return {"error": f"Update failure: {e}"}

    async def get_neglected(self, days_threshold: int) -> list[dict]:
        """Return contacts whose last_interaction is older than threshold.

        Used by the proactive loop to surface neglected relationships.
        """
        try:
            cutoff = (datetime.now().date() - timedelta(days=days_threshold)).isoformat()

            conn = self._get_conn()
            rows = conn.execute(
                """SELECT * FROM contacts
                   WHERE last_interaction IS NOT NULL
                   AND last_interaction < ?
                   ORDER BY last_interaction ASC""",
                (cutoff,),
            ).fetchall()
            conn.close()

            results = [self._row_to_dict(row) for row in rows]
            logger.info("Neglected contacts (>%d days): %d found", days_threshold, len(results))
            return results

        except sqlite3.Error as e:
            logger.error("Failed to get neglected contacts: %s", e)
            return []
