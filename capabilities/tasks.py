from __future__ import annotations

"""
Tasks capability.

Things the user needs to do. Chitra references tasks proactively
when the user has free time or when tasks are overdue.

Actions:
    create(task) — create a new task
    list(status) — return tasks filtered by status
    complete(id) — mark a task as done
    get_overdue() — pending tasks past their due date
    get_due_today() — pending tasks due today
"""

import logging

logger = logging.getLogger(__name__)


class Tasks:
    """Manages the local task store."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    async def create(self, task: dict) -> dict:
        """Create a new task. ID is auto-generated."""
        raise NotImplementedError

    async def list(self, status: str = "all") -> list[dict]:
        """Return tasks filtered by status (pending, done, all)."""
        raise NotImplementedError

    async def complete(self, task_id: str) -> dict:
        """Mark a task as done."""
        raise NotImplementedError

    async def get_overdue(self) -> list[dict]:
        """Return pending tasks past their due date."""
        raise NotImplementedError

    async def get_due_today(self) -> list[dict]:
        """Return pending tasks due today."""
        raise NotImplementedError
