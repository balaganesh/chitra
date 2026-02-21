"""
Context assembly for LLM calls.

Before every LLM call, assembles:
- Memory context block (user preferences, facts, relationships)
- System state snapshot (time, date, battery)
- Upcoming calendar events and active reminders
- Conversation history (last N turns)
"""

import logging

logger = logging.getLogger(__name__)


class ContextAssembler:
    """Builds the full context payload injected into every LLM call."""

    def __init__(self, memory, system_state, calendar, reminders):
        self.memory = memory
        self.system_state = system_state
        self.calendar = calendar
        self.reminders = reminders

    async def assemble(self, conversation_history: list) -> dict:
        """Assemble complete context for an LLM call.

        Returns a dict with:
            - system_prompt: str (identity + context block)
            - conversation_history: list of recent turns
        """
        raise NotImplementedError
