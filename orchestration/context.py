"""
Context assembly for LLM calls.

Before every LLM call, assembles:
- Chitra identity and response format instructions
- Memory context block (user preferences, facts, relationships)
- System state snapshot (time, date, battery)
- Upcoming calendar events and active reminders
- Conversation history (last N turns)

The assembled system prompt is what makes the LLM "know" the user on every call.
"""

import logging

from llm.prompts import CAPABILITY_CATALOG, SYSTEM_IDENTITY, RESPONSE_FORMAT_INSTRUCTION

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

        Gathers data from Memory, System State, Calendar, and Reminders,
        then constructs the full system prompt.

        Args:
            conversation_history: list of {"role": "user"|"assistant", "content": str}

        Returns:
            {
                "system_prompt": str,
                "conversation_history": list
            }
        """
        try:
            # Gather context from all capabilities concurrently
            memory_ctx = await self.memory.get_context()
            system_state = await self.system_state.get()
            upcoming_events = await self.calendar.get_upcoming(hours_ahead=1)
            upcoming_reminders = await self.reminders.list_upcoming(hours_ahead=1)

            # Build context sections
            sections = [SYSTEM_IDENTITY]

            # Memory context block
            memory_block = memory_ctx.get("context_block", "")
            if memory_block:
                sections.append(memory_block)

            # System state
            state_block = self._format_system_state(system_state)
            if state_block:
                sections.append(state_block)

            # Upcoming events
            events_block = self._format_upcoming_events(upcoming_events)
            if events_block:
                sections.append(events_block)

            # Upcoming reminders
            reminders_block = self._format_upcoming_reminders(upcoming_reminders)
            if reminders_block:
                sections.append(reminders_block)

            # Capability catalog — tells the LLM exactly what actions exist
            sections.append(CAPABILITY_CATALOG)

            # Response format instruction — always last in system prompt
            sections.append(RESPONSE_FORMAT_INSTRUCTION)

            system_prompt = "\n\n".join(sections)

            return {
                "system_prompt": system_prompt,
                "conversation_history": conversation_history,
            }

        except Exception as e:
            logger.error("Context assembly failed: %s", e)
            # Minimal fallback — identity + catalog + format, so the LLM can still respond
            return {
                "system_prompt": f"{SYSTEM_IDENTITY}\n\n{CAPABILITY_CATALOG}\n\n{RESPONSE_FORMAT_INSTRUCTION}",
                "conversation_history": conversation_history,
            }

    def _format_system_state(self, state: dict) -> str:
        """Format system state snapshot as natural language."""
        if "error" in state:
            return ""

        dt = state.get("datetime", "unknown")
        day = state.get("day_of_week", "unknown")
        time_of_day = state.get("time_of_day", "unknown")
        battery = state.get("battery_percent", -1)

        lines = [f"Current state: It is {time_of_day}, {day}. Time: {dt[:16]}."]
        if battery >= 0:
            lines.append(f"Battery: {battery}%.")

        return " ".join(lines)

    def _format_upcoming_events(self, events: list[dict]) -> str:
        """Format upcoming calendar events as natural language."""
        if not events:
            return ""

        lines = ["Upcoming events:"]
        for event in events:
            title = event.get("title", "untitled")
            time = event.get("time", "")
            duration = event.get("duration_minutes", 60)
            participants = event.get("participants", [])

            entry = f"- {title} at {time} ({duration} min)"
            if participants:
                entry += f" with {', '.join(participants)}"
            lines.append(entry)

        return "\n".join(lines)

    def _format_upcoming_reminders(self, reminders: list[dict]) -> str:
        """Format upcoming reminders as natural language."""
        if not reminders:
            return ""

        lines = ["Upcoming reminders:"]
        for reminder in reminders:
            text = reminder.get("text", "")
            trigger_at = reminder.get("trigger_at", "")
            lines.append(f"- {text} (at {trigger_at[:16]})")

        return "\n".join(lines)
