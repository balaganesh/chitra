"""
Proactive loop — background task that ticks on a configurable interval.

On every tick:
1. Check triggered reminders (Reminders.get_fired)
2. Check upcoming calendar events (Calendar.get_upcoming)
3. Check neglected contacts (Contacts.get_neglected)
4. Check overdue tasks (Tasks.get_overdue)
5. Lightweight LLM call — is there anything worth surfacing?
6. If yes, formulate message and speak/display
7. If no, sleep until next tick

Never interrupts an active conversation (checks is_user_active flag).
"""

import asyncio
import logging
import os

logger = logging.getLogger(__name__)


class ProactiveLoop:
    """Background loop that surfaces relevant information unprompted."""

    def __init__(self, core):
        self.core = core
        self.interval = int(os.environ.get("CHITRA_PROACTIVE_INTERVAL", "60"))

    async def run(self):
        """Run the proactive loop indefinitely."""
        raise NotImplementedError

    async def tick(self):
        """Single proactive tick — gather context, decide whether to speak."""
        raise NotImplementedError
