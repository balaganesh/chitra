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
import sqlite3
import uuid
from datetime import datetime

from storage.schema import TASKS_SCHEMA

logger = logging.getLogger(__name__)


class Tasks:
    """Manages the local task store."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Ensure the tasks table exists."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(TASKS_SCHEMA)
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            logger.error("Failed to initialize tasks database: %s", e)

    def _get_conn(self) -> sqlite3.Connection:
        """Return a connection with row factory for dict-like access."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _row_to_dict(self, row: sqlite3.Row) -> dict:
        """Convert a sqlite3.Row to a plain dict."""
        return {
            "id": row["id"],
            "title": row["title"],
            "notes": row["notes"],
            "due_date": row["due_date"],
            "status": row["status"],
            "priority": row["priority"],
            "created_at": row["created_at"],
        }

    async def create(self, task: dict) -> dict:
        """Create a new task. ID is auto-generated.

        Required fields: title
        Optional fields: notes, due_date, priority (high/normal/low)
        """
        try:
            title = task.get("title")
            if not title:
                return {"error": "Missing required field: title"}

            task_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            priority = task.get("priority", "normal")

            if priority not in ("high", "normal", "low"):
                return {"error": f"Invalid priority: {priority}"}

            conn = self._get_conn()
            conn.execute(
                """INSERT INTO tasks
                   (id, title, notes, due_date, status, priority, created_at)
                   VALUES (?, ?, ?, ?, 'pending', ?, ?)""",
                (
                    task_id,
                    title,
                    task.get("notes", ""),
                    task.get("due_date"),
                    priority,
                    now,
                ),
            )
            conn.commit()

            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            conn.close()

            result = self._row_to_dict(row)
            logger.info("Created task: %s (priority: %s)", title, priority)
            return result

        except sqlite3.Error as e:
            logger.error("Failed to create task: %s", e)
            return {"error": f"Storage failure: {e}"}

    async def list(self, status: str = "all") -> list[dict]:
        """Return tasks filtered by status (pending, done, all)."""
        try:
            conn = self._get_conn()

            if status == "all":
                rows = conn.execute(
                    "SELECT * FROM tasks ORDER BY priority DESC, created_at DESC",
                ).fetchall()
            elif status in ("pending", "done"):
                rows = conn.execute(
                    "SELECT * FROM tasks WHERE status = ? ORDER BY priority DESC, created_at DESC",
                    (status,),
                ).fetchall()
            else:
                conn.close()
                return []

            conn.close()
            return [self._row_to_dict(row) for row in rows]

        except sqlite3.Error as e:
            logger.error("Failed to list tasks: %s", e)
            return []

    async def complete(self, task_id: str) -> dict:
        """Mark a task as done."""
        try:
            conn = self._get_conn()

            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            if row is None:
                conn.close()
                return {"error": f"Task not found: {task_id}"}

            conn.execute("UPDATE tasks SET status = 'done' WHERE id = ?", (task_id,))
            conn.commit()

            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            conn.close()

            result = self._row_to_dict(row)
            logger.info("Completed task: %s", result["title"])
            return result

        except sqlite3.Error as e:
            logger.error("Failed to complete task %s: %s", task_id, e)
            return {"error": f"Update failure: {e}"}

    async def get_overdue(self) -> list[dict]:
        """Return pending tasks past their due date.

        Used by the proactive loop to surface overdue work.
        """
        try:
            today = datetime.now().date().isoformat()

            conn = self._get_conn()
            rows = conn.execute(
                """SELECT * FROM tasks
                   WHERE status = 'pending'
                   AND due_date IS NOT NULL
                   AND due_date < ?
                   ORDER BY due_date ASC""",
                (today,),
            ).fetchall()
            conn.close()

            results = [self._row_to_dict(row) for row in rows]
            if results:
                logger.info("Overdue tasks: %d", len(results))
            return results

        except sqlite3.Error as e:
            logger.error("Failed to get overdue tasks: %s", e)
            return []

    async def get_due_today(self) -> list[dict]:
        """Return pending tasks due today."""
        try:
            today = datetime.now().date().isoformat()

            conn = self._get_conn()
            rows = conn.execute(
                """SELECT * FROM tasks
                   WHERE status = 'pending'
                   AND due_date = ?
                   ORDER BY priority DESC""",
                (today,),
            ).fetchall()
            conn.close()

            return [self._row_to_dict(row) for row in rows]

        except sqlite3.Error as e:
            logger.error("Failed to get tasks due today: %s", e)
            return []
