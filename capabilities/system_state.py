"""
System State capability.

Always-available device and environment context.
Injected into every LLM call alongside Memory.

Actions:
    get() — return current system state snapshot
"""

import logging

logger = logging.getLogger(__name__)


class SystemState:
    """Provides current device and environment context."""

    async def get(self) -> dict:
        """Return current system state snapshot.

        Returns:
            {
                "datetime": str,
                "day_of_week": str,
                "battery_percent": int,
                "time_of_day": "morning" | "afternoon" | "evening" | "night"
            }
        """
        raise NotImplementedError
