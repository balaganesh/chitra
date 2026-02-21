from __future__ import annotations

"""
Memory capability — the heart of Chitra.

Stores everything Chitra knows about the user: stated preferences, observed
patterns, relationship context, personal facts. Injected as context into
every LLM call so the model always knows the user.

Categories: preference, fact, observation, relationship
Sources: stated (confidence 1.0), inferred (0.5-0.9)

Actions:
    store(entry) — save a new memory entry
    get_context() — return formatted context block for LLM injection
    search(query) — return memory entries relevant to a topic
    update(id, content) — update an existing memory entry
    deactivate(id) — soft delete (never injected again, retained in storage)

Context window rules (from MEMORY_DESIGN.md):
    Always include: preferences, high-confidence facts (>=0.8), relationships referenced within 30 days
    Include if relevant: observations
    Never include: inactive entries, low-confidence observations (< 0.5) older than 60 days
"""

import logging
import sqlite3
import uuid
from datetime import datetime, timedelta

from storage.schema import MEMORY_SCHEMA

logger = logging.getLogger(__name__)


class Memory:
    """The personal knowledge layer. Makes Chitra feel like it knows you."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Ensure the memories table exists."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(MEMORY_SCHEMA)
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            logger.error("Failed to initialize memory database: %s", e)

    def _get_conn(self) -> sqlite3.Connection:
        """Return a connection with row factory for dict-like access."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _row_to_dict(self, row: sqlite3.Row) -> dict:
        """Convert a sqlite3.Row to a plain dict."""
        return {
            "id": row["id"],
            "category": row["category"],
            "subject": row["subject"],
            "content": row["content"],
            "confidence": row["confidence"],
            "source": row["source"],
            "contact_id": row["contact_id"],
            "created_at": row["created_at"],
            "last_referenced": row["last_referenced"],
            "active": bool(row["active"]),
        }

    async def store(self, entry: dict) -> dict:
        """Save a new memory entry. ID is auto-generated.

        Required fields: category, subject, content
        Optional fields: confidence (default 1.0), source (default "stated"), contact_id

        Returns the stored entry with generated id and timestamps.
        """
        try:
            memory_id = str(uuid.uuid4())
            now = datetime.now().isoformat()

            category = entry.get("category")
            subject = entry.get("subject")
            content = entry.get("content")

            if not all([category, subject, content]):
                return {"error": "Missing required fields: category, subject, content"}

            if category not in ("preference", "fact", "observation", "relationship"):
                return {"error": f"Invalid category: {category}"}

            confidence = entry.get("confidence", 1.0)
            source = entry.get("source", "stated")
            contact_id = entry.get("contact_id")

            if source not in ("stated", "inferred"):
                return {"error": f"Invalid source: {source}"}

            conn = self._get_conn()
            conn.execute(
                """INSERT INTO memories
                   (id, category, subject, content, confidence, source, contact_id, created_at, last_referenced, active)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                (memory_id, category, subject, content, confidence, source, contact_id, now, now),
            )
            conn.commit()

            row = conn.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
            conn.close()

            result = self._row_to_dict(row)
            logger.info("Stored memory: [%s] %s", category, subject)
            return result

        except sqlite3.Error as e:
            logger.error("Failed to store memory: %s", e)
            return {"error": f"Storage failure: {e}"}

    async def get_context(self) -> dict:
        """Return all relevant memory formatted as a context block for LLM injection.

        Applies context window rules from MEMORY_DESIGN.md:
        - Always include: all preferences, facts with confidence >= 0.8,
          relationships referenced within 30 days
        - Include: observations with confidence >= 0.5
        - Never include: inactive entries, low-confidence observations (< 0.5) older than 60 days

        Returns:
            {"context_block": str} — structured natural language, not raw JSON
        """
        try:
            conn = self._get_conn()
            now = datetime.now()
            thirty_days_ago = (now - timedelta(days=30)).isoformat()
            sixty_days_ago = (now - timedelta(days=60)).isoformat()

            # Fetch all active entries
            rows = conn.execute(
                "SELECT * FROM memories WHERE active = 1 ORDER BY category, created_at"
            ).fetchall()

            # Apply context window rules — only include entries that pass filters
            preferences = []
            facts = []
            relationships = []
            observations = []
            included_ids = []

            for row in rows:
                entry = self._row_to_dict(row)
                category = entry["category"]
                confidence = entry["confidence"]
                last_ref = entry["last_referenced"]

                if category == "preference":
                    # Always include all preferences
                    preferences.append(entry)
                    included_ids.append(entry["id"])

                elif category == "fact":
                    # Include facts with confidence >= 0.8
                    if confidence >= 0.8:
                        facts.append(entry)
                        included_ids.append(entry["id"])

                elif category == "relationship":
                    # Include relationships referenced within 30 days
                    if last_ref >= thirty_days_ago:
                        relationships.append(entry)
                        included_ids.append(entry["id"])

                elif category == "observation":
                    # Skip low-confidence observations older than 60 days
                    if confidence < 0.5 and entry["created_at"] < sixty_days_ago:
                        continue
                    # Include observations with confidence >= 0.5
                    if confidence >= 0.5:
                        observations.append(entry)
                        included_ids.append(entry["id"])

            # Update last_referenced ONLY for entries actually included
            # This ensures aging/recency rules work correctly — entries not
            # included will naturally age out over time
            if included_ids:
                placeholders = ",".join("?" for _ in included_ids)
                conn.execute(
                    f"UPDATE memories SET last_referenced = ? WHERE id IN ({placeholders})",
                    [now.isoformat()] + included_ids,
                )
                conn.commit()

            conn.close()

            # Build the context block as structured natural language
            context_block = self._format_context_block(preferences, facts, relationships, observations)

            return {"context_block": context_block}

        except sqlite3.Error as e:
            logger.error("Failed to assemble memory context: %s", e)
            return {"context_block": ""}

    def _format_context_block(
        self,
        preferences: list[dict],
        facts: list[dict],
        relationships: list[dict],
        observations: list[dict],
    ) -> str:
        """Format memory entries into a natural language context block.

        This is what the LLM reads as background knowledge about the user.
        """
        sections = []

        if preferences or facts:
            lines = ["About the user:"]
            for entry in facts:
                lines.append(f"- {entry['content']}")
            for entry in preferences:
                lines.append(f"- {entry['content']}")
            sections.append("\n".join(lines))

        if relationships:
            lines = ["People:"]
            for entry in relationships:
                lines.append(f"- {entry['content']}")
            sections.append("\n".join(lines))

        if observations:
            lines = ["Current patterns:"]
            for entry in observations:
                lines.append(f"- {entry['content']}")
            sections.append("\n".join(lines))

        return "\n\n".join(sections)

    async def search(self, query: str) -> list[dict]:
        """Return memory entries relevant to a topic or subject.

        Searches both subject and content fields for the query string.
        Only returns active entries.
        """
        try:
            conn = self._get_conn()
            rows = conn.execute(
                """SELECT * FROM memories
                   WHERE active = 1
                   AND (subject LIKE ? OR content LIKE ?)
                   ORDER BY confidence DESC, created_at DESC""",
                (f"%{query}%", f"%{query}%"),
            ).fetchall()
            conn.close()

            results = [self._row_to_dict(row) for row in rows]
            logger.info("Memory search '%s': %d results", query, len(results))
            return results

        except sqlite3.Error as e:
            logger.error("Memory search failed: %s", e)
            return []

    async def update(self, memory_id: str, content: str) -> dict:
        """Update an existing memory entry's content.

        Also updates last_referenced timestamp. If this is a user correction
        of an inferred memory, the caller should update confidence and source
        separately via a follow-up store or direct update.
        """
        try:
            conn = self._get_conn()
            now = datetime.now().isoformat()

            conn.execute(
                "UPDATE memories SET content = ?, last_referenced = ? WHERE id = ? AND active = 1",
                (content, now, memory_id),
            )
            conn.commit()

            row = conn.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
            conn.close()

            if row is None:
                return {"error": f"Memory not found: {memory_id}"}

            result = self._row_to_dict(row)
            logger.info("Updated memory: %s", memory_id)
            return result

        except sqlite3.Error as e:
            logger.error("Failed to update memory %s: %s", memory_id, e)
            return {"error": f"Update failure: {e}"}

    async def deactivate(self, memory_id: str) -> dict:
        """Soft delete — sets active to false. Never injected into context again.

        The entry is retained in storage but excluded from get_context() and search().
        """
        try:
            conn = self._get_conn()
            row = conn.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()

            if row is None:
                conn.close()
                return {"error": f"Memory not found: {memory_id}"}

            conn.execute("UPDATE memories SET active = 0 WHERE id = ?", (memory_id,))
            conn.commit()
            conn.close()

            logger.info("Deactivated memory: %s", memory_id)
            return {"status": "deactivated"}

        except sqlite3.Error as e:
            logger.error("Failed to deactivate memory %s: %s", memory_id, e)
            return {"error": f"Deactivation failure: {e}"}
