"""
AI Orchestration Core — the primary process of Chitra.

Boots on startup, never exits. Handles:
1. Input handling — receives user text from Voice I/O
2. Context assembly — assembles Memory + System State + history before every LLM call
3. LLM reasoning — sends context to local LLM, parses structured JSON response
4. Action execution — dispatches to capability modules based on LLM decisions

Also runs the proactive background loop.
"""

import asyncio
import logging
import os

logger = logging.getLogger(__name__)


class OrchestrationCore:
    """Primary Chitra process. Orchestrates all capabilities through the LLM."""

    def __init__(self):
        self.is_user_active = False
        self.conversation_history = []
        self.max_history_turns = int(os.environ.get("CHITRA_HISTORY_TURNS", "10"))

    async def run(self):
        """Main entry point. Initialize capabilities, run onboarding if needed, start loops."""
        raise NotImplementedError("Orchestration Core not yet implemented")

    async def handle_input(self, user_text: str) -> str:
        """Process user input through the full pipeline: context → LLM → action → response."""
        raise NotImplementedError

    async def execute_action(self, action: dict) -> dict:
        """Dispatch an action to the appropriate capability module."""
        raise NotImplementedError

    async def store_memories(self, memory_entries: list):
        """Store new memory entries from the LLM response."""
        raise NotImplementedError
