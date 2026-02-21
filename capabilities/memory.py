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
"""

import logging

logger = logging.getLogger(__name__)


class Memory:
    """The personal knowledge layer. Makes Chitra feel like it knows you."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    async def store(self, entry: dict) -> dict:
        """Save a new memory entry. ID is auto-generated."""
        raise NotImplementedError

    async def get_context(self) -> dict:
        """Return all relevant memory formatted as a context block for LLM injection.

        Returns:
            {"context_block": str} — structured natural language, not raw JSON
        """
        raise NotImplementedError

    async def search(self, query: str) -> list[dict]:
        """Return memory entries relevant to a topic or subject."""
        raise NotImplementedError

    async def update(self, memory_id: str, content: str) -> dict:
        """Update an existing memory entry."""
        raise NotImplementedError

    async def deactivate(self, memory_id: str) -> dict:
        """Soft delete — sets active to false. Never injected into context again."""
        raise NotImplementedError
